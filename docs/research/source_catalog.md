# Phase 2 原始资料目录与访问审计

## 研究边界与结论

核查日期：2026-10-19（Asia/Shanghai）。基准提交：`a23154596baf7ed557fafbdc2b81c77d5f6045b9`（任务开始时最新远程 main）。

本轮没有取得任何可核对的原始发言、字幕或交易案例。已核实资料范围为空，研究状态为 **受阻 / PARTIAL**。不能据此声称还原了 Martin Luk 的交易系统。本目录中的访问失败是运行时观测；来源内容和发布信息没有因此获证实。

## 证据分级

- `VERIFIED`：核对 Martin 本人的原始发言或可验证案例；不自动意味着规则可机械执行。
- `PARTIAL`：已有原始依据，但实施条件不完整。访问失败或只有用户线索不属于此状态。
- `UNVERIFIED`：尚未核实，或只有二手转述。
- `CONFLICTING`：不同公开资料存在明显冲突，需分别记录来源、时间和适用环境。

来源身份、单条规则真实性、可编码程度分别评价，不以发布者声誉代替逐条核查。

## SRC-001：首要访谈线索

- URL：https://www.youtube.com/watch?v=VKNEJA5r8zw
- 用户提供信息：TraderLion 于 2026-01-31 发布，约 4 小时 9 分钟。
- 发布者、日期、时长及 Martin 发言者身份：均尚未独立核实。
- 视频正式标题、原始语种、字幕类型与准确性：未知。
- 内容证据状态：`UNVERIFIED`。
- 视频页、字幕列表、oEmbed 元数据接口均访问失败：代理隧道返回 `403 Forbidden`。
- 全片已核查覆盖率：0%；未取得任一可核对片段。以用户所述时长计，约 00:00:00–04:09:00 全部待核查，准确结尾待确认。
- 未获取原始语音，未获取完整字幕，未核验自动字幕，不以简介或章节替代正文。

## 第一轮实际执行的访问尝试

使用 Python urllib，通过当前环境默认 HTTPS 网络路由，保留 TLS 校验。以下请求均未取得正文，不是目标站已确认不存在该内容。

| ID | 请求 URL | 目的 | 实测结果 |
| --- | --- | --- | --- |
| A01 | https://www.youtube.com/watch?v=VKNEJA5r8zw | 视频页、元数据和字幕线索 | Tunnel connection failed: 403 Forbidden |
| A02 | https://www.youtube.com/api/timedtext?v=VKNEJA5r8zw&type=list | 字幕轨列表 | 同上 |
| A03 | https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=VKNEJA5r8zw&format=json | 独立核对元数据 | 同上 |
| A04 | https://traderlion.com/?s=Martin+Luk | 查找发布者原始访谈或文章 | 同上 |
| A05 | https://www.google.com/search?q=Martin+Luk+trading+interview | 定位其他一手资料 | 同上 |
| A06 | https://www.bing.com/search?q=Martin+Luk+trading+interview | 另一搜索入口 | 同上 |
| A07 | https://x.com/search?q=Martin%20Luk&src=typed_query | 定位本人账号与发言 | 同上 |

A04–A07 只是检索入口，不能登记为已取得的原始发言。未找到可核实的本人 X 账号、其他视频、论坛帖子或历史交易案例；不猜测账号和链接。

## 网络诊断与恢复条件

环境配置显示网络为 restricted，仅选择 package_managers 预设，没有自定义放行域名。上述目的站未在可见规则中。代理拒绝与此一致；无法判定目的站自身是否还存在登录、反自动化或地区限制。

已保存增量网络草稿：`www.youtube.com`、`traderlion.com`、`www.google.com`、`www.bing.com`、`x.com`、`api.github.com`。保留原有预设；最后一个域名用于 PR 和 CI 查询。保存草稿不代表当前网络已应用，尚无发布验证记录。后续运行时观测显示部分站点已可访问，但 YouTube 仍失败，不能据此认定全部放行已生效。若后续返回明确的媒体或字幕资源域名，再按实际需要补充，不预先开放所有域名。

也可以使用用户提供且有出处的完整字幕或音频。导入后仍须检查覆盖范围、说话人、时间定位和关键数字；单有文件不代表已核验真实性。

