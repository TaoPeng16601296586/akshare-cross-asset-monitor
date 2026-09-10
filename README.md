# 大类资产数据监测基座 v0.3

定位：**明日可展示的数据底座 + Dashboard 框架**。全部数据来自 AKShare 对公开数据源的封装，不做 AI 判断，不生成投资建议，不对缺失数据做模型补值。

## v0.2 关键变化

1. 中证指数改为优先使用 `stock_zh_index_hist_csindex()`，减少东财接口不稳定对沪深300/中证500/中证1000/中证红利的影响。
2. DXY 使用“东方财富 → 新浪”两级备用。
3. 中金所国债期货增加 `match_main_contract("cffex") + futures_zh_spot(..., market="FF")` 实时主力合约方案，用来补 TS/TF/T/TL 展示。
4. 增加国债/政策性金融债收盘收益率曲线。
5. 修复债券ETF名称分类，并保留 ETF 二级交易资金流。
6. 每日保存沪深交易所 ETF 份额快照，并生成真实的份额变化；没有足够历史时明确留空。
7. 商品增加中证商品指数。
8. 所有 `processed` 输出尽量采用中文字段名。
9. 增加 Streamlit Dashboard，仅展示客观数据和抓取状态。

## 明确不伪造的数据

以下数据如果 AKShare 当前没有稳定公开接口，本版本留空：
- DR001 / DR007
- R001 / R007
- 分机构现券净买入
- 债基实时久期
- 理财周度规模

FDR007 是“存款类机构回购定盘利率”，不会在本项目中改名成 DR007。

## 运行

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python src/run_all.py
streamlit run dashboard/app.py
```

浏览器会打开 Dashboard。

## 从 v0.1 升级

如果你已经在 `F:\akshare_cross_asset_monitor` 跑过 v0.1，建议不要删除原 `data/`，因为已有 ETF 份额快照有价值。

最简单：
1. 备份旧项目；
2. 用 v0.2 的 `src/`、`dashboard/`、`requirements.txt`、`README.md` 覆盖旧项目；
3. 保留旧 `data/`；
4. 再运行 `python src/run_all.py`。

这样 ETF 申赎模块会利用累计的真实交易所份额快照计算变化。

## 明天展示时建议强调

- 数据层和判断层严格分离；
- 当前平台只做“事实层”：价格、收益率、资金/份额、持仓、宏观；
- AKShare 某个上游源失败时，Dashboard会显示待补，不让AI或程序虚构；
- 后期针对票据、ABS、REITs等低流动性固收资产，只需要在这个客观数据基座之上补充专属数据与分析层。


## v0.2.1 展示修正

- Raw 与 Processed CSV 的通用英文字段统一转为中文；
- 国债原始行情中的 open/high/low/close 明确命名为开盘/最高/最低/收盘收益率，避免误解成价格；
- Dashboard 会自动读取最新时间戳文件，不再要求所有文件必须以 `_latest.csv` 命名；
- 国开债收益率曲线改为从 AKShare 官方曲线映射表动态匹配，避免硬编码名称变化导致报错；
- 所有缺失项继续明确留空，不进行 AI 或统计补值。


## v0.3 Dashboard 展示优化

- 总览顶部改为四大资产卡片：沪深300、10Y国债收益率、黄金、USD/CNY；
- 宏观快照前置到总览页：PMI、CPI、PPI、固定资产投资、社融、M2；
- 申万一级行业自动生成领涨 / 领跌 TOP10；
- 行业资金流自动生成净流入 / 净流出 TOP10；
- ETF申赎增加申购 / 赎回 TOP10；
- 中国市场配色：数值上涨/流入为红色，下降/流出为绿色；
- USD/CNH 与 DXY 等当前缺失接口移到外汇页末尾和“待补数据”区域；
- ETF统计日期修复：防止 YYYYMMDD 整数被 pandas 误识别为 1970 年纳秒时间；
- ETF申赎表合并当前 ETF 最新价和当日涨跌幅；
- Dashboard 自动读取带时间戳的最新文件。

### 演示启动

刷新数据：

```powershell
python src\run_all.py
```

只修复 / 重算 ETF 申赎：

```powershell
python src\etf_subscription.py
```

启动 Dashboard：

```powershell
python -m streamlit run dashboard\app.py
```

Windows 也可以直接双击：

```text
refresh_data.cmd
start_dashboard.cmd
```
