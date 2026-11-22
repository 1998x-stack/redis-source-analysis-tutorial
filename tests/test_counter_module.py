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
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def cli(port_number, *args, allow_shutdown=False):
    result = subprocess.run(
        [str(CLI), "--raw", "-h", "127.0.0.1", "-p", str(port_number), *map(str, args)],
        text=True,
        capture_output=True,
        timeout=15,
    )
    if result.returncode and not allow_shutdown:
        raise AssertionError(f"redis-cli {args} failed: {result.stdout} {result.stderr}")
    return result.stdout.strip()


def wait_until(fn, seconds=20):
    deadline = time.time() + seconds
    last = None
    while time.time() < deadline:
        try:
            last = fn()
            if last:
                return last
        except (OSError, subprocess.TimeoutExpired, AssertionError) as exc:
            last = str(exc)
        time.sleep(0.05)
    raise AssertionError(f"timeout; last={last}")


def wait_for_aof_ready(port_number, directory: Path):
    manifest = directory / "appendonlydir" / "appendonly.aof.manifest"

    def ready():
        if not manifest.exists():
            return None
        info = cli(port_number, "INFO", "persistence")
        if (
            "aof_rewrite_in_progress:0" in info
            and "aof_rewrite_scheduled:0" in info
            and "aof_last_bgrewrite_status:ok" in info
        ):
            return manifest.read_text(encoding="utf-8")
        return None

    return wait_until(ready, 40)


def encode(*args):
    values = [arg if isinstance(arg, bytes) else str(arg).encode() for arg in args]
    frame = b"*" + str(len(values)).encode() + b"\r\n"
    for value in values:
        frame += b"$" + str(len(value)).encode() + b"\r\n" + value + b"\r\n"
    return frame


def read_line(stream):
    line = stream.readline()
    if not line.endswith(b"\r\n"):
        raise AssertionError(f"invalid RESP line: {line!r}")
    return line[:-2]


def read_reply(stream):
    prefix = stream.read(1)
    if prefix == b"+":
        return ("simple", read_line(stream))
    if prefix == b"-":
        return ("error", read_line(stream))
    if prefix == b":":
        return ("integer", int(read_line(stream)))
    if prefix == b"$":
        length = int(read_line(stream))
        if length == -1:
            return ("bulk", None)
        value = stream.read(length)
        if stream.read(2) != b"\r\n":
            raise AssertionError("bulk string missing CRLF")
        return ("bulk", value)
    if prefix == b"*":
        count = int(read_line(stream))
        if count == -1:
            return ("null-array", None)
        return ("array", [read_reply(stream) for _ in range(count)])
    raise AssertionError(f"unsupported RESP prefix {prefix!r}")


def wait_for_server(proc, log, port_number, seconds=20):
    deadline = time.time() + seconds
    last = None
    while time.time() < deadline:
        if proc.poll() is not None:
            log.flush()
            log_path = Path(log.name)
            details = log_path.read_text(encoding="utf-8", errors="replace")
            raise AssertionError(
                f"redis-server exited with {proc.returncode} before PING became ready:\n{details}"
            )
        try:
            if cli(port_number, "PING") == "PONG":
                return
        except (OSError, subprocess.TimeoutExpired, AssertionError) as exc:
            last = str(exc)
        time.sleep(0.05)
    log.flush()
    details = Path(log.name).read_text(encoding="utf-8", errors="replace")
    raise AssertionError(f"redis-server readiness timeout; last={last}\n{details}")


def start(directory: Path, port_number: int, aof: bool, rdb_preamble=True):
    directory.mkdir(parents=True, exist_ok=True)
    args = [
        str(SERVER),
        "--bind", "127.0.0.1",
        "--port", str(port_number),
        "--dir", str(directory),
        "--save", "",
        "--appendonly", "yes" if aof else "no",
        "--loadmodule", str(MODULE),
    ]
    if aof:
        args.extend([
            "--appendfsync", "always",
            "--aof-use-rdb-preamble", "yes" if rdb_preamble else "no",
        ])
    log = open(directory / "redis.log", "w")
    proc = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT)
    try:
        wait_for_server(proc, log, port_number)
        if aof:
            expected_preamble = "yes" if rdb_preamble else "no"
            config = cli(port_number, "CONFIG", "GET", "aof-use-rdb-preamble")
            if config.splitlines()[-1] != expected_preamble:
                raise AssertionError(f"unexpected aof-use-rdb-preamble: {config}")
            # A new appendonly directory can trigger an initial bootstrap rewrite.
            # Wait for that child before taking the manifest snapshot for our test rewrite.
            wait_for_aof_ready(port_number, directory)
    except Exception:
        proc.terminate()
        try:
            proc.wait(timeout=4)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=4)
        log.close()
        raise
    return proc, log


