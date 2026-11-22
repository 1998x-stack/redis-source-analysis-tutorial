# Mini-Redis (Linux / RESP2 teaching server)

A deliberately small, tested C server that demonstrates the mechanics of a Redis-like request path:

1. nonblocking TCP accept on loopback;
2. one epoll event loop;
3. incremental RESP2 array-of-bulk-strings parser;
4. command dispatch and a dynamically resized hash table;
5. binary-safe String and Hash values;
6. buffered replies with partial-write handling.

## Build and test

    make
    make test
    ./mini-redis 6380
    redis-cli -p 6380 PING
    redis-cli -p 6380 SET hello world
    redis-cli -p 6380 GET hello

The integration test covers fragmented TCP frames, pipelining, embedded NUL/CRLF bytes, String/Hash commands, wrong-type errors, deletion, and invalid-frame rejection.

## Explicit scope

This is NOT a Redis clone and is not production software. It implements only PING, ECHO, SET, GET, HSET, HGET, HLEN, DEL, EXISTS, DBSIZE, and QUIT. It supports only RESP2 command arrays whose elements are bulk strings. It has no authentication/ACL, TLS, inline protocol, RESP3, transactions, Lua/Functions, modules, Pub/Sub, Streams, expiration, eviction, persistence, replication, Cluster, Sentinel, command table metadata, I/O threads, or crash-recovery guarantees. It binds only to 127.0.0.1.

The fixed-size request/response limits are intentional safety boundaries. The hash function and table are pedagogical and do not reproduce Redis 7.2.4 dict (which uses SipHash and incremental rehash). The event loop resembles Redis's readiness-driven design, but this program is not a drop-in implementation of ae.c.
