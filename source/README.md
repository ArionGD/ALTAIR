# ALTAIR Source (in progress)

Scrapes public sentiment/popularity signals about tickers from the open web
and X.com. **Standalone module — not wired into the scoring pipeline
(`src/engine/`) or the FastAPI API yet.** Run it directly as a script for now.

## How it works

- **Web search** (`search_client.web_search`) — general query (`"<ticker> stock"`)
  via DuckDuckGo, using the [`ddgs`](https://pypi.org/project/ddgs/) package.
  No API key required.
- **X.com search** (`search_client.x_search`) — the same DDG search, restricted
  to `site:x.com`. This is **not** a direct scrape of x.com — it queries DDG's
  index of X, which is the only practical no-auth, no-paid-API way to surface
  X post content right now (X's own search requires a logged-in session; its
  official API is paid).
- **Sentiment scoring** (`lexicon.py`) — simple bullish/bearish keyword
  counting per snippet (title + body), averaged per ticker into a
  `-1..1` `avg_sentiment` score. `mention_count` (web + X combined) and
  `x_mention_count` serve as rough popularity proxies.

## Known limitations (read before trusting the numbers)

- **DDG's X.com index is partial and inconsistent** — it does surface real
  individual post snippets (verified manually), but it is not exhaustive.
  Treat `x_mention_count` as a rough signal, not a full mention count.
- **The sentiment scorer is a keyword lexicon, not an NLP model** — it will
  miscount sarcasm, negation ("not bullish"), and finance-specific jargon
  outside its word lists. Good enough to prototype with; not investment
  advice.
- **Google is not implemented.** Google's search results page is far more
  aggressively rate-limited/CAPTCHA'd for unauthenticated scraping than DDG,
  so it isn't included here. `search_client.py` is structured so a
  Google-backed function could be added alongside `web_search`/`x_search` if
  needed later.
- Every ticker triggers 2 searches with a pause between them (rate-limit
  courtesy to DDG) — scanning a large ticker list will take a while.

## Usage

```powershell
# from the repo root, with the backend venv active
python -m source.run NYKAA.NS ZOMATO.NS TSLA
```

Writes results to `source/output/sentiment_scores.csv` (gitignored) and
prints a summary table. Omit ticker arguments to scan the small built-in
default list in `run.py`.

## Files

```
lexicon.py        Bullish/bearish keyword lists + score_text()
search_client.py  DDG web_search() / x_search() wrappers
collector.py      SentimentCollector — orchestrates search + scoring + CSV output
run.py            CLI entrypoint (python -m source.run)
output/            Generated CSVs (gitignored)
```
