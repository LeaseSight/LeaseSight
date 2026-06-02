"""
Cross-platform helper (Windows-focused) to free port 8080 by identifying
the owning PID and terminating it. Intended to be run before launching uvicorn.

Usage:
    python scratch/clear_backend.py
    python scratch/clear_backend.py --aggressive  # extra python.exe sweep

This script uses `netstat -ano` output on Windows to find owners of :8080.
If a PID is found it will call `taskkill /F /PID <pid>`.
"""
import subprocess
import sys
import re
from argparse import ArgumentParser

def find_pids_for_port(port: int = 8080):
    try:
        out = subprocess.check_output(["netstat", "-ano", "-p", "tcp"], text=True, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"[clear_backend] netstat failed: {e}")
        return []
    pids = set()
    for line in out.splitlines():
        if f":{port} " in line or f":{port}\r" in line or f":{port}\n" in line:
            m = re.search(r"LISTENING\s+(\d+)$", line)
            if m:
                pids.add(int(m.group(1)))
            else:
                # Fallback: grab last numeric token
                toks = re.findall(r"(\d+)", line)
                if toks:
                    pids.add(int(toks[-1]))
    return list(pids)

def kill_pid(pid: int):
    try:
        print(f"[clear_backend] Killing PID {pid}...")
        subprocess.check_call(["taskkill", "/F", "/PID", str(pid)])
        print(f"[clear_backend] PID {pid} terminated.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[clear_backend] taskkill failed for PID {pid}: {e}")
        return False

def python_sweep():
    # Aggressive: try to kill python.exe processes that likely belong to old uvicorn runs.
    # Do not kill every python.exe; tasklist rows must include a backend-specific marker.
    try:
        out = subprocess.check_output(["tasklist", "/FI", "IMAGENAME eq python.exe", "/V"], text=True, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"[clear_backend] tasklist failed: {e}")
        return
    for line in out.splitlines():
        lowered = line.lower()
        if "uvicorn" in lowered or "api.main" in lowered or ":8080" in lowered:
            m = re.search(r"\s(\d+)\s", line)
            if m:
                pid = int(m.group(1))
                kill_pid(pid)

def main():
    parser = ArgumentParser()
    parser.add_argument("--aggressive", action="store_true", help="Also sweep python.exe processes that look like uvicorn")
    args = parser.parse_args()

    pids = find_pids_for_port(8080)
    if not pids:
        print("[clear_backend] No listeners found on port 8080.")
    else:
        for pid in pids:
            kill_pid(pid)

    if args.aggressive:
        print("[clear_backend] Aggressive mode: sweeping python.exe processes...")
        python_sweep()

if __name__ == '__main__':
    main()
