import re
import numpy as np
import pandas as pd
import requests
import streamlit as st
import yfinance as yf
from bs4 import BeautifulSoup
from io import StringIO

st.set_page_config(
    page_title="Bubble Sniffer by Financify",
    page_icon="🐝",
    layout="wide"
)

# --- Financify paid login + usage protection ---
from pathlib import Path as _FinancifyPath
import sys as _financify_sys
_FINANCIFY_ROOT = _FinancifyPath(__file__).resolve().parent
if not (_FINANCIFY_ROOT / "common").exists() and (_FINANCIFY_ROOT.parent / "common").exists():
    _FINANCIFY_ROOT = _FINANCIFY_ROOT.parent
if str(_FINANCIFY_ROOT) not in _financify_sys.path:
    _financify_sys.path.insert(0, str(_FINANCIFY_ROOT))
from common.protect_tool import require_tool_access, record_tool_use
# --- end Financify protection imports ---

TOOL_NAME = "bubble-sniffer"
user = require_tool_access(TOOL_NAME)


HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

MONTH_PATTERN = r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"


# --------------------------------------------------
# Premium UI styling helpers
# --------------------------------------------------

PREMIUM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    :root {
        --honey: #FFB703;
        --gold: #F6C453;
        --amber: #FB8500;
        --ink: #14213D;
        --deep: #0B1020;
        --cream: #FFF8E7;
        --mint: #D8F3DC;
        --rose: #FFE0E9;
        --sky: #E4F1FF;
        --card: rgba(255, 255, 255, 0.82);
        --border: rgba(20, 33, 61, 0.12);
    }

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .stApp {
        background:
            radial-gradient(circle at 10% 8%, rgba(255, 183, 3, 0.28), transparent 32%),
            radial-gradient(circle at 90% 12%, rgba(33, 158, 188, 0.20), transparent 28%),
            radial-gradient(circle at 70% 95%, rgba(251, 133, 0, 0.18), transparent 35%),
            linear-gradient(135deg, #FFFDF7 0%, #FFF4C8 38%, #F6FBFF 100%);
        color: var(--deep);
    }

    .block-container {
        padding-top: 2.1rem;
        padding-bottom: 3rem;
        max-width: 1260px;
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #111827 0%, #1f2937 52%, #3b2602 100%);
        border-right: 1px solid rgba(255,255,255,0.12);
    }

    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span {
        color: #FFF7D6 !important;
    }

    div[data-testid="stTextInput"] input {
        border-radius: 16px;
        border: 1px solid rgba(246, 196, 83, 0.45);
        background: rgba(255,255,255,0.95);
        padding: 0.9rem 1rem;
        font-weight: 700;
        color: #111827;
    }

    .stButton > button {
        width: 100%;
        min-height: 3.2rem;
        border-radius: 18px;
        border: 0;
        background: linear-gradient(135deg, #FFB703 0%, #FB8500 48%, #E63946 100%);
        color: #111827;
        font-weight: 900;
        letter-spacing: 0.3px;
        box-shadow: 0 16px 35px rgba(251, 133, 0, 0.28);
        transition: transform .18s ease, box-shadow .18s ease;
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 22px 42px rgba(251, 133, 0, 0.36);
        color: #111827;
    }

    .hero-card {
        position: relative;
        overflow: hidden;
        border-radius: 34px;
        padding: 2.2rem 2.4rem;
        background:
            linear-gradient(135deg, rgba(11,16,32,0.95), rgba(31,41,55,0.94)),
            radial-gradient(circle at 85% 20%, rgba(255,183,3,0.35), transparent 30%);
        color: white;
        border: 1px solid rgba(255,255,255,0.12);
        box-shadow: 0 26px 70px rgba(17, 24, 39, 0.28);
        margin-bottom: 1.5rem;
    }

    .hero-card:after {
        content: "";
        position: absolute;
        width: 260px;
        height: 260px;
        right: -70px;
        top: -80px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(255,183,3,0.42), transparent 64%);
    }

    .hero-kicker {
        display: inline-flex;
        gap: 0.5rem;
        align-items: center;
        padding: 0.45rem 0.85rem;
        border-radius: 999px;
        background: rgba(255, 183, 3, 0.16);
        border: 1px solid rgba(255, 183, 3, 0.35);
        color: #FFE8A3;
        font-weight: 800;
        font-size: 0.88rem;
        margin-bottom: 1rem;
    }

    .hero-title {
        font-size: clamp(2.3rem, 5vw, 4.3rem);
        line-height: 0.96;
        font-weight: 900;
        letter-spacing: -2px;
        margin: 0;
        color: #ffffff;
    }

    .hero-subtitle {
        max-width: 780px;
        margin-top: 1.05rem;
        color: rgba(255,255,255,0.80);
        font-size: 1.05rem;
        line-height: 1.75;
        font-weight: 500;
    }

    .mini-pill-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.7rem;
        margin-top: 1.45rem;
    }

    .mini-pill {
        padding: 0.58rem 0.95rem;
        border-radius: 999px;
        background: rgba(255,255,255,0.10);
        border: 1px solid rgba(255,255,255,0.14);
        color: rgba(255,255,255,0.90);
        font-size: 0.88rem;
        font-weight: 700;
    }

    .premium-card {
        border-radius: 28px;
        padding: 1.35rem 1.45rem;
        background: var(--card);
        border: 1px solid var(--border);
        box-shadow: 0 18px 48px rgba(15, 23, 42, 0.10);
        backdrop-filter: blur(14px);
        margin: 1.2rem 0;
    }

    .dialogue-box {
        border-radius: 24px;
        padding: 1.1rem 1.2rem;
        margin: 1rem 0;
        border: 1px solid rgba(255,255,255,0.62);
        box-shadow: 0 16px 40px rgba(15,23,42,0.10);
    }

    .dialogue-title {
        font-weight: 900;
        font-size: 1rem;
        margin-bottom: 0.25rem;
        color: #111827;
    }

    .dialogue-text {
        font-weight: 600;
        line-height: 1.65;
        color: rgba(17,24,39,0.78);
    }

    .dialogue-info { background: linear-gradient(135deg, #E4F1FF, #FFFFFF); }
    .dialogue-honey { background: linear-gradient(135deg, #FFF3B0, #FFFFFF); }
    .dialogue-green { background: linear-gradient(135deg, #D8F3DC, #FFFFFF); }
    .dialogue-red { background: linear-gradient(135deg, #FFE0E9, #FFFFFF); }

    .section-title {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        font-size: 1.65rem;
        font-weight: 900;
        color: #111827;
        letter-spacing: -0.6px;
        margin-top: 2rem;
        margin-bottom: 0.6rem;
    }

    .section-title span {
        width: 12px;
        height: 34px;
        border-radius: 999px;
        background: linear-gradient(180deg, #FFB703, #FB8500);
        box-shadow: 0 10px 26px rgba(251,133,0,0.30);
    }

    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, rgba(255,255,255,0.95), rgba(255,246,214,0.92));
        border: 1px solid rgba(251,133,0,0.18);
        border-radius: 24px;
        padding: 1.2rem 1.1rem;
        box-shadow: 0 18px 40px rgba(15,23,42,0.10);
    }

    div[data-testid="metric-container"] label {
        font-weight: 800;
        color: rgba(17,24,39,0.64) !important;
    }

    div[data-testid="metric-container"] [data-testid="stMetricValue"] {
        color: #111827;
        font-weight: 900;
    }

    .table-shell {
        margin: 1rem 0 1.4rem 0;
        border-radius: 26px;
        overflow: hidden;
        border: 1px solid rgba(20,33,61,0.10);
        box-shadow: 0 18px 48px rgba(15,23,42,0.11);
        background: rgba(255,255,255,0.90);
    }

    .table-scroll {
        overflow-x: auto;
    }

    table.premium-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        font-size: 0.94rem;
        color: #111827;
    }

    table.premium-table thead th {
        position: sticky;
        top: 0;
        z-index: 2;
        background: linear-gradient(135deg, #111827, #1f2937 55%, #3b2602);
        color: #FFF7D6;
        text-align: left;
        padding: 1.05rem 1rem;
        font-weight: 900;
        white-space: nowrap;
        border-bottom: 1px solid rgba(255,255,255,0.12);
    }

    table.premium-table tbody td,
    table.premium-table tbody th {
        padding: 0.95rem 1rem;
        border-bottom: 1px solid rgba(20,33,61,0.08);
        font-weight: 650;
        vertical-align: middle;
    }

    table.premium-table tbody tr:nth-child(odd) { background: rgba(255,248,231,0.72); }
    table.premium-table tbody tr:nth-child(even) { background: rgba(255,255,255,0.86); }
    table.premium-table tbody tr:hover { background: #FFF0B8; }

    .badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 78px;
        padding: 0.32rem 0.7rem;
        border-radius: 999px;
        font-weight: 900;
        font-size: 0.80rem;
        border: 1px solid rgba(0,0,0,0.06);
    }

    .badge-pass, .badge-good, .badge-okay { background: #D8F3DC; color: #0B6B2C; }
    .badge-fail, .badge-red-flag, .badge-weak { background: #FFE0E9; color: #A4133C; }
    .badge-partial, .badge-momentum, .badge-missing { background: #FFF3B0; color: #8A5A00; }

    .footer-note {
        margin-top: 2rem;
        padding: 1rem 1.1rem;
        border-radius: 22px;
        background: rgba(17,24,39,0.90);
        color: rgba(255,255,255,0.82);
        font-weight: 650;
        text-align: center;
        box-shadow: 0 18px 44px rgba(15,23,42,0.16);
    }
</style>
"""

st.markdown(PREMIUM_CSS, unsafe_allow_html=True)


def dialogue_box(title, text, variant="info"):
    st.markdown(
        f"""
        <div class="dialogue-box dialogue-{variant}">
            <div class="dialogue-title">{title}</div>
            <div class="dialogue-text">{text}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def section_title(title):
    st.markdown(f'<div class="section-title"><span></span>{title}</div>', unsafe_allow_html=True)


def _display_cell(x):
    if pd.isna(x):
        return "N/A"
    if isinstance(x, (int, float, np.integer, np.floating)):
        return f"{float(x):,.2f}"
    text = str(x)
    badge_key = text.lower().replace(" ", "-").replace("/", "-")
    if badge_key in ["pass", "fail", "partial", "good", "okay", "red-flag", "weak", "momentum", "missing"]:
        return f'<span class="badge badge-{badge_key}">{text}</span>'
    return text


def show_numbered_dataframe(df):
    df = df.copy()
    df.index = range(1, len(df) + 1)
    display_df = df.copy()
    for col in display_df.columns:
        display_df[col] = display_df[col].map(_display_cell)
    html = display_df.to_html(escape=False, classes="premium-table")
    st.markdown(f'<div class="table-shell"><div class="table-scroll">{html}</div></div>', unsafe_allow_html=True)


# --------------------------------------------------
# Basic helpers
# --------------------------------------------------

def clean_number(x):
    try:
        if x is None or pd.isna(x):
            return np.nan

        x = str(x)
        x = x.replace(",", "")
        x = x.replace("%", "")
        x = x.replace("₹", "")
        x = x.replace("Rs.", "")
        x = x.replace("Rs", "")
        x = x.replace("Cr.", "")
        x = x.replace("Cr", "")
        x = x.replace("crores", "")
        x = x.replace("crore", "")
        x = x.replace("x", "")
        x = x.replace("−", "-")
        x = x.strip()

        if x in ["", "-", "—", "None", "nan"]:
            return np.nan

        match = re.search(r"-?\d+\.?\d*", x)
        if match:
            return float(match.group())

        return np.nan

    except Exception:
        return np.nan


def safe_float(x):
    try:
        if x is None or pd.isna(x):
            return np.nan
        return float(x)
    except Exception:
        return np.nan


def valid_values(values):
    return [safe_float(v) for v in values if not pd.isna(safe_float(v))]


def last_n(values, n=5):
    vals = valid_values(values)
    if len(vals) >= n:
        return vals[-n:]
    return [np.nan] * (n - len(vals)) + vals


def latest(values):
    vals = valid_values(values)
    return vals[-1] if vals else np.nan


def is_increasing(values):
    vals = valid_values(values)

    if len(vals) < 3:
        return False

    return vals[-1] > vals[0] and vals[-1] >= vals[-2]


def positive_and_increasing(values):
    vals = valid_values(values)

    if len(vals) < 3:
        return False

    if not all(v > 0 for v in vals):
        return False

    # Strict continuous increasing trend:
    # every year must be higher than the previous year.
    # No dip or flat year is allowed.
    return all(vals[i] > vals[i - 1] for i in range(1, len(vals)))


def calculate_margin(numerator, denominator):
    output = []

    for n, d in zip(numerator, denominator):
        n = safe_float(n)
        d = safe_float(d)

        if not np.isnan(n) and not np.isnan(d) and d != 0:
            output.append((n / d) * 100)
        else:
            output.append(np.nan)

    return output


def calculate_growth(values):
    vals = valid_values(values)

    if len(vals) < 2:
        return np.nan

    old = vals[-2]
    new = vals[-1]

    if old == 0:
        return np.nan

    return ((new - old) / abs(old)) * 100


def calculate_inventory_turnover(inventory_days):
    output = []

    for d in inventory_days:
        d = safe_float(d)

        if not np.isnan(d) and d > 0:
            output.append(365 / d)
        else:
            output.append(np.nan)

    return output


def calculate_incremental_roe(profit_after_tax, net_worth):
    output = []

    for i in range(1, len(profit_after_tax)):
        pat_now = safe_float(profit_after_tax[i])
        pat_prev = safe_float(profit_after_tax[i - 1])

        nw_now = safe_float(net_worth[i])
        nw_prev = safe_float(net_worth[i - 1])

        if (
            not np.isnan(pat_now)
            and not np.isnan(pat_prev)
            and not np.isnan(nw_now)
            and not np.isnan(nw_prev)
            and (nw_now - nw_prev) != 0
        ):
            output.append(((pat_now - pat_prev) / (nw_now - nw_prev)) * 100)
        else:
            output.append(np.nan)

    return output


# --------------------------------------------------
# Screener helpers
# --------------------------------------------------

def normalize_text(x):
    try:
        if x is None:
            return ""
        x = str(x)
        x = x.replace("\xa0", " ")
        x = x.replace("+", " ")
        x = x.replace("%", " %")
        x = re.sub(r"\s+", " ", x)
        return x.strip()
    except Exception:
        return ""


def normalize_label(x):
    x = normalize_text(x).lower()
    x = x.replace("%", "")
    x = re.sub(r"[^a-z0-9/ &.-]", " ", x)
    x = re.sub(r"\s+", " ", x)
    return x.strip()


def flatten_columns(df):
    df = df.copy()

    def clean_col_part(x):
        s = normalize_text(x)
        if not s:
            return ""
        if s.lower() in ["nan", "none"]:
            return ""
        if s.lower().startswith("unnamed"):
            return ""
        return s

    if isinstance(df.columns, pd.MultiIndex):
        new_cols = []
        for col in df.columns:
            parts = [clean_col_part(x) for x in col]
            parts = [p for p in parts if p]
            new_cols.append(" ".join(parts).strip())
        df.columns = new_cols
    else:
        df.columns = [clean_col_part(c) for c in df.columns]

    if len(df.columns) > 0 and not str(df.columns[0]).strip():
        df.columns = ["Metric"] + list(df.columns[1:])

    return df


def extract_year_columns(df):
    year_cols = []

    for col in df.columns:
        c = normalize_text(col)

        if re.search(rf"{MONTH_PATTERN}\s+\d{{4}}", c, re.I):
            year_cols.append(col)

    return year_cols


def is_annual_table(df):
    year_cols = extract_year_columns(df)
    return len(year_cols) >= 3


def table_first_col_text(df):
    if df is None or df.empty:
        return ""

    df = flatten_columns(df)
    first_col = df.columns[0]
    return " ".join(df[first_col].astype(str).map(normalize_label).tolist())


def find_row_values_exact_first(df, exact_aliases, contains_aliases=None, annual_only=True):
    if df is None or df.empty:
        return []

    df = flatten_columns(df)

    if annual_only and not is_annual_table(df):
        return []

    first_col = df.columns[0]
    year_cols = extract_year_columns(df)

    if not year_cols:
        year_cols = list(df.columns[1:])

    labels_clean = df[first_col].astype(str).map(normalize_label)

    for alias in exact_aliases:
        alias_clean = normalize_label(alias)
        mask = labels_clean == alias_clean

        if mask.any():
            row = df[mask].iloc[0]
            return [clean_number(row[c]) for c in year_cols]

    if contains_aliases:
        for alias in contains_aliases:
            alias_clean = normalize_label(alias)
            mask = labels_clean.str.contains(re.escape(alias_clean), na=False)

            if mask.any():
                row = df[mask].iloc[0]
                return [clean_number(row[c]) for c in year_cols]

    return []


def get_text_metric(text, label):
    try:
        clean = normalize_text(text)
        pattern = re.escape(label) + r"\s*[^0-9\-]{0,80}\s*(-?\d[\d,]*\.?\d*)"
        match = re.search(pattern, clean, flags=re.I)

        if match:
            return clean_number(match.group(1))

        return np.nan

    except Exception:
        return np.nan


def get_top_ratio_from_html(soup, label):
    try:
        items = soup.select("li.flex.flex-space-between")

        for item in items:
            name = normalize_text(item.get_text(" ", strip=True))

            if label.lower() in name.lower():
                numbers = re.findall(r"-?\d[\d,]*\.?\d*", name)

                if numbers:
                    return clean_number(numbers[-1])

        return np.nan

    except Exception:
        return np.nan


def table_from_screener_section(soup, section_id):
    section = soup.find(id=section_id)

    if section is None:
        return pd.DataFrame()

    table = section.find("table")

    if table is None:
        return pd.DataFrame()

    header_row = table.find("thead")
    headers = []

    if header_row:
        ths = header_row.find_all("th")
        headers = [normalize_text(th.get_text(" ", strip=True)) for th in ths]

    body = table.find("tbody") or table
    rows = []

    for tr in body.find_all("tr"):
        cells = tr.find_all(["th", "td"])

        if not cells:
            continue

        row = [normalize_text(cell.get_text(" ", strip=True)) for cell in cells]

        if len(row) >= 2:
            rows.append(row)

    if not rows:
        return pd.DataFrame()

    max_len = max(len(r) for r in rows)

    if not headers or len(headers) < max_len:
        first_row_years = [x for x in rows[0] if re.search(rf"{MONTH_PATTERN}\s+\d{{4}}", x, re.I)]

        if len(first_row_years) >= 3:
            headers = ["Metric"] + first_row_years
        else:
            headers = ["Metric"] + [f"Col {i}" for i in range(1, max_len)]

    headers = headers[:max_len]

    if len(headers) < max_len:
        headers += [f"Col {i}" for i in range(len(headers), max_len)]

    clean_rows = []

    for r in rows:
        r = r[:max_len] + [""] * (max_len - len(r))
        clean_rows.append(r)

    df = pd.DataFrame(clean_rows, columns=headers)
    df = flatten_columns(df)

    if len(df.columns) > 0:
        df = df.rename(columns={df.columns[0]: "Metric"})

    return df


def tables_from_screener_html(html):
    soup = BeautifulSoup(html, "html.parser")

    section_ids = {
        "profit_loss": "profit-loss",
        "balance_sheet": "balance-sheet",
        "cash_flow": "cash-flow",
        "ratios": "ratios",
        "shareholding": "shareholding"
    }

    parsed = {}

    for key, section_id in section_ids.items():
        parsed[key] = table_from_screener_section(soup, section_id)

    # Fallback: if Screener changes section IDs, use pandas read_html as backup.
    if all(df.empty for df in parsed.values()):
        try:
            tables = pd.read_html(StringIO(html))
            tables = [flatten_columns(t) for t in tables]

            for t in tables:
                first_col_text = table_first_col_text(t)

                if t.empty:
                    continue

                if "sales" in first_col_text and "net profit" in first_col_text:
                    parsed["profit_loss"] = t
                elif "equity capital" in first_col_text and "reserves" in first_col_text:
                    parsed["balance_sheet"] = t
                elif "cash from operating" in first_col_text or "free cash flow" in first_col_text:
                    parsed["cash_flow"] = t
                elif "inventory days" in first_col_text or "roce" in first_col_text:
                    parsed["ratios"] = t
                elif "promoters" in first_col_text and "public" in first_col_text:
                    parsed["shareholding"] = t
        except Exception:
            pass

    return parsed, soup


def fetch_screener(symbol):
    symbol = normalize_text(symbol).upper().replace(".NS", "")

    urls = [
        f"https://www.screener.in/company/{symbol}/consolidated/",
        f"https://www.screener.in/company/{symbol}/"
    ]

    html = None
    final_url = None
    last_error = None

    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.screener.in/",
        "Connection": "keep-alive"
    }

    for url in urls:
        try:
            r = session.get(url, headers=headers, timeout=30)
            page = r.text or ""

            bad_page = (
                r.status_code != 200
                or "Company not found" in page
                or "Page not found" in page
                or "Access denied" in page
                or "captcha" in page.lower()
            )

            if not bad_page and ("Profit & Loss" in page or "Balance Sheet" in page or "Cash Flows" in page):
                html = page
                final_url = url
                break

            last_error = f"{url} returned status {r.status_code}"

        except Exception as e:
            last_error = str(e)
            continue

    if not html:
        raise ValueError(f"Could not fetch usable Screener page for {symbol}. Last error: {last_error}")

    tables, soup = tables_from_screener_html(html)
    page_text = soup.get_text(" ", strip=True)

    data = {
        "source_url": final_url,

        "revenue": [],
        "profit_after_tax": [],
        "earnings_per_share": [],

        "cash_flow_from_operations": [],
        "free_cash_flow": [],
        "capital_expenditure": [],

        "return_on_equity": [],
        "return_on_capital_employed": [],
        "debt_to_equity_analytical": [],
        "inventory_days": [],
        "debtor_days": [],
        "dividend_payout": [],

        "reserves": [],
        "equity_capital": [],
        "borrowings": [],
        "net_worth": [],

        "retail_contribution": [],

        "current_pe": np.nan,
        "current_price": np.nan,
        "market_cap": np.nan
    }

    data["current_pe"] = get_top_ratio_from_html(soup, "Stock P/E")
    if np.isnan(data["current_pe"]):
        data["current_pe"] = get_text_metric(page_text, "Stock P/E")

    data["current_price"] = get_top_ratio_from_html(soup, "Current Price")
    if np.isnan(data["current_price"]):
        data["current_price"] = get_text_metric(page_text, "Current Price")

    data["market_cap"] = get_top_ratio_from_html(soup, "Market Cap")
    if np.isnan(data["market_cap"]):
        data["market_cap"] = get_text_metric(page_text, "Market Cap")

    profit_loss_df = tables.get("profit_loss", pd.DataFrame())
    balance_sheet_df = tables.get("balance_sheet", pd.DataFrame())
    cash_flow_df = tables.get("cash_flow", pd.DataFrame())
    ratios_df = tables.get("ratios", pd.DataFrame())
    shareholding_df = tables.get("shareholding", pd.DataFrame())

    if not profit_loss_df.empty:
        data["revenue"] = find_row_values_exact_first(
            profit_loss_df,
            exact_aliases=["Sales", "Revenue", "Revenue from Operations", "Total Revenue"],
            contains_aliases=["sales", "revenue from operations"],
            annual_only=True
        )

        data["profit_after_tax"] = find_row_values_exact_first(
            profit_loss_df,
            exact_aliases=["Net Profit", "Profit After Tax", "Profit after tax", "PAT", "Profit for the year", "Profit for the period"],
            contains_aliases=["net profit", "profit after tax", "profit for the year"],
            annual_only=True
        )

        data["earnings_per_share"] = find_row_values_exact_first(
            profit_loss_df,
            exact_aliases=["EPS in Rs", "EPS", "Earnings Per Share", "Basic EPS", "Diluted EPS"],
            contains_aliases=["eps in rs", "eps"],
            annual_only=True
        )

        data["dividend_payout"] = find_row_values_exact_first(
            profit_loss_df,
            exact_aliases=["Dividend Payout %", "Dividend Payout", "Dividend payout %"],
            contains_aliases=["dividend payout"],
            annual_only=True
        )

    if not cash_flow_df.empty:
        data["cash_flow_from_operations"] = find_row_values_exact_first(
            cash_flow_df,
            exact_aliases=["Cash from Operating Activity", "Cash Flow from Operating Activity", "Net Cash from Operating Activities", "Cash generated from operations"],
            contains_aliases=["cash from operating", "cash flow from operating", "net cash from operating"],
            annual_only=True
        )

        data["free_cash_flow"] = find_row_values_exact_first(
            cash_flow_df,
            exact_aliases=["Free Cash Flow", "FCF"],
            contains_aliases=["free cash flow"],
            annual_only=True
        )

        data["capital_expenditure"] = find_row_values_exact_first(
            cash_flow_df,
            exact_aliases=["Fixed assets purchased", "Fixed Assets Purchased", "Purchase of fixed assets", "Purchase of Property Plant and Equipment", "Purchase of PPE", "Capital Expenditure", "Capex"],
            contains_aliases=["fixed assets purchased", "purchase of fixed assets", "purchase of property plant", "capital expenditure"],
            annual_only=True
        )

    if not ratios_df.empty:
        data["return_on_capital_employed"] = find_row_values_exact_first(
            ratios_df,
            exact_aliases=["ROCE %", "ROCE", "Return on Capital Employed"],
            contains_aliases=["roce", "return on capital employed"],
            annual_only=True
        )

        data["inventory_days"] = find_row_values_exact_first(
            ratios_df,
            exact_aliases=["Inventory Days"],
            contains_aliases=["inventory days"],
            annual_only=True
        )

        data["debtor_days"] = find_row_values_exact_first(
            ratios_df,
            exact_aliases=["Debtor Days"],
            contains_aliases=["debtor days"],
            annual_only=True
        )

        data["debt_to_equity_analytical"] = find_row_values_exact_first(
            ratios_df,
            exact_aliases=["Debt to equity", "Debt / Equity", "D/E"],
            contains_aliases=["debt to equity", "debt / equity"],
            annual_only=True
        )

        if not data["dividend_payout"]:
            data["dividend_payout"] = find_row_values_exact_first(
                ratios_df,
                exact_aliases=["Dividend Payout %", "Dividend Payout", "Dividend payout %"],
                contains_aliases=["dividend payout"],
                annual_only=True
            )

    if not balance_sheet_df.empty:
        data["reserves"] = find_row_values_exact_first(
            balance_sheet_df,
            exact_aliases=["Reserves", "Reserve", "Other Equity", "Reserves and Surplus"],
            contains_aliases=["reserves", "other equity"],
            annual_only=True
        )

        data["equity_capital"] = find_row_values_exact_first(
            balance_sheet_df,
            exact_aliases=["Equity Capital", "Share Capital", "Equity Share Capital"],
            contains_aliases=["equity capital", "share capital"],
            annual_only=True
        )

        data["borrowings"] = find_row_values_exact_first(
            balance_sheet_df,
            exact_aliases=["Borrowings", "Total Borrowings", "Debt"],
            contains_aliases=["borrowings", "debt"],
            annual_only=True
        )

    if not shareholding_df.empty:
        data["retail_contribution"] = find_row_values_exact_first(
            shareholding_df,
            exact_aliases=["Public", "Retail", "Retail and others", "Others"],
            contains_aliases=["public", "retail", "others"],
            annual_only=False
        )

    if data["equity_capital"] and data["reserves"]:
        eq = last_n(data["equity_capital"], 10)
        res = last_n(data["reserves"], 10)

        net_worth = []

        for e, r in zip(eq, res):
            if not np.isnan(e) and not np.isnan(r):
                net_worth.append(e + r)
            else:
                net_worth.append(np.nan)

        data["net_worth"] = net_worth

    if data["profit_after_tax"] and data["net_worth"]:
        pat_vals = last_n(data["profit_after_tax"], 10)
        nw_vals = last_n(data["net_worth"], 10)

        roe_calc = []

        for p, nw in zip(pat_vals, nw_vals):
            if not np.isnan(p) and not np.isnan(nw) and nw != 0:
                roe_calc.append((p / nw) * 100)
            else:
                roe_calc.append(np.nan)

        data["return_on_equity"] = roe_calc

    if not data["debt_to_equity_analytical"] and data["borrowings"] and data["net_worth"]:
        debt_vals = last_n(data["borrowings"], 10)
        nw_vals = last_n(data["net_worth"], 10)

        de_calc = []

        for d, nw in zip(debt_vals, nw_vals):
            if not np.isnan(d) and not np.isnan(nw) and nw != 0:
                de_calc.append(d / nw)
            else:
                de_calc.append(np.nan)

        data["debt_to_equity_analytical"] = de_calc

    if not data["free_cash_flow"] and data["cash_flow_from_operations"] and data["capital_expenditure"]:
        cfo_vals = last_n(data["cash_flow_from_operations"], 10)
        capex_vals = last_n(data["capital_expenditure"], 10)

        fcf_calc = []

        for cfo, capex in zip(cfo_vals, capex_vals):
            if not np.isnan(cfo) and not np.isnan(capex):
                fcf_calc.append(cfo - abs(capex))
            else:
                fcf_calc.append(np.nan)

        data["free_cash_flow"] = fcf_calc

    if not any([data["revenue"], data["profit_after_tax"], data["cash_flow_from_operations"], data["reserves"]]):
        raise ValueError("Screener page opened, but annual financial tables could not be parsed.")

    return data


# --------------------------------------------------
# yfinance + Yahoo price fallback
# --------------------------------------------------

def _first_series(obj):
    """Return the first numeric series from a DataFrame/Series safely."""
    if obj is None:
        return pd.Series(dtype="float64")

    if isinstance(obj, pd.Series):
        return obj

    if isinstance(obj, pd.DataFrame):
        if obj.empty:
            return pd.Series(dtype="float64")
        return obj.iloc[:, 0]

    return pd.Series(dtype="float64")


def normalize_price_history(hist):
    """
    Convert yfinance/yahoo output into a clean DataFrame with only Close and Volume.
    This handles normal columns, MultiIndex columns, and partially missing latest rows.
    """
    if hist is None or not isinstance(hist, pd.DataFrame) or hist.empty:
        return pd.DataFrame(columns=["Close", "Volume"])

    df = hist.copy()

    close = None
    volume = None

    if isinstance(df.columns, pd.MultiIndex):
        for level in range(df.columns.nlevels):
            level_values = [str(x).strip().lower() for x in df.columns.get_level_values(level)]

            if "close" in level_values and close is None:
                try:
                    close = _first_series(df.xs(df.columns.get_level_values(level)[level_values.index("close")], axis=1, level=level))
                except Exception:
                    close = None

            if "volume" in level_values and volume is None:
                try:
                    volume = _first_series(df.xs(df.columns.get_level_values(level)[level_values.index("volume")], axis=1, level=level))
                except Exception:
                    volume = None
    else:
        col_map = {str(c).strip().lower(): c for c in df.columns}

        if "close" in col_map:
            close = df[col_map["close"]]
        elif "adj close" in col_map:
            close = df[col_map["adj close"]]

        if "volume" in col_map:
            volume = df[col_map["volume"]]

    # Extra fallback for flattened or strange column names like "Close CIPLA.NS"
    if close is None:
        for c in df.columns:
            c_text = " ".join(map(str, c)) if isinstance(c, tuple) else str(c)
            if "close" in c_text.lower() and "adj" not in c_text.lower():
                close = _first_series(df[c])
                break

    if volume is None:
        for c in df.columns:
            c_text = " ".join(map(str, c)) if isinstance(c, tuple) else str(c)
            if "volume" in c_text.lower():
                volume = _first_series(df[c])
                break

    if close is None:
        return pd.DataFrame(columns=["Close", "Volume"])

    out = pd.DataFrame(index=df.index)
    out["Close"] = pd.to_numeric(close, errors="coerce")

    if volume is not None:
        out["Volume"] = pd.to_numeric(volume, errors="coerce")
    else:
        out["Volume"] = np.nan

    out = out.dropna(subset=["Close"])
    out = out[~out.index.duplicated(keep="last")]
    out = out.sort_index()

    return out


def fetch_yahoo_chart_api(yf_symbol):
    """Direct Yahoo chart fallback used when yfinance history returns empty on Streamlit."""
    symbol = str(yf_symbol).strip().upper()
    if not symbol:
        return pd.DataFrame(columns=["Close", "Volume"])

    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {
        "range": "3y",
        "interval": "1d",
        "includePrePost": "false",
        "events": "history"
    }

    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=25)
        if r.status_code != 200:
            return pd.DataFrame(columns=["Close", "Volume"])

        payload = r.json()
        chart = payload.get("chart", {})
        result = chart.get("result", [])

        if not result:
            return pd.DataFrame(columns=["Close", "Volume"])

        result0 = result[0]
        timestamps = result0.get("timestamp", [])
        quote = result0.get("indicators", {}).get("quote", [{}])[0]

        if not timestamps or "close" not in quote:
            return pd.DataFrame(columns=["Close", "Volume"])

        out = pd.DataFrame({
            "Date": pd.to_datetime(timestamps, unit="s"),
            "Close": quote.get("close", []),
            "Volume": quote.get("volume", [])
        })

        out = out.set_index("Date")
        return normalize_price_history(out)

    except Exception:
        return pd.DataFrame(columns=["Close", "Volume"])


def fetch_yfinance(yf_symbol):
    symbol = str(yf_symbol).strip().upper()

    data = {
        "price_history": pd.DataFrame(columns=["Close", "Volume"]),
        "current_pe": np.nan,
        "earnings_yield": np.nan,
        "price_source": "Not fetched"
    }

    if not symbol:
        return data

    candidate_symbols = [symbol]

    # NSE sometimes fails on Yahoo temporarily. BSE fallback gives usable technical indicators.
    if symbol.endswith(".NS"):
        candidate_symbols.append(symbol.replace(".NS", ".BO"))

    for candidate in candidate_symbols:
        # Method 1: yfinance Ticker.history
        try:
            ticker = yf.Ticker(candidate)
            hist = ticker.history(period="3y", interval="1d", auto_adjust=False, actions=False)
            hist = normalize_price_history(hist)

            if not hist.empty and len(hist.dropna(subset=["Close"])) >= 200:
                data["price_history"] = hist
                data["price_source"] = f"yfinance history: {candidate}"
                break
        except Exception:
            pass

        # Method 2: yfinance download fallback
        try:
            hist = yf.download(
                candidate,
                period="3y",
                interval="1d",
                auto_adjust=False,
                progress=False,
                threads=False
            )
            hist = normalize_price_history(hist)

            if not hist.empty and len(hist.dropna(subset=["Close"])) >= 200:
                data["price_history"] = hist
                data["price_source"] = f"yfinance download: {candidate}"
                break
        except Exception:
            pass

        # Method 3: direct Yahoo chart API fallback
        try:
            hist = fetch_yahoo_chart_api(candidate)

            if not hist.empty and len(hist.dropna(subset=["Close"])) >= 200:
                data["price_history"] = hist
                data["price_source"] = f"Yahoo chart API: {candidate}"
                break
        except Exception:
            pass

    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        pe = safe_float(info.get("trailingPE", np.nan))
        data["current_pe"] = pe

        if not np.isnan(pe) and pe != 0:
            data["earnings_yield"] = 100 / pe

    except Exception:
        pass

    return data


# --------------------------------------------------
# Price indicators
# --------------------------------------------------

def calculate_rsi(price_data, period=14):
    price_data = normalize_price_history(price_data)

    if price_data.empty or "Close" not in price_data.columns:
        return np.nan

    close = pd.to_numeric(price_data["Close"], errors="coerce").dropna()

    if len(close) < period + 1:
        return np.nan

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    latest_gain = avg_gain.iloc[-1]
    latest_loss = avg_loss.iloc[-1]

    if pd.isna(latest_gain) or pd.isna(latest_loss):
        return np.nan

    if latest_loss == 0:
        return 100.0 if latest_gain > 0 else 50.0

    rs = latest_gain / latest_loss
    rsi = 100 - (100 / (1 + rs))

    return safe_float(rsi)


def calculate_dma(price_data):
    price_data = normalize_price_history(price_data)

    if price_data.empty or "Close" not in price_data.columns:
        return np.nan, np.nan

    close = pd.to_numeric(price_data["Close"], errors="coerce").dropna()

    dma50 = close.rolling(50, min_periods=50).mean().iloc[-1] if len(close) >= 50 else np.nan
    dma200 = close.rolling(200, min_periods=200).mean().iloc[-1] if len(close) >= 200 else np.nan

    return safe_float(dma50), safe_float(dma200)


def calculate_volume_index(price_data):
    price_data = normalize_price_history(price_data)

    if price_data.empty or "Volume" not in price_data.columns:
        return np.nan

    volume = pd.to_numeric(price_data["Volume"], errors="coerce").dropna()

    if len(volume) < 20:
        return np.nan

    latest_volume = volume.iloc[-1]
    average_volume = volume.tail(50).mean()

    if pd.isna(latest_volume) or pd.isna(average_volume) or average_volume == 0:
        return np.nan

    return safe_float(latest_volume / average_volume)


# --------------------------------------------------
# App UI
# --------------------------------------------------

st.markdown(
    """
    <div class="hero-card">
        <div class="hero-kicker">🐝 Bubble Sniffer • Premium Honey Console</div>
        <h1 class="hero-title">Bubble Sniffer by Financify</h1>
        <div class="hero-subtitle">
            Checks whether a stock has real honey or just too much market buzz. Educational only. Not investment advice.
        </div>
        <div class="mini-pill-row">
            <div class="mini-pill">🍯 Fundamental Honey Check</div>
            <div class="mini-pill">🐝 Bubble / Hype Check</div>
            <div class="mini-pill">📊 Clean Annual Tables</div>
            <div class="mini-pill">✨ Premium Dashboard View</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

dialogue_box(
    "How to use this tool",
    "Enter the Screener/NSE symbol and Yahoo Finance symbol, then press Sniff Bubble. The calculation logic is unchanged; this version only makes the tool more breathable, colourful, premium and user-friendly.",
    "honey"
)

with st.sidebar:
    st.markdown("### 🐝 Input Console")
    dialogue_box(
        "Stock identity",
        "Use Screener symbol for financial statements and Yahoo symbol for price indicators.",
        "honey"
    )

    screener_symbol = st.text_input("Screener / NSE Symbol", value="CIPLA")
    yahoo_symbol = st.text_input("Yahoo Finance Symbol", value="CIPLA.NS")

    st.markdown("---")
    run = st.button("🐝 Sniff Bubble", type="primary")

    dialogue_box(
        "Reminder",
        "This is an educational tool only. It is not a stock recommendation, target price, or buy/sell signal.",
        "info"
    )

if run:
    record_tool_use(TOOL_NAME)
    with st.container():
        dialogue_box("Step 1", "Fetching annual financial data from Screener first.", "info")
        with st.spinner("Fetching Screener data first..."):
            try:
                screener = fetch_screener(screener_symbol)
                st.success("Screener data fetched.")
            except Exception as e:
                screener = {}
                st.error(f"Screener fetch failed: {e}")

        dialogue_box("Step 2", "Fetching yfinance fallback for price indicators like RSI, moving averages and volume index.", "info")
        with st.spinner("Fetching yfinance fallback for price indicators..."):
            try:
                yfin = fetch_yfinance(yahoo_symbol)
                st.success("yfinance fallback fetched.")
                if yfin.get("price_source") and yfin.get("price_source") != "Not fetched":
                    dialogue_box("Price data source", yfin.get("price_source"), "green")
            except Exception as e:
                yfin = {}
                st.warning(f"yfinance fallback failed: {e}")

    revenue = last_n(screener.get("revenue", []), 5)
    profit_after_tax = last_n(screener.get("profit_after_tax", []), 5)
    earnings_per_share = last_n(screener.get("earnings_per_share", []), 5)

    cash_flow_from_operations = last_n(screener.get("cash_flow_from_operations", []), 5)
    free_cash_flow = last_n(screener.get("free_cash_flow", []), 5)

    return_on_equity = last_n(screener.get("return_on_equity", []), 5)
    return_on_capital_employed = last_n(screener.get("return_on_capital_employed", []), 5)

    inventory_days = last_n(screener.get("inventory_days", []), 5)
    dividend_payout = last_n(screener.get("dividend_payout", []), 5)
    debt_to_equity_analytical = last_n(screener.get("debt_to_equity_analytical", []), 5)

    reserves = last_n(screener.get("reserves", []), 5)
    equity_capital = last_n(screener.get("equity_capital", []), 5)

    net_worth = []

    for e, r in zip(equity_capital, reserves):
        if not np.isnan(e) and not np.isnan(r):
            net_worth.append(e + r)
        else:
            net_worth.append(np.nan)

    if all(np.isnan(x) for x in return_on_equity):
        return_on_equity = calculate_margin(profit_after_tax, net_worth)

    profit_after_tax_margin = calculate_margin(profit_after_tax, revenue)
    inventory_turnover = calculate_inventory_turnover(inventory_days)
    incremental_roe = calculate_incremental_roe(profit_after_tax, net_worth)

    current_pe = screener.get("current_pe", np.nan)

    if np.isnan(current_pe):
        current_pe = yfin.get("current_pe", np.nan)

    eps_growth_latest = calculate_growth(earnings_per_share)

    if not np.isnan(current_pe) and not np.isnan(eps_growth_latest) and eps_growth_latest > 0:
        peg_ratio = current_pe / eps_growth_latest
    else:
        peg_ratio = np.nan

    if not np.isnan(current_pe) and current_pe != 0:
        earnings_yield = 100 / current_pe
    else:
        earnings_yield = yfin.get("earnings_yield", np.nan)

    price_history = yfin.get("price_history", pd.DataFrame())

    rsi = calculate_rsi(price_history)
    dma50, dma200 = calculate_dma(price_history)
    volume_index = calculate_volume_index(price_history)

    retail_contribution = screener.get("retail_contribution", [])
    retail_contribution = valid_values(retail_contribution)

    if len(retail_contribution) >= 2:
        retail_increased = retail_contribution[-1] > retail_contribution[-2]
    else:
        retail_increased = None

    section_title("Fetched Annual Data")
    dialogue_box(
        "Financial statement snapshot",
        "The table below keeps the same annual data, but presents it in a cleaner, more spacious and premium format.",
        "honey"
    )

    preview = pd.DataFrame({
        "Metric": [
            "Revenue",
            "Profit After Tax",
            "Profit After Tax Margin",
            "Earnings Per Share",
            "Cash Flow from Operations",
            "Free Cash Flow",
            "Return on Equity",
            "Return on Capital Employed",
            "Inventory Days",
            "Inventory Turnover",
            "Dividend Payout",
            "D/E Analytical Ratio"
        ],
        "Year 1": [
            revenue[0], profit_after_tax[0], profit_after_tax_margin[0],
            earnings_per_share[0], cash_flow_from_operations[0], free_cash_flow[0],
            return_on_equity[0], return_on_capital_employed[0], inventory_days[0],
            inventory_turnover[0], dividend_payout[0], debt_to_equity_analytical[0]
        ],
        "Year 2": [
            revenue[1], profit_after_tax[1], profit_after_tax_margin[1],
            earnings_per_share[1], cash_flow_from_operations[1], free_cash_flow[1],
            return_on_equity[1], return_on_capital_employed[1], inventory_days[1],
            inventory_turnover[1], dividend_payout[1], debt_to_equity_analytical[1]
        ],
        "Year 3": [
            revenue[2], profit_after_tax[2], profit_after_tax_margin[2],
            earnings_per_share[2], cash_flow_from_operations[2], free_cash_flow[2],
            return_on_equity[2], return_on_capital_employed[2], inventory_days[2],
            inventory_turnover[2], dividend_payout[2], debt_to_equity_analytical[2]
        ],
        "Year 4": [
            revenue[3], profit_after_tax[3], profit_after_tax_margin[3],
            earnings_per_share[3], cash_flow_from_operations[3], free_cash_flow[3],
            return_on_equity[3], return_on_capital_employed[3], inventory_days[3],
            inventory_turnover[3], dividend_payout[3], debt_to_equity_analytical[3]
        ],
        "Year 5": [
            revenue[4], profit_after_tax[4], profit_after_tax_margin[4],
            earnings_per_share[4], cash_flow_from_operations[4], free_cash_flow[4],
            return_on_equity[4], return_on_capital_employed[4], inventory_days[4],
            inventory_turnover[4], dividend_payout[4], debt_to_equity_analytical[4]
        ]
    })

    show_numbered_dataframe(preview)

    section_title("🍯 Fundamental Honey Check")
    dialogue_box(
        "Quality first",
        "This section checks whether the stock has real honey in the business numbers before looking at market buzz.",
        "green"
    )

    score = 0
    results = []

    if is_increasing(revenue):
        score += 1
        results.append(["Revenue Growth", "Pass", "Revenue is increasing."])
    else:
        results.append(["Revenue Growth", "Fail", "Revenue is not clearly increasing."])

    if latest(profit_after_tax_margin) > 20 and is_increasing(profit_after_tax_margin):
        score += 1
        results.append(["Profit After Tax Margin", "Pass", "PAT margin is above 20% and increasing."])
    else:
        results.append(["Profit After Tax Margin", "Fail", "PAT margin is not above 20% and increasing."])

    if is_increasing(earnings_per_share):
        score += 1
        results.append(["Earnings Per Share", "Pass", "EPS is increasing."])
    else:
        results.append(["Earnings Per Share", "Fail", "EPS is not clearly increasing."])

    if positive_and_increasing(free_cash_flow) and positive_and_increasing(cash_flow_from_operations):
        score += 1
        results.append(["Cash Flow Quality", "Pass", "FCF and CFO are positive and continuously increasing with no dip."])
    else:
        results.append(["Cash Flow Quality", "Fail", "FCF and CFO are not both positive and continuously increasing with no dip."])

    if (
        latest(return_on_equity) > 20
        and latest(return_on_capital_employed) > 20
        and is_increasing(return_on_equity)
        and is_increasing(return_on_capital_employed)
    ):
        score += 1
        results.append(["Return Ratios", "Pass", "ROE and ROCE are both above 20% and increasing."])
    else:
        results.append(["Return Ratios", "Fail", "ROE and ROCE are not both above 20% and increasing."])

    if is_increasing(earnings_per_share) and is_increasing(incremental_roe):
        score += 1
        results.append(["Incremental ROE vs EPS", "Pass", "EPS and incremental ROE are improving. Growth quality looks good."])
    elif is_increasing(earnings_per_share) and not is_increasing(incremental_roe):
        results.append(["Incremental ROE vs EPS", "Fail", "EPS increasing but incremental ROE decreasing. Growth quality may be weak."])
    else:
        results.append(["Incremental ROE vs EPS", "Fail", "EPS and incremental ROE do not confirm quality growth."])

    if is_increasing(profit_after_tax_margin) and is_increasing(inventory_turnover):
        score += 1
        results.append(["PAT Margin vs Inventory Turnover", "Pass", "Both PAT margin and inventory turnover are improving."])
    elif is_increasing(profit_after_tax_margin) or is_increasing(inventory_turnover):
        score += 0.5
        results.append(["PAT Margin vs Inventory Turnover", "Partial", "Either PAT margin or inventory turnover is improving."])
    else:
        results.append(["PAT Margin vs Inventory Turnover", "Fail", "Both are decreasing or weak. Red flag."])

    if latest(dividend_payout) < 10:
        score += 1
        results.append(["Dividend Payout", "Pass", "Dividend payout is below 10%."])
    else:
        results.append(["Dividend Payout", "Fail", "Dividend payout is above 10% or unavailable."])

    if latest(debt_to_equity_analytical) < 0.2:
        score += 1
        results.append(["D/E Analytical Ratio", "Pass", "D/E analytical ratio is below 0.2."])
    else:
        results.append(["D/E Analytical Ratio", "Fail", "D/E analytical ratio is above 0.2 or unavailable."])

    result_df = pd.DataFrame(results, columns=["Parameter", "Result", "Comment"])

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Fundamental Score", f"{score}/9")
    c2.metric("EPS Growth Latest", f"{eps_growth_latest:.2f}%" if not np.isnan(eps_growth_latest) else "N/A")
    c3.metric("Current P/E", f"{current_pe:.2f}" if not np.isnan(current_pe) else "N/A")
    c4.metric("PEG Ratio", f"{peg_ratio:.2f}" if not np.isnan(peg_ratio) else "N/A")

    show_numbered_dataframe(result_df)

    if score >= 8:
        dialogue_box(
            "🍯 Strong Honey",
            "Fundamental score is 8 or above. Premium valuation may be justified if growth continues.",
            "green"
        )
    else:
        dialogue_box(
            "🐝 Fundamental score is below 8",
            "Checking bubble / hype indicators now.",
            "honey"
        )

        section_title("🐝 Bubble / Hype Check")

        bubble_score = 0
        bubble_results = []

        if not np.isnan(volume_index):
            if volume_index > 2:
                bubble_score += 1
                bubble_results.append(["Volume Index", "Red Flag", f"Volume index is high at {volume_index:.2f}x."])
            else:
                bubble_results.append(["Volume Index", "Okay", f"Volume index is {volume_index:.2f}x."])
        else:
            bubble_results.append(["Volume Index", "Missing", "Could not calculate volume index."])

        if not np.isnan(rsi):
            if rsi > 70:
                bubble_score += 1
                bubble_results.append(["RSI", "Red Flag", f"RSI is overheated at {rsi:.2f}."])
            else:
                bubble_results.append(["RSI", "Okay", f"RSI is {rsi:.2f}."])
        else:
            bubble_results.append(["RSI", "Missing", "Could not calculate RSI."])

        if not np.isnan(dma50) and not np.isnan(dma200):
            if dma50 > dma200:
                bubble_score += 0.5
                bubble_results.append(["50 DMA vs 200 DMA", "Momentum", "50 DMA is above 200 DMA."])
            else:
                bubble_results.append(["50 DMA vs 200 DMA", "Weak", "50 DMA is below 200 DMA."])
        else:
            bubble_results.append(["50 DMA vs 200 DMA", "Missing", "Could not calculate moving averages."])

        if retail_increased is True:
            bubble_score += 1
            bubble_results.append(["Retail Contribution", "Red Flag", "Retail / public contribution has increased."])
        elif retail_increased is False:
            bubble_results.append(["Retail Contribution", "Okay", "Retail / public contribution has not increased."])
        else:
            bubble_results.append(["Retail Contribution", "Missing", "Could not detect retail/public contribution from Screener."])

        if not np.isnan(current_pe):
            if current_pe > 25:
                bubble_score += 1
                bubble_results.append(["P/E Ratio", "Red Flag", f"P/E is above 25 at {current_pe:.2f}."])
            else:
                bubble_results.append(["P/E Ratio", "Good", f"P/E is below 25 at {current_pe:.2f}."])
        else:
            bubble_results.append(["P/E Ratio", "Missing", "Could not fetch P/E."])

        if not np.isnan(peg_ratio):
            if peg_ratio > 1.5:
                bubble_score += 1
                bubble_results.append(["PEG Ratio", "Red Flag", f"PEG is above 1.5 at {peg_ratio:.2f}."])
            else:
                bubble_results.append(["PEG Ratio", "Good", f"PEG is below 1.5 at {peg_ratio:.2f}."])
        else:
            bubble_results.append(["PEG Ratio", "Missing", "Could not calculate PEG because P/E or EPS growth is missing."])

        if not np.isnan(earnings_yield):
            if earnings_yield < 5:
                bubble_score += 1
                bubble_results.append(["Earnings Yield", "Red Flag", f"Earnings yield is low at {earnings_yield:.2f}%."])
            else:
                bubble_results.append(["Earnings Yield", "Good", f"Earnings yield is {earnings_yield:.2f}%."])
        else:
            bubble_results.append(["Earnings Yield", "Missing", "Could not calculate earnings yield."])

        bubble_df = pd.DataFrame(bubble_results, columns=["Bubble Parameter", "View", "Comment"])

        st.metric("Bubble Score", f"{bubble_score}/7")

        if bubble_score >= 5:
            dialogue_box("🔥 Full Madness Mode", "Weak fundamentals plus strong hype signs. Bubble risk looks high.", "red")
        elif bubble_score >= 3:
            dialogue_box("🐝 Buzz Building", "Some bubble signs are visible.", "honey")
        else:
            dialogue_box("🍯 No Major Bubble Smell", "Hype signs are not very strong.", "green")

        show_numbered_dataframe(bubble_df)

        if not price_history.empty:
            section_title("Price Chart")
            dialogue_box("Price movement", "Latest closing price movement from the fetched price history.", "info")
            st.line_chart(price_history["Close"])

    st.markdown(
        '<div class="footer-note">Educational tool only. Not investment advice, stock recommendation, target price, or buy/sell signal.</div>',
        unsafe_allow_html=True
    )
else:
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        dialogue_box("🍯 Step 1", "Enter Screener/NSE symbol for annual financials.", "honey")
    with col_b:
        dialogue_box("📈 Step 2", "Enter Yahoo Finance symbol for price indicators.", "info")
    with col_c:
        dialogue_box("🐝 Step 3", "Press Sniff Bubble and read the premium dashboard.", "green")