def stop(proc, log, port_number):
    try:
        cli(port_number, "SHUTDOWN", "NOSAVE", allow_shutdown=True)
    except Exception:
        pass
    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        proc.terminate()
        try:
            proc.wait(timeout=4)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=4)
    log.close()


def assert_watch_invalidation(port_number):
    with socket.create_connection(("127.0.0.1", port_number), timeout=3) as sock:
        stream = sock.makefile("rb")
        sock.sendall(encode("WATCH", "inventory"))
        assert read_reply(stream) == ("simple", b"OK")
        sock.sendall(encode("MULTI"))
        assert read_reply(stream) == ("simple", b"OK")
        sock.sendall(encode("GET", "inventory"))
        assert read_reply(stream) == ("simple", b"QUEUED")
        assert cli(port_number, "COUNTER.INCR", "inventory", "1") == "43"
        sock.sendall(encode("EXEC"))
        assert read_reply(stream) == ("null-array", None)
        stream.close()


def main():
    with tempfile.TemporaryDirectory(prefix="redis-module-counter-") as temp:
        root = Path(temp)

        # RDB load/save path for the custom module type.
        port_number = port()
        directory = root / "rdb"
        proc, log = start(directory, port_number, aof=False)
        assert "countermod" in cli(port_number, "MODULE", "LIST")
        assert cli(port_number, "COUNTER.SET", "inventory", "41") == "OK"
        assert cli(port_number, "COUNTER.INCR", "inventory", "1") == "42"
        assert cli(port_number, "COUNTER.GET", "inventory") == "42"
        assert cli(port_number, "SAVE") == "OK"
        stop(proc, log, port_number)

        proc, log = start(directory, port_number, aof=False)
        assert cli(port_number, "COUNTER.GET", "inventory") == "42"
        assert_watch_invalidation(port_number)
        stop(proc, log, port_number)
        print("PASS Module custom type: command registration, RDB load/save, WATCH invalidation")

        # Force an AOF BASE file (not an RDB preamble) so aof_rewrite is exercised.
        port_number = port()
        directory = root / "aof"
        proc, log = start(directory, port_number, aof=True, rdb_preamble=False)
        assert cli(port_number, "COUNTER.SET", "balance", "100") == "OK"
        assert cli(port_number, "COUNTER.INCR", "balance", "23") == "123"

        manifest = directory / "appendonlydir" / "appendonly.aof.manifest"
        before_manifest = manifest.read_text(encoding="utf-8")
        assert "type i" in before_manifest
        assert "type i" in before_manifest

        rewrite_reply = cli(port_number, "BGREWRITEAOF")
        if "started" not in rewrite_reply.lower():
            raise AssertionError(f"expected BGREWRITEAOF to start immediately, got: {rewrite_reply}")

        def rewrite_done():
            if not manifest.exists():
                return None
            current = manifest.read_text(encoding="utf-8")
            info = cli(port_number, "INFO", "persistence")
            if (
                current != before_manifest
                and "aof_rewrite_in_progress:0" in info
                and "aof_rewrite_scheduled:0" in info
                and "aof_last_bgrewrite_status:ok" in info
            ):
                return current
            return None

        manifest_text = wait_until(rewrite_done, 40)
        base_line = next(
            (line for line in manifest_text.splitlines()
             if line.startswith("file ") and ".base.aof" in line),
            None,
        )
        assert base_line, manifest_text
        base_name = base_line.split()[1]
        base_path = directory / "appendonlydir" / base_name
        assert b"counter.set" in base_path.read_bytes().lower(), (
            "AOF BASE did not contain the custom type rewrite command"
        )

        stop(proc, log, port_number)
        proc, log = start(directory, port_number, aof=True, rdb_preamble=False)
        assert cli(port_number, "COUNTER.GET", "balance") == "123"
        stop(proc, log, port_number)
        print("PASS Module custom type: AOF rewrite callback emits replayable counter.set state")


if __name__ == "__main__":
    main()
