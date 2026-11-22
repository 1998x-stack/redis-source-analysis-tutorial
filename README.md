# Redis 源码解析：从字节到集群
> 28 个章节的 Redis 源码阅读路线。01–27 章以 Redis **7.2.4** 为源码基线；第 28 章交叉核对 Redis 8.10.3 GA 与 8.12-RC3 预发布状态。全部章节均已完成独立内容重构。

**课程入口**：[GitHub Pages](https://1998x-stack.github.io/redis-source-analysis-tutorial/) · [仓库](https://github.com/1998x-stack/redis-source-analysis-tutorial)

## 阅读路线
1. **01–10 基础与容器**：从启动调试、内存、SDS、dict、skiplist、对象到 String/Hash/List 的源码执行链。
2. **11–15 集合与执行引擎**：Set/ZSET、Stream/Geo/HLL、文件事件、定时器与网络 I/O（14 张 SVG）。
3. **16–20 命令、持久化与复制**：命令分派、RDB、Multi-Part AOF、过期/淘汰、PSYNC 与全量同步（15 张 SVG）。
4. **21–25 高可用与诊断**：ACK、Sentinel、Cluster、INFO/LATENCY、Bigkey/Hotkey、GDB/perf/strace（新增 15 张 SVG 与可运行隔离实验）。
5. **26–28 扩展与版本演进**：Lua VM 与事务语义、Module 自定义类型和阻塞客户端、Redis 8 版本/许可演进与 RESP2 Mini-Redis；每章均有源码依据、图解和可复现实验。

## 仓库结构
```
.
├── AGENTS.md                       # 写作、源码验证、SVG 与 QA 协议
├── docs/                           # GitHub Pages 静态发布根目录
│   ├── index.html                  # 阅读首页 / 学习路径 / 全部 28 章
│   ├── catalog.json                # 课程清单及 QA 状态
│   ├── chapters/NN.html            # 28 篇独立文章
│   └── assets/{css,js,svg}/        # 共享排版、交互、专业矢量图
├── examples/
│   ├── mini-redis/                 # epoll + RESP2 教学服务器和集成测试
│   └── redis-module/               # Redis 7.2.4 Module API 计数器
├── tests/test_counter_module.py    # RDB / AOF rewrite / WATCH 模块集成测试
├── scripts/validate_site.py        # 无依赖的本地完整性检查
└── .github/workflows/             # CI + GitHub Pages 部署
```

根目录与 `docs/01.html`～`docs/28.html` 设兼容重定向，避免旧链接失效。每章正文均位于 `docs/chapters/`；示例源代码保存在仓库根目录 `examples/`，页面使用稳定 GitHub 源码链接，避免 GitHub Pages 指向发布目录之外的文件。

## 本地阅读与检查
```bash
python3 -m http.server 8000 -d docs
# 浏览 http://localhost:8000/
python3 scripts/validate_site.py
make -C examples/mini-redis test
# 若已构建独立 Redis 7.2.4，可运行真实机制冒烟实验：
python3 scripts/redis_724_smoke.py /path/to/redis-724/src
# 构建并测试 Module 自定义类型（RDB / AOF rewrite / WATCH）：
cc -std=c11 -O2 -g -Wall -Wextra -Werror -fPIC -shared \
  -I /path/to/redis-7.2.4/src -o /tmp/countermod.so examples/redis-module/counter_module.c
python3 tests/test_counter_module.py /path/to/redis-7.2.4/src /tmp/countermod.so
```
静态站点无 Node/框架构建依赖。在 GitHub 的 Settings → Pages 中选择 **GitHub Actions** 作为发布源；`pages.yml` 会上传 `docs/` 并部署。切换源属于仓库设置，需要管理员检查；仅添加工作流不代表已经上线。

## 版本与证据
源码锚定 `redis/redis` 的 [7.2.4 标签](https://github.com/redis/redis/tree/7.2.4)。文章引用版本固定的文件，以免后续实现改变误导读者。Redis 的 7.2/7.4/8 许可及模块集不同，详见 [Redis 官方许可说明](https://redis.io/legal/licenses/)。

视觉叙事受 [Olah-style-posts](https://github.com/1998x-stack/Olah-style-posts) 启发，图解为本仓库新绘制，不复用第三方图像。