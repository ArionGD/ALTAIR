"""CLI entrypoint for the sentiment scraper.

Usage:
    python -m source.run NYKAA.NS ZOMATO.NS TSLA
    python -m source.run                          # uses DEFAULT_TICKERS
    python -m source.run --output my_scores.csv NYKAA.NS
"""

import argparse

from source.collector import SentimentCollector

DEFAULT_TICKERS = ["NYKAA.NS", "ZOMATO.NS", "PAYTM.NS", "TSLA", "AAPL"]


def main():
    parser = argparse.ArgumentParser(description="ALTAIR sentiment scraper")
    parser.add_argument("tickers", nargs="*", default=DEFAULT_TICKERS, help="Ticker symbols to scan")
    parser.add_argument("--output", default="source/output/sentiment_scores.csv")
    args = parser.parse_args()

    collector = SentimentCollector()
    df = collector.collect_many(args.tickers, output_csv=args.output)
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
