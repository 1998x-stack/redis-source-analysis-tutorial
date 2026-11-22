#!/usr/bin/env python3
from __future__ import annotations
import socket
import subprocess
import sys
import time

BIN = sys.argv[1]

def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

def encode(*args: bytes) -> bytes:
    out = b"*" + str(len(args)).encode() + b"\r\n"
    for value in args:
        out += b"$" + str(len(value)).encode() + b"\r\n" + value + b"\r\n"
    return out

def read_line(f):
    line = f.readline()
    if not line.endswith(b"\r\n"):
        raise AssertionError(f"invalid RESP line: {line!r}")
    return line[:-2]

def read_reply(f):
    prefix = f.read(1)
    if prefix == b"+":
        return ("simple", read_line(f))
    if prefix == b"-":
        return ("error", read_line(f))
    if prefix == b":":
        return ("integer", int(read_line(f)))
    if prefix == b"$":
        n = int(read_line(f))
        if n == -1:
            return ("bulk", None)
        value = f.read(n)
        if f.read(2) != b"\r\n":
            raise AssertionError("bulk string missing CRLF")
        return ("bulk", value)
    raise AssertionError(f"unsupported reply prefix {prefix!r}")

def main():
    port = free_port()
    proc = subprocess.Popen([BIN, str(port)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        deadline = time.time() + 5
        while time.time() < deadline:
            try:
                s = socket.create_connection(("127.0.0.1", port), timeout=0.2)
                break
            except OSError:
                if proc.poll() is not None:
                    raise AssertionError(proc.stderr.read().decode(errors="replace"))
                time.sleep(0.03)
        else:
            raise AssertionError("server did not start")
        s.close()

        with socket.create_connection(("127.0.0.1", port), timeout=2) as sock:
            f = sock.makefile("rb")
            sock.sendall(encode(b"PING"))
            assert read_reply(f) == ("simple", b"PONG")
            sock.sendall(encode(b"SET", b"hello", b"world"))
            assert read_reply(f) == ("simple", b"OK")
            sock.sendall(encode(b"GET", b"hello"))
            assert read_reply(f) == ("bulk", b"world")

            key, value = b"k\x00\r\n", b"v\x00\r\n\xff"
            sock.sendall(encode(b"SET", key, value))
            assert read_reply(f) == ("simple", b"OK")
            sock.sendall(encode(b"GET", key))
            assert read_reply(f) == ("bulk", value)

            sock.sendall(encode(b"SET", b"pipe", b"1") + encode(b"GET", b"pipe") + encode(b"PING"))
            assert read_reply(f) == ("simple", b"OK")
            assert read_reply(f) == ("bulk", b"1")
            assert read_reply(f) == ("simple", b"PONG")

            frame = encode(b"SET", b"fragment", b"arrived")
            sock.sendall(frame[:5])
            time.sleep(0.03)
            sock.sendall(frame[5:13])
            time.sleep(0.03)
            sock.sendall(frame[13:])
            assert read_reply(f) == ("simple", b"OK")
            sock.sendall(encode(b"GET", b"fragment"))
            assert read_reply(f) == ("bulk", b"arrived")

            sock.sendall(encode(b"HSET", b"profile", b"name", b"Redis", b"city", b"Tokyo"))
            assert read_reply(f) == ("integer", 2)
            sock.sendall(encode(b"HGET", b"profile", b"city"))
            assert read_reply(f) == ("bulk", b"Tokyo")
            sock.sendall(encode(b"HLEN", b"profile"))
            assert read_reply(f) == ("integer", 2)
            sock.sendall(encode(b"GET", b"profile"))
            assert read_reply(f)[0] == "error"

            sock.sendall(encode(b"EXISTS", b"hello", b"missing", b"hello"))
            assert read_reply(f) == ("integer", 2)
            sock.sendall(encode(b"DEL", b"hello", b"missing"))
            assert read_reply(f) == ("integer", 1)
            sock.sendall(encode(b"GET", b"hello"))
            assert read_reply(f) == ("bulk", None)
            sock.sendall(encode(b"DBSIZE"))
            assert read_reply(f)[0] == "integer"

            sock.sendall(encode(b"QUIT"))
            assert read_reply(f) == ("simple", b"OK")

        with socket.create_connection(("127.0.0.1", port), timeout=2) as bad:
            bf = bad.makefile("rb")
            bad.sendall(b"*2\r\n$4\r\nPING\r\n$9999999\r\n")
            kind, message = read_reply(bf)
            assert kind == "error" and b"Protocol error" in message
        print("PASS Mini-Redis: RESP framing, pipelining, binary data, hash/string commands, limits")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)

if __name__ == "__main__":
    main()
