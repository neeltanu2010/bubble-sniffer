import re
import numpy as np
import pandas as pd
import requests
import streamlit as st
import yfinance as yf
from bs4 import BeautifulSoup

st.set_page_config(
    page_title="Bubble Sniffer by Financify",
    page_icon="🐝",
    layout="wide"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

MONTH_PATTERN = r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"


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

    return all(v > 0 for v in vals) and vals[-1] > vals[0] and vals[-1] >= vals[-2]


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


def show_numbered_dataframe(df):
    df = df.copy()
    df.index = range(1, len(df) + 1)
    st.dataframe(df, use_container_width=True)


# --------------------------------------------------
# Screener helpers
# --------------------------------------------------

def flatten_columns(df):
    df = df.copy()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [
            " ".join([str(x) for x in col if str(x).lower() != "nan"]).strip()
            for col in df.columns
        ]
    else:
        df.columns = [str(c).strip() for c in df.columns]

    return df


def extract_year_columns(df):
    year_cols = []

    for col in df.columns:
        c = str(col).strip()

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
    return " ".join(df[first_col].astype(str).str.lower().tolist())


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

    labels = df[first_col].astype(str).str.lower().str.strip()
    labels_clean = labels.str.replace(r"\s+", " ", regex=True)

    for alias in exact_aliases:
        alias_clean = alias.lower().strip()
        mask = labels_clean == alias_clean

        if mask.any():
            row = df[mask].iloc[0]
            return [clean_number(row[c]) for c in year_cols]

    if contains_aliases:
        for alias in contains_aliases:
            alias_clean = alias.lower().strip()
            mask = labels_clean.str.contains(re.escape(alias_clean), na=False)

            if mask.any():
                row = df[mask].iloc[0]
                return [clean_number(row[c]) for c in year_cols]

    return []


def get_text_metric(text, label):
    try:
        pattern = label + r".{0,80}?(-?\d+\.?\d*)"
        match = re.search(pattern, text, flags=re.I)

        if match:
            return clean_number(match.group(1))

        return np.nan

    except Exception:
        return np.nan


def get_top_ratio_from_html(soup, label):
    try:
        items = soup.select("li.flex.flex-space-between")

        for item in items:
            name = item.get_text(" ", strip=True)

            if label.lower() in name.lower():
                numbers = re.findall(r"-?\d+\.?\d*", name)

                if numbers:
                    return clean_number(numbers[-1])

        return np.nan

    except Exception:
        return np.nan


def fetch_screener(symbol):
    urls = [
        f"https://www.screener.in/company/{symbol}/consolidated/",
        f"https://www.screener.in/company/{symbol}/"
    ]

    html = None
    final_url = None

    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=25)

            if r.status_code == 200 and "Company not found" not in r.text:
                html = r.text
                final_url = url
                break

        except Exception:
            continue

    if not html:
        raise ValueError("Could not fetch Screener page.")

    tables = pd.read_html(html)
    tables = [flatten_columns(t) for t in tables]

    soup = BeautifulSoup(html, "html.parser")
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

    for df in tables:
        if df.empty or not is_annual_table(df):
            continue

        first_col_text = table_first_col_text(df)

        looks_like_profit_loss = (
            ("sales" in first_col_text or "revenue" in first_col_text)
            and ("net profit" in first_col_text or "profit after tax" in first_col_text or "eps" in first_col_text)
        )

        if looks_like_profit_loss:
            revenue = find_row_values_exact_first(
                df,
                exact_aliases=[
                    "Sales",
                    "Revenue",
                    "Revenue from Operations",
                    "Total Revenue"
                ],
                contains_aliases=[
                    "sales",
                    "revenue from operations"
                ],
                annual_only=True
            )

            if revenue and len(revenue) >= 3:
                data["revenue"] = revenue

            pat = find_row_values_exact_first(
                df,
                exact_aliases=[
                    "Net Profit",
                    "Profit After Tax",
                    "Profit after tax",
                    "PAT",
                    "Profit for the year",
                    "Profit for the period"
                ],
                contains_aliases=[
                    "net profit",
                    "profit after tax",
                    "profit for the year"
                ],
                annual_only=True
            )

            if pat and len(pat) >= 3:
                data["profit_after_tax"] = pat

            eps = find_row_values_exact_first(
                df,
                exact_aliases=[
                    "EPS in Rs",
                    "EPS",
                    "Earnings Per Share",
                    "Basic EPS",
                    "Diluted EPS"
                ],
                contains_aliases=[
                    "eps in rs",
                    "eps"
                ],
                annual_only=True
            )

            if eps and len(eps) >= 3:
                data["earnings_per_share"] = eps

            dividend_payout = find_row_values_exact_first(
                df,
                exact_aliases=[
                    "Dividend Payout %",
                    "Dividend Payout",
                    "Dividend payout %"
                ],
                contains_aliases=[
                    "dividend payout"
                ],
                annual_only=True
            )

            if dividend_payout and len(dividend_payout) >= 1:
                data["dividend_payout"] = dividend_payout

        looks_like_cash_flow = (
            "cash from operating" in first_col_text
            or "cash flow from operating" in first_col_text
            or "cash from investing" in first_col_text
            or "free cash flow" in first_col_text
        )

        if looks_like_cash_flow:
            cfo = find_row_values_exact_first(
                df,
                exact_aliases=[
                    "Cash from Operating Activity",
                    "Cash Flow from Operating Activity",
                    "Net Cash from Operating Activities",
                    "Cash generated from operations"
                ],
                contains_aliases=[
                    "cash from operating",
                    "cash flow from operating",
                    "net cash from operating"
                ],
                annual_only=True
            )

            if cfo and len(cfo) >= 3:
                data["cash_flow_from_operations"] = cfo

            fcf = find_row_values_exact_first(
                df,
                exact_aliases=[
                    "Free Cash Flow",
                    "FCF"
                ],
                contains_aliases=[
                    "free cash flow"
                ],
                annual_only=True
            )

            if fcf and len(fcf) >= 3:
                data["free_cash_flow"] = fcf

            capex = find_row_values_exact_first(
                df,
                exact_aliases=[
                    "Fixed assets purchased",
                    "Fixed Assets Purchased",
                    "Purchase of fixed assets",
                    "Purchase of Property Plant and Equipment",
                    "Purchase of PPE",
                    "Capital Expenditure",
                    "Capex"
                ],
                contains_aliases=[
                    "fixed assets purchased",
                    "purchase of fixed assets",
                    "purchase of property plant",
                    "capital expenditure"
                ],
                annual_only=True
            )

            if capex and len(capex) >= 3:
                data["capital_expenditure"] = capex

        looks_like_ratio_table = (
            "roe" in first_col_text
            or "roce" in first_col_text
            or "return on equity" in first_col_text
            or "return on capital employed" in first_col_text
            or "inventory days" in first_col_text
            or "debtor days" in first_col_text
            or "dividend payout" in first_col_text
        )

        if looks_like_ratio_table:
            roce = find_row_values_exact_first(
                df,
                exact_aliases=[
                    "ROCE",
                    "Return on Capital Employed"
                ],
                contains_aliases=[
                    "roce",
                    "return on capital employed"
                ],
                annual_only=True
            )

            if roce and len(roce) >= 3:
                data["return_on_capital_employed"] = roce

            inv_days = find_row_values_exact_first(
                df,
                exact_aliases=[
                    "Inventory Days"
                ],
                contains_aliases=[
                    "inventory days"
                ],
                annual_only=True
            )

            if inv_days and len(inv_days) >= 3:
                data["inventory_days"] = inv_days

            debtor_days = find_row_values_exact_first(
                df,
                exact_aliases=[
                    "Debtor Days"
                ],
                contains_aliases=[
                    "debtor days"
                ],
                annual_only=True
            )

            if debtor_days and len(debtor_days) >= 3:
                data["debtor_days"] = debtor_days

            de = find_row_values_exact_first(
                df,
                exact_aliases=[
                    "Debt to equity",
                    "Debt / Equity",
                    "D/E"
                ],
                contains_aliases=[
                    "debt to equity",
                    "debt / equity"
                ],
                annual_only=True
            )

            if de and len(de) >= 3:
                data["debt_to_equity_analytical"] = de

            dividend_payout = find_row_values_exact_first(
                df,
                exact_aliases=[
                    "Dividend Payout %",
                    "Dividend Payout",
                    "Dividend payout %"
                ],
                contains_aliases=[
                    "dividend payout"
                ],
                annual_only=True
            )

            if dividend_payout and len(dividend_payout) >= 1:
                data["dividend_payout"] = dividend_payout

        looks_like_balance_sheet = (
            "equity capital" in first_col_text
            or "reserves" in first_col_text
            or "borrowings" in first_col_text
            or "share capital" in first_col_text
        )

        if looks_like_balance_sheet:
            reserves = find_row_values_exact_first(
                df,
                exact_aliases=[
                    "Reserves",
                    "Reserve",
                    "Other Equity",
                    "Reserves and Surplus"
                ],
                contains_aliases=[
                    "reserves",
                    "other equity"
                ],
                annual_only=True
            )

            if reserves and len(reserves) >= 3:
                data["reserves"] = reserves

            equity_capital = find_row_values_exact_first(
                df,
                exact_aliases=[
                    "Equity Capital",
                    "Share Capital",
                    "Equity Share Capital"
                ],
                contains_aliases=[
                    "equity capital",
                    "share capital"
                ],
                annual_only=True
            )

            if equity_capital and len(equity_capital) >= 3:
                data["equity_capital"] = equity_capital

            borrowings = find_row_values_exact_first(
                df,
                exact_aliases=[
                    "Borrowings",
                    "Total Borrowings",
                    "Debt"
                ],
                contains_aliases=[
                    "borrowings",
                    "debt"
                ],
                annual_only=True
            )

            if borrowings and len(borrowings) >= 3:
                data["borrowings"] = borrowings

        looks_like_shareholding = (
            "promoters" in first_col_text
            or "public" in first_col_text
            or "fii" in first_col_text
            or "dii" in first_col_text
        )

        if looks_like_shareholding:
            public_holding = find_row_values_exact_first(
                df,
                exact_aliases=[
                    "Public",
                    "Retail",
                    "Retail and others",
                    "Others"
                ],
                contains_aliases=[
                    "public",
                    "retail",
                    "others"
                ],
                annual_only=False
            )

            if public_holding and len(public_holding) >= 2:
                data["retail_contribution"] = public_holding

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

    return data


