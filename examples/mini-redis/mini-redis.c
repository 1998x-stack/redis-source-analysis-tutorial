#define _GNU_SOURCE
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <netinet/in.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <strings.h>
#include <string.h>
#include <sys/epoll.h>
#include <sys/socket.h>
#include <unistd.h>

#define MAX_EVENTS 128
#define MAX_ARGS 64
#define MAX_BULK (1024u * 1024u)
#define MAX_INPUT (4u * 1024u * 1024u)
#define MAX_OUTPUT (8u * 1024u * 1024u)
#define INITIAL_BUCKETS 1024u
#define READ_CHUNK 16384u

typedef struct { unsigned char *data; size_t len; } blob;
typedef struct hash_field {
    blob field, value;
    struct hash_field *next;
} hash_field;
typedef enum { VALUE_STRING, VALUE_HASH } value_type;
typedef struct kv_entry {
    blob key;
    value_type type;
    union { blob string; hash_field *fields; } value;
    struct kv_entry *next;
} kv_entry;
typedef struct {
    kv_entry **buckets;
    size_t bucket_count, size;
} store;
typedef struct {
    const unsigned char *data;
    size_t len;
} arg;
typedef struct client {
    int fd;
    unsigned char *input;
    size_t input_len, input_cap;
    unsigned char *output;
    size_t output_len, output_sent, output_cap;
    int close_after_write;
    struct client *next;
} client;

static store db;
static volatile sig_atomic_t stopping = 0;
static int listener_tag;

static void on_signal(int sig) { (void)sig; stopping = 1; }

static uint64_t hash_bytes(const unsigned char *p, size_t n) {
    uint64_t h = UINT64_C(14695981039346656037);
    for (size_t i = 0; i < n; i++) {
        h ^= p[i];
        h *= UINT64_C(1099511628211);
    }
    return h;
}

static int blob_copy(blob *dst, const unsigned char *src, size_t len) {
    dst->data = malloc(len ? len : 1);
    if (!dst->data) return -1;
    if (len) memcpy(dst->data, src, len);
    dst->len = len;
    return 0;
}

static void blob_free(blob *b) {
    free(b->data);
    b->data = NULL;
    b->len = 0;
}

static int blob_equal(const blob *a, const unsigned char *p, size_t n) {
    return a->len == n && (n == 0 || memcmp(a->data, p, n) == 0);
}

static void fields_free(hash_field *f) {
    while (f) {
        hash_field *next = f->next;
        blob_free(&f->field);
        blob_free(&f->value);
        free(f);
        f = next;
    }
}

static void entry_free(kv_entry *e) {
    if (!e) return;
    blob_free(&e->key);
    if (e->type == VALUE_STRING) blob_free(&e->value.string);
    else fields_free(e->value.fields);
    free(e);
}

static int store_init(store *s) {
    s->bucket_count = INITIAL_BUCKETS;
    s->size = 0;
    s->buckets = calloc(s->bucket_count, sizeof(*s->buckets));
    return s->buckets ? 0 : -1;
}

static kv_entry *store_find(store *s, const unsigned char *key, size_t len) {
    size_t slot = (size_t)(hash_bytes(key, len) % s->bucket_count);
    for (kv_entry *e = s->buckets[slot]; e; e = e->next)
        if (blob_equal(&e->key, key, len)) return e;
    return NULL;
}

static int store_resize(store *s) {
    if (s->bucket_count > SIZE_MAX / 2) return -1;
    size_t next_count = s->bucket_count * 2;
    kv_entry **next = calloc(next_count, sizeof(*next));
    if (!next) return -1;
    for (size_t i = 0; i < s->bucket_count; i++) {
        kv_entry *e = s->buckets[i];
        while (e) {
            kv_entry *after = e->next;
            size_t slot = (size_t)(hash_bytes(e->key.data, e->key.len) % next_count);
            e->next = next[slot];
            next[slot] = e;
            e = after;
        }
    }
    free(s->buckets);
    s->buckets = next;
    s->bucket_count = next_count;
    return 0;
}

