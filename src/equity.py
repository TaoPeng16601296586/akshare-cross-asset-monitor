from datetime import date
import akshare as ak
import pandas as pd
from common import safe_call, save, price_summary

INDEX_CFG = {
    "上证指数": ("sina","sh000001"),
    "深证成指": ("sina","sz399001"),
    "创业板指": ("sina","sz399006"),
    "科创50": ("sina","sh000688"),
    "沪深300": ("csindex","000300"),
    "中证500": ("csindex","000905"),
    "中证1000": ("csindex","000852"),
    "中证红利": ("csindex","000922"),
}

def fetch_indices():
    t=date.today(); start=f"{t.year-1}1201"; end=t.strftime("%Y%m%d")
    rows=[]; raw=[]
    for name,(provider,symbol) in INDEX_CFG.items():
        if provider=="csindex":
            df=safe_call(name, ak.stock_zh_index_hist_csindex, symbol=symbol, start_date=start, end_date=end)
            if df.empty:
                df=safe_call(name+"-fallback", ak.stock_zh_index_daily, symbol="sh"+symbol)
        else:
            df=safe_call(name, ak.stock_zh_index_daily, symbol=symbol)
        if df.empty: continue
        df=df.copy(); df.insert(0,"资产名称",name)
        raw.append(df)
        rows.append(price_summary(df,name,date_cols=("date","日期"),price_cols=("close","收盘")))
    if raw: save(pd.concat(raw,ignore_index=True),"equity","核心指数历史",snapshot=False)
    if rows: save(pd.DataFrame(rows),"equity","核心指数概览",processed=True,snapshot=False)

def fetch_industry_and_flow():
    frames=[]
    for level in ["一级行业","二级行业"]:
        df=safe_call("申万"+level,ak.index_realtime_sw,symbol=level)
        if not df.empty:
            df=df.copy(); df.insert(0,"行业层级",level); frames.append(df)
    if frames: save(pd.concat(frames,ignore_index=True),"equity","申万行业价格",processed=True,snapshot=False)

    frames=[]
    for period in ["即时","3日排行","5日排行","10日排行","20日排行"]:
        df=safe_call("同花顺行业资金-"+period,ak.stock_fund_flow_industry,symbol=period)
        if not df.empty:
            df=df.copy(); df.insert(0,"统计周期",period); frames.append(df)
    if frames: save(pd.concat(frames,ignore_index=True),"equity","行业资金流",processed=True,snapshot=False)

def fetch_etf():
    df=safe_call("ETF行情",ak.fund_etf_spot_em)
    if df.empty:return
    save(df,"equity","ETF全量行情",snapshot=False)
    keep=["代码","名称","最新价","涨跌幅","成交量","成交额","换手率","主力净流入-净额",
          "主力净流入-净占比","最新份额","流通市值","总市值","数据日期","更新时间"]
    keep=[c for c in keep if c in df.columns]
    out=df[keep].copy()
    ren={"代码":"资产代码","名称":"资产名称","涨跌幅":"当日涨跌幅(%)",
         "主力净流入-净额":"当日主力资金净流入","主力净流入-净占比":"主力资金净流入占比(%)",
         "最新份额":"最新基金份额"}
    out=out.rename(columns=ren)
    save(out,"equity","ETF行情与交易资金",processed=True,snapshot=False)


def _fetch_sse_etf_scale(d):
    """上交所ETF份额：取指定统计日期的份额。

    akshare 的 fund_etf_scale_sse() 在「该统计日期无数据」时，会对空结果直接
    取列而抛 KeyError。这属于当日尚未发布 / 非交易日的正常情况，静默返回空表。
    """
    try:
        return ak.fund_etf_scale_sse(date=d)
    except KeyError:
        return pd.DataFrame()
    except Exception as e:
        print(f"[WARN] 上交所ETF份额-{d}: {type(e).__name__}: {e}")
        return pd.DataFrame()


def fetch_etf_share_snapshot():
    from datetime import timedelta
    fetched=date.today().strftime("%Y%m%d")

    # 上交所：接口返回真实的「统计日期」（通常为 T-1，交易所发布有延迟）。
    sse=pd.DataFrame(); sse_stat=None
    for back in range(10):
        d=(date.today()-timedelta(days=back)).strftime("%Y%m%d")
        sse=_fetch_sse_etf_scale(d)
        if not sse.empty:
            if "统计日期" not in sse.columns:
                sse.insert(0,"统计日期",d)
            sse_stat=str(sse["统计日期"].iloc[0])[:10]
            break
    if not sse.empty:
        save(sse,"equity","上交所ETF份额快照",snapshot=True)
        print(f"[INFO] 上交所ETF份额快照 统计日期={sse_stat}（抓取日期={fetched}）")
    else:
        print("[WARN] 上交所ETF份额快照: 最近10个自然日均无数据")

    # 深交所：akshare 的 fund_etf_scale_szse() 不返回任何日期列，交易所页面只提供
    # 「当前」规模快照，无法得知真实统计日。这里显式写成 抓取日期，不再伪造
    # 统计日期，以免与上交所的真实统计日混淆、污染份额变化计算。
    sz=safe_call("深交所ETF份额",ak.fund_etf_scale_szse)
    if not sz.empty:
        sz=sz.copy()
        sz.insert(0,"抓取日期",fetched)
        save(sz,"equity","深交所ETF份额快照",snapshot=True)
        print(f"[INFO] 深交所ETF份额快照 抓取日期={fetched}（交易所未公布统计日期）")


def main():
    print("=== EQUITY v0.2 ===")
    fetch_indices(); fetch_industry_and_flow(); fetch_etf(); fetch_etf_share_snapshot()
if __name__=="__main__": main()