# --------------------------------------------------
# yfinance fallback
# --------------------------------------------------

def fetch_yfinance(yf_symbol):
    ticker = yf.Ticker(yf_symbol)

    data = {
        "price_history": pd.DataFrame(),
        "current_pe": np.nan,
        "earnings_yield": np.nan
    }

    try:
        hist = ticker.history(period="2y")
        data["price_history"] = hist
    except Exception:
        pass

    try:
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
    if price_data.empty or "Close" not in price_data.columns:
        return np.nan

    delta = price_data["Close"].diff()

    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = -delta.where(delta < 0, 0).rolling(period).mean()

    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    return rsi.iloc[-1]


def calculate_dma(price_data):
    if price_data.empty or "Close" not in price_data.columns:
        return np.nan, np.nan

    dma50 = price_data["Close"].rolling(50).mean().iloc[-1]
    dma200 = price_data["Close"].rolling(200).mean().iloc[-1]

    return dma50, dma200


def calculate_volume_index(price_data):
    if price_data.empty or "Volume" not in price_data.columns:
        return np.nan

    latest_volume = price_data["Volume"].iloc[-1]
    average_volume = price_data["Volume"].rolling(50).mean().iloc[-1]

    if pd.isna(average_volume) or average_volume == 0:
        return np.nan

    return latest_volume / average_volume