static kv_entry *store_create_entry(store *s, const unsigned char *key, size_t len) {
    kv_entry *e = calloc(1, sizeof(*e));
    if (!e || blob_copy(&e->key, key, len) != 0) {
        free(e);
        return NULL;
    }
    size_t slot = (size_t)(hash_bytes(key, len) % s->bucket_count);
    e->next = s->buckets[slot];
    s->buckets[slot] = e;
    s->size++;
    if (s->size > s->bucket_count * 3 / 4) (void)store_resize(s);
    return e;
}

static int store_set_string(store *s, const unsigned char *key, size_t key_len,
                            const unsigned char *value, size_t value_len) {
    /* Allocate the replacement first: an OOM must not leave a ghost key. */
    blob next = {0};
    if (blob_copy(&next, value, value_len) != 0) return -1;

    kv_entry *e = store_find(s, key, key_len);
    if (!e) {
        e = store_create_entry(s, key, key_len);
        if (!e) {
            blob_free(&next);
            return -1;
        }
        e->type = VALUE_STRING;
        e->value.string = next;
        return 0;
    }

    if (e->type == VALUE_HASH) fields_free(e->value.fields);
    else blob_free(&e->value.string);
    e->type = VALUE_STRING;
    e->value.string = next;
    return 0;
}

static int store_set_hash_field(store *s, const unsigned char *key, size_t key_len,
                                const unsigned char *field, size_t field_len,
                                const unsigned char *value, size_t value_len) {
    kv_entry *e = store_find(s, key, key_len);
    if (e && e->type != VALUE_HASH) return -1;

    if (e) {
        for (hash_field *existing = e->value.fields; existing; existing = existing->next) {
            if (blob_equal(&existing->field, field, field_len)) {
                blob next = {0};
                if (blob_copy(&next, value, value_len) != 0) return -2;
                blob_free(&existing->value);
                existing->value = next;
                return 0;
            }
        }
    }

    /* Build the field completely before publishing a new hash key. */
    hash_field *f = calloc(1, sizeof(*f));
    if (!f || blob_copy(&f->field, field, field_len) != 0 ||
        blob_copy(&f->value, value, value_len) != 0) {
        if (f) {
            blob_free(&f->field);
            blob_free(&f->value);
            free(f);
        }
        return -2;
    }

    if (!e) {
        e = store_create_entry(s, key, key_len);
        if (!e) {
            blob_free(&f->field);
            blob_free(&f->value);
            free(f);
            return -2;
        }
        e->type = VALUE_HASH;
        e->value.fields = NULL;
    }
    f->next = e->value.fields;
    e->value.fields = f;
    return 1;
}

static const blob *store_get_hash_field(store *s, const unsigned char *key, size_t key_len,
                                        const unsigned char *field, size_t field_len,
                                        int *wrong_type) {
    kv_entry *e = store_find(s, key, key_len);
    *wrong_type = 0;
    if (!e) return NULL;
    if (e->type != VALUE_HASH) { *wrong_type = 1; return NULL; }
    for (hash_field *f = e->value.fields; f; f = f->next)
        if (blob_equal(&f->field, field, field_len)) return &f->value;
    return NULL;
}

static size_t store_hash_len(store *s, const unsigned char *key, size_t key_len,
                             int *wrong_type) {
    kv_entry *e = store_find(s, key, key_len);
    *wrong_type = 0;
    if (!e) return 0;
    if (e->type != VALUE_HASH) { *wrong_type = 1; return 0; }
    size_t n = 0;
    for (hash_field *f = e->value.fields; f; f = f->next) n++;
    return n;
}

static const blob *store_get_string(store *s, const unsigned char *key, size_t key_len,
                                    int *wrong_type) {
    kv_entry *e = store_find(s, key, key_len);
    *wrong_type = 0;
    if (!e) return NULL;
    if (e->type != VALUE_STRING) { *wrong_type = 1; return NULL; }
    return &e->value.string;
}

static int store_del(store *s, const unsigned char *key, size_t len) {
    size_t slot = (size_t)(hash_bytes(key, len) % s->bucket_count);
    kv_entry **link = &s->buckets[slot];
    while (*link) {
        kv_entry *e = *link;
        if (blob_equal(&e->key, key, len)) {
            *link = e->next;
            entry_free(e);
            s->size--;
            return 1;
        }
        link = &e->next;
    }
    return 0;
}

