# Codex 开发规范

## 范围与证据

- 当前只开发 Martin Luk Trading System V1，用于交易研究与学习。
- 忠实复刻优先于收益优化。不得自行发明规则并声称来自 Martin Luk。
- 公开资料未明确披露的规则必须标记为 `UNVERIFIED`，不能静默转成实现默认值。
- 实现规则前，在 `docs/sources.md` 登记原始来源、时间戳或段落、原文及解读；区分核实陈述与研究假设，记录冲突和缺失信息。
- 不得为方便编程而简化重要交易逻辑。缺失信息需明确记录，不能虚构结论。
- Pullback、Breakout、Episodic Pivot、Parabolic 是待核实的研究方向，不得仅凭名称推断个人规则。
- 本次基础建设不实现具体策略；不开发 V2/V3，不连接真实券商，不执行实盘交易。

## 工作方式

- 使用 Python 3.12 和简单的 `src` 布局，仅在需要时增加依赖或抽象。
- 使用当前隔离环境中的现有仓库；除非用户明确要求，不创建 Git worktree。
- 保留提交历史，使用功能分支和 Pull Request；禁止直接推送远程 `main` 或强制覆盖历史。
- 不提交凭证、受限行情数据、虚拟环境或生成的研究输出。
- 保持改动聚焦当前任务。

## 验证

在仓库根目录创建并激活 Python 3.12 虚拟环境，运行：

```bash
python -m pip install -e '.[dev]'
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

新增功能须有能发现实际行为错误的测试。基础导入测试不等于策略验证。汇报实际命令和结果，区分通过、失败、跳过和未运行。
