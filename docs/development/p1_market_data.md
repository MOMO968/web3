# P1：行情数据与指标契约

本阶段按 [V1 正式规格](../spec/v1_final_development_spec.md) 第 5、6.4、9、11 节实现数据基础。无买卖信号、仓位计算、交易引擎或 UI。**下述计算、预热及聚合约定为 APPROXIMATION/工程定义，不是 Martin 本人披露的固定参数。** ADR 与 RS 的窗口必须由调用方显式指定；本阶段没有引入选股门槛。

## 安装及离线示例

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python examples/p1_local_data.py
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

示例读取 `examples/synthetic_minutes.csv`，只含虚构代码 DEMO 的五根分钟线，无密钥、网络请求或真实行情授权需求。预期聚合 OHLCV 为 `(100, 106, 99, 105, 150)`、coverage 为 1。它不演示真实分钟历史覆盖，也不代表后续回测已完成。

新增依赖 `exchange-calendars==4.11.2` 用于 XNYS 日历；显式固定 `pandas==2.3.3`，因为实测此日历版本在 pandas 3 的日期单位下会将范围内日期误判为越界。日历版本和数据版本均应作为后续研究快照的一部分。当前 NumPy 2.5 环境下该日历依赖有弃用警告，测试通过，未隐藏警告。

## 数据模型

- `Bar`：symbol、start/end、available_at、timeframe、session、OHLCV、adjustment、complete、交易时区及币种。USD 价格、股数成交量，零成交量允许；不支持期货/外汇或其他币种。
- `Timeframe`：`1m`、`5m`、`15m`、`60m`、`1d`。日线覆盖完整常规交易时段，不以 UTC 零点或自然日时间戳代替开收盘。
- 所有 datetime 必须带时区，可用 UTC 或美东表示；比较按真实时刻，输出日历区间为 `America/New_York`。
- K 线标记开端，区间为 `[start, end)`；OHLCV 最早只能在 end 时刻使用，available_at 不得早于 end。日线不能在收盘前使用当日高低收盘。
- 非有限/缺失价格、非正价格、负/非有限成交量、OHLC 排序错误、重复记录、时段越界、非交易日、错位周期均拒绝，不做静默修复。
- Provider 会排序乱序输入，但不会合并重复项。同一股票、起点、周期、时段和复权口径有多个修订版本时必须分开快照；没有实现多版本数据库。
- CSV 列及 ISO 时间戳格式以示例文件为准；缺列或坏行报错并给出行号。调用方显式提供能力、版本及可选 adjustment_as_of。

## 查询、缺口和数据可用性

`Query` 显式要求 symbol、timeframe、start/end 和 as_of，默认常规时段与 RAW。start/end 是请求范围；as_of 是研究者当时可观察的上界，两者不能混淆。

只返回 **start >= 请求 start、end <= 请求 end、end <= as_of、available_at <= as_of** 的整根 K 线；切到桶中间的请求边缘不生成部分桶。跨日查询只枚举真实交易时段；周末和节假日不是缺口。不请求所有时段的混合序列，盘前和常规时段分开查询。

`DataResult` 包含 query、bars、expected（已闭合的预期日历区间）、missing（整根缺失或尚未到达）、issues、provider、version 及复权可用时点。构造时验证时间边界、记录身份、缺口声明及顺序，避免 adapter 返回未来数据。

- `coverage` = 完整返回 K 线数 / 已闭合预期 K 线数；无已闭合区间时为 None，不伪装 100%。
- `complete` 仅在有预期区间、无问题/缺口、且每根 K 线完整时为 True。
- issues 包括 `REQUEST_EXTENDS_BEYOND_AS_OF`、`NO_COMPLETED_INTERVALS`、`MISSING_OR_NOT_YET_AVAILABLE`、`INCOMPLETE_SOURCE_BARS`、`INCOMPLETE_CONSTITUENTS`。
- 挂牌覆盖缺失、停牌、供应商缺口和延迟到达无法仅凭 OHLCV 区分，均显式标记。不会补零、插值或前向填充。
- 聚合桶有一部分分钟缺失时，可返回可观察部分的 OHLCV 供诊断，但标记 complete=False；全桶缺失列入 missing。消费者必须检查完整性，不能将诊断值用于策略。
- 查询未来范围时，已完成历史部分仍可返回，但 complete=False。未结束的 5/15/60 分钟桶一律不暴露，不能用未来分钟补齐。

## Provider 边界

`MarketDataProvider` 定义 `capabilities` 和 `history(Query) -> DataResult`。未来供应商可实现此契约，不需要改变指标或聚合算法。`Capabilities` 明示周期、历史分钟、盘前、公司行为、历史元数据和复权能力；能力不等于每只股票每个时刻都有覆盖。

`LocalProvider` 支持构造的 Bar 快照；`data.csv_loader.load_csv` 提供本地 CSV 入口。`AggregatingProvider` 以任意支持 1m 的 Provider 为源合成 5/15/60m，其他周期委托原 Provider；此 adapter 不提供公司行为/历史元数据。