static void store_free(store *s) {
    if (!s->buckets) return;
    for (size_t i = 0; i < s->bucket_count; i++) {
        kv_entry *e = s->buckets[i];
        while (e) {
            kv_entry *next = e->next;
            entry_free(e);
            e = next;
        }
    }
    free(s->buckets);
    s->buckets = NULL;
    s->size = s->bucket_count = 0;
}

static int output_append(client *c, const void *data, size_t len) {
    if (len > MAX_OUTPUT || c->output_len - c->output_sent > MAX_OUTPUT - len) return -1;
    if (c->output_sent) {
        size_t pending = c->output_len - c->output_sent;
        memmove(c->output, c->output + c->output_sent, pending);
        c->output_len = pending;
        c->output_sent = 0;
    }
    size_t need = c->output_len + len;
    if (need > c->output_cap) {
        size_t cap = c->output_cap ? c->output_cap : 1024;
        while (cap < need) cap *= 2;
        if (cap > MAX_OUTPUT) cap = MAX_OUTPUT;
        unsigned char *p = realloc(c->output, cap);
        if (!p) return -1;
        c->output = p;
        c->output_cap = cap;
    }
    if (len) memcpy(c->output + c->output_len, data, len);
    c->output_len += len;
    return 0;
}

static int reply_simple(client *c, const char *s) {
    return output_append(c, "+", 1) || output_append(c, s, strlen(s)) ||
           output_append(c, "\r\n", 2) ? -1 : 0;
}
static int reply_error(client *c, const char *s) {
    return output_append(c, "-ERR ", 5) || output_append(c, s, strlen(s)) ||
           output_append(c, "\r\n", 2) ? -1 : 0;
}
static int reply_integer(client *c, long long n) {
    char buf[64];
    int len = snprintf(buf, sizeof(buf), ":%lld\r\n", n);
    return len < 0 ? -1 : output_append(c, buf, (size_t)len);
}
static int reply_null(client *c) { return output_append(c, "$-1\r\n", 5); }
static int reply_bulk(client *c, const unsigned char *data, size_t len) {
    char header[64];
    int n = snprintf(header, sizeof(header), "$%zu\r\n", len);
    if (n < 0 || output_append(c, header, (size_t)n) != 0 ||
        output_append(c, data, len) != 0 || output_append(c, "\r\n", 2) != 0)
        return -1;
    return 0;
}

static int arg_is(const arg *a, const char *s) {
    size_t n = strlen(s);
    return a->len == n && strncasecmp((const char *)a->data, s, n) == 0;
}

typedef enum { PARSE_BAD = -1, PARSE_MORE = 0, PARSE_DONE = 1 } parse_status;

static parse_status read_decimal_line(const unsigned char *buf, size_t len,
                                      size_t *pos, size_t *value) {
    size_t start = *pos, end = start;
    while (end + 1 < len && !(buf[end] == '\r' && buf[end + 1] == '\n')) {
        if (end - start >= 20) return PARSE_BAD;
        end++;
    }
    if (end + 1 >= len) return (len - start > 20) ? PARSE_BAD : PARSE_MORE;
    if (end == start) return PARSE_BAD;
    size_t n = 0;
    for (size_t i = start; i < end; i++) {
        if (buf[i] < '0' || buf[i] > '9') return PARSE_BAD;
        unsigned digit = (unsigned)(buf[i] - '0');
        if (n > (SIZE_MAX - digit) / 10) return PARSE_BAD;
        n = n * 10 + digit;
    }
    *value = n;
    *pos = end + 2;
    return PARSE_DONE;
}

