# Redis 源码解析：从字节到集群
> 28 个章节的 Redis 源码阅读路线。28 章均已按 Redis **7.2.4** 重写，并为每章附 `evidence/NN.json`。

**课程入口**：[GitHub Pages](https://1998x-stack.github.io/redis-source-analysis-tutorial/) · [仓库](https://github.com/1998x-stack/redis-source-analysis-tutorial)

## 阅读路线
1. **01–10 基础与容器**：从启动调试、内存、SDS、dict、skiplist、对象到 String/Hash/List 的源码执行链。
2. **11–15 集合与执行引擎**：Set/ZSET、Stream/Geo/HLL、文件事件、定时器与网络 I/O（新增 14 张 SVG、机制交互、可复现实验）。
3. **16–28 命令全链路、持久化与工程**：命令执行、RDB/AOF、复制、集群、性能定位、Lua/模块（均按 Redis 7.2.4 重写并附 evidence）。

## 仓库结构
```
.
├── AGENTS.md                       # 写作、源码验证、SVG 与 QA 协议
├── docs/                           # GitHub Pages 静态发布根目录
│   ├── index.html                  # 阅读首页 / 学习路径 / 全部 28 章
│   ├── catalog.json                # 课程清单及 QA 状态
│   ├── chapters/NN.html            # 28 篇独立文章
│   ├── chapters/theme.css          # 历史文章兼容样式（当前章节已不再引用）
│   └── assets/{css,js,svg}/        # 共享排版、交互、专业矢量图
├── scripts/validate_site.py        # 无依赖的本地完整性检查
└── .github/workflows/             # CI + GitHub Pages 部署
```

根目录与 `docs/01.html`～`docs/28.html` 设兼容重定向，避免旧链接失效。28 章正文均位于 `docs/chapters/`，按 Redis 7.2.4 重写。

## 本地阅读与检查
```bash
python3 -m http.server 8000 -d docs
# 浏览 http://localhost:8000/
python3 scripts/validate_site.py
# 若已构建独立 Redis 7.2.4，可运行真实机制冒烟实验：
python3 scripts/redis_724_smoke.py /path/to/redis-724/src
```
静态站点无 Node/框架构建依赖。在 GitHub 的 Settings → Pages 中选择 **GitHub Actions** 作为发布源；`pages.yml` 会上传 `docs/` 并部署。切换源属于仓库设置，需要管理员检查；仅添加工作流不代表已经上线。

## 版本与证据
源码锚定 `redis/redis` 的 [7.2.4 标签](https://github.com/redis/redis/tree/7.2.4)。文章引用版本固定的文件，以免后续实现改变误导读者。Redis 的 7.2/7.4/8 许可及模块集不同，详见 [Redis 官方许可说明](https://redis.io/legal/licenses/)。

视觉叙事受 [Olah-style-posts](https://github.com/1998x-stack/Olah-style-posts) 启发，图解为本仓库新绘制，不复用第三方图像。