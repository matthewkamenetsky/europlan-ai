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