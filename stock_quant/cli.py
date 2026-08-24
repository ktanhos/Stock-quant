from __future__ import annotations

import argparse

from stock_quant.analysis import latest_analysis, run_signal_pipeline
from stock_quant.data import VnstockClient, save_frame


def main() -> None:
    parser = argparse.ArgumentParser(description="Stock Quant")
    parser.add_argument("symbols", nargs="+", help="Stock symbols")
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--output", default="data/processed/latest.parquet")
    args = parser.parse_args()

    client = VnstockClient()
    prices = client.fetch_price_history(args.symbols, args.start, args.end)
    result = run_signal_pipeline(prices)
    save_frame(result, args.output)
    print(latest_analysis(result, args.symbols).to_string(index=False))


if __name__ == "__main__":
    main()
