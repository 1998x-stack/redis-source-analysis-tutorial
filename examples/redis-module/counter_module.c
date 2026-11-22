#include <limits.h>
#include "redismodule.h"

typedef struct {
    long long value;
} CounterValue;

static RedisModuleType *CounterType = NULL;

static void *counter_rdb_load(RedisModuleIO *io, int encver) {
    if (encver != 1) return NULL;
    long long value = RedisModule_LoadSigned(io);
    if (RedisModule_IsIOError(io)) return NULL;
    CounterValue *v = RedisModule_Alloc(sizeof(*v));
    if (!v) return NULL;
    v->value = value;
    return v;
}

static void counter_rdb_save(RedisModuleIO *io, void *value) {
    CounterValue *v = value;
    RedisModule_SaveSigned(io, v->value);
}

static void counter_aof_rewrite(RedisModuleIO *io, RedisModuleString *key, void *value) {
    CounterValue *v = value;
    RedisModule_EmitAOF(io, "counter.set", "sl", key, v->value);
}

static size_t counter_mem_usage(const void *value) {
    (void)value;
    return sizeof(CounterValue);
}

static void counter_digest(RedisModuleDigest *md, void *value) {
    CounterValue *v = value;
    RedisModule_DigestAddLongLong(md, v->value);
    RedisModule_DigestEndSequence(md);
}

static void counter_free(void *value) {
    RedisModule_Free(value);
}

static int get_counter_key(RedisModuleCtx *ctx, RedisModuleString *keyname,
                           int mode, RedisModuleKey **key, CounterValue **value) {
    *key = RedisModule_OpenKey(ctx, keyname, mode);
    if (!*key) return REDISMODULE_ERR;
    int type = RedisModule_KeyType(*key);
    if (type == REDISMODULE_KEYTYPE_EMPTY) {
        *value = NULL;
        return REDISMODULE_OK;
    }
    if (type != REDISMODULE_KEYTYPE_MODULE ||
        RedisModule_ModuleTypeGetType(*key) != CounterType) {
        RedisModule_CloseKey(*key);
        *key = NULL;
        return REDISMODULE_ERR;
    }
    *value = RedisModule_ModuleTypeGetValue(*key);
    return *value ? REDISMODULE_OK : REDISMODULE_ERR;
}

static int counter_set(RedisModuleCtx *ctx, RedisModuleString **argv, int argc) {
    if (argc != 3) return RedisModule_WrongArity(ctx);
    long long value;
    if (RedisModule_StringToLongLong(argv[2], &value) != REDISMODULE_OK)
        return RedisModule_ReplyWithError(ctx, "ERR value is not an integer");

    RedisModuleKey *key = NULL;
    CounterValue *v = NULL;
    if (get_counter_key(ctx, argv[1], REDISMODULE_WRITE, &key, &v) != REDISMODULE_OK)
        return RedisModule_ReplyWithError(ctx, "WRONGTYPE key holds another data type");

    if (!v) {
        v = RedisModule_Alloc(sizeof(*v));
        if (!v) {
            RedisModule_CloseKey(key);
            return RedisModule_ReplyWithError(ctx, "ERR out of memory");
        }
        v->value = value;
        if (RedisModule_ModuleTypeSetValue(key, CounterType, v) != REDISMODULE_OK) {
            RedisModule_Free(v);
            RedisModule_CloseKey(key);
            return RedisModule_ReplyWithError(ctx, "ERR cannot set module value");
        }
    } else {
        v->value = value;
    }

    RedisModule_SignalModifiedKey(ctx, argv[1]);
    RedisModule_ReplicateVerbatim(ctx);
    RedisModule_CloseKey(key);
    return RedisModule_ReplyWithSimpleString(ctx, "OK");
}

