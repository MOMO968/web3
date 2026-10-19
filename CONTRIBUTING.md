# 贡献指南

1. 创建功能分支，不直接推送远程 `main`，不改写已有历史。
2. 按 README 使用 Python 3.12 安装开发依赖。
3. 保持改动聚焦 V1；策略研究先补充公开证据和 `UNVERIFIED` 项，再提出实现方案。本次骨架不包含策略实现。
4. 运行 `python -m pytest`、`python -m ruff check .` 和 `python -m ruff format --check .`。
5. 提交 Pull Request，说明改动、证据来源、测试结果和已知限制，待审查后合并。

参见 [资料索引](docs/sources.md) 和 [Codex 规范](AGENTS.md)。研究假设必须与原始表述分开，未披露细节不得被默认参数掩盖。不要提交凭证、受限行情数据或实际券商连接。
