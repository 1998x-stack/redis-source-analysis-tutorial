# Redis 源码教程第 16–20 章技术审计记录

- 固定源码基准：`redis/redis@7.2.4`。
- 新文均为独立上下文，不依赖上一章才能理解；每篇含 3 张原创 SVG、源码链接、可复现实验与边界说明。
- 图示为解释性控制流/逻辑布局，不伪装成真实内存 dump 或运行时抓包。

| 章 | 核心核验点 | Redis 7.2.4 关键源码 |
|---|---|---|
| 16 | `processCommand` 的查找、权限、Cluster、OOM、loading/stale/pause gate；MULTI queue；`call` dirty diff、slowlog/stats/monitor 与传播；`resp_parser.c` 是 RM_Call/Lua 回复解析器而非 client request parser | server.c, networking.c, resp_parser.c, commands.def |
| 17 | RDB_VERSION=11；`rdbSaveBackground` fork 子进程；temp file、flush/fsync、rename、dir fsync；COW 只复制被写脏页面；加载校验 header/version/opcode/EOF/CRC64 | rdb.c, rdb.h, rio.c |
| 18 | Redis 7.0 起 Multi-Part AOF；manifest 描述 BASE/INCR/HISTORY；rewrite 前 parent 打开新 INCR，child 生成 BASE；fsync always/everysec/no 的区别 | aof.c, server.c, bio.c, rdb.c |
| 19 | `db->expires` 存绝对到期时间；惰性过期与主动抽样；replica 逻辑过期但不擅自删除；maxmemory 淘汰与 TTL 独立；LRU/LFU 是近似算法 | db.c, expire.c, evict.c, server.h |
| 20 | replid + byte offset；replid2 的有效 offset 边界；PSYNC backlog 范围；7.2 共享 replBufBlock 列表 + rax 索引；FULLRESYNC 的 RDB/增量流衔接 | replication.c, server.h, rdb.c |

## 本批修正的跨版本与概念错误
1. Multi-Part AOF 是 Redis 7.0 起的机制，不能归为 Redis 8 新特性；7.0+ rewrite 中父进程开新 INCR，子进程生成 BASE。
2. RDB 7.2.4 文件格式版本号是 11；运行时 object encoding 不是 RDB type code。
3. COW 是 fork 后写入页面触发的复制，不是 fork 时复制整个 Redis 数据集。
4. TTL expiration 与 maxmemory eviction 由不同条件触发；不要把 expired_keys 和 evicted_keys 混为一个指标。
5. 7.2.4 的 replication buffer 内部使用共享 replBufBlock 列表与 rax 索引；固定长度环形 byte array 只是抽象，不是精确结构布局。
6. Redis 7.2 的复制是异步的；WAIT 不是强一致性共识协议。

## 验收范围
- `scripts/validate_site.py`：1–20 章语义结构、28 章目录、所有本地链接、SVG XML/title/desc/viewBox。
- `scripts/browser_qa.py`：首页 + 01–20 章 × 360/390/1440，共 63 个 Chromium 视口；检查 console、图像解码、横向溢出、目录筛选和第 16–20 章交互。
- 本轮尚未在独立 Redis 7.2.4 进程上执行全部命令示例；CI 的静态/浏览器通过不代表 RDB/AOF/复制的故障注入实验已完成。运行结果必须按实际 Actions 日志记录。
