#!/usr/bin/env python3
"""Source-version-pinned integration smoke tests for Redis 7.2.4.

Only runs isolated localhost Redis instances in temporary directories.
No dependencies beyond Python standard library and built Redis executables.
"""
from __future__ import annotations

import binascii
import contextlib
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time


BIN = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else None
if BIN is None:
    raise SystemExit("usage: python scripts/redis_724_smoke.py /path/to/redis-724/src")
SERVER, CLI, CHECK_RDB = (BIN / n for n in ("redis-server", "redis-cli", "redis-check-rdb"))
for executable in (SERVER, CLI, CHECK_RDB):
    if not executable.is_file():
        raise SystemExit(f"missing Redis 7.2.4 executable: {executable}")


def choose_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def redis(port: int, *args: str, timeout: float = 10) -> str:
    cmd = [str(CLI), "--raw", "-h", "127.0.0.1", "-p", str(port), *map(str, args)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise AssertionError(f"redis-cli failed {cmd}: {result.stderr} {result.stdout}")
    if result.stdout.startswith("ERR ") or result.stdout.startswith("NOAUTH "):
        raise AssertionError(f"unexpected Redis error for {args}: {result.stdout}")
    return result.stdout.strip()


def info(port: int, section: str) -> dict[str, str]:
    data = {}
    for line in redis(port, "INFO", section).splitlines():
        if ":" in line and not line.startswith("#"):
            k, v = line.split(":", 1)
            data[k] = v.strip()
    return data


def wait_for(label: str, check, seconds=25):
    until = time.monotonic() + seconds
    last = None
    while time.monotonic() < until:
        try:
            last = check()
            if last:
                return
        except (OSError, subprocess.TimeoutExpired, AssertionError) as exc:
            last = str(exc)
        time.sleep(0.1)
    raise AssertionError(f"timeout waiting for {label}; last observed {last}")


def resp_send(sock, *parts: str):
    raw = f"*{len(parts)}\r\n".encode()
    for part in parts:
        b = part.encode()
        raw += f"${len(b)}\r\n".encode() + b + b"\r\n"
    sock.sendall(raw)


def no_live_data(label: str, proc: subprocess.Popen, log: Path):
    if proc.poll() is not None:
        output = log.read_text(errors="replace")[-3500:] if log.exists() else "(no log)"
        raise AssertionError(f"{label} exited early with code {proc.returncode}: {output}")


with tempfile.TemporaryDirectory(prefix="redis724-smoke-") as root:
    base = Path(root)
    processes = []

    def start(label: str, extra=(), port=None) -> int:
        port = port or choose_port()
        directory = base / label
        directory.mkdir()
        logfile = directory / "server.log"
        argv = [str(SERVER), "--bind", "127.0.0.1", "--port", str(port),
                "--dir", str(directory), "--logfile", str(logfile),
                "--save", "", "--appendonly", "no", "--daemonize", "no", *extra]
        proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        processes.append((label, proc, logfile))
        wait_for(label + " PING", lambda: redis(port, "PING") == "PONG")
        no_live_data(label, proc, logfile)
        return port

    try:
        master = start("master")
        version = info(master, "server")["redis_version"]
        assert version == "7.2.4", f"runtime version mismatch: {version}"
        print(f"PASS pinned runtime version {version}")

        # Ch 23: Slowlog uses command execution duration, not network RTT.
        assert redis(master, "CONFIG", "SET", "slowlog-log-slower-than", "0") == "OK"
        assert redis(master, "CONFIG", "SET", "slowlog-max-len", "128") == "OK"
        assert redis(master, "SET", "lab:metrics", "ok") == "OK"
        assert redis(master, "GET", "lab:metrics") == "ok"
        assert int(redis(master, "SLOWLOG", "LEN")) >= 2
        assert "total_commands_processed" in info(master, "stats")
        assert redis(master, "CONFIG", "SET", "latency-monitor-threshold", "1") == "OK"
        redis(master, "LATENCY", "LATEST")  # may be empty: no samples over threshold
        print("PASS slowlog, INFO counters, latency monitor configuration")

        # Ch 24: HLEN is count, MEMORY USAGE bytes, UNLINK removes key.
        for i in range(220):
            redis(master, "HSET", "lab:large", f"f{i}", f"value{i}")
        assert int(redis(master, "HLEN", "lab:large")) == 220
        mem = int(redis(master, "MEMORY", "USAGE", "lab:large", "SAMPLES", "0"))
        assert mem > 0
        assert redis(master, "UNLINK", "lab:large") == "1"
        assert redis(master, "EXISTS", "lab:large") == "0"
        print(f"PASS MEMORY USAGE / UNLINK semantics ({mem} estimated bytes)")

        # Ch 21: start replica and use same TCP client for SET and WAIT.
        replica = start("replica", extra=("--replicaof", "127.0.0.1", str(master)))
        wait_for("replica online", lambda: info(replica, "replication").get("master_link_status") == "up")
        with socket.create_connection(("127.0.0.1", master), timeout=5) as sock:
            sock.settimeout(12)
            reader = sock.makefile("rb")
            resp_send(sock, "SET", "lab:replication", "synchronized")
            assert reader.readline().strip() == b"+OK"
            resp_send(sock, "WAIT", "1", "10000")
            reply = reader.readline().strip()
            assert reply.startswith(b":") and int(reply[1:]) >= 1, reply
        wait_for("replicated key", lambda: redis(replica, "GET", "lab:replication") == "synchronized")
        print("PASS replica receives write and REPLCONF ACK satisfies WAIT 1")

        # Ch 22: one Sentinel monitoring a master with quorum two cannot authorize failover.
        sentinel_port = choose_port()
        sen_dir = base / "sentinel"
        sen_dir.mkdir()
        sen_cfg = sen_dir / "sentinel.conf"
        sen_cfg.write_text(
            f"port {sentinel_port}\nbind 127.0.0.1\nprotected-mode yes\n"
            f"dir {sen_dir}\nlogfile {sen_dir / 'sentinel.log'}\n"
            f"sentinel monitor demo 127.0.0.1 {master} 2\n"
            "sentinel down-after-milliseconds demo 5000\n"
        )
        proc = subprocess.Popen([str(SERVER), str(sen_cfg), "--sentinel"],
                                stdin=subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        processes.append(("sentinel", proc, sen_dir / "sentinel.log"))
        wait_for("sentinel PING", lambda: redis(sentinel_port, "PING") == "PONG")
        output = redis(sentinel_port, "SENTINEL", "CKQUORUM", "demo")
        assert "NOQUORUM" in output.upper(), output
        print("PASS Sentinel quorum=2 cannot be met by one Sentinel")

        # Ch 22: hash-tag mapping matches Redis 7.2 keyHashSlot()'s CRC16 masking.
        def slot(k: bytes):
            a = k.find(b"{")
            b = k.find(b"}", a+1) if a != -1 else -1
            tag = k[a+1:b] if a != -1 and b > a+1 else k
            return binascii.crc_hqx(tag, 0) & 0x3FFF
        assert slot(b"{user:7}:cart") == slot(b"{user:7}:profile")
        assert 0 <= slot(b"unbraced") < 16384
        print("PASS hash-tag CRC16/16384 slot invariant")

        # Ch 17/18 cross-batch verification: RDB and Multi-Part AOF.
        assert redis(master, "BGSAVE").startswith("Background")
        wait_for("BGSAVE completion", lambda: info(master, "persistence").get("rdb_last_bgsave_status") == "ok"
                 and info(master, "persistence").get("rdb_bgsave_in_progress") == "0"
                 and (base / "master" / "dump.rdb").exists())
        rdb = base / "master" / "dump.rdb"
        assert rdb.open("rb").read(9) == b"REDIS0011"
        checked = subprocess.run([str(CHECK_RDB), str(rdb)], capture_output=True, text=True, timeout=20)
        assert checked.returncode == 0, checked.stdout + checked.stderr
        print("PASS Redis 7.2.4 RDB v11 snapshot and redis-check-rdb")

        aof = start("aof", extra=("--appendonly", "yes"))
        assert redis(aof, "SET", "lab:aof", "multi-part") == "OK"
        out = redis(aof, "BGREWRITEAOF")
        assert "Background" in out, out
        manifest = base / "aof" / "appendonlydir" / "appendonly.aof.manifest"
        wait_for("AOF rewrite manifest", lambda: manifest.exists()
                 and "type b" in manifest.read_text()
                 and "type i" in manifest.read_text()
                 and info(aof, "persistence").get("aof_rewrite_in_progress") == "0"
                 and info(aof, "persistence").get("aof_last_bgrewrite_status") == "ok", seconds=45)
        print("PASS Redis 7.2.4 Multi-Part AOF BASE/INCR manifest")

        print("ALL Redis 7.2.4 integration smoke checks passed")
    finally:
        for label, proc, logfile in reversed(processes):
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=3)