static parse_status parse_command(const unsigned char *buf, size_t len,
                                  size_t *consumed, arg *argv, size_t *argc) {
    if (len == 0) return PARSE_MORE;
    if (buf[0] != '*') return PARSE_BAD;
    size_t pos = 1, count = 0;
    parse_status st = read_decimal_line(buf, len, &pos, &count);
    if (st != PARSE_DONE) return st;
    if (count == 0 || count > MAX_ARGS) return PARSE_BAD;
    for (size_t i = 0; i < count; i++) {
        if (pos >= len) return PARSE_MORE;
        if (buf[pos++] != '$') return PARSE_BAD;
        size_t bulk_len = 0;
        st = read_decimal_line(buf, len, &pos, &bulk_len);
        if (st != PARSE_DONE) return st;
        if (bulk_len > MAX_BULK) return PARSE_BAD;
        if (bulk_len > SIZE_MAX - pos - 2) return PARSE_BAD;
        if (len - pos < bulk_len + 2) return PARSE_MORE;
        if (buf[pos + bulk_len] != '\r' || buf[pos + bulk_len + 1] != '\n')
            return PARSE_BAD;
        argv[i].data = buf + pos;
        argv[i].len = bulk_len;
        pos += bulk_len + 2;
    }
    *argc = count;
    *consumed = pos;
    return PARSE_DONE;
}

static int dispatch(client *c, arg *a, size_t argc) {
    if (arg_is(&a[0], "PING")) {
        if (argc == 1) return reply_simple(c, "PONG");
        if (argc == 2) return reply_bulk(c, a[1].data, a[1].len);
        return reply_error(c, "wrong number of arguments for 'ping' command");
    }
    if (arg_is(&a[0], "ECHO")) {
        if (argc != 2) return reply_error(c, "wrong number of arguments for 'echo' command");
        return reply_bulk(c, a[1].data, a[1].len);
    }
    if (arg_is(&a[0], "SET")) {
        if (argc != 3) return reply_error(c, "wrong number of arguments for 'set' command");
        if (store_set_string(&db, a[1].data, a[1].len, a[2].data, a[2].len) != 0)
            return reply_error(c, "out of memory");
        return reply_simple(c, "OK");
    }
    if (arg_is(&a[0], "GET")) {
        if (argc != 2) return reply_error(c, "wrong number of arguments for 'get' command");
        int wrong = 0;
        const blob *v = store_get_string(&db, a[1].data, a[1].len, &wrong);
        if (wrong) return reply_error(c, "WRONGTYPE Operation against a key holding the wrong kind of value");
        return v ? reply_bulk(c, v->data, v->len) : reply_null(c);
    }
    if (arg_is(&a[0], "HSET")) {
        if (argc < 4 || (argc - 2) % 2 != 0)
            return reply_error(c, "wrong number of arguments for 'hset' command");
        long long added = 0;
        for (size_t i = 2; i < argc; i += 2) {
            int rc = store_set_hash_field(&db, a[1].data, a[1].len,
                                          a[i].data, a[i].len, a[i+1].data, a[i+1].len);
            if (rc == -1) return reply_error(c, "WRONGTYPE Operation against a key holding the wrong kind of value");
            if (rc == -2) return reply_error(c, "out of memory");
            added += rc;
        }
        return reply_integer(c, added);
    }
    if (arg_is(&a[0], "HGET")) {
        if (argc != 3) return reply_error(c, "wrong number of arguments for 'hget' command");
        int wrong = 0;
        const blob *v = store_get_hash_field(&db, a[1].data, a[1].len,
                                             a[2].data, a[2].len, &wrong);
        if (wrong) return reply_error(c, "WRONGTYPE Operation against a key holding the wrong kind of value");
        return v ? reply_bulk(c, v->data, v->len) : reply_null(c);
    }
    if (arg_is(&a[0], "HLEN")) {
        if (argc != 2) return reply_error(c, "wrong number of arguments for 'hlen' command");
        int wrong = 0;
        size_t n = store_hash_len(&db, a[1].data, a[1].len, &wrong);
        if (wrong) return reply_error(c, "WRONGTYPE Operation against a key holding the wrong kind of value");
        return reply_integer(c, (long long)n);
    }
    if (arg_is(&a[0], "DEL") || arg_is(&a[0], "EXISTS")) {
        int is_del = arg_is(&a[0], "DEL");
        if (argc < 2) return reply_error(c, "wrong number of arguments");
        long long count = 0;
        for (size_t i = 1; i < argc; i++)
            count += is_del ? store_del(&db, a[i].data, a[i].len)
                            : (store_find(&db, a[i].data, a[i].len) != NULL);
        return reply_integer(c, count);
    }
    if (arg_is(&a[0], "DBSIZE")) {
        if (argc != 1) return reply_error(c, "wrong number of arguments for 'dbsize' command");
        return reply_integer(c, (long long)db.size);
    }
    if (arg_is(&a[0], "QUIT")) {
        if (argc != 1) return reply_error(c, "wrong number of arguments for 'quit' command");
        c->close_after_write = 1;
        return reply_simple(c, "OK");
    }
    return reply_error(c, "unknown command");
}

