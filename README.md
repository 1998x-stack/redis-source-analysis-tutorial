# 🔧 Redis源码分析 · 从入门到精通

> 📘 28章 实战体系

一套完整的 **Redis源码分析 · 从入门到精通** 全中文实战课程体系，共 **28 章**。本课程以 HTML 可视化的形式呈现，从基础原理到工程实践循序渐进，适合系统性学习与复习。

## 🚀 快速开始

无需安装任何依赖，直接用浏览器打开 `index.html` 即可在线阅读全部章节：

```bash
open index.html   # macOS
# 或在浏览器中直接打开 index.html
```

## 📖 章节目录

| # | 章节 | 核心主题 |
|---|------|----------|
| 01 | Redis源码全景图 | 项目架构、antirez设计哲学、阅读路线图、环境搭建 |
| 02 | 编译与调试环境搭建 | Makefile编译选项、GDB调试配置、VSCode+clangd |
| 03 | 内存管理：zmalloc与jemalloc | zmalloc源码、jemalloc原理、used_memory统计、内存碎片分析 |
| 04 | SDS动态字符串 | 二进制安全设计、五种sdshdr、预分配与惰性释放、embstr/raw/int编码 |
| 05 | 链表、压缩列表与listpack | adlist双向链表、ziplist连锁更新、listpack替代方案、quicklist混合结构 |
| 06 | 字典与渐进式rehash | dict三层结构、MurmurHash2、渐进式rehash、SCAN命令原理 |
| 07 | 跳表与整数集合 | skiplist层高随机生成、intset自适应升级、zset双结构设计、跳表vs红黑树 |
| 08 | redisObject与编码转换 | type/encoding/refcount/lru、编码阈值与转换、共享对象池、OBJECT命令源码 |
| 09 | String与Hash命令实现 | SET/GET/INCR源码、HSET/HGET实现、HFE字段过期、批量操作优化 |
| 10 | List命令与阻塞操作 | quicklist深层结构、push/pop命令、BLPOP阻塞队列、消息队列模式 |
| 11 | Set与Sorted Set命令实现 | 集合运算SINTER/SUNION、zaddGenericCommand、ZUNIONSTORE聚合、编码切换阈值 |
| 12 | Stream、Geo与HyperLogLog | rax基数树、消费组与PEL、GeoHash编码、HLL基数估算 |
| 13 | 事件循环（上）：文件事件 | Reactor模式、aeEventLoop结构、epoll/kqueue/io_uring后端、AE_BARRIER优化 |
| 14 | 事件循环（下）：时间事件 | serverCron周期任务、beforeSleep钩子、hz参数调优、阻塞操作配合 |
| 15 | 网络IO架构 | 网络模型演进史、connection抽象层、IO多线程机制、输出缓冲区管理 |
| 16 | 命令处理全流程 | RESP协议解析、命令查找表、ACL权限校验、响应输出 |
| 17 | RDB持久化 | fork写时复制、rdbSave序列化、BGSAVE调度、CRC64校验 |
| 18 | AOF与混合持久化 | 命令追加与刷盘、fsync三种策略、AOF重写、RDB+AOF混合 |
| 19 | 键过期与内存淘汰 | 惰性删除+定期删除、LRU近似算法、LFU对数计数器、8种淘汰策略 |
| 20 | 主从复制（上） | 全量同步RDB传输、PSYNC部分重同步、replication backlog、环形缓冲溢出 |
| 21 | 主从复制（下） | 无盘复制、级联复制拓扑、min-replicas安全阀、命令传播 |
| 22 | Sentinel哨兵与Cluster集群 | SDOWN/ODOWN判定、Raft故障转移选举、哈希槽与MOVED/ASK、Gossip协议 |
| 23 | 性能诊断工具链 | INFO命令全解、latency monitor、slowlog、perf火焰图 |
| 24 | 生产环境踩坑指南 | bigkey/hotkey问题、fork与THP陷阱、CPU/内存排查、配置陷阱 |
| 25 | 源码级问题定位实战 | GDB断点调试、core dump分析、strace追踪、三个实战案例 |
| 26 | Lua脚本与事务 | EVAL/EVALSHA源码、lua_limit_timeout、MULTI/EXEC/WATCH、原子性保证 |
| 27 | Module开发实战 | Module API体系、自定义命令与类型、Redis Stack生态、完整Module示例 |
| 28 | Redis 8.x前瞻与手写Mini-Redis | Vector Sets向量搜索、io_uring接入、Valkey社区、从零实现Mini-Redis |

## 📂 项目结构

```text
redis-source-analysis-tutorial/
├── index.html      # 课程主入口（在线阅读全部章节）
├── 01.html ~ 28.html   # 各章节正文
├── courses.json    # 课程元数据（标题/章节/主题）
└── theme.css       # 统一主题样式
```

## ✨ 课程特色

- **全中文实战体系**：面向中文读者，由浅入深，覆盖原理与工程实践
- **28 章完整内容**：系统化章节编排，形成完整知识闭环
- **可视化呈现**：HTML 图文并茂，适合快速浏览与重点回顾
- **即开即用**：无需构建、无需服务器，纯静态页面随开随看

---
*本课程由 `redis-source-analysis-tutorial/` 项目维护。*