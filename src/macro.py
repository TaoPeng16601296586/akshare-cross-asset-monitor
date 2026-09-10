import akshare as ak
import pandas as pd
from common import safe_call, save

ENDPOINTS={
"采购经理指数PMI":"macro_china_pmi",
"固定资产投资":"macro_china_gdzctz",
"社会消费品零售总额":"macro_china_consumer_goods_retail",
"工业增加值同比":"macro_china_industrial_production_yoy",
"居民消费价格指数CPI":"macro_china_cpi",
"工业生产者出厂价格指数PPI":"macro_china_ppi",
"社会融资规模增量":"macro_china_shrzgm",
"货币供应量M1_M2":"macro_china_money_supply",
"新增人民币贷款":"macro_china_new_financial_credit",
"出口同比":"macro_china_exports_yoy",
"进口同比":"macro_china_imports_yoy",
"贸易差额":"macro_china_trade_balance",
"外汇储备":"macro_china_fx_reserves_yearly",
"存款准备金率":"macro_china_reserve_requirement_ratio",
}

def main():
    print("=== MACRO v0.2 ===")
    manifest=[]
    for cn,fn in ENDPOINTS.items():
        func=getattr(ak,fn,None)
        if func is None:
            manifest.append({"数据集":cn,"AKShare接口":fn,"状态":"当前版本无此接口"}); continue
        df=safe_call(fn,func)
        if df.empty:
            manifest.append({"数据集":cn,"AKShare接口":fn,"状态":"抓取失败或空"}); continue
        save(df,"macro",cn,processed=True,snapshot=False)
        manifest.append({"数据集":cn,"AKShare接口":fn,"状态":"成功","行数":len(df)})
    save(pd.DataFrame(manifest),"macro","宏观数据状态表",processed=True,snapshot=False)

if __name__=="__main__": main()
