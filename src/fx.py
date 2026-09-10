import akshare as ak
import pandas as pd
from common import safe_call, save, price_summary

def main():
    print("=== FX v0.2 ===")
    spot=safe_call("ChinaMoney即期",ak.fx_spot_quote)
    if not spot.empty: save(spot,"fx","人民币外汇即期报价",processed=True,snapshot=True)

    cnh=safe_call("USDCNH",ak.forex_hist_em,symbol="USDCNH")
    if not cnh.empty:
        save(cnh,"fx","美元兑离岸人民币历史",snapshot=False)
        save(pd.DataFrame([price_summary(cnh,"美元兑离岸人民币",date_cols=("日期",),price_cols=("最新价",))]),
             "fx","美元兑离岸人民币概览",processed=True,snapshot=False)

    fixing=safe_call("人民币中间价",ak.currency_boc_safe)
    if not fixing.empty:
        if "美元" in fixing.columns:
            fixing=fixing.copy()
            fixing["美元兑人民币中间价"]=pd.to_numeric(fixing["美元"],errors="coerce")/100
        save(fixing,"fx","人民币中间价历史",processed=True,snapshot=False)

    dxy=safe_call("DXY-Eastmoney",ak.index_global_hist_em,symbol="美元指数")
    if dxy.empty:
        dxy=safe_call("DXY-Sina",ak.index_global_hist_sina,symbol="美元指数")
    if not dxy.empty:
        save(dxy,"fx","美元指数历史",snapshot=False)
        save(pd.DataFrame([price_summary(dxy,"美元指数",date_cols=("日期","date"),price_cols=("最新价","close"))]),
             "fx","美元指数概览",processed=True,snapshot=False)

    swaps=safe_call("外汇掉期",ak.fx_swap_quote)
    if not swaps.empty: save(swaps,"fx","外汇掉期报价",processed=True,snapshot=True)

if __name__=="__main__": main()
