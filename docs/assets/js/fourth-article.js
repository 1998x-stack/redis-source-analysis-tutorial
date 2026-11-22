/* Progressive explanations for Redis chapters 16–20. */
(() => {
  "use strict";
  const copy = {
    "command-route": {
      set: "SET 通过命令查找、arity、认证/ACL、路由和资源检查后进入 call()；handler 改变数据集，call 计算 dirty 差值并按 flags 传播。",
      acl: "ACL 不通过时 processCommand 返回 NOPERM 错误；业务 handler 不会执行，也不会因该命令产生正常写入传播。",
      multi: "MULTI 上下文中的普通命令进入 queueMultiCommand 并返回 QUEUED；真正执行发生在后续 EXEC。",
      cluster: "如果 key slot 不属于当前节点，Cluster 路由会返回 MOVED/ASK 或重定向，当前节点不会调用本地 keyspace handler。"
    },
    "rdb-cow": {
      low: "低写入：父进程大部分时间只读或修改少量页面，子进程看到 fork 时的视图，COW 私有副本较少。",
      medium: "中等写入：被父进程修改的内存页触发 COW；成本由被写脏的页分布决定，而不是简单等于数据集大小。",
      high: "高写入：大量不同页面在子进程完成前被父进程修改，COW RSS 可能明显增长；同时 fork 和子进程时长也影响峰值。"
    },
    "aof-fsync": {
      always: "always：每次 AOF flush 后同步 fsync，Redis 7.2.4 可进行 group commit；延迟更高，fsync 失败按强确认语义处理。",
      everysec: "everysec：由 BIO 后台线程执行 fsync；主线程遇到未完成的 fsync 时可能延后部分写入，存在未同步窗口。",
      no: "no：Redis 不主动 fsync，依赖操作系统的回写策略；不能从 write 成功推断数据已持久化到设备。"
    },
    "expiry-eviction": {
      ttl: "TTL expiration：比较 key 的绝对到期时间；惰性过期在访问时触发，主动过期通过 expires 字典抽样清理。",
      allkeys: "allkeys-lru：maxmemory 超限后，从整个 keyspace 抽样估计最近使用时间并选择候选，不要求 key 有 TTL。",
      volatile: "volatile-ttl：只在带 TTL 的键中挑选剩余 TTL 较短者；没有符合条件的 volatile key 时，无法按此策略释放数据。",
      none: "noeviction：不主动删除 key；当命令需要新增内存且无法满足 maxmemory 时，写命令可能收到 OOM 错误。"
    },
    "psync-path": {
      partial: "部分同步要求 replid 匹配当前 ID，或在 second_replid_offset 边界内匹配 replid2；请求 offset 还必须落在 backlog 可提供的字节区间。",
      old: "如果请求 offset 早于 backlog 起点，缺失字节已经被裁剪；即使 replid 相同，也无法仅靠当前 backlog 补齐。",
      mismatch: "如果 replication ID 不属于当前或有效的第二历史，主节点无法证明数据集历史连续，必须走 FULLRESYNC。",
      fresh: "新副本没有 cached master 时发送 PSYNC ? -1，明确要求 FULLRESYNC，先建立快照基线再追赶增量流。"
    }
  };
  for (const root of document.querySelectorAll("[data-fourth-demo]")) {
    const kind = root.getAttribute("data-fourth-demo");
    const select = root.querySelector("select");
    const output = root.querySelector("[data-output]");
    if (!select || !output) continue;
    const update = () => { output.textContent = copy[kind]?.[select.value] || "暂无对应说明"; };
    select.addEventListener("change", update);
    select.addEventListener("input", update);
    update();
  }
})();