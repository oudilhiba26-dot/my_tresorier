"""
Jumia Food Morocco Scraper
Scrapes food prices from Jumia Food (https://www.jumia.com.ma/)
Note: Jumia Food uses dynamic JavaScript rendering, so BeautifulSoup alone may not work.
For production, use Playwright or Selenium.
"""

import requests
from bs4 import BeautifulSoup
from typing import List
from datetime import datetime
import logging
import time

from .base_scraper import BaseScraper, PriceData
from .scraper_utils import (
    create_session_with_retries,
    get_fallback_mock_data,
    categorize_request_error,
    USER_AGENTS
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JumiaFoodScraper(BaseScraper):
    """Scraper for Jumia Food Morocco"""
    
    def __init__(self):
        super().__init__("Jumia Food")
        self.base_url = "https://www.jumia.com.ma"
        self.session = create_session_with_retries(retries=3, backoff_factor=0.5)
        self.user_agent_index = 0
        self.request_delay = 2.0  # Longer delay for Jumia
    
    def _get_next_user_agent(self) -> str:
        """Rotate through user agents"""
        ua = USER_AGENTS[self.user_agent_index % len(USER_AGENTS)]
        self.user_agent_index += 1
        return ua
    
    def scrape_prices(self, search_query: str = None) -> List[PriceData]:
        """
        Scrape food prices from Jumia Food.
        
        For demonstration, this scrapes search results for common food items.
        In production, use Playwright to handle JavaScript rendering.
        
        Args:
            search_query: Product to search (e.g., "rice", "oil", "milk")
            
        Returns:
            List of PriceData objects
        """
        try:
            # Default search queries if none provided
            search_queries = search_query.split(",") if search_query else ["rice", "oil", "milk"]
            all_prices = []
            
            for query in search_queries:
                query = query.strip()
                logger.info(f"Scraping Jumia Food for: {query}")
                
                # Try real scraping first
                prices = self._scrape_with_retry(query)
                
                if prices:
                    all_prices.extend(prices)
                    logger.info(f"Successfully fetched {len(prices)} items from Jumia Food for '{query}'")
                else:
                    # Fall back to mock data if real scraping fails
                    logger.warning(f"Real scraping failed for '{query}', using fallback data...")
                    mock_prices = self._get_mock_prices(query)
                    all_prices.extend(mock_prices)
                    logger.info(f"Using {len(mock_prices)} fallback items for '{query}'")
                
                # Add delay between requests
                time.sleep(self.request_delay)
            
            return all_prices
            
        except Exception as e:
            logger.error(f"Critical error in scrape_prices: {e}")
            return []
    
    def _scrape_with_retry(self, query: str) -> List[PriceData]:
        """Attempt to scrape Jumia Food with retry logic"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                headers = {"User-Agent": self._get_next_user_agent()}
                search_url = f"{self.base_url}/catalog/?q={query}"
                
                response = self.session.get(search_url, headers=headers, timeout=10)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, "html.parser")
                products = soup.find_all("article", class_="prd")
                
                logger.info(f"Found {len(products)} products for '{query}'")
                
                prices = []
                for product in products[:5]:
                    try:
                        price_data = self._extract_product_info(product, query)
                        if price_data:
                            prices.append(price_data)
                    except Exception as e:
                        logger.debug(f"Error extracting product: {e}")
                
                return prices
                
            except requests.Timeout as e:
                logger.warning(f"[NetworkError] Timeout on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    
            except requests.ConnectionError as e:
                logger.warning(f"[NetworkError] Connection error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    
            except requests.RequestException as e:
                error_type = categorize_request_error(e).__name__
                logger.warning(f"[{error_type}] Request error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
        
        return []
    
    def _get_mock_prices(self, query: str) -> List[PriceData]:
        """Get fallback mock prices"""
        mock_data = get_fallback_mock_data(query, self.source_name)
        prices = []
        
        for product_name, price in mock_data:
            prices.append(PriceData(
                product_name=product_name,
                price=price,
                currency="MAD",
                unit="piece",
                source=f"{self.source_name} (Demo)",
                scrape_date=datetime.now(),
                product_url=""
            ))
        
        return prices
    
    def _extract_product_info(self, product_element, product_type: str) -> PriceData:
        """
        Extract product name and price from a product element.
        
        Note: CSS selectors need to be verified by inspecting the actual Jumia page.
        """
        try:
            # Try to find product name
            name_elem = product_element.find("h2", class_="name")
            product_name = name_elem.text.strip() if name_elem else f"Unknown {product_type}"
            
            # Try to find price
            price_elem = product_element.find("div", class_="prc")
            if price_elem:
                price_text = price_elem.text.strip().replace("MAD", "").replace(",", ".").strip()
                try:
                    price = float(price_text)
                except ValueError:
                    logger.warning(f"Could not parse price: {price_text}")
                    return None
            else:
                return None
            
            # Try to find product URL
            link_elem = product_element.find("a", class_="core")
            url = link_elem["href"] if link_elem else ""
            
            return PriceData(
                product_name=product_name,
                price=price,
                currency="MAD",
                unit="piece",  # Adjust based on actual product type
                source=self.source_name,
                scrape_date=datetime.now(),
                product_url=url
            )
            
        except Exception as e:
            logger.warning(f"Error extracting product info: {e}")
            return None
    
    def parse_product_page(self, url: str) -> PriceData:
        """Parse a single Jumia Food product page"""
        try:
            headers = {"User-Agent": self._get_next_user_agent()}
            response = self.session.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Extract details (selectors need verification)
            name = soup.find("h1")
            price = soup.find("span", class_="prc")
            
            if name and price:
                return PriceData(
                    product_name=name.text.strip(),
                    price=float(price.text.replace("MAD", "").strip()),
                    currency="MAD",
                    unit="piece",
                    source=self.source_name,
                    scrape_date=datetime.now(),
                    product_url=url
                )
        except requests.Timeout:
            logger.warning(f"Timeout parsing product page: {url}")
        except requests.RequestException as e:
            logger.warning(f"Error parsing product page: {e}")
        except Exception as e:
            logger.error(f"Error parsing product page: {e}")
        
        return None
