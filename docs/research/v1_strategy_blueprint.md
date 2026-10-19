# Martin Luk Trading System — V1 统一策略总纲（研究草案）

> **状态：RESEARCH IN PROG​RESS / 不可直接用于实盘。** 本文件汇总截至2026-10-19的研究成果，按系统执行环节而非访问批次组织；**不新增、也不替代具体证据**。规则出处和核查状态以 [rule_registry.md](rule_registry.md)、[source_catalog.md](source_catalog.md)、[trade_case_studies.md](trade_case_studies.md)、[unknowns_and_conflicts.md](unknowns_and_conflicts.md) 为准。若本文与逐条出处矛盾，应暂缓编码并重新核对原文。

## 0. 研究基准与版本

- **V1高保真目标**：复现 Martin 本人公开描述的交易方法，不追求回测收益最大化；无法唯一确定的条件不可冒充本人原始算法。
- **时间版本**：2024年的 Breakout / EP / Parabolic 相关实践（2025年本人文章及访谈回顾），与2025年以 Pullback 为重点的实践（2026年深度访谈）分开保留。
- **证据强度**：
  - `VERIFIED_PUBLIC_SELF_REPORT`：本人署名文章明确自述，可确认其公开表达，但非经纪商流水认证；
  - `TIMED_TRANSCRIPT_REVIEW`：有原访谈带时码转录，尚未逐句对照音频/图表；
  - `TRANSCRIPT_REVIEW`：本人访谈工作转录，时间码及ASR待验证；
  - `UNVERIFIED`：包括二手观点、未经核实阈值及缺失原话内容。
