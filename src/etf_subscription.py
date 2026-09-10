from __future__ import annotations

from pathlib import Path
import re
from datetime import date, timedelta

import pandas as pd

from common import RAW, PROCESSED, save


def _normalize_code(s: pd.Series) -> pd.Series:
    out = s.astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    return out.str.zfill(6)


def _parse_date_series(s: pd.Series) -> pd.Series:
    """
    Robust date parsing.
    Important fix:
    pandas.to_datetime(integer_20260910) can be interpreted as nanoseconds from 1970.
    Therefore all numeric YYYYMMDD values are converted to strings first.
    """
    raw = s.copy()

    # Numeric dates like 20260910.0 -> "20260910"
    numeric = pd.to_numeric(raw, errors="coerce")
    txt = raw.astype(str).str.strip()
    numeric_mask = numeric.notna()
    if numeric_mask.any():
        vals = numeric[numeric_mask].round().astype("Int64").astype(str)
        txt.loc[numeric_mask] = vals

    txt = txt.str.replace(r"\.0$", "", regex=True)

    result = pd.Series(pd.NaT, index=txt.index, dtype="datetime64[ns]")

    mask8 = txt.str.fullmatch(r"\d{8}", na=False)
    if mask8.any():
        result.loc[mask8] = pd.to_datetime(txt.loc[mask8], format="%Y%m%d", errors="coerce")

    mask_other = ~mask8
    if mask_other.any():
        result.loc[mask_other] = pd.to_datetime(txt.loc[mask_other], errors="coerce")

    return result


def _date_from_filename(path: Path):
    # Match the first plausible YYYYMMDD inside filename.
    m = re.search(r"(20\d{6})", path.stem)
    if not m:
        return pd.NaT
    return pd.to_datetime(m.group(1), format="%Y%m%d", errors="coerce")


def _standardize(df: pd.DataFrame, file_path: Path) -> pd.DataFrame:
    code_col = next((c for c in ["基金代码", "证券代码", "代码", "资产代码"] if c in df.columns), None)
    name_col = next((c for c in ["基金简称", "证券简称", "名称", "资产名称"] if c in df.columns), None)
    share_col = next((c for c in ["基金份额", "份额", "最新份额", "最新基金份额"] if c in df.columns), None)
    # 注意：深交所快照没有交易所公布的统计日期，只有我们写入的「抓取日期」。
    # 两者口径不同、不可互相替代，因此这里按来源如实取用，不做任何伪造对齐。
    date_col = next((c for c in ["统计日期", "日期", "数据日期", "抓取日期", "requested_date"] if c in df.columns), None)

    if code_col is None or share_col is None:
        return pd.DataFrame()

    out = pd.DataFrame()
    out["资产代码"] = _normalize_code(df[code_col])
    out["资产名称"] = df[name_col].astype(str).str.strip() if name_col else ""
    out["基金份额"] = pd.to_numeric(df[share_col], errors="coerce")

    if date_col:
        out["统计日期"] = _parse_date_series(df[date_col])
    else:
        out["统计日期"] = _date_from_filename(file_path)

    # If source date column exists but some rows failed, use filename date only as row-level fallback.
    fallback = _date_from_filename(file_path)
    if pd.notna(fallback):
        out["统计日期"] = out["统计日期"].fillna(fallback)

    # Explicitly reject epoch-like / impossible dates.
    lower = pd.Timestamp("2010-01-01")
    upper = pd.Timestamp(date.today() + timedelta(days=2))
    valid = out["统计日期"].between(lower, upper, inclusive="both")
    out = out[valid].copy()

    return out.dropna(subset=["资产代码", "基金份额", "统计日期"])


def _read_current_etf_market() -> pd.DataFrame:
    path = PROCESSED / "equity" / "ETF行情与交易资金_latest.csv"
    if not path.exists():
        return pd.DataFrame()

    try:
        df = pd.read_csv(path, encoding="utf-8-sig")
    except Exception:
        return pd.DataFrame()

    if "资产代码" not in df.columns:
        return pd.DataFrame()

    df = df.copy()
    df["资产代码"] = _normalize_code(df["资产代码"])
    keep = ["资产代码"]
    for c in ["资产名称", "最新价", "当日涨跌幅(%)", "成交额", "当日主力资金净流入", "主力资金净流入占比(%)"]:
        if c in df.columns:
            keep.append(c)
    return df[keep].drop_duplicates("资产代码", keep="last")