static int process_input(client *c) {
    while (c->input_len && !c->close_after_write) {
        arg argv[MAX_ARGS];
        size_t argc = 0, consumed = 0;
        parse_status st = parse_command(c->input, c->input_len, &consumed, argv, &argc);
        if (st == PARSE_MORE) return 0;
        if (st == PARSE_BAD) {
            c->input_len = 0;
            c->close_after_write = 1;
            return reply_error(c, "Protocol error");
        }
        if (dispatch(c, argv, argc) != 0) return -1;
        memmove(c->input, c->input + consumed, c->input_len - consumed);
        c->input_len -= consumed;
    }
    return 0;
}

static int input_append(client *c, const unsigned char *data, size_t len) {
    if (len > MAX_INPUT || c->input_len > MAX_INPUT - len) return -1;
    size_t need = c->input_len + len;
    if (need > c->input_cap) {
        size_t cap = c->input_cap ? c->input_cap : 4096;
        while (cap < need) cap *= 2;
        if (cap > MAX_INPUT) cap = MAX_INPUT;
        unsigned char *p = realloc(c->input, cap);
        if (!p) return -1;
        c->input = p;
        c->input_cap = cap;
    }
    memcpy(c->input + c->input_len, data, len);
    c->input_len += len;
    return 0;
}

static void client_free(client *c) {
    if (!c) return;
    close(c->fd);
    free(c->input);
    free(c->output);
    free(c);
}

static void client_remove(int epfd, client **clients, client *c) {
    (void)epoll_ctl(epfd, EPOLL_CTL_DEL, c->fd, NULL);
    client **p = clients;
    while (*p && *p != c) p = &(*p)->next;
    if (*p == c) *p = c->next;
    client_free(c);
}

static int client_update_events(int epfd, client *c) {
    struct epoll_event ev;
    memset(&ev, 0, sizeof(ev));
    ev.events = EPOLLRDHUP;
    /* Once a reply must be sent before closing, stop accepting more input. */
    if (!c->close_after_write) ev.events |= EPOLLIN;
    if (c->output_sent < c->output_len) ev.events |= EPOLLOUT;
    ev.data.ptr = c;
    return epoll_ctl(epfd, EPOLL_CTL_MOD, c->fd, &ev);
}

static int client_read(client *c) {
    unsigned char buf[READ_CHUNK];
    for (;;) {
        ssize_t n = recv(c->fd, buf, sizeof(buf), 0);
        if (n > 0) {
            if (input_append(c, buf, (size_t)n) != 0) {
                c->close_after_write = 1;
                return reply_error(c, "query buffer limit exceeded");
            }
            if (process_input(c) != 0) return -1;
            if (c->close_after_write) return 0;
            continue;
        }
        if (n == 0) {
            c->close_after_write = 1;
            return 0;
        }
        if (errno == EINTR) continue;
        if (errno == EAGAIN || errno == EWOULDBLOCK) return 0;
        return -1;
    }
}

static int client_write(client *c) {
    while (c->output_sent < c->output_len) {
        ssize_t n = send(c->fd, c->output + c->output_sent,
                         c->output_len - c->output_sent, MSG_NOSIGNAL);
        if (n > 0) { c->output_sent += (size_t)n; continue; }
        if (n < 0 && errno == EINTR) continue;
        if (n < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) return 0;
        return -1;
    }
    c->output_len = c->output_sent = 0;
    return c->close_after_write ? 1 : 0;
}

