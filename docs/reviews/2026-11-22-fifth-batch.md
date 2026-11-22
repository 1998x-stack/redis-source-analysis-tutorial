# 第五批：Redis 源码教程 21–25 章审计（2026-11-22）

## 版本与方法
- 唯一实现基准：`redis/redis@7.2.4`；核对上游源码文件、函数签名、状态机与官方 Redis 说明。
- 5 篇完全自洽文章；15 张单独原创 SVG；5 个不依赖外部网络的交互机制示例。
- 图形是源代码解释图而非真实抓包、性能数据或实验结果。对可能有破坏性的命令提供隔离前提，不将生产系统级变更作为直接操作步骤。

| 章节 | 锁定事实 | 关键文件 |
|---|---|---|
| 21 复制工程 | REPLCONF ACK/WAIT 的 offset 语义；good replicas write gate 与逐写确认不同；共享 replBufBlock/backlog、级联流和 PSYNC 回退 | replication.c, server.h, networking.c |
| 22 Sentinel/Cluster | SDOWN vs ODOWN quorum vs leader majority；failover FSM；hash slots=16384、CRC16 hash tag、ASK/MOVED；Cluster master 多数票 | sentinel.c, cluster.c, cluster.h |
| 23 诊断工具 | INFO Counter 与窗口速率；SLOWLOG μs 与 LATENCY ms 的计量边界；LATENCY 每秒较大样本，不是完整 P99 | server.c, slowlog.c, latency.c |
| 24 生产故障 | Bigkey 容量 vs Hotkey QPS；MEMORY USAGE 取样；UNLINK 条件异步释放；fork COW、THP 与 Redis/系统 OOM | object.c, lazyfree.c, evict.c, rdb.c |
| 25 源码调试 | Makefile DEBUG/OPTIMIZATION；processCommand/call/setCommand 调用链；符号匹配；core/ptrace 敏感与扰动性 | src/Makefile, networking.c, server.c, t_string.c, debug.c |

## 质量门禁
- 静态校验扩到 1–25 章；21–25 每篇必须有 3 张 SVG、独立源码链接、至少 8 个 section（含 source）及有效交互。
- 浏览器 Playwright Chromium：主页 + 01–25 章 × 360/390/1440，共 78 个视口；检查横向溢出、JS console、图像 decode、首页重构状态筛选、每章控制响应。
- 已在 GitHub Actions 使用官方 `redis/redis@7.2.4` 源码编译独立 Redis 二进制，运行 `scripts/redis_724_smoke.py`：Redis 7.2.4 版本、INFO/SLOWLOG、MEMORY USAGE/UNLINK、主从复制 + 同连接 WAIT ACK、一个 Sentinel 不足以达到 quorum=2、hash tag 槽公式、RDB v11 + redis-check-rdb、Multi-Part AOF BASE/INCR manifest 均通过。验证记录：[runtime-smoke #45039944806](https://github.com/1998x-stack/redis-source-analysis-tutorial/actions/runs/45039944806)。
- 这些是功能/结构冒烟实验，并未执行 21–25 章全部命令脚本：特别是级联在负载下的延迟、实际 Sentinel 3 节点故障转移、Cluster 迁移、生产 THP、GDB 断点/strace/perf/core 故障注入仍未实机验证。只在正文注明预期行为，不能把它们归入已通过测试。
- 静态与浏览器 CI、Pages 部署和合并情况单独在 Actions/PR 核查；上述 runtime smoke 的成功不意味着 GitHub Pages 已发布。

## 重要边界
- WAIT 不是磁盘持久化/严格强一致；min-replicas 不是每条命令的 ACK 证明。
- Sentinel ODOWN quorum 与选 leader 的多数票是两道门槛；Redis Cluster 不能使用 Sentinel 票数解释。
- Redis 7.2 没有 Redis 8.4 新的原子槽迁移 API；旧版 MIGRATING/IMPORTING 依赖 ASKING。
- SLOWLOG 不含网络 I/O；LATENCY monitor 的事件历史不是真实 P99 分布。
- UNLINK 可能同步释放简单对象；RSS 释放又是下一层 allocator/OS 行为。
- 不在生产使用 DEBUG SEGFAULT、DEBUG SLEEP、未经评估的 ptrace、sysctl THP 修改或无备份的 AOF 修复。
