"""ALTAIR Sentiment Collector.

Scrapes public web + X.com search results for a ticker, scores each snippet
with the lexicon in lexicon.py, and aggregates a per-ticker sentiment +
popularity reading. Standalone module — not wired into the main scoring
pipeline (src/engine/) or the FastAPI API yet.
"""

import os
import time

import pandas as pd

from source.lexicon import score_text
from source.search_client import web_search, x_search


class SentimentCollector:
    def __init__(self, results_per_source: int = 8, pause: float = 1.5):
        self.results_per_source = results_per_source
        self.pause = pause

    def collect_ticker(self, ticker: str, query_label: str | None = None) -> dict:
        """Runs a general web search and an X-restricted search for one ticker.

        query_label lets you search a more natural query than the raw symbol,
        e.g. query_label="Nykaa" for ticker="NYKAA.NS".
        """
        label = query_label or ticker
        print(f"[*] Scraping sentiment for {ticker} ({label})...")

        web_results = [{**r, "source": "web"} for r in web_search(f"{label} stock", self.results_per_source)]
        time.sleep(self.pause)
        x_results = [{**r, "source": "x"} for r in x_search(f"{label} stock", self.results_per_source)]
        time.sleep(self.pause)

        snippets = []
        for r in web_results + x_results:
            text = f"{r.get('title', '')} {r.get('body', '')}"
            snippets.append({**r, "sentiment": score_text(text)})

        mention_count = len(snippets)
        x_mention_count = len(x_results)
        avg_sentiment = round(sum(s["sentiment"] for s in snippets) / mention_count, 3) if mention_count else 0.0

        return {
            "ticker": ticker,
            "mention_count": mention_count,
            "x_mention_count": x_mention_count,
            "avg_sentiment": avg_sentiment,
            "snippets": snippets,
        }

    def collect_many(self, tickers: list[str], output_csv: str | None = None) -> pd.DataFrame:
        rows = []
        for ticker in tickers:
            result = self.collect_ticker(ticker)
            rows.append({k: v for k, v in result.items() if k != "snippets"})

        df = pd.DataFrame(rows).sort_values(by="avg_sentiment", ascending=False)

        if output_csv:
            os.makedirs(os.path.dirname(output_csv), exist_ok=True)
            df.to_csv(output_csv, index=False)
            print(f"\n[+] Saved: {output_csv}")

        return df
