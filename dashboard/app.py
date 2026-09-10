from __future__ import annotations

from pathlib import Path
import re
import math

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"

st.set_page_config(
    page_title="大类资产数据监测基座",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1500px;}
      div[data-testid="stMetric"] {
          border: 1px solid rgba(128,128,128,0.25);
          border-radius: 10px;
          padding: 10px 14px;
          background: rgba(128,128,128,0.035);
      }
      .asset-card {
          border: 1px solid rgba(128,128,128,0.25);
          border-radius: 12px;
          padding: 15px 16px 12px 16px;
          min-height: 132px;
          background: rgba(128,128,128,0.035);
      }
      .card-title {font-size: 0.92rem; opacity: .72; margin-bottom: 8px;}
      .card-value {font-size: 1.62rem; font-weight: 700; line-height: 1.2;}
      .card-delta {font-size: .95rem; margin-top: 8px; font-weight: 600;}
      .up-cn {color: #d62728;}
      .down-cn {color: #1a9850;}
      .flat-cn {color: #777;}
      .section-note {font-size: .85rem; opacity: .65;}
      h2, h3, h4 {letter-spacing: .01em;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("大类资产数据监测基座")
st.caption("AKShare 客观事实数据层｜无 AI 加工｜价格、收益率、资金/份额、持仓与宏观状态统一展示")


def read(group: str, name: str) -> pd.DataFrame:
    folder = DATA / group
    if not folder.exists():
        return pd.DataFrame()

    preferred = folder / f"{name}_latest.csv"
    if preferred.exists():
        p = preferred
    else:
        candidates = sorted(
            folder.glob(f"{name}_*.csv"),
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            return pd.DataFrame()
        p = candidates[0]

    try:
        return pd.read_csv(p, encoding="utf-8-sig")
    except Exception:
        return pd.DataFrame()


def find_col(df: pd.DataFrame, candidates=None, contains=None):
    candidates = candidates or []
    for c in candidates:
        if c in df.columns:
            return c
    if contains:
        for c in df.columns:
            if all(k in str(c) for k in contains):
                return c
    return None


# ── 数据来源 / 单位 / 统计口径（用于逐板块注明，便于与 Wind 核对）──────────
# 这些信息来自 src/*.py 中调用的 AKShare 接口与公开数据源；口径以官方披露为准。
SOURCE = {
    "核心指数概览": {
        "来源": "新浪财经 / 中证指数网（经 AKShare）",
        "单位": "点位（指数收盘值）",
        "口径": "指数收盘点位及基于收盘价的涨跌幅（当日 / 近5个交易日 / 年初至今）",
    },
    "申万行业价格": {
        "来源": "申万宏源行业指数（经 AKShare）",
        "单位": "点位；涨跌幅 %",
        "口径": "申万一级/二级行业指数收盘及当日涨跌幅",
    },
    "行业资金流": {
        "来源": "同花顺数据中心·行业资金流（经 AKShare）",
        "单位": "亿元",
        "口径": "同花顺定义的行业「流入资金 / 流出资金 / 净额」；其具体大单/超大单阈值口径以同花顺官方页面说明为准",
    },
    "商品价格概览": {
        "来源": "新浪财经·国内期货日线（主力连续，经 AKShare）",
        "单位": "黄金 元/克；白银 元/千克；沪铜/沪铝/铁矿石/螺纹钢 元/吨；原油 元/桶",
        "口径": "期货主力连续合约收盘价及涨跌幅（当日 / 近5个交易日 / 年初至今）",
    },
    "商品持仓变化": {
        "来源": "新浪财经·国内期货日线（经 AKShare）",
        "单位": "手",
        "口径": "期货持仓量（手）及相对前一交易日 / 近5个交易日的变化",
    },
    "国债收益率概览": {
        "来源": "中国债券信息网 / 新浪（中债国债到期收益率，经 AKShare）",
        "单位": "收益率 %；变动 bp（1bp=0.01%）",
        "口径": "国债到期收益率及当日 / 近5个交易日 / 年初至今的变动（bp）",
    },
    "人民币中间价历史": {
        "来源": "中国外汇交易中心 / 中国银行（人民币汇率中间价，经 AKShare）",
        "单位": "元/1外币（美元兑人民币中间价）",
        "口径": "中国人民银行授权公布的每日人民币汇率中间价",
    },
    "人民币外汇即期报价": {
        "来源": "中国货币网（ChinaMoney）外汇即期报价（经 AKShare）",
        "单位": "元/1外币",
        "口径": "即期买卖报价（买/卖双边价）",
    },
    "ETF基金申赎份额变化": {
        "来源": "上交所 / 深交所 ETF 基金份额（经 AKShare）",
        "单位": "基金份额：份；成交额/主力净流入：元",
        "口径": "交易所披露的基金份额；份额变化为相邻两期份额之差；主力资金净流入为东方财富口径（与申赎严格分开）",
    },
    "宏观": {
        "来源": "国家统计局 / 中国人民银行 / 海关总署等公开数据（经 AKShare 各宏观接口）",
        "单位": "按指标（见各卡片）",
        "口径": "官方公布口径，未经任何加工或外推",
    },
}

COMMODITY_UNIT = {
    "黄金": "元/克",
    "白银": "元/千克",
    "沪铜": "元/吨",
    "沪铝": "元/吨",
    "铁矿石": "元/吨",
    "螺纹钢": "元/吨",
    "原油": "元/桶",
}


def src_note(key: str, extra: str = ""):
    m = SOURCE.get(key, {})
    parts = [f"来源：{m.get('来源', '')}", f"单位：{m.get('单位', '')}", f"口径：{m.get('口径', '')}"]
    if extra:
        parts.append(extra)
    st.caption(" ｜ ".join(parts))


def parse_cn_number(v):
    if pd.isna(v):
        return math.nan
    if isinstance(v, (int, float)):
        return float(v)

    s = str(v).strip().replace(",", "").replace("%", "")
    if s in {"", "-", "--", "nan", "None"}:
        return math.nan

    mult = 1.0
    if "万亿" in s:
        mult = 1e12
        s = s.replace("万亿", "")
    elif "亿" in s:
        mult = 1e8
        s = s.replace("亿", "")
    elif "万" in s:
        mult = 1e4
        s = s.replace("万", "")

    try:
        return float(s) * mult
    except Exception:
        m = re.search(r"[-+]?\d*\.?\d+", s)
        return float(m.group()) * mult if m else math.nan


def fmt_num(v, digits=2, suffix=""):
    try:
        if pd.isna(v):
            return "-"
        return f"{float(v):,.{digits}f}{suffix}"
    except Exception:
        return str(v) if v not in (None, "") else "-"


def fmt_cn_amount(v):
    n = parse_cn_number(v)
    if pd.isna(n):
        return "-"
    sign = "-" if n < 0 else ""
    n = abs(n)
    if n >= 1e8:
        return f"{sign}{n/1e8:.2f}亿"
    if n >= 1e4:
        return f"{sign}{n/1e4:.2f}万"
    return f"{sign}{n:,.2f}"


def color_value(v):
    n = parse_cn_number(v)
    if pd.isna(n):
        return ""
    if n > 0:
        return "color:#d62728;font-weight:600;"
    if n < 0:
        return "color:#1a9850;font-weight:600;"
    return "color:#777;"


def styled_table(df: pd.DataFrame, sign_cols=None, fmt=None):
    if df.empty:
        return df
    styler = df.style
    sign_cols = [c for c in (sign_cols or []) if c in df.columns]
    if sign_cols:
        styler = styler.map(color_value, subset=sign_cols)
    if fmt:
        valid = {k: v for k, v in fmt.items() if k in df.columns}
        if valid:
            styler = styler.format(valid, na_rep="-")
    return styler


def card(title, value, delta=None, footnote=None, reverse=False):
    cls = "flat-cn"
    delta_text = "-"
    if delta is not None and not pd.isna(parse_cn_number(delta)):
        n = parse_cn_number(delta)
        # China market convention: positive numeric change red, negative green.
        # reverse=True can be used if the semantic direction should be inverted.
        if reverse:
            n = -n
        cls = "up-cn" if n > 0 else ("down-cn" if n < 0 else "flat-cn")
        if isinstance(delta, str):
            delta_text = delta
        else:
            delta_text = f"{float(delta):+.2f}"
    elif isinstance(delta, str):
        delta_text = delta

    foot = f'<div class="section-note">{footnote}</div>' if footnote else ""
    st.markdown(
        f"""
        <div class="asset-card">
          <div class="card-title">{title}</div>
          <div class="card-value">{value}</div>
          <div class="card-delta {cls}">{delta_text}</div>
          {foot}
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_asset_row(df, name_keyword):
    if df.empty or "资产名称" not in df.columns:
        return None
    hit = df[df["资产名称"].astype(str).str.contains(name_keyword, na=False)]
    return hit.iloc[0] if not hit.empty else None


def _period_key(v):
    # 只保留数字：'2026年07月份' -> 202607；'201501' -> 201501；'2025-09-08' -> 202509。
    # 注意：不能用 re.search(r"(20\d{2})\D*?(\d{1,2})?")——其惰性量词会把月份吞掉，
    # 使所有 '2026年XX月份' 都退化成 202601，导致“最新一期”取到任意某个月。
    digits = re.sub(r"\D", "", str(v))
    if len(digits) >= 6:
        return int(digits[:6])
    if len(digits) == 4:
        return int(digits) * 100 + 1
    return -1


def _fmt_period(v):
    """把期数显示得干净：202604 -> 2026-04；202604.0 -> 2026-04。"""
    s = re.sub(r"\.0$", "", str(v).strip())
    if re.fullmatch(r"\d{6}", s):
        return f"{s[:4]}-{s[4:]}"
    return s


def latest_macro_row(df):
    if df.empty:
        return None, None

    date_col = find_col(
        df,
        ["月份", "日期", "时间", "统计时间", "报告期", "季度", "年份", "公布时间", "生效时间", "商品"],
    )
    if date_col:
        temp = df.copy()
        temp["_排序"] = temp[date_col].map(_period_key)
        temp = temp.sort_values("_排序")
        row = temp.iloc[-1]
        return row, date_col

    return df.iloc[-1], None


def macro_metric(file_name, label, preferred_cols=None, contains_groups=None, unit=None):
    df = read("macro", file_name)
    if df.empty:
        return {"指标": label, "最新期": "-", "最新值": "-", "变化": None, "前值": None, "单位": unit}

    row, date_col = latest_macro_row(df)
    value_col = find_col(df, preferred_cols or [])

    if value_col is None and contains_groups:
        for contains in contains_groups:
            value_col = find_col(df, contains=contains)
            if value_col:
                break

    if value_col is None:
        numeric_candidates = []
        for c in df.columns:
            if c == date_col:
                continue
            converted = pd.to_numeric(df[c], errors="coerce")
            if converted.notna().sum() > 0:
                numeric_candidates.append(c)
        value_col = numeric_candidates[0] if numeric_candidates else None

    if value_col is None:
        return {"指标": label, "最新期": _fmt_period(row[date_col]) if date_col else "-", "最新值": "-", "变化": None, "前值": None, "单位": unit}

    temp = df.copy()
    if date_col:
        temp["_排序"] = temp[date_col].map(_period_key)
        temp = temp.sort_values("_排序")
    vals = pd.to_numeric(temp[value_col], errors="coerce").dropna()

    current = vals.iloc[-1] if len(vals) else math.nan
    prev = vals.iloc[-2] if len(vals) >= 2 else math.nan
    delta = current - prev if pd.notna(current) and pd.notna(prev) else None

    return {
        "指标": label,
        "最新期": _fmt_period(row[date_col]) if date_col else "-",
        "最新值": current,
        "前值": prev,
        "变化": delta,
        "字段": value_col,
        "单位": unit,
    }


def industry_flow_tables():
    df = read("equity", "行业资金流")
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    if "统计周期" in df.columns:
        now = df[df["统计周期"].astype(str).eq("即时")].copy()
        if now.empty:
            now = df.copy()
    else:
        now = df.copy()

    name_col = find_col(now, ["行业", "名称", "行业名称", "板块名称"])
    net_col = find_col(now, ["净额", "主力净流入-净额", "资金净额"], contains=["净"])
    pct_col = find_col(now, ["行业-涨跌幅", "阶段涨跌幅", "涨跌幅", "涨跌幅(%)"])

    if not name_col or not net_col:
        return pd.DataFrame(), pd.DataFrame()

    now["_净额数值"] = now[net_col].map(parse_cn_number)
    cols = [name_col, net_col] + ([pct_col] if pct_col else [])

    top = now.nlargest(10, "_净额数值")[cols].copy()
    bottom = now.nsmallest(10, "_净额数值")[cols].copy()

    rename = {name_col: "行业", net_col: "资金净额"}
    if pct_col:
        rename[pct_col] = "涨跌幅"
    top = top.rename(columns=rename)
    bottom = bottom.rename(columns=rename)
    top.insert(0, "排名", range(1, len(top) + 1))
    bottom.insert(0, "排名", range(1, len(bottom) + 1))
    return top, bottom


def industry_price_tables():
    df = read("equity", "申万行业价格")
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    if "行业层级" in df.columns:
        lv1 = df[df["行业层级"].astype(str).eq("一级行业")].copy()
        if not lv1.empty:
            df = lv1

    name_col = find_col(df, ["指数名称", "行业名称", "名称", "指数简称", "行业"])
    pct_col = find_col(df, ["日涨跌幅_calc_pct", "涨跌幅", "涨跌幅(%)", "今日涨跌幅"])

    if pct_col is None and {"最新价", "昨收盘"}.issubset(df.columns):
        df = df.copy()
        df["_涨跌幅"] = (
            pd.to_numeric(df["最新价"], errors="coerce")
            / pd.to_numeric(df["昨收盘"], errors="coerce")
            - 1
        ) * 100
        pct_col = "_涨跌幅"

    if not name_col or not pct_col:
        return pd.DataFrame(), pd.DataFrame()

    df["_涨跌数值"] = df[pct_col].map(parse_cn_number)
    top = df.nlargest(10, "_涨跌数值")[[name_col, pct_col]].copy()
    bottom = df.nsmallest(10, "_涨跌数值")[[name_col, pct_col]].copy()
    top.columns = ["行业", "当日涨跌幅(%)"]
    bottom.columns = ["行业", "当日涨跌幅(%)"]
    top.insert(0, "排名", range(1, len(top) + 1))
    bottom.insert(0, "排名", range(1, len(bottom) + 1))
    return top, bottom


def etf_flow_tables():
    df = read("equity", "ETF基金申赎份额变化")
    if df.empty or "当日份额变化" not in df.columns:
        return pd.DataFrame(), pd.DataFrame()

    x = df.copy()
    # Defensive cleanup for old bad files.
    if "统计日期" in x.columns:
        d = pd.to_datetime(x["统计日期"], errors="coerce")
        x = x[d.dt.year.ge(2010)].copy()

    x["_份额变化"] = pd.to_numeric(x["当日份额变化"], errors="coerce")
    x = x.dropna(subset=["_份额变化"])
    if x.empty:
        return pd.DataFrame(), pd.DataFrame()

    cols = [c for c in ["资产名称", "资产代码", "当日份额变化", "当日涨跌幅(%)", "最新价"] if c in x.columns]
    sub = x.nlargest(10, "_份额变化")[cols].copy()
    red = x.nsmallest(10, "_份额变化")[cols].copy()
    sub.insert(0, "排名", range(1, len(sub) + 1))
    red.insert(0, "排名", range(1, len(red) + 1))
    return sub, red


def fx_spot_usdcny():
    df = read("fx", "人民币外汇即期报价")
    if not df.empty:
        pair_col = find_col(df, ["货币对", "货币对名称", "currency_pair"])
        if pair_col:
            hit = df[df[pair_col].astype(str).str.contains("USD/CNY|美元.*人民币", regex=True, na=False)]
            if not hit.empty:
                row = hit.iloc[0]
                buy_col = find_col(df, ["买报价", "买入价", "bid"])
                sell_col = find_col(df, ["卖报价", "卖出价", "ask"])
                buy = parse_cn_number(row[buy_col]) if buy_col else math.nan
                sell = parse_cn_number(row[sell_col]) if sell_col else math.nan
                if pd.notna(buy) and pd.notna(sell):
                    return (buy + sell) / 2, f"买 {buy:.4f} / 卖 {sell:.4f}"
                if pd.notna(buy):
                    return buy, "ChinaMoney 即期买报价"

    fixing = read("fx", "人民币中间价历史")
    if not fixing.empty and "美元兑人民币中间价" in fixing.columns:
        row, _ = latest_macro_row(fixing)
        val = parse_cn_number(row["美元兑人民币中间价"])
        return val, "人民币中间价"
    return math.nan, "当前无可用即期报价"


def render_market_cards():
    eq = read("equity", "核心指数概览")
    bond = read("fixed_income", "国债收益率概览")
    cmd = read("commodity", "商品价格概览")

    eq_row = get_asset_row(eq, "上证指数")
    bond_row = get_asset_row(bond, "10年")
    gold_row = get_asset_row(cmd, "黄金")
    fx_val, fx_note = fx_spot_usdcny()

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        if eq_row is not None:
            card(
                "权益｜上证指数（点）",
                fmt_num(eq_row.get("最新价"), 2),
                f"{parse_cn_number(eq_row.get('当日涨跌幅(%)')):+.2f}%" if pd.notna(parse_cn_number(eq_row.get("当日涨跌幅(%)"))) else None,
                f"1周 {fmt_num(eq_row.get('近一周涨跌幅(%)'), 2, '%')}｜YTD {fmt_num(eq_row.get('年初至今涨跌幅(%)'), 2, '%')}｜收盘 {eq_row.get('数据日期')}",
            )
        else:
            card("权益｜上证指数（点）", "-", None, "等待数据")

    with c2:
        if bond_row is not None:
            bp = parse_cn_number(bond_row.get("当日变动(bp)"))
            card(
                "债券｜10Y国债收益率（%）",
                fmt_num(bond_row.get("最新收益率(%)"), 3, "%"),
                f"{bp:+.2f} bp" if pd.notna(bp) else None,
                f"1周 {fmt_num(bond_row.get('近一周变动(bp)'), 2, ' bp')}｜YTD {fmt_num(bond_row.get('年初至今变动(bp)'), 2, ' bp')}｜{bond_row.get('数据日期')}",
            )
        else:
            card("债券｜10Y国债收益率（%）", "-", None, "等待数据")

    with c3:
        if gold_row is not None:
            d = parse_cn_number(gold_row.get("当日涨跌幅(%)"))
            card(
                "大宗｜黄金主连（元/克）",
                fmt_num(gold_row.get("最新价"), 2),
                f"{d:+.2f}%" if pd.notna(d) else None,
                f"1周 {fmt_num(gold_row.get('近一周涨跌幅(%)'), 2, '%')}｜YTD {fmt_num(gold_row.get('年初至今涨跌幅(%)'), 2, '%')}｜{gold_row.get('数据日期')}",
            )
        else:
            card("大宗｜黄金主连（元/克）", "-", None, "等待数据")

    with c4:
        card(
            "外汇｜USD/CNY（元）",
            fmt_num(fx_val, 4),
            None,
            f"{fx_note}（即期，非收盘）",
        )


def render_macro_snapshot():
    metrics = [
        macro_metric(
            "采购经理指数PMI", "制造业PMI", unit="（指数）",
            preferred_cols=["制造业-指数", "制造业PMI"],
            contains_groups=[["制造业", "指数"]],
        ),
        macro_metric(
            "居民消费价格指数CPI", "CPI同比", unit="%",
            preferred_cols=["全国-同比增长", "同比增长"],
            contains_groups=[["全国", "同比"], ["同比"]],
        ),
        macro_metric(
            "工业生产者出厂价格指数PPI", "PPI同比", unit="%",
            preferred_cols=["当月同比增长", "同比增长"],
            contains_groups=[["同比"]],
        ),
        macro_metric(
            "固定资产投资", "固定资产投资同比", unit="%",
            preferred_cols=["同比增长", "累计同比增长", "自年初累计同比增长"],
            contains_groups=[["同比"]],
        ),
        macro_metric(
            "社会融资规模增量", "社融增量", unit="亿元",
            preferred_cols=["社会融资规模增量", "社会融资规模增量(亿元)"],
            contains_groups=[["社会融资", "增量"]],
        ),
        macro_metric(
            "货币供应量M1_M2", "M2同比", unit="%",
            preferred_cols=["货币和准货币(M2)-同比增长", "M2同比增长"],
            contains_groups=[["M2", "同比"]],
        ),
    ]

    cols = st.columns(6)
    for c, m in zip(cols, metrics):
        with c:
            current = m["最新值"]
            delta = m["变化"]
            prev = m.get("前值")
            unit = m.get("单位") or ""
            if pd.notna(parse_cn_number(current)):
                value = f"{fmt_num(current, 2)}{unit}"
                delta_text = f"较前值 {delta:+.2f}{unit}" if delta is not None and pd.notna(delta) else "—"
            else:
                value, delta_text = "-", None
            foot = f"{m['最新期']}｜{m.get('字段','')}"
            if prev is not None and pd.notna(parse_cn_number(prev)):
                foot += f"｜前值 {fmt_num(prev, 2)}{unit}"
            card(m["指标"], value, delta_text, foot)


def overview():
    st.subheader("市场总览")
    render_market_cards()

    st.markdown("### 宏观快照")
    st.caption("「最新值」= 官方最近一期公布值；「较前值」= 最新值 − 前值（环比）。同比类指标（CPI/PPI/M2/固投同比）的较前值为百分点(pp)；社融增量/贷款为月度增量，环比波动大，建议结合同比或累计看。")
    render_macro_snapshot()

    st.markdown("### 一、四大类资产价格表现")
    st.caption("价格为客观原始值；各板块的来源、单位、口径见每张表上方说明，可与 Wind 逐项核对。")

    # 权益
    st.markdown("#### 权益｜核心指数")
    src_note("核心指数概览")
    eq = read("equity", "核心指数概览")
    if not eq.empty:
        eq = eq.copy()
        eq.insert(1, "单位", "点")
        eq = eq[[c for c in ["资产名称", "单位", "数据日期", "最新价", "当日涨跌幅(%)", "近一周涨跌幅(%)", "年初至今涨跌幅(%)"] if c in eq.columns]]
        st.dataframe(
            styled_table(eq, ["当日涨跌幅(%)", "近一周涨跌幅(%)", "年初至今涨跌幅(%)"],
                         {"最新价": "{:,.2f}", "当日涨跌幅(%)": "{:+.2f}%",
                          "近一周涨跌幅(%)": "{:+.2f}%", "年初至今涨跌幅(%)": "{:+.2f}%"}),
            width="stretch", hide_index=True,
        )
    else:
        st.info("等待权益数据")

    # 债券
    st.markdown("#### 债券市场收益率｜国债到期收益率")
    src_note("国债收益率概览")
    bond = read("fixed_income", "国债收益率概览")
    if not bond.empty:
        st.dataframe(
            styled_table(
                bond,
                sign_cols=["当日变动(bp)", "近一周变动(bp)", "年初至今变动(bp)"],
                fmt={
                    "最新收益率(%)": "{:.3f}%",
                    "当日变动(bp)": "{:+.2f}",
                    "近一周变动(bp)": "{:+.2f}",
                    "年初至今变动(bp)": "{:+.2f}",
                },
            ),
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("等待债券收益率数据")

    # 大宗
    st.markdown("#### 大宗商品｜期货主连价格")
    src_note("商品价格概览")
    cmd = read("commodity", "商品价格概览")
    if not cmd.empty:
        cmd = cmd.copy()
        cmd["单位"] = cmd["资产名称"].map(COMMODITY_UNIT).fillna("")
        cmd = cmd[[c for c in ["资产名称", "单位", "数据日期", "最新价", "当日涨跌幅(%)", "近一周涨跌幅(%)", "年初至今涨跌幅(%)"] if c in cmd.columns]]
        st.dataframe(
            styled_table(cmd, ["当日涨跌幅(%)", "近一周涨跌幅(%)", "年初至今涨跌幅(%)"],
                         {"最新价": "{:,.2f}", "当日涨跌幅(%)": "{:+.2f}%",
                          "近一周涨跌幅(%)": "{:+.2f}%", "年初至今涨跌幅(%)": "{:+.2f}%"}),
            width="stretch", hide_index=True,
        )
    else:
        st.info("等待大宗商品数据")

    # 外汇
    st.markdown("#### 外汇｜人民币汇率")
    src_note("人民币外汇即期报价", "注：美元指数 DXY 与离岸 USD/CNH 当前接口未稳定获取，见页尾说明。")
    fx_val, fx_note = fx_spot_usdcny()
    c1, c2 = st.columns([1, 2])
    with c1:
        card("USD/CNY 即期（元）", fmt_num(fx_val, 4), None, fx_note)
    with c2:
        fixing = read("fx", "人民币中间价历史")
        if not fixing.empty:
            row, dcol = latest_macro_row(fixing)
            if row is not None:
                mid = parse_cn_number(row.get("美元兑人民币中间价"))
                st.caption(f"人民币中间价（美元兑人民币）：{fmt_num(mid, 4)} 元 ｜ 数据日期：{row.get('日期')}")
        else:
            st.info("等待外汇中间价数据")

    st.markdown("### 二、资金流向与仓位观察")
    st.caption("资金类指标口径各异，请务必结合每张表上方注明的「来源 / 单位 / 口径」解读。")

    st.markdown("#### 权益行业资金流向（净流入 / 净流出）")
    src_note("行业资金流")
    inflow, outflow = industry_flow_tables()
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### 🔺 行业资金净流入 TOP10（亿元）")
        if not inflow.empty:
            st.dataframe(styled_table(inflow, ["资金净额"], {"资金净额": "{:+,.2f}"}),
                         width="stretch", hide_index=True)
        else:
            st.info("当前无可排序行业资金流")
    with c2:
        st.markdown("##### 🔻 行业资金净流出 TOP10（亿元）")
        if not outflow.empty:
            st.dataframe(styled_table(outflow, ["资金净额"], {"资金净额": "{:+,.2f}"}),
                         width="stretch", hide_index=True)
        else:
            st.info("当前无可排序行业资金流")

    st.markdown("#### 商品期货持仓变化")
    src_note("商品持仓变化")
    oi = read("commodity", "商品持仓变化")
    if not oi.empty:
        st.dataframe(styled_table(oi, ["当日持仓变化", "近一周持仓变化"],
                                  {"最新持仓量": "{:,.0f}", "当日持仓变化": "{:+,.0f}", "近一周持仓变化": "{:+,.0f}"}),
                     width="stretch", hide_index=True)
    else:
        st.info("等待商品持仓数据")

    st.markdown("#### ETF 份额申赎")
    src_note("ETF基金申赎份额变化")
    subs, reds = etf_flow_tables()
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### 🔺 当日份额增加 TOP10（份）")
        if not subs.empty:
            st.dataframe(styled_table(subs, ["当日份额变化"], {"当日份额变化": "{:+,.0f}"}),
                         width="stretch", hide_index=True)
        else:
            st.info("尚未积累至少两个有效交易日的ETF份额快照")
    with c2:
        st.markdown("##### 🔻 当日份额减少 TOP10（份）")
        if not reds.empty:
            st.dataframe(styled_table(reds, ["当日份额变化"], {"当日份额变化": "{:+,.0f}"}),
                         width="stretch", hide_index=True)
        else:
            st.info("尚未积累至少两个有效交易日的ETF份额快照")

    with st.expander("行业当日涨跌强弱（申万一级行业）"):
        src_note("申万行业价格")
        gainers, losers = industry_price_tables()
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### 🔺 领涨 TOP10")
            if not gainers.empty:
                st.dataframe(styled_table(gainers, ["当日涨跌幅(%)"], {"当日涨跌幅(%)": "{:+.2f}%"}),
                             width="stretch", hide_index=True)
            else:
                st.info("当前行业价格字段不足")
        with c2:
            st.markdown("##### 🔻 领跌 TOP10")
            if not losers.empty:
                st.dataframe(styled_table(losers, ["当日涨跌幅(%)"], {"当日涨跌幅(%)": "{:+.2f}%"}),
                             width="stretch", hide_index=True)
            else:
                st.info("当前行业价格字段不足")

    with st.expander("当前待补 / 暂不可用数据（放在最后，不影响事实数据基座展示）"):
        st.markdown(
            """
            - **USD/CNH 历史**：当前东方财富历史接口受代理网络影响；
            - **美元指数 DXY**：当前两套公开接口均未稳定返回；
            - **DR001 / DR007 / R001 / R007**：本版本不使用 FDR 等不同口径指标冒充；
            - **T / TL 国债期货**：当前 AKShare 主力合约识别未完整返回；
            - **分机构现券净买入、理财规模、债基实时久期**：属于后续增强数据源。
            """
        )


def equity_page():
    st.subheader("权益市场")
    gainers, losers = industry_price_tables()
    inflow, outflow = industry_flow_tables()

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 行业领涨")
        if not gainers.empty:
            st.dataframe(styled_table(gainers, ["当日涨跌幅(%)"], {"当日涨跌幅(%)": "{:+.2f}%"}),
                         width="stretch", hide_index=True)
    with c2:
        st.markdown("#### 行业领跌")
        if not losers.empty:
            st.dataframe(styled_table(losers, ["当日涨跌幅(%)"], {"当日涨跌幅(%)": "{:+.2f}%"}),
                         width="stretch", hide_index=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 行业资金净流入")
        if not inflow.empty:
            st.dataframe(styled_table(inflow, ["资金净额", "涨跌幅"]),
                         width="stretch", hide_index=True)
    with c2:
        st.markdown("#### 行业资金净流出")
        if not outflow.empty:
            st.dataframe(styled_table(outflow, ["资金净额", "涨跌幅"]),
                         width="stretch", hide_index=True)

    for name in ["核心指数概览", "申万行业价格", "ETF行情与交易资金", "ETF基金申赎份额变化"]:
        st.markdown(f"#### {name}")
        df = read("equity", name)
        if not df.empty:
            st.dataframe(df, width="stretch", hide_index=True, height=420)
        else:
            st.info("当前未获取到数据")


def bond_page():
    st.subheader("固定收益市场")
    st.caption("收益率变化统一使用 bp；资金价格、现券、期货、ETF分别展示，不合成虚构的“债券净流入”。")
    names = [
        "国债收益率概览", "关键收益率曲线", "收益率曲线状态",
        "回购定盘利率_FR_FDR", "Shibor",
        "银行间现券成交", "国债期货主力实时", "债券ETF行情与交易资金",
    ]
    for name in names:
        st.markdown(f"#### {name}")
        df = read("fixed_income", name)
        if not df.empty:
            st.dataframe(df.tail(200).iloc[::-1], width="stretch", hide_index=True, height=400)
        else:
            st.info("当前未获取到数据；本平台不使用错误替代口径填充")


def fx_page():
    st.subheader("外汇市场")
    st.caption("优先展示当前真实可获得的人民币即期、中间价和掉期；缺失的 CNH/DXY 放在页面末尾。")

    fx_val, fx_note = fx_spot_usdcny()
    c1, c2 = st.columns([1, 3])
    with c1:
        card("USD/CNY", fmt_num(fx_val, 4), None, fx_note)
    with c2:
        spot = read("fx", "人民币外汇即期报价")
        if not spot.empty:
            st.dataframe(spot, width="stretch", hide_index=True)

    for name in ["人民币中间价历史", "外汇掉期报价"]:
        st.markdown(f"#### {name}")
        df = read("fx", name)
        if not df.empty:
            st.dataframe(df.tail(100).iloc[::-1], width="stretch", hide_index=True)
        else:
            st.info("当前未获取到数据")

    st.markdown("---")
    st.markdown("### 待补充的外汇扩展指标")
    for name in ["美元兑离岸人民币概览", "美元指数概览"]:
        st.markdown(f"#### {name}")
        df = read("fx", name)
        if not df.empty:
            st.dataframe(df, width="stretch", hide_index=True)
        else:
            st.info("当前公开接口未稳定获取，暂不展示虚构数据")


def commodity_page():
    st.subheader("大宗商品")
    for name in ["商品价格概览", "商品持仓变化", "中证商品指数"]:
        st.markdown(f"#### {name}")
        df = read("commodity", name)
        if not df.empty:
            if name == "商品价格概览":
                st.dataframe(
                    styled_table(
                        df,
                        ["当日涨跌幅(%)", "近一周涨跌幅(%)", "年初至今涨跌幅(%)"],
                        {
                            "当日涨跌幅(%)": "{:+.2f}%",
                            "近一周涨跌幅(%)": "{:+.2f}%",
                            "年初至今涨跌幅(%)": "{:+.2f}%",
                        },
                    ),
                    width="stretch",
                    hide_index=True,
                )
            else:
                st.dataframe(df.tail(150).iloc[::-1], width="stretch", hide_index=True)
        else:
            st.info("当前未获取到数据")


def macro_page():
    st.subheader("宏观数据")
    st.caption("宏观指标按官方公布口径原样展示（最新值 / 前值 / 同比 / 环比），不做加工或外推。来源与单位见「宏观数据状态表」及各卡片。")
    render_macro_snapshot()

    status = read("macro", "宏观数据状态表")
    if not status.empty:
        st.markdown("#### 宏观数据采集状态")
        st.dataframe(status, width="stretch", hide_index=True)

    if (DATA / "macro").exists():
        for p in sorted((DATA / "macro").glob("*_latest.csv")):
            if p.name in {"宏观数据状态表_latest.csv", "macro_manifest_latest.csv"}:
                continue
            st.markdown(f"#### {p.stem.replace('_latest','')}")
            try:
                df = pd.read_csv(p, encoding="utf-8-sig")
            except Exception:
                continue
            if df.empty:
                st.info("无数据")
                continue

            # 关键修复：原实现直接 df.tail(36)，而多数宏观文件是「新→旧」排序，
            # tail 取到的是最老的数据（2008-2012 年）。这里统一按时间升序后再取尾部，
            # 并标注真实的数据区间。
            dcol = find_col(df, ["月份", "日期", "时间", "统计时间", "报告期", "季度", "年份", "公布时间", "生效时间", "商品"])
            if dcol:
                disp = df.copy()
                disp["_排序"] = disp[dcol].map(_period_key)
                disp = disp.sort_values("_排序").drop(columns=["_排序"])
                tail = disp.tail(24).iloc[::-1]
                try:
                    first = str(disp.iloc[0][dcol])
                    last = str(disp.iloc[-1][dcol])
                    st.caption(f"数据区间：{first} ～ {last}（按时间降序，最新在前，展示最近 {len(tail)} 期）")
                except Exception:
                    pass
                # 滞后提示：若最新日期距今超过 90 天，明显提醒。
                try:
                    last_ts = pd.to_datetime(str(disp.iloc[-1][dcol]), errors="coerce")
                    if pd.notna(last_ts) and (pd.Timestamp.today() - last_ts).days > 90:
                        st.warning(f"⚠️ 该数据集最新日期为 {last_ts.date()}，已滞后超过 90 天，请以官方最新发布为准。")
                except Exception:
                    pass
            else:
                tail = df.tail(24)

            st.dataframe(tail, width="stretch", hide_index=True)


def status_page():
    st.subheader("数据基座状态")
    checks = [
        ("权益核心指数", not read("equity", "核心指数概览").empty, "中证指数网 / 新浪"),
        ("申万行业价格", not read("equity", "申万行业价格").empty, "申万"),
        ("行业资金流", not read("equity", "行业资金流").empty, "同花顺"),
        ("ETF行情", not read("equity", "ETF行情与交易资金").empty, "东方财富"),
        ("ETF申赎份额", not read("equity", "ETF基金申赎份额变化").empty, "沪深交易所份额快照"),
        ("国债收益率", not read("fixed_income", "国债收益率概览").empty, "公开债券行情"),
        ("政策性金融债曲线", not read("fixed_income", "关键收益率曲线").empty, "中国货币网"),
        ("资金面 FR/FDR", not read("fixed_income", "回购定盘利率_FR_FDR").empty, "中国货币网"),
        ("银行间现券", not read("fixed_income", "银行间现券成交").empty, "银行间市场公开行情"),
        ("国债期货", not read("fixed_income", "国债期货主力实时").empty, "中金所 / 新浪"),
        ("人民币即期", not read("fx", "人民币外汇即期报价").empty, "ChinaMoney"),
        ("USD/CNH", not read("fx", "美元兑离岸人民币概览").empty, "公开外汇行情"),
        ("美元指数", not read("fx", "美元指数概览").empty, "公开全球指数行情"),
        ("商品价格与持仓", not read("commodity", "商品价格概览").empty, "国内期货公开行情"),
        ("宏观数据", not read("macro", "宏观数据状态表").empty, "国家统计及公开宏观接口"),
    ]
    df = pd.DataFrame(checks, columns=["数据模块", "当前状态", "主要公开来源"])
    df["当前状态"] = df["当前状态"].map({True: "已获取", False: "待补 / 接口暂不可用"})
    st.dataframe(df, width="stretch", hide_index=True)
    st.warning("原则：数据缺失时明确留空。FDR007 不改名成 DR007；没有机构净买入数据时也不生成替代数字。")


tabs = st.tabs(["总览", "权益", "债券", "大宗商品", "宏观数据", "外汇", "数据状态"])

with tabs[0]:
    overview()
with tabs[1]:
    equity_page()
with tabs[2]:
    bond_page()
with tabs[3]:
    commodity_page()
with tabs[4]:
    macro_page()
with tabs[5]:
    fx_page()
with tabs[6]:
    status_page()
