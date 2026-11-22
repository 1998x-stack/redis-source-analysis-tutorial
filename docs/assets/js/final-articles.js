/* Offline teaching models for chapters 26–28. Each article contains a complete static explanation. */
(() => {
  "use strict";
  const models = {
    lua: {
      pure: "Redis 7.2.4 在 Lua VM 上安装 LUA_MASKCOUNT hook，每 100000 条 Lua 指令触发检查；纯 Lua 循环也会被检查，不必等 redis.call 返回。",
      before: "超过 lua-time-limit 后脚本进入 timed-out/BUSY 状态。若尚未执行写命令，可以从另一个连接发送 SCRIPT KILL；脚本不会自动并行执行。",
      after: "脚本已经执行写命令后，SCRIPT KILL 会返回 UNKILLABLE。Redis 不会回滚先前写入；必须等待脚本结束或在明确接受数据损失时采取进程级恢复措施。",
      function: "Redis Function 与 Lua 脚本共享阻塞式执行模型；中止函数使用 FUNCTION KILL，而不是 SCRIPT KILL。已产生写效果时同样不能安全中止。"
    },
    transaction: {
      queue: "排队阶段发生语法/参数错误会设置 CLIENT_DIRTY_EXEC；随后 EXEC 返回 EXECABORT，队列不会开始执行。",
      watch: "WATCH 的 key 在 EXEC 前被修改或过期，会设置 CLIENT_DIRTY_CAS；EXEC 返回 null array，应用通常需要重新读取并重试。",
      runtime: "运行时 WRONGTYPE 是 EXEC 回复数组中的一个错误元素；队列后面的命令仍继续执行，前面的成功写入也不会回滚。",
      script: "Lua 脚本的原子性是执行期间不与其他客户端命令交错；先 SET 后发生 runtime error 时，SET 已产生的效果不会自动撤销。"
    },
    module: {
      load: "moduleLoad 使用 dlopen/dlsym 找到 RedisModule_OnLoad；OnLoad 首先调用 RedisModule_Init，再注册命令和自定义数据类型。",
      type: "RedisModule_CreateDataType 注册类型回调：RDB load/save、AOF rewrite、mem_usage、digest 和 free。RDB 与 AOF 是两条不同的恢复路径。",
      worker: "主线程调用 BlockClient，worker 执行慢任务；需要从 worker 调用 Redis API 时，使用 GetThreadSafeContext 并 Lock/Unlock，最后 UnblockClient。",
      unsafe: "不要把命令回调的 RedisModuleCtx 直接交给后台线程，也不要让模块线程在 OnUnload 后继续运行；模块是进程内原生代码，不是沙箱。"
    },
    resp: {
      fragment: "当前缓冲还没有完整的 RESP frame，解析器返回 MORE，保留已收字节，等下一次 recv 追加数据；不能把 TCP 分片当成协议错误。",
      pipeline: "一个 TCP read 中可以包含多个 RESP 命令。解析一个 frame 后精确消费 consumed 字节，再循环解析缓冲区剩余内容。",
      malformed: "非法前缀、超出上限的长度或错误 CRLF 属于 BAD frame；教学服务器返回错误并关闭连接，不能继续猜测后续边界。",
      binary: "Bulk string 由长度决定边界，payload 可以包含 NUL、CRLF 和非 UTF-8 字节。不能用 strlen 或 '\\0' 作为 RESP 数据终止符。"
    },
    release: {
      ga: "截至 2026-11-23，Redis 8.10.3 是已发布 GA 系列中的最新补丁版本；8.12-RC3 是预发布标签，不能作为普通生产 GA 推荐。",
      modules: "Redis 8 发行包纳入 Search、JSON、Time Series、Probabilistic 等能力，但发行源码仍有模块清单和模块目录，模块在运行时加载；发行包整合不等于所有模块变成 core commands。",
      license: "Redis 7.2.x 及更早版本为 BSD-3-Clause；7.4.x 为 RSALv2/SSPLv1；Redis 8+ 增加 AGPLv3 选项。采用前应阅读具体版本 LICENSE。"
    }
  };
  for (const root of document.querySelectorAll("[data-final-demo]")) {
    const kind = root.getAttribute("data-final-demo");
    const select = root.querySelector("select");
    const output = root.querySelector("[data-output]");
    if (!select || !output) continue;
    const update = () => { output.textContent = models[kind]?.[select.value] || "未找到对应状态说明"; };
    select.addEventListener("change", update);
    select.addEventListener("input", update);
    update();
  }
})();
