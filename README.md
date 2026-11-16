# 事件 Alpha 候选因子

从财经快讯生成待检验的事件 Alpha 卡片。模型负责把新闻拆到赛道并写出逻辑，分数、去重和入库由代码完成。回测、正交和交易不在这个仓库里。

当前版本是逻辑修订版 V1.2。不含舆情。上游交出可交给中游检验的因子定义，不做中性化、IC 和回测。

## 运行样例

样例不需要密钥，也不访问网络。四条短句是仓库自写的，不是电报原文。

```bash
cd event-alpha
python -m venv .venv
.venv/bin/pip install -r requirements.txt
PYTHONPATH=src .venv/bin/python -m event_alpha --out out
PYTHONPATH=src .venv/bin/python -m pytest
```

在这台机器上，依赖已经装在上一级目录的 `.venv`：

```bash
cd "/mnt/d/Projects/A股因子/event-alpha"
PYTHONPATH=src ../.venv/bin/python -m event_alpha --out out
PYTHONPATH=src ../.venv/bin/python -m pytest
```

样例期望：

- 电力设备补贴：入库，正分，`qualitative_only`
- 铜冶炼减产：入库，铜价未接入时 `quantitative_missing`，强度不超过 0.45
- 单一股东减持：不入库，原因 `no_alpha`
- 制造业 PMI 49.3：入库，负分，偏离口径 `pmi_vs_50_and_trailing_12`，`consensus_surprise` 为空

命令行样例只跑电力设备这一条。测试仍覆盖上面四条短句。

通过的卡片写入 `out/candidates.jsonl`，并在 `out/factors/` 各写一份给中游的因子文件，状态为 `pending_verify`。样例成份不是真实股票，代码以 `SAMPLE` 开头。重复运行不会再写同一张卡片。

## 真实新闻

把密钥放在 `event-alpha/.env`，不要写进对话，也不要提交到 Git：

```
DEEPSEEK_API_KEY=你的密钥
```

```bash
PYTHONPATH=src ../.venv/bin/python -m event_alpha --live --limit 8 --out out
```

`--live` 拉取财联社电报。电报失败时改用东财快讯。另外拉取东财最新的重大事项和资产重组公告。每条都必须有日期和钟点，缺钟点的直接丢掉，不用当前时间填。

AKShare 的 `stock_notice_report` 只返回公告日期。同一条公告记录里的 `display_time` 才是发布时间，程序用这个字段。

有效期从该时间起算：短期 5 天，中期 20 天。窗口外的卡片不入库，原因是 `expired`。

## 接真实新闻

事件主源是财联社电报，函数 `stock_news_global_cls`。电报失败或为空时，改用东财快讯 `stock_news_global_em`。公告来自东财公告接口，字段与 AKShare 公告表一致，并补上被表格丢掉的发布时间。

星矿是财联社的机构接口。没有账号时不调用，也不伪造数据。

```bash
PYTHONPATH=src .venv/bin/python -m event_alpha --live --limit 8 --out out
```

没有 `.env` 里的 `DEEPSEEK_API_KEY` 时，`--live` 会直接退出。实时快讯正文只留在 `out/`，这个目录已忽略，不要提交到 Git。

数值校准同样走 AKShare：

| 用途 | 函数 | 是否进入分数 |
|---|---|---|
| 制造业 PMI | `macro_china_pmi` | 进入。相对 50，并相对近 12 期 |
| CPI | `macro_china_cpi` | 宏观事件进入。列「全国-同比增长」 |
| PPI | `macro_china_ppi` | 宏观事件进入。列「当月同比增长」 |
| 工业增加值 | `macro_china_industrial_value_added` | 宏观事件进入。列「同比增长」 |
| 期货主力 | `futures_main_sina` | 已对照的供需事件进入。只用新闻日之前的收盘价 |
| 行业指数 | `stock_board_industry_hist_em` | 不进入分数。只写新闻日前最多 5 个交易日涨跌 |

这版 AKShare 没有带预测值的宏观接口。字段 `consensus_surprise` 固定为空，文案里不写「超预期」。

## 分数

幅度档：weak 0.35，mid 0.65，strong 0.90。`base = 置信度 × 幅度档`。

宏观事件，或已对照大宗的供需事件，在取到偏离时：

`intensity = 0.6 × base + 0.4 × min(1, |偏离| / 2)`

取不到数时，强度上限 0.45，标记 `quantitative_missing`。政策、技术、海外，以及没有品种对照的供需，标记 `qualitative_only`，不设这道上限。

`signed_score = 方向 × intensity`。利多为正，利空为负。中性、强度低于 0.20、偏离与方向明显相反，都不入库。

一条新闻可以产出多张卡片，每张对应一个申万一级行业。新闻正文明确写出某一个二级业务时，卡片再补该申万二级；没写明、对不上该一级，或同时指向多个二级，二级留空。去重键是新闻编号加一级行业。因子库不写进下一次的提示词。

## 交给中游

入库卡片同时写成 `out/factors/{因子名称}.json`。中游读取的基础属性是名称、逻辑、表达式、适用赛道、持仓周期。同文件还有新闻时间、有效期、方向、带符号分数、二级行业、赋值规则和成份股。

赋值规则：有效期内，申万一级成份股的因子值等于 `signed_score`，有效期外为 0。同一个一级行业里的分数相同，所以这张因子先检验行业方向，保留行业涨跌。`in_level2` 为真的股票只是一级内部的对照子集，分数不另算。没有这组差别时，不做行业中性化。

实时成份来自申万行业指数当前成份，函数 `index_component_sw`。计入日晚于新闻日的股票剔除。已经调出指数的历史成份，这个接口不提供。二级没有公开发布的指数时，成份说明是 `level2_missing`，一级篮子仍然给出。拉不到成份时说明是 `missing`，不编造股票代码。
