"""
Fetch daily price history for tickers from screener_results.csv using yfinance.
Install: pip install yfinance pandas
"""
import argparse

import pandas as pd
import yfinance as yf


def fetch_daily_prices(
    csv_path: str = "screener_results.csv",
    ticker_column: str = "Ticker",
    months: int | None = 12,
    period: str | None = None,
    output_path: str = "daily_prices.csv",
):
    """
    Load tickers from CSV, fetch daily OHLCV from Yahoo Finance, save to CSV.

    :param csv_path: Path to screener CSV (must have a ticker column).
    :param ticker_column: Name of column containing ticker symbols.
    :param months: Number of months of history (e.g. 12 = 1 year). Used if period is None.
    :param period: yfinance period: "1mo", "3mo", "6mo", "1y", "2y", "5y", "max". Overrides months if set.
    :param output_path: Where to save the combined daily price CSV.
    """
    df = pd.read_csv(csv_path)
    if ticker_column not in df.columns:
        raise ValueError(f"Column '{ticker_column}' not found. Columns: {list(df.columns)}")
    tickers = df[ticker_column].dropna().unique().tolist()
    tickers = [t for t in tickers if t and str(t).strip()]

    if not period:
        # yfinance: 1mo, 3mo, 6mo, 1y, 2y, 5y, max
        if not months:
            period = "1y"
        elif months <= 1:
            period = "1mo"
        elif months <= 3:
            period = "3mo"
        elif months <= 6:
            period = "6mo"
        elif months <= 12:
            period = "1y"
        elif months <= 24:
            period = "2y"
        else:
            period = "5y"

    print(f"Fetching daily prices for {len(tickers)} tickers, period={period}...")
    out_rows = []
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period=period, interval="1d", auto_adjust=True)
            if hist.empty:
                continue
            hist = hist.reset_index()
            hist["Ticker"] = ticker
            hist = hist.rename(columns={"Date": "Date", "Open": "Open", "High": "High", "Low": "Low", "Close": "Close", "Volume": "Volume"})
            hist["Date"] = pd.to_datetime(hist["Date"]).dt.strftime("%Y-%m-%d")
            out_rows.append(hist[["Date", "Ticker", "Open", "High", "Low", "Close", "Volume"]])
        except Exception as e:
            print(f"  Skip {ticker}: {e}")

    if not out_rows:
        print("No data fetched.")
        return
    result = pd.concat(out_rows, ignore_index=True)
    result.to_csv(output_path, index=False)
    print(f"Saved {len(result)} rows to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch daily prices for tickers from a screener CSV.")
    parser.add_argument("--csv", default="screener_results.csv", help="Input CSV with ticker column")
    parser.add_argument("--column", default="Ticker", help="Name of ticker column")
    parser.add_argument("--months", type=int, default=12, help="Number of months of history (default 12)")
    parser.add_argument("--period", type=str, default=None, help="Override: 1mo, 3mo, 6mo, 1y, 2y, 5y, max")
    parser.add_argument("--output", default="daily_prices.csv", help="Output CSV path")
    args = parser.parse_args()
    fetch_daily_prices(
        csv_path=args.csv,
        ticker_column=args.column,
        months=args.months,
        period=args.period,
        output_path=args.output,
    )
