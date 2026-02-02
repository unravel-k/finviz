#!/usr/bin/env python3
"""
Run the Finviz screener and send the results to Telegram chat(s).
Requires env vars: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID.
TELEGRAM_CHAT_ID: one chat ID, or comma-separated list (e.g. 123,456,789).
"""
import os
import sys
from io import BytesIO

import requests

# Add repo root so we can import finviz
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from finviz.screener import Screener
from finviz.helper_functions.save_data import export_to_csv

DEFAULT_SCREENER_URL = (
    "https://finviz.com/screener.ashx?v=111&f=fa_eps5years_pos,fa_epsqoq_o20,fa_epsyoy_o15,"
    "fa_estltgrowth_pos,fa_roe_o15,fa_sales5years_pos,sh_price_o15,ta_highlow52w_a30h,"
    "ta_sma200_sb50,ta_sma50_pa&ft=4"
)
# Candlestick chart: daily (1D), past 1y – user zooms to 1Y on chart (TradingView)
CHART_URL = "https://www.tradingview.com/chart/?symbol={ticker}&interval=1D"


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    raw = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not raw:
        print("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID (comma-separated for multiple)", file=sys.stderr)
        sys.exit(1)
    chat_ids = [c.strip() for c in raw.split(",") if c.strip()]

    stock_list = Screener.init_from_url(DEFAULT_SCREENER_URL, rows=None)
    n = len(stock_list.data)

    # Summary with each ticker as link to 12m daily chart (HTML, under 4096 chars)
    tickers = [row.get("Ticker", "") for row in stock_list.data if row.get("Ticker")]
    ticker_links = [
        f'<a href="{CHART_URL.format(ticker=t)}">{t}</a>' for t in tickers if t
    ]
    summary = (
        f"📊 Finviz screener – {n} stocks (daily candlestick, zoom to 1Y)\n\n"
        + "\n".join(ticker_links)
    )
    if len(summary) > 4000:
        summary = summary[:3997] + "…"

    # CSV as document
    csv_str = export_to_csv(stock_list.headers, stock_list.data, filename=None)
    csv_bytes = csv_str.encode("utf-8")

    base = f"https://api.telegram.org/bot{token}"
    failed = []

    for chat_id in chat_ids:
        # Send summary (HTML so ticker links are clickable)
        r = requests.post(
            f"{base}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": summary,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=30,
        )
        if not r.ok:
            failed.append((chat_id, f"sendMessage: {r.status_code} {r.text}"))
            continue
        # Send CSV file
        r = requests.post(
            f"{base}/sendDocument",
            data={"chat_id": chat_id, "caption": "screener_results.csv"},
            files={"document": ("screener_results.csv", BytesIO(csv_bytes), "text/csv")},
            timeout=30,
        )
        if not r.ok:
            failed.append((chat_id, f"sendDocument: {r.status_code} {r.text}"))

    if failed:
        for cid, err in failed:
            print(f"Failed for chat {cid}: {err}", file=sys.stderr)
        sys.exit(1)
    print(f"Sent {n} stocks to {len(chat_ids)} chat(s).")


if __name__ == "__main__":
    main()
