#!/usr/bin/env python3
from __future__ import annotations
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REDIS_SRC = Path(sys.argv[1]).resolve()
MODULE = Path(sys.argv[2]).resolve()
SERVER = REDIS_SRC / "redis-server"
CLI = REDIS_SRC / "redis-cli"

def port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

def cli(p, *args, allow_shutdown=False):
    r = subprocess.run([str(CLI), "--raw", "-h", "127.0.0.1", "-p", str(p), *map(str, args)],
                       text=True, capture_output=True, timeout=15)
    if r.returncode and not allow_shutdown:
        raise AssertionError(f"redis-cli {args} failed: {r.stdout} {r.stderr}")
    return r.stdout.strip()

def wait_until(fn, seconds=20):
    end = time.time() + seconds
    last = None
    while time.time() < end:
        try:
            last = fn()
            if last:
                return last
        except (OSError, subprocess.TimeoutExpired):
            pass
        time.sleep(0.05)
    raise AssertionError(f"timeout; last={last}")

def start(directory: Path, p: int, aof: bool):
    directory.mkdir(parents=True, exist_ok=True)
    args = [str(SERVER), "--bind", "127.0.0.1", "--port", str(p),
            "--dir", str(directory), "--save", "", "--appendonly", "yes" if aof else "no",
            "--appendfsync", "always", "--loadmodule", str(MODULE)]
    log = open(directory / "redis.log", "w")
    proc = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT)
    wait_until(lambda: cli(p, "PING") == "PONG")
    return proc, log

def stop(proc, log, p):
    try:
        cli(p, "SHUTDOWN", "NOSAVE", allow_shutdown=True)
    except Exception:
        pass
    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        proc.terminate()
        proc.wait(timeout=4)
    log.close()

def main():
    with tempfile.TemporaryDirectory(prefix="redis-module-counter-") as temp:
        root = Path(temp)

        p = port()
        directory = root / "rdb"
        proc, log = start(directory, p, False)
        assert "countermod" in cli(p, "MODULE", "LIST")
        assert cli(p, "COUNTER.SET", "inventory", "41") == "OK"
        assert cli(p, "COUNTER.INCR", "inventory", "1") == "42"
        assert cli(p, "COUNTER.GET", "inventory") == "42"
        assert cli(p, "SAVE") == "OK"
        stop(proc, log, p)
        proc, log = start(directory, p, False)
        assert cli(p, "COUNTER.GET", "inventory") == "42"
        stop(proc, log, p)
        print("PASS Module custom type: command registration, RDB save/load, modified-key signalling")

        p = port()
        directory = root / "aof"
        proc, log = start(directory, p, True)
        assert cli(p, "COUNTER.SET", "balance", "100") == "OK"
        assert cli(p, "COUNTER.INCR", "balance", "23") == "123"
        cli(p, "BGREWRITEAOF")
        manifest = directory / "appendonlydir" / "appendonly.aof.manifest"
        def rewrite_done():
            info = cli(p, "INFO", "persistence")
            return manifest.exists() and "aof_rewrite_in_progress:0" in info and "aof_last_bgrewrite_status:ok" in info
        wait_until(rewrite_done, 40)
        manifest_text = manifest.read_text()
        assert "type b" in manifest_text
        stop(proc, log, p)
        proc, log = start(directory, p, True)
        assert cli(p, "COUNTER.GET", "balance") == "123"
        stop(proc, log, p)
        print("PASS Module custom type: AOF rewrite emits replayable counter.set state")

if __name__ == "__main__":
    main()
