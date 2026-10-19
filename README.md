# Martin Luk Trading System V1

基于香港交易员 Martin Luk 公开表述的美股交易研究项目。仓库名称暂保留 `web3`。

## 目标与边界

V1 以高保真复刻实际交易系统为目标，用于研究与学习，不以优化收益率为目标。忠实复刻优先于策略优化；不得发明规则并归因于 Martin Luk，不得为方便编程而简化重要交易逻辑。公开资料未明确披露的规则统一标记为 `UNVERIFIED`。

后续研究方向包括 Pullback、Breakout、Episodic Pivot、Parabolic。名称仅代表待核实的研究方向，不代表已确认其定义或使用方式；实现前必须建立可追溯的公开证据。

当前仅提供项目骨架、测试框架和 CI，尚未实现行情获取、指标、选股、策略、风控或回测。不开发 V2/V3，不连接真实券商，不执行实盘交易。

## 开发

要求 Python 3.12。在仓库根目录执行：

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

无需 API 密钥、行情订阅或外部服务，无应用服务需要启动。当前测试只验证包可安装、可导入及模块定位，不验证交易规则或盈利能力。

## 目录

```text
src/
  data/         # 美股历史行情（预留）
  indicators/   # 技术指标（预留）
  scanner/      # 股票筛选（预留）
  strategies/   # 交易策略（预留）
  risk/         # 风险与仓位管理（预留）
  backtest/     # 历史回测（预留）
tests/          # 自动化测试
docs/           # 原始资料与研究文档
.github/workflows/ci.yml
```

采用 `src` 布局；各模块目前仅包含说明。参见 [资料索引](docs/sources.md)、[Codex 规范](AGENTS.md)、[贡献指南](CONTRIBUTING.md)。所有开发通过分支和 Pull Request 提交，禁止直接推送远程 `main`。
