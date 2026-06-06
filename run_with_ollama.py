#!/usr/bin/env python3
"""run_with_ollama.py — Cross-platform Ollama orchestrator.

Checks if Ollama is running on OLLAMA_URL. If not, starts 'ollama serve'
in the background, waits for it to become ready, pre-warms the qwen3-vl model,
runs the video_pipeline.py program with the given arguments, and stops the
background Ollama process it started (if any).
"""
import os
import sys
import time
import subprocess
import urllib.request
import urllib.error
import json

from video_pipeline_core.platform_tools import resolve_python, resolve_ollama_url, resolve_ollama

def is_ollama_running(url):
    try:
        req = urllib.request.Request(f"{url}/api/tags")
        with urllib.request.urlopen(req, timeout=2) as r:
            return r.status == 200
    except Exception:
        return False

def warm_model(url, model="qwen3-vl:4b-instruct"):
    print(f"[wrapper] warming up {model}...")
    body = json.dumps({
        "model": model,
        "prompt": "hi",
        "stream": False,
        "keep_alive": "30m",
        "options": {"num_predict": 5}
    }).encode()
    try:
        req = urllib.request.Request(
            f"{url}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            r.read()
    except Exception as e:
        print(f"[wrapper] warm up warning: {e}")

def main():
    url = resolve_ollama_url()
    started_ollama = False
    proc = None

    if not is_ollama_running(url):
        print("[wrapper] ollama is not running. Starting ollama serve...")
        try:
            ollama_exe = resolve_ollama()
        except Exception as e:
            print(f"[wrapper] error resolving ollama executable: {e}")
            ollama_exe = "ollama"
            if sys.platform == "win32":
                local_appdata = os.environ.get("LOCALAPPDATA", "")
                if local_appdata:
                    candidate = os.path.join(local_appdata, "Programs", "Ollama", "ollama.exe")
                    if os.path.isfile(candidate):
                        ollama_exe = candidate
        
        print(f"[wrapper] using ollama executable: {ollama_exe}")
        
        # Start ollama serve in background
        if sys.platform == "win32":
            # On Windows, use creationflags to run in background without creating a console window
            proc = subprocess.Popen(
                [ollama_exe, "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
            )
        else:
            proc = subprocess.Popen(
                [ollama_exe, "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        started_ollama = True

        # Wait for ollama to be ready
        ready = False
        for i in range(1, 11):
            time.sleep(1)
            if is_ollama_running(url):
                print(f"[wrapper] ollama ready after {i}s")
                ready = True
                break
        if not ready:
            print("[wrapper] Warning: ollama serve started but API not responding.")
    else:
        print("[wrapper] ollama is already running.")

    # Warm model
    warm_model(url)

    # Run video_pipeline.py
    here = os.path.dirname(os.path.abspath(__file__))
    pipeline_py = os.path.join(here, "video_pipeline.py")
    python_exe = resolve_python()
    
    cmd = [python_exe, pipeline_py] + sys.argv[1:]
    print(f"[wrapper] running pipeline: {' '.join(cmd)}")
    
    pipeline_exit = 0
    try:
        pipeline_exit = subprocess.run(cmd).returncode
    except KeyboardInterrupt:
        pipeline_exit = 130
        print("[wrapper] interrupted by user")
    
    # Cleanup
    if started_ollama and proc:
        print("[wrapper] stopping ollama...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

    sys.exit(pipeline_exit)

if __name__ == "__main__":
    main()
