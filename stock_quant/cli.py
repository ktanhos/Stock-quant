from __future__ import annotations

import argparse

from stock_quant.analysis import latest_analysis, run_signal_pipeline
from stock_quant.consensus import consensus_overview, consensus_report, views_table
from stock_quant.data import VnstockClient, save_frame


def print_consensus(result, symbols: list[str], threshold: float) -> None:
    reports = consensus_report(result, symbols, overlap_threshold=threshold)
    if not reports:
        print("Không có mã nào đủ dữ liệu để phân tích đồng thuận")
        return

    if len(reports) > 1:
        print("\n== Tổng quan đồng thuận ==")
        print(consensus_overview(reports).to_string(index=False))

    for report in reports:
        print(f"\n== {report.symbol} · {report.consensus_label} ==")
        print(views_table(report).to_string(index=False))

        print("\nMarket Narrative:")
        print(report.narrative)

        if report.agreement_groups:
            print("\nNhóm đồng thuận:")
            for group in report.agreement_groups:
                print(f"  - {group.label} ({group.size}): " + ", ".join(group.names))

        if report.conflicts:
            print("\nMâu thuẫn:")
            for note in report.conflicts:
                print(f"  - {note.message}")

        if report.neutral_views:
            print("\nTrung tính:")
            for view in report.neutral_views:
                print(f"  - {view.name}: {view.reading.lower()}")

        for note in report.notes:
            print(f"\nGhi chú: {note}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Stock Quant · Consensus Analysis")
    parser.add_argument("symbols", nargs="+", help="Stock symbols")
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--mode", choices=["free", "registered"], default="free")
    parser.add_argument("--output", default="data/processed/latest.parquet")
    parser.add_argument("--overlap-threshold", type=float, default=0.70)
    parser.add_argument("--scores-only", action="store_true", help="Chỉ in bảng Score gốc")
    args = parser.parse_args()

    client = VnstockClient(mode=args.mode)
    prices = client.fetch_price_history(args.symbols, args.start, args.end)
    result = run_signal_pipeline(prices)
    save_frame(result, args.output)

    if args.scores_only:
        print(latest_analysis(result, args.symbols).to_string(index=False))
        return

    print_consensus(result, args.symbols, args.overlap_threshold)


if __name__ == "__main__":
    main()
