"""Thin wrapper around DuckDuckGo search (the `ddgs` package).

DDG is used instead of Google because it has no official scraping API either,
but tolerates unauthenticated automated queries far better in practice and
`ddgs` handles the request/parsing details. Google search scraping is much
more aggressively rate-limited/CAPTCHA'd and isn't implemented here.

X.com/Twitter itself is not scraped directly — it's a JS-rendered SPA that
requires a logged-in session for most content, and its official API is paid.
Instead, `x_search()` restricts the DDG query to `site:x.com`, which surfaces
individual post snippets DDG has indexed. This is a best-effort proxy for "X
sentiment," not a full-coverage firehose: DDG's indexing of X is partial and
inconsistent, so mention counts here should be read as a rough signal, not an
exhaustive count.
"""

import time

from ddgs import DDGS
from ddgs.exceptions import DDGSException


def _search(query: str, max_results: int, retries: int = 2, backoff: float = 2.0) -> list[dict]:
    for attempt in range(retries + 1):
        try:
            with DDGS() as ddgs:
                return list(ddgs.text(query, max_results=max_results))
        except DDGSException as e:
            if attempt == retries:
                print(f"    [!] Search failed for '{query}': {e}")
                return []
            time.sleep(backoff * (attempt + 1))
    return []


def web_search(query: str, max_results: int = 8) -> list[dict]:
    """General web search — news, blogs, forums, analyst coverage, etc."""
    return _search(query, max_results)


def x_search(query: str, max_results: int = 8) -> list[dict]:
    """Search restricted to X.com — see module docstring for the tradeoffs."""
    return _search(f"site:x.com {query}", max_results)