缺能力抛 `CapabilityError`（如 `PREMARKET_UNAVAILABLE`、`TIMEFRAME_UNAVAILABLE`、`ADJUSTMENT_UNAVAILABLE`）。公司行为和历史元数据方法当前明确报不可用。没有绑定真实供应商，行业/市值/退市证券覆盖、QQQ/IWM 实际历史及历史分钟盘前数据均未交付；需要对应数据后另行接入，不拿普通交易时段冒充盘前。

## 交易日历与聚合

使用 `exchange_calendars` 的 XNYS 日历，显式支持 1990–2035 年，超范围报错。该日历为当前版本的交易日安排，未来临时休市或历史修订需升级/重新核查；不是每个历史时点当时发布的日历版本档案。其他市场或证券的特殊交易安排不支持。

- 常规时段通常 09:30–16:00 美东，夏令时 UTC 开盘由 14:30 变为 13:30，提前收市以日历为准（测试覆盖 2024-07-03、11-29、12-24 的 13:00 收市）。
- 盘前工程约定为交易日 04:00–常规开盘，含提前收市日。历史不同年代/交易所不保证均有此覆盖；数据缺失仍会披露，不假设供应商从 04:00 有数据。
- 不提供盘后。日线只含常规时段，不合并盘前。
- 5/15/60m 各自从所选时段开端锚定；常规小时线从 09:30 起，最后一根为 15:30–16:00；13:00 提前收市的尾桶为 12:30–13:00。盘前小时线从 04:00 起，不与常规时段混桶。
- 桶末尾截到该时段结束。日历规定的 30 分钟尾桶如果所有分钟齐全就是完整桶，不是数据不完整。
- 聚合 O=首根 open、H=max high、L=min low、C=末根 close、V=sum volume；available_at 为桶终点及所有可用子 K 线 available_at 的最大值。延迟分钟未到达时不会偷看其值。

## 复权、修订与历史时点限制

RAW、SPLIT、TOTAL_RETURN 是不同口径，不能混用。**本实现不执行拆分或分红调整，也不声称提供公司行为数据。** 调整后的价格须由可信 adapter/本地快照提供，且必须声明 adjustment_as_of；仅在该时点不晚于查询 as_of 时允许使用，避免把包含未来公司行为的当前复权快照用于较早历史。

available_at 必须是该数值版本实际可知的时间；晚到/修订的记录不能回填成原始收盘时刻。当前版本不是可信时间戳认证服务，无法从 CSV 自动验证供应商是否如实标注。若只有今天下载的历史修订快照，应保守标记今天可用，不能宣称已拥有真正历史时点行情。

不自动连接公司行为服务，不重建历史股票池、行业或市值，不保证无幸存者偏差。RAW 价格跨拆股会产生机械跳变；使用前必须明确口径和覆盖，不能据此误判强弱。

## 指标工程定义

优先使用 `daily_indicators(DataResult, adr_period=...)`：按交易日历 expected 建立逐日位置，将缺失日保留为 None，使用已闭合且可观察的日线。底层数值函数假定调用方已经按此时间轴提供数据，缺口不能通过缩短列表隐藏。

| 指标 | 工程公式与边界 |
| --- | --- |
| EMA 9/21/50/150 | 连续 n 个有效 close 的 SMA 作为首值，之后 `EMA_t=EMA_prev+2/(n+1)*(close_t-EMA_prev)`。此前输出 None；None/不完整日线重置状态，重新预热。不使用未来值或反向填充。 |
| ADR (%) | `mean(100*(high/low-1), n 个连续完整日线)`。n 显式可配置，非 ATR，也不填入 Martin 未确认的周期。缺失/不完整重置窗口。 |
| RS (%) | 显式传入不同代码的 benchmark 日线 DataResult（例如 QQQ 或 IWM）及 n；`100*((C_t/C_t-n)/(B_t/B_t-n)-1)`。n 是交易日间隔，需 n+1 个对应完整交易日。以真实交易时刻对齐，as_of 和复权口径必须相同；缺任一天输出 None，不前向填基准，也不是百分位 RS 排名。 |
| Dollar Volume | RAW close × 原始股数 volume，单位 USD，是成交额代理而非逐笔真实成交金额。复权价格与股数口径未作协调，调整后的 bar 返回 None，不能将其当作原始美元成交额。 |
| EMA 分类 | EMA9>EMA21>EMA50 为 Lead，反序为 Lag，其他严格不等排列为 Mediocre；任何缺值或任意两条相等为 Unknown。不是买卖信号。 |

pipeline 返回时间轴、EMA 字典、ADR、Dollar Volume、分类及 as_of、数据版本、参数、APPROXIMATION 标识。RS 通过单独函数传入基准，避免隐式绑定供应商或基准。

数值函数拒绝非有限/非正价格及无效窗口。无成交量日不会被自动认定流动性合格；本阶段不实现 scanner 门槛。短历史不足 150 根时 EMA150 合法返回 None。

## 验证范围

构造数据验证精确值、预热/缺口、EMA 分类、基准对齐、1→5/15/60m、开收盘及短尾、夏令时、提前收市、节假日、盘前隔离、缺能力、修订时间与未来价格扰动不影响过去输出。CSV 示例同样有预期结果测试。

测试验证实现的工程契约，不验证供应商实际数据质量或 Martin 交易策略，也未运行真实数据回测。下一阶段 P2 需另行授权。