static int counter_incr(RedisModuleCtx *ctx, RedisModuleString **argv, int argc) {
    if (argc != 2 && argc != 3) return RedisModule_WrongArity(ctx);
    long long delta = 1;
    if (argc == 3 && RedisModule_StringToLongLong(argv[2], &delta) != REDISMODULE_OK)
        return RedisModule_ReplyWithError(ctx, "ERR increment is not an integer");

    RedisModuleKey *key = NULL;
    CounterValue *v = NULL;
    if (get_counter_key(ctx, argv[1], REDISMODULE_WRITE, &key, &v) != REDISMODULE_OK)
        return RedisModule_ReplyWithError(ctx, "WRONGTYPE key holds another data type");

    if (!v) {
        v = RedisModule_Alloc(sizeof(*v));
        if (!v) {
            RedisModule_CloseKey(key);
            return RedisModule_ReplyWithError(ctx, "ERR out of memory");
        }
        v->value = 0;
        if (RedisModule_ModuleTypeSetValue(key, CounterType, v) != REDISMODULE_OK) {
            RedisModule_Free(v);
            RedisModule_CloseKey(key);
            return RedisModule_ReplyWithError(ctx, "ERR cannot set module value");
        }
    }
    if ((delta > 0 && v->value > LLONG_MAX - delta) ||
        (delta < 0 && v->value < LLONG_MIN - delta)) {
        RedisModule_CloseKey(key);
        return RedisModule_ReplyWithError(ctx, "ERR increment would overflow");
    }
    v->value += delta;
    long long result = v->value;
    RedisModule_SignalModifiedKey(ctx, argv[1]);
    RedisModule_ReplicateVerbatim(ctx);
    RedisModule_CloseKey(key);
    return RedisModule_ReplyWithLongLong(ctx, result);
}

static int counter_get(RedisModuleCtx *ctx, RedisModuleString **argv, int argc) {
    if (argc != 2) return RedisModule_WrongArity(ctx);
    RedisModuleKey *key = NULL;
    CounterValue *v = NULL;
    if (get_counter_key(ctx, argv[1], REDISMODULE_READ, &key, &v) != REDISMODULE_OK)
        return RedisModule_ReplyWithError(ctx, "WRONGTYPE key holds another data type");
    if (!v) {
        RedisModule_CloseKey(key);
        return RedisModule_ReplyWithNull(ctx);
    }
    long long result = v->value;
    RedisModule_CloseKey(key);
    return RedisModule_ReplyWithLongLong(ctx, result);
}

int RedisModule_OnLoad(RedisModuleCtx *ctx, RedisModuleString **argv, int argc) {
    REDISMODULE_NOT_USED(argv);
    REDISMODULE_NOT_USED(argc);
    if (RedisModule_Init(ctx, "countermod", 1, REDISMODULE_APIVER_1) == REDISMODULE_ERR)
        return REDISMODULE_ERR;

    RedisModule_SetModuleOptions(ctx, REDISMODULE_OPTIONS_HANDLE_IO_ERRORS);
    RedisModuleTypeMethods methods = {
        .version = REDISMODULE_TYPE_METHOD_VERSION,
        .rdb_load = counter_rdb_load,
        .rdb_save = counter_rdb_save,
        .aof_rewrite = counter_aof_rewrite,
        .mem_usage = counter_mem_usage,
        .digest = counter_digest,
        .free = counter_free
    };
    CounterType = RedisModule_CreateDataType(ctx, "counter01", 1, &methods);
    if (!CounterType) return REDISMODULE_ERR;

    if (RedisModule_CreateCommand(ctx, "counter.set", counter_set,
                                  "write deny-oom", 1, 1, 1) == REDISMODULE_ERR)
        return REDISMODULE_ERR;
    if (RedisModule_CreateCommand(ctx, "counter.incr", counter_incr,
                                  "write deny-oom", 1, 1, 1) == REDISMODULE_ERR)
        return REDISMODULE_ERR;
    if (RedisModule_CreateCommand(ctx, "counter.get", counter_get,
                                  "readonly", 1, 1, 1) == REDISMODULE_ERR)
        return REDISMODULE_ERR;
    return REDISMODULE_OK;
}