# --------------------------------------------------
# App UI
# --------------------------------------------------

st.title("🐝 Bubble Sniffer by Financify")
st.caption("Checks whether a stock has real honey or just too much market buzz. Educational only. Not investment advice.")

with st.sidebar:
    st.header("Input")

    screener_symbol = st.text_input("Screener / NSE Symbol", value="CIPLA")
    yahoo_symbol = st.text_input("Yahoo Finance Symbol", value="CIPLA.NS")

    run = st.button("🐝 Sniff Bubble", type="primary")

if run:
    with st.spinner("Fetching Screener data first..."):
        try:
            screener = fetch_screener(screener_symbol)
            st.success("Screener data fetched.")
        except Exception as e:
            screener = {}
            st.error(f"Screener fetch failed: {e}")

    with st.spinner("Fetching yfinance fallback for price indicators..."):
        try:
            yfin = fetch_yfinance(yahoo_symbol)
            st.success("yfinance fallback fetched.")
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

    st.subheader("Fetched Annual Data")

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

    st.markdown("---")
    st.header("🍯 Fundamental Honey Check")

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
        results.append(["Cash Flow Quality", "Pass", "FCF and CFO are positive and increasing."])
    else:
        results.append(["Cash Flow Quality", "Fail", "FCF and CFO are not both positive and increasing."])

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

    if latest(debt_to_equity_analytical) < 0.8:
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
        st.success("🍯 Strong Honey: Fundamental score is 8 or above. Premium valuation may be justified if growth continues.")
    else:
        st.warning("🐝 Fundamental score is below 8. Checking bubble / hype indicators.")

        st.markdown("---")
        st.header("🐝 Bubble / Hype Check")

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
            st.error("🔥 Full Madness Mode: Weak fundamentals plus strong hype signs. Bubble risk looks high.")
        elif bubble_score >= 3:
            st.warning("🐝 Buzz Building: Some bubble signs are visible.")
        else:
            st.success("🍯 No Major Bubble Smell: Hype signs are not very strong.")

        show_numbered_dataframe(bubble_df)

        if not price_history.empty:
            st.subheader("Price Chart")
            st.line_chart(price_history["Close"])

    st.caption("Educational tool only. Not investment advice, stock recommendation, target price, or buy/sell signal.")