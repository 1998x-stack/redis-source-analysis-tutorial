/* Progressive enhancements for chapters 21–25. The HTML contains complete default explanations. */
(() => {
  "use strict";
  const models = {
    "replica-ack": {
      acked: "ACK 更新副本已处理的复制 offset；WAIT 可以在客户端写入的 offset 达到副本确认后返回数量。但 ACK 本身不保证磁盘已 fsync。",
      timeout: "WAIT 超时只返回确认数量。之前的 SET 已执行，不会因为 WAIT 返回 0 而回滚；故障切换仍可能丢失未复制写入。",
      quorum: "min-replicas-to-write 使用 ONLINE 且 ACK 时间在 max-lag 内的副本数量门槛，数量不够时可能拒绝新的写入，不会等待当前命令的复制 offset。",
      disk: "副本处理完复制命令并回复 ACK 与其 AOF/fsync 完成是不同的时间点；必须单独定义磁盘持久化和容灾目标。"
    },
    "sentinel-votes": {
      sdown: "本地 SDOWN 只证明这个 Sentinel 的探测超时；它不足以形成 ODOWN，更不是 leader 授权。",
      odown: "3 Sentinel、quorum=2：2 个报告下线达到 ODOWN 门槛；实际故障转移仍需 leader 获得多数和至少 quorum 的投票。",
      leader: "5 Sentinel、quorum=2：2 票可能足以让某个 Sentinel 认为 ODOWN，却不能选出 leader，因为绝对多数至少是 3。",
      ready: "5 Sentinel、quorum=2：假定 3 票都支持同一个候选且 epoch 一致，则满足绝对多数与 quorum 的双门槛；后续还需晋升、重配置和客户端重新路由。"
    },
    "latency-source": {
      slowlog: "先检查 SLOWLOG 阈值、长度和是否查询了正确实例。若执行耗时确实短，则排查网络、输出缓冲、队列和宿主机调度。",
      fork: "LATENCY 的 fork 事件属于内部采样；结合 latest_fork_usec、BGSAVE 时间、COW 与系统 CPU/RSS 对齐，避免仅因时间相关就断定根因。",
      command: "SLOWLOG 中命令执行慢，可结合 key 大小/编码、commandstats 和 GDB/perf 的具体 handler 路径进一步验证。",
      empty: "LATENCY LATEST 为空可能因为未启用监控、未超过毫秒阈值或没有触发对应事件；它不是客户端 RTT 全部正常的证明。"
    },
    "symptom-route": {
      big: "Bigkey：优先用 HLEN/LLEN/STRLEN 等类型计数及 MEMORY USAGE 判断规模；--bigkeys 的最大数量不等于精确最大内存。",
      hot: "Hotkey：必须结合业务 QPS；--hotkeys 要求 LFU policy，OBJECT FREQ 是概率计数器，不是精确请求次数。",
      fork: "BGSAVE/AOF rewrite 触发 fork + 写脏页 COW，可能造成 RSS 峰值；检查 latest_fork_usec、rdb/aof COW、THP 和 OS 内存预算。",
      oom: "先区分 Redis maxmemory 拒写和内核 OOM killer 杀进程，不能看到 OOM 字样就认为是同一种故障。"
    },
    "debug-layers": {
      client: "优先核对客户端排队/网络/TLS、响应体量与 OS 调度，再确认 SLOWLOG 配置。没有慢日志不等于 Redis 端到端请求不慢。",
      handler: "检查慢日志参数、对象大小及命令复杂度；固定 7.2.4 版本，在隔离 GDB 中断到 setCommand 或对应 handler。",
      fork: "对齐 fork 事件、latest_fork_usec、COW 与子进程状态；用受控的写负载复现而不是直接修改生产 THP。",
      crash: "保留 Redis 日志、原二进制和匹配符号；检查系统 coredump 策略，然后在离线 GDB 中分析 thread apply all bt；core 可能含敏感内存。"
    }
  };
  for (const root of document.querySelectorAll("[data-fifth-demo]")) {
    const kind=root.getAttribute("data-fifth-demo");
    const select=root.querySelector("select");
    const output=root.querySelector("[data-output]");
    if(!select||!output) continue;
    const update=()=>{output.textContent=models[kind]?.[select.value]||"未找到对应的状态说明";};
    select.addEventListener("change",update);
    select.addEventListener("input",update);
    update();
  }
})();