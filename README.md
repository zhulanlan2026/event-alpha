# 事件 Alpha 候选因子

从财经快讯生成待检验的事件 Alpha 卡片。模型负责把新闻拆到赛道并写出逻辑，分数、去重和入库由代码完成。回测、正交和交易不在这个仓库里。

当前版本是逻辑修订版 V1.1。不含舆情。

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

通过的卡片写入 `out/candidates.jsonl`，状态为 `pending_verify`。重复运行不会再写同一张卡片。

## 接真实新闻

事件主源是财联社电报，函数 `stock_news_global_cls`。电报失败或为空时，改用东财快讯 `stock_news_global_em`。两条都经过 AKShare 1.20.65。

星矿是财联社的机构接口。没有账号时不调用，也不伪造数据。

```bash
export DEEPSEEK_API_KEY=你的密钥
PYTHONPATH=src .venv/bin/python -m event_alpha --live --out out
```

没有 `DEEPSEEK_API_KEY` 时，`--live` 会直接退出。实时快讯正文只留在 `out/`，这个目录已忽略，不要提交到 Git。

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

一条新闻可以产出多张卡片，每张对应一个申万一级行业。去重键是新闻编号加赛道。因子库不写进下一次的提示词。
