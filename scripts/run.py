import subprocess
import sys
import time
import os

def run(cmd, **kwargs):
    print(f">> {cmd}")
    return subprocess.Popen(cmd, shell=True, **kwargs)

def main():
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(ROOT)

    subprocess.run("ollama pull qwen2.5:3b", shell=True)

    backend = run(
        f"{sys.executable} -m uvicorn main:app --reload",
        cwd=os.path.join(ROOT, "backend")
    )
    time.sleep(2)

    frontend = run("npm start", cwd=os.path.join(ROOT, "frontend"))

    print("\nAll services started. Press Ctrl+C to stop.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        for p in [backend, frontend]:
            p.terminate()

if __name__ == "__main__":
    main()