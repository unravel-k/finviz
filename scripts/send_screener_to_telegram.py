#!/usr/bin/env python3
"""
Run the Finviz screener and send the results to a Telegram chat.
Requires env vars: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID.
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


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID", file=sys.stderr)
        sys.exit(1)

    stock_list = Screener.init_from_url(DEFAULT_SCREENER_URL, rows=None)
    n = len(stock_list.data)

    # Short summary message (under 4096 chars)
    tickers = [row.get("Ticker", "") for row in stock_list.data if row.get("Ticker")]
    summary = (
        f"📊 Finviz screener – {n} stocks\n"
        f"Tickers: {', '.join(tickers)}"
    )
    if len(summary) > 4000:
        summary = summary[:3997] + "…"

    # CSV as document
    csv_str = export_to_csv(stock_list.headers, stock_list.data, filename=None)
    csv_bytes = csv_str.encode("utf-8")

    base = f"https://api.telegram.org/bot{token}"

    # Send summary
    r = requests.post(
        f"{base}/sendMessage",
        json={"chat_id": chat_id, "text": summary, "disable_web_page_preview": True},
        timeout=30,
    )
    if not r.ok:
        print(f"sendMessage failed: {r.status_code} {r.text}", file=sys.stderr)
        sys.exit(1)

    # Send CSV file
    r = requests.post(
        f"{base}/sendDocument",
        data={"chat_id": chat_id, "caption": "screener_results.csv"},
        files={"document": ("screener_results.csv", BytesIO(csv_bytes), "text/csv")},
        timeout=30,
    )
    if not r.ok:
        print(f"sendDocument failed: {r.status_code} {r.text}", file=sys.stderr)
        sys.exit(1)

    print(f"Sent {n} stocks to Telegram.")


if __name__ == "__main__":
    main()
