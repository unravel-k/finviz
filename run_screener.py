import argparse
import os
import sys

from finviz.screener import Screener

# Directory where this script lives (so outputs are always here)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def list_filters(filters_dict):
    """Print all filter keys and their option labels (for debugging)."""
    for key in sorted(filters_dict.keys()):
        opts = list(filters_dict[key].keys())
        print(f"  {key!r}: {opts[:5]}{'...' if len(opts) > 5 else ''}")


def get_filter_tag(filters_dict, key_substring, option_substring):
    """Get filter tag by partial key match (Finviz label text can vary)."""
    key_sub = key_substring.lower()
    option_sub = option_substring.lower()
    for key, options in filters_dict.items():
        if key_sub in key.lower():
            for opt_text, tag in options.items():
                if option_sub in opt_text.lower():
                    return tag
    # Debug: show similar keys and options
    similar = [k for k in filters_dict.keys() if key_sub[:3] in k.lower() or key_sub.split()[0] in k.lower()]
    if similar:
        print(f"Keys similar to {key_substring!r}: {similar[:8]}", file=sys.stderr)
        for k in similar[:2]:
            print(f"  Options for {k!r}: {list(filters_dict[k].keys())[:10]}", file=sys.stderr)
    raise KeyError(f"No filter found for key containing {key_substring!r}, option containing {option_substring!r}")


filters = Screener.load_filter_dict()

# Run with: python run_screener.py --list-filters  to see exact key/option names from Finviz
parser = argparse.ArgumentParser()
parser.add_argument("--list-filters", action="store_true", help="Print all filter keys and options, then exit")
parser.add_argument("--rows", type=int, default=None, help="Max number of results (default: all)")
parser.add_argument("--url", type=str, default=None, help="Use exact Finviz screener URL instead of building from filters")
args = parser.parse_args()
if args.list_filters:
    print("Filter keys and (first few) options from Finviz:")
    list_filters(filters)
    sys.exit(0)

# Same 10 criteria as your Finviz screenshot. Order must match working URL or Finviz returns different results.
# Working URL f= order: fa_eps5years_pos, fa_epsqoq_o20, fa_epsyoy_o15, fa_estltgrowth_pos, fa_roe_o15,
#   fa_sales5years_pos, sh_price_o15, ta_highlow52w_a30h, ta_sma200_sb50, ta_sma50_pa
FALLBACK_TAGS = [
    "fa_eps5years_pos",   # EPS Growth Past 5 Years Positive
    "fa_epsqoq_o20",      # EPS Growth Qtr Over Qtr Over 20%
    "fa_epsyoy_o15",      # EPS Growth This Year Over 15%
    "fa_estltgrowth_pos", # EPS Growth Next 5 Years Positive
    "fa_roe_o15",         # Return on Equity Over +15%
    "fa_sales5years_pos", # Sales Growth Past 5 Years Positive
    "sh_price_o15",       # Price $ Over $15
    "ta_highlow52w_a30h", # 52-Week 30% or more above Low
    "ta_sma200_sb50",     # 200-Day SMA: Price below 50% of SMA200
    "ta_sma50_pa",        # 50-Day Price above SMA50
]


def _tag(filters_dict, key_sub, opt_sub, fallback):
    try:
        return get_filter_tag(filters_dict, key_sub, opt_sub)
    except KeyError:
        return fallback


# Known-good URL (Finviz returns 43 with this; building from filters can return 1)
DEFAULT_SCREENER_URL = (
    "https://finviz.com/screener.ashx?v=111&f=fa_eps5years_pos,fa_epsqoq_o20,fa_epsyoy_o15,"
    "fa_estltgrowth_pos,fa_roe_o15,fa_sales5years_pos,sh_price_o15,ta_highlow52w_a30h,"
    "ta_sma200_sb50,ta_sma50_pa&ft=4"
)
# rows=None (default) = get all results; use --rows 50 to limit
if args.url:
    stock_list = Screener.init_from_url(args.url, rows=args.rows)
else:
    stock_list = Screener.init_from_url(DEFAULT_SCREENER_URL, rows=args.rows)

n = len(stock_list.data)
# With all 10 filters, Finviz typically returns 1–2 stocks (criteria are very strict)
print(f"Fetched {n} stocks")
print(stock_list)

csv_path = os.path.join(SCRIPT_DIR, "screener_results.csv")
stock_list.to_csv(csv_path)
print(f"Saved to {csv_path}")

# Charts page: open in browser, one click opens all chart tabs
CHART_URL = "https://www.tradingview.com/chart/?symbol={ticker}&interval=1D"
tickers = [r.get("Ticker", "") for r in stock_list.data if r.get("Ticker")]
company = {r.get("Ticker", ""): r.get("Company", "") for r in stock_list.data}
trs = "".join(
    f'<tr><td><a href="{CHART_URL.format(ticker=t)}" target="_blank">{t}</a></td><td>{company.get(t, "")}</td></tr>'
    for t in tickers if t
)
urls_js = ",".join(repr(CHART_URL.format(ticker=t)) for t in tickers if t)
charts_html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Finviz screener – charts</title>
<style>body{{font-family:sans-serif;margin:1rem}} table{{border-collapse:collapse}}
td,th{{border:1px solid #ccc;padding:6px 10px;text-align:left}} th{{background:#eee}} a{{color:#06c}}
.btn{{margin:1rem 0;padding:10px 20px;font-size:1rem;cursor:pointer}}</style>
</head>
<body>
<h1>Finviz screener – {len(tickers)} stocks</h1>
<p>Daily candlestick (TradingView). Zoom to 1Y on each chart.</p>
<button class="btn" onclick="openAll()">Open all charts in new tabs</button>
<p><small>Browsers may limit how many tabs open at once; click again for the rest.</small></p>
<table><thead><tr><th>Ticker</th><th>Company</th></tr></thead><tbody>{trs}</tbody></table>
<script>var urls=[{urls_js}];function openAll(){{urls.forEach(function(u){{window.open(u,'_blank');}});}}</script>
</body>
</html>"""
charts_path = os.path.join(SCRIPT_DIR, "screener_charts.html")
with open(charts_path, "w", encoding="utf-8") as f:
    f.write(charts_html)
print(f"Saved to {charts_path} (open in browser → click button to open all charts in new tabs)")
