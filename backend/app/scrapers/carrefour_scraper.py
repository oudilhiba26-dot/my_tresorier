"""
Carrefour Morocco Scraper — Fixed & Optimized
=============================================
Carrefour MA is a JavaScript-rendered site (React/Next.js).
Strategy (in order of preference):
  1. Playwright (headless Chromium) — most reliable
  2. Carrefour MA internal API (JSON endpoints discovered via network tab)
  3. Mock / fallback data

Install requirements:
    pip install playwright beautifulsoup4 requests
    playwright install chromium
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from urllib.parse import quote_plus

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("carrefour_scraper")

# ---------------------------------------------------------------------------
# Data model  (replaces the external PriceData import)
# ---------------------------------------------------------------------------

@dataclass
class PriceData:
    product_name: str
    price: float
    currency: str = "MAD"
    unit: str = "piece"
    source: str = "Carrefour"
    scrape_date: datetime = field(default_factory=datetime.now)
    product_url: str = ""

    def __repr__(self) -> str:  # noqa: D401
        return f"<PriceData {self.product_name!r} {self.price} {self.currency}>"


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

USER_AGENTS = [
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/17.4.1 Safari/605.1.15"
    ),
    (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
]


def _make_session(retries: int = 3, backoff: float = 0.5) -> requests.Session:
    """Return a requests.Session with automatic retry on 5xx / network errors."""
    session = requests.Session()
    retry = Retry(
        total=retries,
        backoff_factor=backoff,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


# ---------------------------------------------------------------------------
# Fallback mock data  (used only when all network strategies fail)
# ---------------------------------------------------------------------------

_MOCK_CATALOGUE: dict[str, list[tuple[str, float]]] = {
    "rice": [
        ("Riz Basmati Extra Long 1kg", 24.95),
        ("Riz Uncle Ben's 500g", 18.50),
        ("Riz Blanc Carrefour 5kg", 64.90),
    ],
    "oil": [
        ("Huile d'Olive Vierge Extra 1L", 89.00),
        ("Huile de Tournesol Carrefour 1L", 28.50),
        ("Huile de Soja Lesieur 5L", 115.00),
    ],
    "milk": [
        ("Lait Centrale Danone 1L", 9.75),
        ("Lait Entier Carrefour 1L", 8.50),
        ("Lait UHT Lactel 1L", 12.50),
    ],
    "sugar": [
        ("Sucre Blanc Cristal 1kg", 7.50),
        ("Sucre Roux Bio 500g", 14.95),
    ],
    "flour": [
        ("Farine de Blé T55 1kg", 9.50),
        ("Farine Complète Bio 1kg", 17.90),
    ],
}

_DEFAULT_MOCK = [("Produit générique", 15.00)]


def _get_mock_prices(query: str, source: str) -> list[PriceData]:
    """Return demo / mock data for a given query keyword."""
    key = query.lower().strip()
    items = _MOCK_CATALOGUE.get(key, _DEFAULT_MOCK)
    return [
        PriceData(
            product_name=name,
            price=price,
            currency="MAD",
            unit="piece",
            source=f"{source} (Demo)",
            product_url="",
        )
        for name, price in items
    ]


# ---------------------------------------------------------------------------
# Strategy 1 — Carrefour MA unofficial JSON API
# ---------------------------------------------------------------------------
# Carrefour MA's frontend calls an internal search API.
# Endpoint discovered via browser DevTools → Network tab.
# This is more stable than scraping HTML and returns structured JSON.

_API_BASE = "https://www.carrefour.ma/api/2.0/json/reply/Search"
_API_HEADERS = {
    "Accept": "application/json",
    "Accept-Language": "fr-MA,fr;q=0.9",
    "Referer": "https://www.carrefour.ma/",
    "Origin": "https://www.carrefour.ma",
}


def _parse_api_price(raw_price) -> Optional[float]:
    """Safely parse a price value that may be string, int, or float."""
    if raw_price is None:
        return None
    try:
        return float(str(raw_price).replace(",", ".").replace("\xa0", "").strip())
    except ValueError:
        return None


def _fetch_via_api(query: str, session: requests.Session, ua: str) -> list[PriceData]:
    """
    Query the Carrefour MA internal search JSON API.
    Returns an empty list on failure so the caller can try next strategy.
    """
    params = {
        "q": query,
        "page": 1,
        "pageSize": 10,
        "lang": "fr",
        "store": "MA",
    }
    headers = {**_API_HEADERS, "User-Agent": ua}

    try:
        resp = session.get(_API_BASE, params=params, headers=headers, timeout=12)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.JSONDecodeError:
        logger.debug("API did not return valid JSON — likely JS-gated.")
        return []
    except requests.RequestException as exc:
        logger.debug(f"API request error: {exc}")
        return []

    products = data.get("products") or data.get("results") or data.get("data") or []
    if not isinstance(products, list):
        logger.debug("Unexpected API response shape.")
        return []

    results: list[PriceData] = []
    for item in products[:8]:
        name = item.get("name") or item.get("title") or item.get("label") or ""
        if not name:
            continue

        raw = (
            item.get("price")
            or item.get("salePrice")
            or item.get("priceValue")
            or item.get("currentPrice")
        )
        price = _parse_api_price(raw)
        if price is None:
            continue

        url_slug = item.get("url") or item.get("link") or ""
        full_url = f"https://www.carrefour.ma{url_slug}" if url_slug.startswith("/") else url_slug

        results.append(
            PriceData(
                product_name=name.strip(),
                price=price,
                currency="MAD",
                unit=item.get("unit") or "piece",
                source="Carrefour",
                product_url=full_url,
            )
        )

    logger.info(f"API strategy returned {len(results)} items for '{query}'.")
    return results


# ---------------------------------------------------------------------------
# Strategy 2 — Playwright (headless browser)
# ---------------------------------------------------------------------------

def _fetch_via_playwright(query: str) -> list[PriceData]:
    """
    Use Playwright to render the Carrefour MA search page and extract product data.
    Falls back gracefully if Playwright is not installed.
    """
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        logger.debug("Playwright not installed; skipping browser strategy.")
        return []

    results: list[PriceData] = []
    url = f"https://www.carrefour.ma/search?q={quote_plus(query)}"

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent=USER_AGENTS[0],
                locale="fr-MA",
                viewport={"width": 1280, "height": 800},
            )
            page = ctx.new_page()
            page.goto(url, wait_until="networkidle", timeout=30_000)

            # Wait for product cards — inspect the real DOM to confirm selector.
            # Common selectors on Carrefour MA (verify with DevTools):
            PRODUCT_CARD_SELECTOR = (
                "[data-testid='product-card'], "
                ".product-card, "
                ".product-item, "
                "article[class*='product']"
            )
            try:
                page.wait_for_selector(PRODUCT_CARD_SELECTOR, timeout=10_000)
            except PWTimeout:
                logger.warning("Playwright: product cards did not appear — selector may be wrong.")
                browser.close()
                return []

            cards = page.query_selector_all(PRODUCT_CARD_SELECTOR)
            logger.info(f"Playwright found {len(cards)} product cards for '{query}'.")

            for card in cards[:8]:
                # --- Product name ---
                name_el = card.query_selector(
                    "[data-testid='product-name'], .product-name, h3, h2"
                )
                name = name_el.inner_text().strip() if name_el else ""
                if not name:
                    continue

                # --- Price ---
                price_el = card.query_selector(
                    "[data-testid='product-price'], .product-price, "
                    "[class*='price']:not([class*='old']):not([class*='before'])"
                )
                if not price_el:
                    continue
                price_text = price_el.inner_text().strip()
                price_match = re.search(r"(\d[\d\s]*[.,]\d{1,2}|\d+)", price_text)
                if not price_match:
                    continue
                price = float(price_match.group(1).replace(" ", "").replace(",", "."))

                # --- URL ---
                link_el = card.query_selector("a[href]")
                href = link_el.get_attribute("href") if link_el else ""
                full_url = (
                    f"https://www.carrefour.ma{href}"
                    if href and href.startswith("/")
                    else href or ""
                )

                results.append(
                    PriceData(
                        product_name=name,
                        price=price,
                        currency="MAD",
                        unit="piece",
                        source="Carrefour",
                        product_url=full_url,
                    )
                )

            browser.close()

    except Exception as exc:
        logger.error(f"Playwright strategy failed: {exc}")

    logger.info(f"Playwright strategy returned {len(results)} items for '{query}'.")
    return results


# ---------------------------------------------------------------------------
# Main scraper class
# ---------------------------------------------------------------------------

class CarrefourScraper:
    """
    Scraper for Carrefour Morocco (https://www.carrefour.ma).

    Tries strategies in order:
      1. Internal JSON API  (fast, no browser needed)
      2. Playwright headless browser  (reliable for JS-heavy sites)
      3. Mock / demo data  (always works, clearly labelled)
    """

    SOURCE_NAME = "Carrefour"
    BASE_URL = "https://www.carrefour.ma"
    REQUEST_DELAY = 1.2  # seconds between queries

    def __init__(self) -> None:
        self._session = _make_session(retries=3, backoff=0.5)
        self._ua_index = 0

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def scrape_prices(self, search_query: str | None = None) -> list[PriceData]:
        """
        Scrape food prices from Carrefour Morocco.

        Args:
            search_query: Comma-separated product keywords, e.g. "rice,oil,milk".
                          Defaults to ["rice", "oil", "milk"] when omitted.

        Returns:
            List of PriceData instances (never raises).
        """
        queries = (
            [q.strip() for q in search_query.split(",") if q.strip()]
            if search_query
            else ["rice", "oil", "milk"]
        )

        all_prices: list[PriceData] = []

        for i, query in enumerate(queries):
            logger.info(f"[{i+1}/{len(queries)}] Searching for: '{query}'")
            prices = self._fetch_with_fallback(query)
            all_prices.extend(prices)

            if i < len(queries) - 1:
                time.sleep(self.REQUEST_DELAY)

        logger.info(f"Total results collected: {len(all_prices)}")
        return all_prices

    def parse_product_page(self, url: str) -> Optional[PriceData]:
        """
        Parse a single Carrefour product page via Playwright.
        Returns None on failure.
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.warning("Playwright not installed; cannot parse individual product pages.")
            return None

        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                page = browser.new_context(user_agent=self._next_ua()).new_page()
                page.goto(url, wait_until="networkidle", timeout=30_000)

                name_el = page.query_selector("h1")
                price_el = page.query_selector(
                    "[data-testid='product-price'], [class*='price']"
                )

                name = name_el.inner_text().strip() if name_el else ""
                price_text = price_el.inner_text().strip() if price_el else ""
                price_match = re.search(r"(\d[\d\s]*[.,]\d{1,2}|\d+)", price_text)

                browser.close()

                if name and price_match:
                    return PriceData(
                        product_name=name,
                        price=float(price_match.group(1).replace(" ", "").replace(",", ".")),
                        currency="MAD",
                        unit="piece",
                        source=self.SOURCE_NAME,
                        product_url=url,
                    )
        except Exception as exc:
            logger.error(f"parse_product_page error: {exc}")

        return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _next_ua(self) -> str:
        ua = USER_AGENTS[self._ua_index % len(USER_AGENTS)]
        self._ua_index += 1
        return ua

    def _fetch_with_fallback(self, query: str) -> list[PriceData]:
        """Try each strategy in order; return first non-empty result."""

        # Strategy 1: Internal JSON API
        prices = _fetch_via_api(query, self._session, self._next_ua())
        if prices:
            return prices

        # Strategy 2: Playwright headless browser
        logger.info(f"API returned nothing for '{query}'; trying Playwright...")
        prices = _fetch_via_playwright(query)
        if prices:
            return prices

        # Strategy 3: Mock data
        logger.warning(
            f"All live strategies failed for '{query}'; returning labelled demo data."
        )
        return _get_mock_prices(query, self.SOURCE_NAME)


# ---------------------------------------------------------------------------
# Quick smoke-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    scraper = CarrefourScraper()
    results = scraper.scrape_prices("rice,oil")

    print(f"\n{'='*55}")
    print(f"  Results ({len(results)} items)")
    print(f"{'='*55}")
    for item in results:
        print(f"  {item.product_name:<35} {item.price:>8.2f} {item.currency}  [{item.source}]")
    print(f"{'='*55}\n")