- 两段用户提供的博主解读视频 [AUX-007](https://www.youtube.com/watch?v=lqLm-SBflTI)、[AUX-008](https://www.youtube.com/watch?v=Y7Xb8LjXacI) **尚无法取得可复核视频/字幕正文**；当前不将其中任何具体策略观点归属于 Martin。其他二手解读亦同。

## 1. Market Context — 市场环境与操作风格

**已公开表达**：Swing / trend-following，以当时市场反馈调整 Breakout、Pullback、Short 等手法。关注 QQQ/IWM、领先和落后股名单、自身新开仓表现；市场震荡、反复止损时减少出手，指数快速延伸时对新开仓更谨慎。

**不可编码部分**：市场宽度指标、交易反馈统计窗口、市场状态与仓位比例的映射均没有本人公开的完整统一算法。

**关联**：ML-T001–002、ML-T021、ML-T027、ML-T037–040、ML-E010。

## 2. Universe & Scanning — 选股与观察名单

**已公开表达**（以2024方法为基准）：
- Potent：寻找前一日最强股票；Pre-market：寻找盘前成交活跃、向上跳空股票；Leader：周末查看过去约一个月领先涨幅股票。
- Watchlist 含每日候选、小市值(<$5B)、Lead / Mediocre / Lag。Lead 为 EMA9>EMA21>EMA50；Lag相反；Mediocre为其他两种交错排列（均线相等如何归类未披露）。
- 偏好高波动（曾公开ADR>5%的经验偏好）及较高 Dollar Volume；观察同一板块多股转强、RS与日/周形态。

**未披露**：gap、成交额、最低股价、leader top-N、ADR窗口/公式、RS计算口径；2025访谈中展示的 scanner 屏幕参数尚未核查。**不可自行设为官方默认阈值**。

**关联**：ML-P001、ML-P004–007、ML-E008–009、ML-E011–014、ML-T033–036。

## 3. Setup — 候选交易形态

| Setup | 已出现的本人说明/案例 | 尚缺关键输入 |
| --- | --- | --- |
| Breakout Long | 前日高点、Opening Range 1/5分钟高点、区间高点突破；偏好日/周整理结构，2024实践较多 | Base成熟度、tightness、情境性提前入场 |
| Pullback Long | 强势股回到日/小时9/21 EMA、AVWAP、结构支撑，在小周期确认反转；2025更常见 | 首次回踩如何定义、支撑容差、趋势质量筛选 |
| EP | 个别事件/跳空与前期高点的组合，如COIN历史交易；不把个例gap>10%升级全局门槛 | 统一催化、流动性、gap/价格过滤 |
| Parabolic Long/Short | 被本人提及为实际手法 | 缺足够具体、完整的入场离场定义 |
| Pullback/Resistance Short | 下降21/50 EMA、swing-high AVWAP阻力，低周期前一小时低点跌破或VWAP复测失败 | “失败”的定义、borrow/shortable约束、具体确认 |

**关联**：ML-E001–007、ML-P009–013、ML-T010–020。

## 4. Entry — 精确入场

- **Breakout**：上一交易日高点或开盘首根1/5分钟K线区间高点突破，是已公开的**价格触发事件**；不能脱离合格结构过滤单独宣称完成策略。
- **Pullback**：高周期支撑（部分实例为小时9/21 EMA）之后，在1/5/15分钟K线突破前一根高点尝试Long；Short有前低跌破的镜像候选。开盘时更常看较短周期。
- **EP**：有COIN opening-range触发实例；不意味着所有EP统一如此。
- **No-lookahead**：用于决策的K线、当日高低点、EMA和成交量必须仅截至决策时刻。

**关联**：ML-E001–006、ML-T016–019、ML-P010。

## 5. Initial Stop, Sizing & Exposure — 初始风险

- 2024公开资料：单笔账户风险常见0.5%–1%；止损常见1%–5%，倾向不超过股票ADR的一半（经验而非无例外硬限制）。
- 2025–2026口述：单笔风险通常约0.5%，可随市场和账户状态调整；单股仓位多数25%–30%，某些做空研究提到不高于35%，需区分时期与交易类型。
- 初始止损一般事前确定并及时执行；有当日低点、入场触发K线低点（Short则相应高点）等不同候选位置。
- **可独立编码的算式**：`risk_budget = equity * risk_fraction`；`shares_by_stop = risk_budget / abs(entry - stop)`；实际股数还受仓位价值上限、最小单位、流动性、成交/滑点影响。
- **不能承诺止损等于最大实际亏损**：跳空、流动性恶化、卖空借券/强平等均可能影响成交。

**关联**：ML-P002–003、ML-P008、ML-P011、ML-E002–003、ML-T003–006、ML-T018。

## 6. Position Management & Exit — 加仓、减仓与离场

- 本人明确称**没有一套完全固定的卖出规则**；部分盈利交易在3R/5R附近、或明显延伸时分批减仓，也有强势趋势中不减仓的情况。
- 个别案例出现一次减约15%、某次收盘跌破9EMA全出、或沿9EMA稍下方设置保护止损的管理方式；这些**都不是所有交易的共同强制规则**。
- Short往往比Long更早落袋（本人口述约2–3天就可能开始减仓），特定极端反转交易（如TQQQ）持仓更短。
- **加仓**：现有证据不足以形成完整统一的 pyramiding 规则，不能从个别二次入场推导“所有盈利仓追加固定X%”。

**关联**：ML-T022–032、ML-P012、ML-E007、ML-C006–014。

## 7. Real Trade Case Regression — 历史交易案例

已登记 AMC、SOFI、COIN、QS、QBTS、HOOD、OKLO、TQQQ、BBAI 等本人讨论的案例，见 [trade_case_studies.md](trade_case_studies.md)。需用视频中的图表、当日行情、当时可获得的事件信息和实际成交证据复核。**历史案例是否吻合只可用于检验所声明的规则，不能反向最优化参数“拟合出”Martin的成绩。**

## 8. V1 复刻完成前的关键缺口（优先级）

1. **P0**：2025访谈约01:30–01:34的 scanner 屏幕截图或视频，确认真实字段和阈值。
2. **P0**：补充视频/本人图表逐笔验证 AMC、SOFI、COIN 的实际形态与触发点。
3. **P1**：2026 Pullback 的首次回踩、AVWAP锚点选择、走势过伸的过滤定义。
4. **P1**：各类 Exit 的分支选择、止损与持仓上限在不同交易时期的规则。
5. **P2**：EP、Parabolic和市场状态识别的进一步本人原始资料。

## 9. Codex 实现约束

- 本文为**整合目录和规格草案**，不是授权立即开发完整交易策略。
- 代码中的 Martin-specific 条件须引用源 Rule ID、适用时期、状态；不可静默把二手资料/工作假说设为“Martin默认规则”。
- 指标与价格事件等客观构件可独立开发和测试，市场筛选与离场策略不得超出已公开规则宣称“完整复刻”。
- V1任务不包含真实券商交易。当前完整 V1 **NOT READY**。
