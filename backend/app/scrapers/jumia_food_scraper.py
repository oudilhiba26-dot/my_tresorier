"""
Jumia Morocco Scraper — Fixed & Optimized
==========================================
Jumia MA is a JavaScript-rendered site. Strategy (in order):
  1. Jumia MA catalog page with SSR-compatible request headers
     (Jumia partially server-side renders article.prd cards when the
      correct Accept / Accept-Language headers are sent — no browser needed)
  2. Playwright headless Chromium — full JS rendering fallback
  3. Mock / demo data — always works, clearly labelled

Install:
    pip install playwright requests beautifulsoup4
    playwright install chromium
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("jumia_scraper")

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class PriceData:
    product_name: str
    price: float
    currency: str = "MAD"
    unit: str = "piece"
    source: str = "Jumia"
    scrape_date: datetime = field(default_factory=datetime.now)
    product_url: str = ""

    def __repr__(self) -> str:
        return f"<PriceData {self.product_name!r} {self.price} {self.currency}>"


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_URL = "https://www.jumia.com.ma"

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

# Jumia partially SSR-renders catalog pages when these headers are present.
# Without Accept: text/html the server may return a JS-only bootstrap bundle.
_SSR_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-MA,fr;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# ---------------------------------------------------------------------------
# Mock / fallback data
# ---------------------------------------------------------------------------

_MOCK_CATALOGUE: dict[str, list[tuple[str, float]]] = {
    "rice": [
        ("Riz Basmati Uncle Ben's 1kg", 32.50),
        ("Riz Blanc Long Grain 5kg", 79.00),
        ("Riz Complet Bio 1kg", 45.90),
    ],
    "oil": [
        ("Huile d'Olive Vierge Extra 1L", 95.00),
        ("Huile de Tournesol 5L", 118.00),
        ("Huile de Table Lesieur 1L", 29.50),
    ],
    "milk": [
        ("Lait Entier UHT 1L", 9.75),
        ("Lait Demi-Écrémé Lactel 1L", 11.50),
        ("Lait en Poudre Nido 400g", 58.00),
    ],
    "sugar": [
        ("Sucre Cristal 1kg", 7.50),
        ("Sucre Glace 500g", 12.00),
    ],
    "flour": [
        ("Farine T55 1kg", 9.00),
        ("Farine Complète 1kg", 15.90),
    ],
}

_DEFAULT_MOCK = [("Produit générique", 15.00)]


def _get_mock_prices(query: str, source_label: str) -> list[PriceData]:
    items = _MOCK_CATALOGUE.get(query.lower().strip(), _DEFAULT_MOCK)
    return [
        PriceData(
            product_name=name,
            price=price,
            source=f"{source_label} (Demo)",
        )
        for name, price in items
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_session(retries: int = 3, backoff: float = 0.6) -> requests.Session:
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


def _parse_price(raw: str) -> Optional[float]:
    """
    Robustly parse a MAD price string.
    Handles: "29,90 MAD", "1 250 MAD", "1.250,00", "29.90", "1250"
    Returns None if no numeric value can be extracted.
    """
    if not raw:
        return None
    # Strip currency labels and whitespace
    cleaned = re.sub(r"[A-Za-z\xa0]", "", raw).strip()
    # Remove thousands separator (space or period before 3-digit groups)
    # e.g. "1 250" → "1250",  "1.250,00" → "1250,00"
    cleaned = re.sub(r"[\s.](?=\d{3}(?:[,\s]|$))", "", cleaned)
    # Normalise decimal comma → dot
    cleaned = cleaned.replace(",", ".")
    match = re.search(r"\d+(?:\.\d+)?", cleaned)
    if not match:
        return None
    try:
        return float(match.group())
    except ValueError:
        return None


def _resolve_url(href: str) -> str:
    """Turn a relative Jumia path into an absolute URL."""
    if not href:
        return ""
    return urljoin(BASE_URL, href)


# ---------------------------------------------------------------------------
# Strategy 1 — SSR-compatible requests + BeautifulSoup
# ---------------------------------------------------------------------------

def _fetch_via_requests(
    query: str,
    session: requests.Session,
    ua: str,
) -> list[PriceData]:
    """
    Fetch Jumia catalog with browser-like headers to trigger SSR rendering.
    Jumia's catalog page returns populated <article class="prd"> cards when
    proper Accept / Accept-Language headers are present.
    """
    url = f"{BASE_URL}/catalog/?q={quote_plus(query)}"
    headers = {**_SSR_HEADERS, "User-Agent": ua}

    try:
        resp = session.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
    except requests.Timeout:
        logger.debug(f"Requests strategy: timeout for '{query}'")
        return []
    except requests.ConnectionError as exc:
        logger.debug(f"Requests strategy: connection error for '{query}': {exc}")
        return []
    except requests.HTTPError as exc:
        logger.debug(f"Requests strategy: HTTP {exc.response.status_code} for '{query}'")
        return []
    except requests.RequestException as exc:
        logger.debug(f"Requests strategy: request error for '{query}': {exc}")
        return []

    soup = BeautifulSoup(resp.content, "html.parser")
    cards = soup.find_all("article", class_="prd")
    logger.info(f"Requests strategy: found {len(cards)} cards for '{query}'")

    results: list[PriceData] = []
    for card in cards[:8]:
        item = _extract_from_card(card)
        if item:
            results.append(item)

    return results


def _extract_from_card(card) -> Optional[PriceData]:
    """
    Extract PriceData from a Jumia <article class="prd"> BSoup element.

    Jumia DOM (verified 2024):
      Name  → <h3 class="name">
      Price → <div class="prc">   e.g. "29,90 MAD"
      Link  → <a class="core" href="/product-slug.html">
    """
    try:
        # Name
        name_el = card.find("h3", class_="name") or card.find("h2", class_="name")
        name = name_el.get_text(strip=True) if name_el else ""
        if not name:
            return None

        # Price
        price_el = (
            card.find("div", class_="prc")
            or card.find("span", class_="prc")
        )
        if not price_el:
            return None
        price = _parse_price(price_el.get_text(strip=True))
        if price is None:
            logger.debug(f"Could not parse price for: {name}")
            return None

        # URL — Jumia hrefs are relative ("/product.html")
        link_el = card.find("a", class_="core") or card.find("a", href=True)
        href = link_el["href"] if link_el else ""
        full_url = _resolve_url(href)

        return PriceData(
            product_name=name,
            price=price,
            currency="MAD",
            unit="piece",
            source="Jumia",
            product_url=full_url,
        )

    except Exception as exc:
        logger.debug(f"_extract_from_card error: {exc}")
        return None


# ---------------------------------------------------------------------------
# Strategy 2 — Playwright headless browser
# ---------------------------------------------------------------------------

def _fetch_via_playwright(query: str) -> list[PriceData]:
    """Full JS rendering via Playwright. Falls back silently if not installed."""
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        logger.debug("Playwright not installed; skipping browser strategy.")
        return []

    url = f"{BASE_URL}/catalog/?q={quote_plus(query)}"
    results: list[PriceData] = []

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent=USER_AGENTS[0],
                locale="fr-MA",
                viewport={"width": 1280, "height": 900},
            )
            page = ctx.new_page()
            page.goto(url, wait_until="networkidle", timeout=30_000)

            try:
                page.wait_for_selector("article.prd", timeout=12_000)
            except PWTimeout:
                logger.warning("Playwright: 'article.prd' never appeared — selector may have changed.")
                browser.close()
                return []

            # Hand off rendered HTML to BeautifulSoup for uniform parsing
            soup = BeautifulSoup(page.content(), "html.parser")
            browser.close()

        cards = soup.find_all("article", class_="prd")
        logger.info(f"Playwright: found {len(cards)} cards for '{query}'")

        for card in cards[:8]:
            item = _extract_from_card(card)
            if item:
                results.append(item)

    except Exception as exc:
        logger.error(f"Playwright strategy failed for '{query}': {exc}")

    return results


# ---------------------------------------------------------------------------
# Main scraper class
# ---------------------------------------------------------------------------

class JumiaFoodScraper:
    """
    Scraper for Jumia Morocco (https://www.jumia.com.ma).

    Three-tier strategy (tried in order per query):
      1. SSR-compatible requests + BeautifulSoup  (fast, no browser)
      2. Playwright headless browser              (reliable for full JS render)
      3. Mock / demo data                         (labelled, always works)
    """

    SOURCE_NAME = "Jumia"
    REQUEST_DELAY = 1.5  # seconds between queries

    def __init__(self) -> None:
        self._session = _make_session()
        self._ua_index = 0

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def scrape_prices(self, search_query: str | None = None) -> list[PriceData]:
        """
        Scrape food prices from Jumia Morocco.

        Args:
            search_query: Comma-separated keywords, e.g. "rice,oil,milk".
                          Defaults to ["rice", "oil", "milk"] when omitted.

        Returns:
            List of PriceData (never raises).
        """
        queries = (
            [q.strip() for q in search_query.split(",") if q.strip()]
            if search_query
            else ["rice", "oil", "milk"]
        )

        all_prices: list[PriceData] = []

        for i, query in enumerate(queries):
            logger.info(f"[{i+1}/{len(queries)}] Searching Jumia for: '{query}'")
            prices = self._fetch_with_fallback(query)
            all_prices.extend(prices)
            if i < len(queries) - 1:
                time.sleep(self.REQUEST_DELAY)

        logger.info(f"Total results: {len(all_prices)}")
        return all_prices

    def parse_product_page(self, url: str) -> Optional[PriceData]:
        """
        Parse a single Jumia product page.
        Returns None on failure (never raises).
        """
        headers = {**_SSR_HEADERS, "User-Agent": self._next_ua()}
        try:
            resp = self._session.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, "html.parser")

            name_el = soup.find("h1")
            # Jumia detail page uses <span class="prc"> for price
            price_el = (
                soup.find("span", class_="prc")
                or soup.find("div", class_="prc")
            )

            if not (name_el and price_el):
                logger.warning(f"parse_product_page: missing name or price at {url}")
                return None

            price = _parse_price(price_el.get_text(strip=True))
            if price is None:
                logger.warning(f"parse_product_page: could not parse price at {url}")
                return None

            return PriceData(
                product_name=name_el.get_text(strip=True),
                price=price,
                currency="MAD",
                unit="piece",
                source=self.SOURCE_NAME,
                product_url=url,
            )

        except requests.Timeout:
            logger.warning(f"parse_product_page: timeout — {url}")
        except requests.HTTPError as exc:
            logger.warning(f"parse_product_page: HTTP {exc.response.status_code} — {url}")
        except requests.RequestException as exc:
            logger.warning(f"parse_product_page: request error — {exc}")
        except Exception as exc:
            logger.error(f"parse_product_page: unexpected error — {exc}")

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

        # Strategy 1: SSR requests
        prices = _fetch_via_requests(query, self._session, self._next_ua())
        if prices:
            return prices

        # Strategy 2: Playwright
        logger.info(f"SSR strategy empty for '{query}'; trying Playwright...")
        prices = _fetch_via_playwright(query)
        if prices:
            return prices

        # Strategy 3: Mock
        logger.warning(f"All live strategies failed for '{query}'; using demo data.")
        return _get_mock_prices(query, self.SOURCE_NAME)


# ---------------------------------------------------------------------------
# Quick smoke-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    scraper = JumiaFoodScraper()
    results = scraper.scrape_prices("rice,oil")

    print(f"\n{'='*60}")
    print(f"  Jumia Results ({len(results)} items)")
    print(f"{'='*60}")
    for item in results:
        print(f"  {item.product_name:<40} {item.price:>8.2f} {item.currency}  [{item.source}]")
    print(f"{'='*60}\n")