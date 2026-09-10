import akshare as ak
import pandas as pd
from common import safe_call, save, price_summary, oi_summary

COMMODITIES={"黄金":"AU0","白银":"AG0","沪铜":"CU0","沪铝":"AL0","铁矿石":"I0","螺纹钢":"RB0","原油":"SC0"}

def main():
    print("=== COMMODITY v0.2 ===")
    raw=[]; ps=[]; os=[]
    for name,symbol in COMMODITIES.items():
        df=safe_call(name,ak.futures_zh_daily_sina,symbol=symbol)
        if df.empty: continue
        x=df.copy(); x.insert(0,"资产名称",name); x.insert(1,"资产代码",symbol); raw.append(x)
        ps.append(price_summary(df,name))
        os.append(oi_summary(df,name))
    if raw: save(pd.concat(raw,ignore_index=True),"commodity","商品期货历史",snapshot=False)
    if ps: save(pd.DataFrame(ps),"commodity","商品价格概览",processed=True,snapshot=False)
    if os: save(pd.DataFrame(os),"commodity","商品持仓变化",processed=True,snapshot=False)

    # 中证商品指数：公共AKShare可用的综合商品指数接口，作为总览补充。
    idx=safe_call("中证商品指数",ak.futures_index_ccidx)
    if not idx.empty: save(idx,"commodity","中证商品指数",processed=True,snapshot=False)

if __name__=="__main__": main()
