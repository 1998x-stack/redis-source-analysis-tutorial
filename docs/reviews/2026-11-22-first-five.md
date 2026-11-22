# 第一批源码交叉核验与质量说明（2026-11-22）
- 对照基准：redis/redis `7.2.4`。以该标签的 `README.md`、`server.c`、`networking.c`、`zmalloc.c`、`sds.h` / `sds.c`、`ziplist.c`、`listpack.c`、`quicklist.c` / `quicklist.h`、`t_list.c` 为主要证据。
- 01 的职责图只表达主请求路径，不将简化伪代码当作完整 `processCommand` 实现。
- 02 不假定发行版 Redis 含匹配 DWARF；命令需在 Linux/macOS 实机运行。
- 03 修正“每次 zmalloc 都写统计前缀”的错误：`HAVE_MALLOC_SIZE` 分支下 `PREFIX_SIZE=0`。
- 04 分离 SDS 头部类型与 redisObject 的 embstr/raw/int 编码，并记录 allocator usable size 可能影响真实 alloc。
- 05 将 ziplist 说明限定为历史机制；在 Redis 7.2，List 值可以具有 listpack / quicklist 对象编码，不是“只能 quicklist”。
- 十张 SVG 均为自绘，保留 title/desc/viewBox；无第三方图像复制。
- 站点结构 / 资源检查将由 `scripts/validate_site.py` + PR CI 验证；尚未证明 Playwright 多视口浏览器检查已经通过，也尚未实机运行 Redis 示例。
- 06–28 原文保留，仍未完成 Redis 7.2.4/8.x 跨版本技术审计；尤其留意涉及 HFE、io_uring、许可与版本新特性的叙述。