def main():
    equity_raw = RAW / "equity"
    if not equity_raw.exists():
        print("[SKIP] ETF申赎：raw/equity 不存在")
        return

    patterns = [
        "*ETF份额快照_*.csv",
        "*etf_share_snapshot_*.csv",
        "*ETF份额_snapshot_*.csv",
    ]

    file_set = []
    for pattern in patterns:
        file_set.extend(equity_raw.glob(pattern))
    files = sorted(set(file_set))

    frames = []
    for f in files:
        try:
            df = pd.read_csv(f, encoding="utf-8-sig")
            x = _standardize(df, f)
            if not x.empty:
                frames.append(x)
        except Exception as exc:
            print(f"[WARN] ETF份额读取 {f.name}: {exc}")

    if not frames:
        print("[SKIP] ETF申赎：没有可用的ETF份额快照")
        return

    x = pd.concat(frames, ignore_index=True)

    # Same ETF may have several intraday snapshots for one statistical date.
    x = (
        x.sort_values(["资产代码", "统计日期"])
         .drop_duplicates(["资产代码", "统计日期"], keep="last")
    )

    # Fill missing fund names from another observation of the same ETF.
    x["资产名称"] = x["资产名称"].replace({"nan": "", "None": ""})
    name_map = (
        x[x["资产名称"].ne("")]
        .drop_duplicates("资产代码", keep="last")
        .set_index("资产代码")["资产名称"]
        .to_dict()
    )
    x["资产名称"] = x.apply(
        lambda r: name_map.get(r["资产代码"], r["资产名称"]) if not r["资产名称"] else r["资产名称"],
        axis=1
    )

    g = x.groupby("资产代码", group_keys=False)
    x["当日份额变化"] = g["基金份额"].diff(1)
    x["近一周份额变化"] = g["基金份额"].diff(5)
    x["近一月份额变化"] = g["基金份额"].diff(20)

    latest = x.groupby("资产代码", as_index=False).tail(1).copy()

    # Enrich with current secondary-market performance.
    market = _read_current_etf_market()
    if not market.empty:
        # Avoid duplicate name column; market name is usually cleaner.
        if "资产名称" in market.columns:
            market = market.rename(columns={"资产名称": "行情资产名称"})
        latest = latest.merge(market, on="资产代码", how="left")
        if "行情资产名称" in latest.columns:
            latest["资产名称"] = latest["行情资产名称"].fillna(latest["资产名称"])
            latest = latest.drop(columns=["行情资产名称"])

    latest["统计日期"] = pd.to_datetime(latest["统计日期"]).dt.strftime("%Y-%m-%d")

    cols = [
        "资产代码", "资产名称", "统计日期", "基金份额",
        "当日份额变化", "近一周份额变化", "近一月份额变化",
        "最新价", "当日涨跌幅(%)", "成交额",
        "当日主力资金净流入", "主力资金净流入占比(%)"
    ]
    cols = [c for c in cols if c in latest.columns]

    save(
        latest[cols].sort_values("当日份额变化", ascending=False, na_position="last"),
        "equity",
        "ETF基金申赎份额变化",
        processed=True,
        snapshot=False,
    )

    # 口径修正：沪深快照的日期基准不同（上交所=交易所统计日，深交所=抓取日），
    # 且沪深 ETF 代码段互不重叠，所以「全局去重日期数」会虚高——它会把两个交易所
    # 各自的单日快照误报成"已积累多个交易日"。真正决定份额变化能否算出的是：
    # 同一只 ETF 是否拿到了 ≥2 个观测。
    unique_dates = x["统计日期"].nunique()
    per_code_days = x.groupby("资产代码")["统计日期"].nunique()
    codes_with_history = int((per_code_days >= 2).sum())
    max_days_per_code = int(per_code_days.max()) if len(per_code_days) else 0

    print(f"[INFO] ETF份额有效交易日数量: {unique_dates}")
    print(f"[INFO] 具备≥2个观测的ETF数量: {codes_with_history}/{per_code_days.size}")
    print(f"[INFO] 单只ETF最大观测天数: {max_days_per_code}")

    if codes_with_history == 0:
        print("[INFO] 每只ETF目前均只有1个观测 → 当日份额变化为空，属正常现象；"
              "再积累1个交易日才会产生变化值。")
    if max_days_per_code < 6:
        print("[INFO] 不足6个有效交易日：近一周份额变化暂不完整。")
    if max_days_per_code < 21:
        print("[INFO] 不足21个有效交易日：近一月份额变化暂不完整。")


if __name__ == "__main__":
    main()