static int make_listener(int port) {
    int fd = socket(AF_INET, SOCK_STREAM | SOCK_NONBLOCK | SOCK_CLOEXEC, 0);
    if (fd < 0) return -1;
    int yes = 1;
    if (setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof(yes)) != 0) {
        close(fd); return -1;
    }
    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons((uint16_t)port);
    if (inet_pton(AF_INET, "127.0.0.1", &addr.sin_addr) != 1 ||
        bind(fd, (struct sockaddr *)&addr, sizeof(addr)) != 0 || listen(fd, 128) != 0) {
        close(fd); return -1;
    }
    return fd;
}

static int accept_clients(int epfd, int listener, client **clients) {
    for (;;) {
        int fd = accept4(listener, NULL, NULL, SOCK_NONBLOCK | SOCK_CLOEXEC);
        if (fd < 0) {
            if (errno == EINTR) continue;
            if (errno == EAGAIN || errno == EWOULDBLOCK) return 0;
            return -1;
        }
        client *c = calloc(1, sizeof(*c));
        if (!c) { close(fd); continue; }
        c->fd = fd;
        c->next = *clients;
        *clients = c;
        struct epoll_event ev;
        memset(&ev, 0, sizeof(ev));
        ev.events = EPOLLIN | EPOLLRDHUP;
        ev.data.ptr = c;
        if (epoll_ctl(epfd, EPOLL_CTL_ADD, fd, &ev) != 0)
            client_remove(epfd, clients, c);
    }
}

int main(int argc, char **argv) {
    int port = 6380;
    if (argc > 2) {
        fprintf(stderr, "usage: %s [port]\n", argv[0]);
        return 2;
    }
    if (argc == 2) {
        char *end = NULL;
        long n = strtol(argv[1], &end, 10);
        if (!end || *end || n < 1 || n > 65535) {
            fprintf(stderr, "invalid port\n");
            return 2;
        }
        port = (int)n;
    }
    if (store_init(&db) != 0) {
        fprintf(stderr, "cannot initialize keyspace\n");
        return 1;
    }
    int listener = make_listener(port);
    if (listener < 0) {
        perror("listen");
        store_free(&db);
        return 1;
    }
    int epfd = epoll_create1(EPOLL_CLOEXEC);
    if (epfd < 0) {
        perror("epoll_create1");
        close(listener);
        store_free(&db);
        return 1;
    }
    struct epoll_event lev;
    memset(&lev, 0, sizeof(lev));
    lev.events = EPOLLIN;
    lev.data.ptr = &listener_tag;
    if (epoll_ctl(epfd, EPOLL_CTL_ADD, listener, &lev) != 0) {
        perror("epoll_ctl");
        close(epfd); close(listener); store_free(&db);
        return 1;
    }
    signal(SIGINT, on_signal);
    signal(SIGTERM, on_signal);
    printf("Mini-Redis RESP2 listening on 127.0.0.1:%d\n", port);
    fflush(stdout);

    client *clients = NULL;
    struct epoll_event events[MAX_EVENTS];
    while (!stopping) {
        int n = epoll_wait(epfd, events, MAX_EVENTS, 1000);
        if (n < 0) {
            if (errno == EINTR) continue;
            perror("epoll_wait");
            break;
        }
        for (int i = 0; i < n; i++) {
            if (events[i].data.ptr == &listener_tag) {
                if (accept_clients(epfd, listener, &clients) != 0) perror("accept4");
                continue;
            }
            client *c = events[i].data.ptr;
            int failed = 0, close_now = 0;
            if (events[i].events & EPOLLIN)
                if (client_read(c) != 0) failed = 1;
            if (!failed && (events[i].events & EPOLLOUT))
                if (client_write(c) < 0) failed = 1;
            if (!failed && (events[i].events & (EPOLLERR | EPOLLHUP | EPOLLRDHUP))) {
                c->close_after_write = 1;
                if (client_write(c) != 0) close_now = 1;
            }
            if (!failed && !close_now && c->output_sent < c->output_len)
                if (client_update_events(epfd, c) != 0) failed = 1;
            if (!failed && !close_now && c->output_sent == c->output_len) {
                if (c->close_after_write) close_now = 1;
                else if (client_update_events(epfd, c) != 0) failed = 1;
            }
            if (failed || close_now) client_remove(epfd, &clients, c);
        }
    }
    while (clients) client_remove(epfd, &clients, clients);
    close(epfd);
    close(listener);
    store_free(&db);
    return 0;
}
