import os
from cerebras.cloud.sdk import Cerebras
from dotenv import load_dotenv

load_dotenv()

client = Cerebras(api_key=os.environ.get("CEREBRAS_API_KEY"))

MODEL = "qwen-3-235b-a22b-instruct-2507"
FALLBACK_MODEL = "llama3.1-8b"

def stream_completion(prompt):
    if isinstance(prompt, str):
        messages = [{"role": "user", "content": prompt}]
    else:
        messages = prompt

    stream = client.chat.completions.create(
        messages=messages,
        model=MODEL,
        max_completion_tokens=4096,
        stream=True
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


def tool_completion(messages: list[dict], tools: list[dict], dispatcher) -> str:
    """
    Agentic tool-calling loop for Cerebras native function calling.

    Sends messages + tool schemas to the LLM. If the LLM requests tool calls,
    dispatches each via the provided dispatcher callable, appends results to the
    messages array, and loops until the LLM returns a plain text response.

    Note: Cerebras does not support streaming during tool-call rounds.
    The final plain text response is returned as a complete string.

    Args:
        messages:   Initial messages array [{role, content}, ...]
        tools:      List of tool schemas in Cerebras/OpenAI function-calling format
        dispatcher: Callable(tool_name: str, args: dict) -> str (JSON result string)

    Returns:
        The final plain text response from the LLM after all tool rounds complete.
    """
    current_messages = list(messages)

    while True:
        response = client.chat.completions.create(
            messages=current_messages,
            model=MODEL,
            max_completion_tokens=4096,
            tools=tools,
            stream=False,
        )

        choice = response.choices[0]
        message = choice.message

        # Always append the assistant turn (may contain tool_calls)
        assistant_turn = {"role": "assistant", "content": message.content or ""}
        if hasattr(message, "tool_calls") and message.tool_calls:
            assistant_turn["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in message.tool_calls
            ]
        current_messages.append(assistant_turn)

        # If no tool calls, we have the final answer
        if not (hasattr(message, "tool_calls") and message.tool_calls):
            return message.content or ""

        # Dispatch each tool call and append results
        import json
        for tc in message.tool_calls:
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}

            result = dispatcher(tc.function.name, args)

            current_messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })