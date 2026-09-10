from datetime import date, timedelta
import akshare as ak
import pandas as pd
from common import safe_call, save, yield_summary, cn_columns

TENORS=["中国1年期国债","中国2年期国债","中国3年期国债","中国5年期国债","中国7年期国债","中国10年期国债","中国30年期国债"]

def fetch_cgb():
    raw=[]; rows=[]
    for name in TENORS:
        df=safe_call(name,ak.bond_gb_zh_sina,symbol=name)
        if df.empty:continue
        x=df.copy()
        x=cn_columns(x, {
            "open":"开盘收益率(%)","high":"最高收益率(%)","low":"最低收益率(%)",
            "close":"收盘收益率(%)","volume":"成交量"
        })
        x.insert(0,"资产名称",name)
        raw.append(x); rows.append(yield_summary(df,name))
    if raw: save(pd.concat(raw,ignore_index=True),"fixed_income","国债收益率历史",snapshot=False)
    if rows: save(pd.DataFrame(rows),"fixed_income","国债收益率概览",processed=True,snapshot=False)

def fetch_curves():
    today=date.today()
    start=max(today-timedelta(days=28), date(today.year,today.month,1)).strftime("%Y%m%d")
    end=today.strftime("%Y%m%d")

    maps=safe_call("曲线映射",ak.bond_china_close_return_map)
    if not maps.empty:
        save(maps,"fixed_income","可用收益率曲线映射",processed=True,snapshot=False)

    # 不硬编码容易变化的精确中文名称：从官方映射表中动态寻找国债/国开/进出口/农发。
    candidates = {
        "国债": ["国债"],
        "国开债": ["国开", "国家开发银行"],
        "进出口行债": ["进出口"],
        "农发行债": ["农发", "农业发展银行"],
    }

    # 先从映射表找所有字符串列，优先选择包含关键词的官方曲线名称。
    available_names = []
    if not maps.empty:
        for col in maps.columns:
            vals = maps[col].dropna().astype(str).tolist()
            available_names.extend(vals)
    available_names = list(dict.fromkeys(available_names))

    frames=[]
    status=[]
    for label, keywords in candidates.items():
        official=None
        for v in available_names:
            if any(k in v for k in keywords):
                official=v
                break
        # 国债通常可以直接使用“国债”
        if official is None and label=="国债":
            official="国债"

        if official is None:
            status.append({"曲线类别":label,"状态":"未在映射表找到"})
            continue

        df=safe_call("曲线-"+label,ak.bond_china_close_return,
                     symbol=official,period="1",start_date=start,end_date=end)
        if df.empty:
            status.append({"曲线类别":label,"官方曲线名称":official,"状态":"抓取失败或空"})
            continue
        df=df.copy()
        df.insert(0,"曲线类别",label)
        df.insert(1,"官方曲线名称",official)
        frames.append(df)
        status.append({"曲线类别":label,"官方曲线名称":official,"状态":"成功","行数":len(df)})

    if frames:
        save(pd.concat(frames,ignore_index=True),"fixed_income","关键收益率曲线",processed=True,snapshot=False)
    if status:
        save(pd.DataFrame(status),"fixed_income","收益率曲线状态",processed=True,snapshot=False)


def fetch_money_market():
    t=date.today()
    df=safe_call("FR/FDR",ak.repo_rate_hist,start_date=date(t.year,1,1).strftime("%Y%m%d"),end_date=t.strftime("%Y%m%d"))
    if not df.empty:
        rename={"date":"日期"}
        df=df.rename(columns=rename)
        save(df,"fixed_income","回购定盘利率_FR_FDR",processed=True,snapshot=False)

    sh=[]
    for ind in ["隔夜","1周"]:
        x=safe_call("Shibor-"+ind,ak.rate_interbank,market="上海银行同业拆借市场",symbol="Shibor人民币",indicator=ind)
        if not x.empty:
            x=x.copy(); x.insert(0,"期限",ind); sh.append(x)
    if sh: save(pd.concat(sh,ignore_index=True),"fixed_income","Shibor",processed=True,snapshot=False)

def fetch_bond_spot():
    df=safe_call("银行间现券",ak.bond_spot_deal)
    if not df.empty: save(df,"fixed_income","银行间现券成交",processed=True,snapshot=True)

def fetch_cffex_realtime():
    # 用中金所主力实时接口补 TS/TF/T/TL 展示，不依赖 T0/TL0 是否出现在日线主连列表。
    contracts=safe_call("中金所主力代码",ak.match_main_contract,symbol="cffex")
    if isinstance(contracts,str) and contracts.strip():
        df=safe_call("中金所主力实时",ak.futures_zh_spot,symbol=contracts,market="FF",adjust="0")
        if not df.empty:
            mapping={"symbol":"合约","time":"时间","open":"开盘价","high":"最高价","low":"最低价",
                     "current_price":"最新价","hold":"持仓量","volume":"成交量",
                     "last_close":"昨收价","last_settle_price":"昨结算价"}
            df=df.rename(columns={k:v for k,v in mapping.items() if k in df.columns})
            if "合约" in df.columns:
                mask=df["合约"].astype(str).str.contains("国债|TS|TF|TL|T",regex=True,na=False)
                df=df[mask].copy()
            save(df,"fixed_income","国债期货主力实时",processed=True,snapshot=True)

def fetch_bond_etf():
    df=safe_call("ETF行情",ak.fund_etf_spot_em)
    if df.empty:return
    pattern=r"国债|政金|政策性金融|地方债|信用债|城投|可转债|公司债|债券|利率债|科创债|国开债"
    bond=df[df["名称"].astype(str).str.contains(pattern,regex=True,na=False)].copy() if "名称" in df.columns else pd.DataFrame()
    if not bond.empty:
        keep=["代码","名称","最新价","涨跌幅","成交额","换手率","主力净流入-净额","主力净流入-净占比","最新份额","总市值"]
        keep=[c for c in keep if c in bond.columns]
        bond=bond[keep].rename(columns={"代码":"资产代码","名称":"资产名称","涨跌幅":"当日涨跌幅(%)",
                                       "主力净流入-净额":"当日主力资金净流入",
                                       "主力净流入-净占比":"主力资金净流入占比(%)",
                                       "最新份额":"最新基金份额"})
        save(bond,"fixed_income","债券ETF行情与交易资金",processed=True,snapshot=False)

def main():
    print("=== FIXED INCOME v0.2 ===")
    fetch_cgb(); fetch_curves(); fetch_money_market(); fetch_bond_spot(); fetch_cffex_realtime(); fetch_bond_etf()
if __name__=="__main__": main()
