# Redis 06–10 第一轮证据与质量复核（2026-11-22）

## 固定证据
全部新增文章以 Redis 官方代码仓库 `7.2.4` tag 为主线。逐章对应 `evidence/06.json` 至 `10.json`。原有 01–05 内容与旧章节链接保留。

| 章节 | 旧稿风险 / 修正 | 主要源码 |
|---|---|---|
| 06 | 不再复用旧式 dictht；明确默认 SipHash 而非 MurmurHash2；SCAN 可重复且 COUNT 非强制配额 | dict.h, dict.c, siphash.c |
| 07 | 跳表在 t_zset.c；内部 rank 1-based 与 ZRANK 0-based；Set 可使用 intset/listpack/HT | t_zset.c, t_set.c, intset.c |
| 08 | 删除“List 始终 quicklist”错误，新增 44 字节 EMBSTR 创建阈值与 LFU/LRU 复用字段 | server.h, object.c, t_list.c |
| 09 | 辨析 SET NX/XX/GET 与 TTL；HSET 返回新增字段数；HFE 属于 Redis 7.4+ | t_string.c, t_hash.c, Redis 7.4 release |
| 10 | 新 List 由 createListListpackObject 创建；阻塞的是客户端而不是主事件循环；BLPOP 不含消费确认 | t_list.c, blocked.c, db.c |

## 原创可视化与限制
本轮新增 13 张语义 SVG，包括完整的跳表层高/跨度、双表 rehash、backed object、SET/Hash 路线、List 阻塞状态机。
采用共享 CSS 和无第三方 JS；图解含 `title`, `desc`, `viewBox`；具体布局需经浏览器多视口截图确认。
小型交互解释仅显示固定状态或数学计算，不读取在线 Redis，不能当作真实运行时性能基准。

## 测试状态说明
- 页面/目录/SVG/链接完整性：由更新后的 `scripts/validate_site.py` 及 PR CI 检查。
- Chromium 360、390、1440px：由 `scripts/browser_qa.py` 与单独 Actions 工作流执行，覆盖本轮新章节的控件变化。
- **未在本任务环境编译或运行 Redis 二进制**；命令示例为待读者按 7.2.4 自行执行的复现实验。不得声称本轮已完成运行时测试。
- 11–28 保留原稿并明确标注待审计；后续仍需核对跨版本 Redis 8 的 API/许可差异。
