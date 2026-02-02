import argparse
import sys

from finviz.screener import Screener


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

stock_list.to_csv("screener_results.csv")
print("Saved to screener_results.csv")
