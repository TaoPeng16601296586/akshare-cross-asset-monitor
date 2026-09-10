from __future__ import annotations
from pathlib import Path
from datetime import datetime
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT/"data"/"raw"
PROCESSED = ROOT/"data"/"processed"

def safe_call(name, func, *args, **kwargs):
    try:
        df = func(*args, **kwargs)
        if df is None:
            return pd.DataFrame()
        return df
    except Exception as e:
        print(f"[WARN] {name}: {type(e).__name__}: {e}")
        return pd.DataFrame()

def save(df, group, name, processed=False, snapshot=False, translate_columns=True):
    if df is None or df.empty:
        print(f"[SKIP] {group}/{name}: empty")
        return
    if translate_columns:
        df = cn_columns(df)
    base = PROCESSED if processed else RAW
    folder = base/group
    folder.mkdir(parents=True, exist_ok=True)
    suffix = datetime.now().strftime("%Y%m%d_%H%M%S") if snapshot else "latest"
    path = folder/f"{name}_{suffix}.csv"
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"[SAVE] {path.relative_to(ROOT)} rows={len(df)}")

def _find_col(df, names):
    return next((x for x in names if x in df.columns), None)

def price_summary(df, asset_name, date_cols=("date","日期"), price_cols=("close","收盘","最新价")):
    dc = _find_col(df, date_cols); pc = _find_col(df, price_cols)
    if df.empty or not dc or not pc:
        return {"资产名称": asset_name}
    x = df[[dc,pc]].copy()
    x[dc] = pd.to_datetime(x[dc], errors="coerce")
    x[pc] = pd.to_numeric(x[pc], errors="coerce")
    x = x.dropna().sort_values(dc)
    if x.empty: return {"资产名称": asset_name}
    now = float(x.iloc[-1][pc]); d = x.iloc[-1][dc]
    p1 = float(x.iloc[-2][pc]) if len(x)>=2 else None
    p5 = float(x.iloc[-6][pc]) if len(x)>=6 else None
    y0 = pd.Timestamp(d.year,1,1)
    pre = x[x[dc] < y0]
    cur = x[x[dc] >= y0]
    py = float(pre.iloc[-1][pc]) if not pre.empty else (float(cur.iloc[0][pc]) if not cur.empty else None)
    ret = lambda b: (now/b-1)*100 if b not in (None,0) else None
    return {"资产名称":asset_name,"数据日期":d.date().isoformat(),"最新价":now,
            "当日涨跌幅(%)":ret(p1),"近一周涨跌幅(%)":ret(p5),"年初至今涨跌幅(%)":ret(py)}

def yield_summary(df, asset_name, date_cols=("date","日期"), y_cols=("close","收盘","到期收益率","最新收益率")):
    dc = _find_col(df, date_cols); yc = _find_col(df, y_cols)
    if df.empty or not dc or not yc:
        return {"资产名称": asset_name}
    x=df[[dc,yc]].copy()
    x[dc]=pd.to_datetime(x[dc],errors="coerce"); x[yc]=pd.to_numeric(x[yc],errors="coerce")
    x=x.dropna().sort_values(dc)
    if x.empty: return {"资产名称":asset_name}
    now=float(x.iloc[-1][yc]); d=x.iloc[-1][dc]
    y1=float(x.iloc[-2][yc]) if len(x)>=2 else None
    y5=float(x.iloc[-6][yc]) if len(x)>=6 else None
    y0=pd.Timestamp(d.year,1,1)
    pre=x[x[dc]<y0]; cur=x[x[dc]>=y0]
    yy=float(pre.iloc[-1][yc]) if not pre.empty else (float(cur.iloc[0][yc]) if not cur.empty else None)
    bp=lambda b:(now-b)*100 if b is not None else None
    return {"资产名称":asset_name,"数据日期":d.date().isoformat(),"最新收益率(%)":now,
            "当日变动(bp)":bp(y1),"近一周变动(bp)":bp(y5),"年初至今变动(bp)":bp(yy)}

def oi_summary(df, asset_name, date_col="date", oi_col="hold"):
    if df.empty or date_col not in df or oi_col not in df:
        return {"资产名称":asset_name}
    x=df[[date_col,oi_col]].copy()
    x[date_col]=pd.to_datetime(x[date_col],errors="coerce")
    x[oi_col]=pd.to_numeric(x[oi_col],errors="coerce")
    x=x.dropna().sort_values(date_col)
    if x.empty: return {"资产名称":asset_name}
    now=float(x.iloc[-1][oi_col]); d=x.iloc[-1][date_col]
    v1=float(x.iloc[-2][oi_col]) if len(x)>=2 else None
    v5=float(x.iloc[-6][oi_col]) if len(x)>=6 else None
    return {"资产名称":asset_name,"数据日期":d.date().isoformat(),"最新持仓量":now,
            "当日持仓变化":now-v1 if v1 is not None else None,
            "近一周持仓变化":now-v5 if v5 is not None else None}


# 常见 AKShare 英文字段 -> 中文字段。仅翻译“语义明确”的通用字段；
# 收益率等特殊字段由各模块在保存前单独处理，避免把 yield 误写成价格。
COMMON_CN_COLUMNS = {
    "instrument": "资产名称",
    "symbol": "资产代码",
    "date": "日期",
    "time": "时间",
    "open": "开盘价",
    "high": "最高价",
    "low": "最低价",
    "close": "收盘价",
    "volume": "成交量",
    "amount": "成交额",
    "turnover": "换手率",
    "hold": "持仓量",
    "settle": "结算价",
    "last_close": "昨收价",
    "last_settle_price": "昨结算价",
    "current_price": "最新价",
    "change": "涨跌额",
    "pct_chg": "涨跌幅(%)",
    "pre_close": "昨收价",
}

def cn_columns(df: pd.DataFrame, extra: dict | None = None) -> pd.DataFrame:
    """将明确可翻译的英文字段统一为中文；extra 可覆盖/补充模块特有字段。"""
    if df is None or df.empty:
        return df
    mapping = dict(COMMON_CN_COLUMNS)
    if extra:
        mapping.update(extra)
    actual = {k: v for k, v in mapping.items() if k in df.columns}
    return df.rename(columns=actual)