## 恢复后的核查顺序（未执行）

1. 核实视频标题、发布者、日期、时长及发言者身份；保存来源与获取时间，不提交整段受版权保护原文。
2. 获取完整字幕，记录手工/自动字幕类型、语言、缺段和说话人；必要时对照语音核对数字、否定词、条件和例外。
3. 顺序覆盖全片并登记实际审阅区间，再按市场环境、选股、类型、入场、卖出、账户风险及案例提取规则。
4. 定位本人其他发言，核对账号身份；保留历史与当前方法的时间差，不把变化自动判为冲突。
5. 每条规则提供短摘录或准确转述及精确定位，所有强制执行条件分别审查；第三方资料仅用于定位。

## 第二轮复查及辅助资料（同日）

由于 GitHub API 已可用，重新检查所有目的站，并对新出现的页面继续定位：

| 请求 | 结果与限制 |
| --- | --- |
| A01–A03 原 URL | 视频页、字幕列表和 oEmbed 仍为代理隧道 403 |
| https://www.youtube.com/watch?v=VKNEJA5r8zw&hl=en | 增加语言参数后仍为代理隧道 403 |
| A04 原 URL | HTTP 200，搜索结果为 Clement Ang 问答和 Ty Rajnus 介绍，不是 Martin 原始访谈 |
| A05 原 URL；https://www.google.com/search?q=%22VKNEJA5r8zw%22 | HTTP 200，但仅返回需要跳转的页面，无可用结果正文 |
| A06 原 URL；https://www.bing.com/search?q=%22Martin+Luk%22+trading+interview 及 https://www.bing.com/search?q=Martin%20Luk%20TraderLion%20trading | HTTP 200，但结果集中为 Martin 吉他、电视剧等无关内容；未用搜索摘要作证据 |
| A07 原 URL | HTTP 200，动态页面壳，无可核对推文正文或本人身份 |
| https://traderlion.com/wp-json/wp/v2/search?search=Martin%20Luk&per_page=100 | HTTP 200，返回上述两篇文章；检查正文后未发现可定位 Martin 原始发言的链接 |

### AUX-002：Clement Ang 问答（第三方线索）

- URL：https://traderlion.com/profile/clement-ang/clement-ang-qa/
- 页面标题：Clement Ang (+522%) Answers 28 Trading Questions。
- 页面署名 Clement Ang，显示发布日期 2026-10-06；这是页面可见信息，未独立核对其历史版本。
- 访问：HTTP 200，读取 HTML 正文并定位到 Martin 姓名所在段落。
- 定位：包含 `take Martin Luk for example` 的回答段落。
- 内容：Clement 以 Martin 为例谈到紧止损与大量失败交易。这是他人的解释，没有 Martin 本人的对应原始陈述或参数，不能升级为 Martin 的止损规则。
- 对 Martin 规则的证据状态：`UNVERIFIED`，仅二手线索。未计入原始证据或可执行规则，也没有从中倒推出阈值。

### AUX-003：Ty Rajnus 介绍（第三方背景，非规则证据）

- URL：https://traderlion.com/profile/ty-rajnus/ty-rajnus-returned-382/
- 页面标题：How Ty Rajnus Returned 382% Short Selling in the 2025 US Investing Championship。
- 搜索页显示发布日期 2026-03-26，未独立核对历史版本。
- 访问：HTTP 200，检查正文中 Martin 姓名所在段落及相关链接。
- 定位：`The 2025 USIC Results in Context` 段落和排名条目。
- 内容：涉及 Martin 的竞赛成绩背景，并非其本人交易规则；不引用收益率倒推策略参数，也不将 Ty 的卖空逻辑归于 Martin。
- 对 Martin 规则的证据状态：`UNVERIFIED`；没有可复核的本人发言定位或本人真实成交记录。

本轮结果修正了“所有入口持续被代理拒绝”的早期观测，但未改变原始发言覆盖率 0% 的结论。当前阻塞是 YouTube 原始视频/字幕无法取得及其他入口未定位到可验证本人发言，不能将整个互联网都描述为不可访问。
