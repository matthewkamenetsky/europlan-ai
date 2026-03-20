import json
import requests
from typing import Generator

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:3b"

def stream_llm(prompt: str) -> Generator[str, None, None]:
    with requests.post(OLLAMA_URL, json={
        "model": MODEL,
        "prompt": prompt,
        "stream": True
    }, stream=True) as response:
        for line in response.iter_lines():
            if line:
                chunk = json.loads(line)
                token = chunk.get("response", "")
                if token:
                    yield token
                if chunk.get("done", False):
                    break