# Docs / 文档维护

- 用户文档：`docs/**`（中文）与 `docs/en/**`（英文），必须保持镜像同步。
- Agent 文档：`docs/agents/**`，由 VitePress `srcExclude` 排除，不会打包进用户站点。
- 站点配置：`docs/.vitepress/config.mts`（侧边栏、导航、locales）。
- 根目录 `AGENTS.md` 只保留全局规则与到本目录的链接。

## 约定

- 不轻易改现有文件名；新增页面要同时补 `docs/` 与 `docs/en/`。
- 中文页 `docs/<path>.md` 对应英文页 `docs/en/<path>.md`。
- 英文内部链接使用 `/en/` 前缀；链接锚点按各自语言标题生成。
- 面向用户的页面只保留“怎么用 / 配置什么”，实现原理放到 `docs/agents/`。
- 新增配置字段先改 `config.example.yaml`，再同步配置文档。
- 构建验证：`cd docs && bunx vitepress build`。
