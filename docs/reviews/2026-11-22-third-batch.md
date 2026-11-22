# Redis 11–15 深度复核（2026-11-22）

## 固定版本核验
每篇都以 `redis/redis@7.2.4` 为基准，逐章检查关键符号与实现。新文独立成篇，不引用上一章作为必要前提。14 张 SVG 为新绘制的解释性图形，并非真实内存逐字节转储。

| 章节 | 修正点 | 源码 |
|---|---|---|
| 11 | Set 为 intset/listpack/HT 三种主要编码；SINTER 按成员集合大小优化候选；ZADD 需要按编码分派 | t_set.c, t_zset.c |
| 12 | Stream 是 rax+listpack；PEL 同时存在 group 与 consumer 索引；Geo 用 52 位分数复用 ZADD；HLL 是具有专用头部的 String 格式 | stream.h, t_stream.c, geo.c, geohash.c, hyperloglog.c |
| 13 | ae.c 依编译期后端选择 epoll/kqueue/select 等；AE_BARRIER 控制回调顺序；Redis 7.2 不应混写未经核验的未来 io_uring 特性 | ae.c, ae.h, ae_epoll.c |
| 14 | aeTimeEvent 保存在无序双向链表，而非 timer heap；usUntilEarliestTimer O(N)；serverCron 的 dynamic-hz 和 run_with_period 有不同节奏 | ae.c, server.c, expire.c |
| 15 | ConnectionType 方法表，网络读写/RESP 状态，I/O fan-out/fan-in 后由主命令执行器执行；addReply 不是写 socket 完成 | connection.h, networking.c, ae.c |

## 自动化门禁
- `scripts/validate_site.py` 验证 28 章、1–15 章语义结构、文件引用与所有 SVG 的 XML/标题/描述/viewBox。
- `scripts/browser_qa.py` 覆盖首页 + 01–15 章、360/390/1440 三种视口共 48 次；检查 JS console、横向溢出、图像解码与新批次机制控件更新。
- 运行结果必须以 CI 日志为准，不得先行宣称通过。
- 本次任务暂未实机编译 Redis 7.2.4，也未逐条执行 redis-cli 示例；文章中的预期输出是依据源码和命令契约编写，需在独立运行时复现。
- 16–28 章节仍保留原文且标注待审计，不应赋予已重构状态。
