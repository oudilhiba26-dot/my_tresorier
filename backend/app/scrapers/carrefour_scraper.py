"""
Carrefour Morocco Scraper
Scrapes food prices from Carrefour (https://www.carrefour.ma/)
Carrefour uses dynamic JavaScript rendering - may need Playwright for production.
"""

import requests
from bs4 import BeautifulSoup
from typing import List
from datetime import datetime
import logging
import re

from .base_scraper import BaseScraper, PriceData

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CarrefourScraper(BaseScraper):
    """Scraper for Carrefour Morocco"""
    
    def __init__(self):
        super().__init__("Carrefour")
        self.base_url = "https://www.carrefour.ma"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    
    def scrape_prices(self, search_query: str = None) -> List[PriceData]:
        """
        Scrape food prices from Carrefour Morocco.
        
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
                logger.info(f"Scraping Carrefour for: {query}")
                
                # Construct search URL for Carrefour
                search_url = f"{self.base_url}/search?q={query}"
                
                try:
                    response = requests.get(search_url, headers=self.headers, timeout=10)
                    response.raise_for_status()
                    
                    soup = BeautifulSoup(response.content, "html.parser")
                    
                    # Find product containers (selectors need verification)
                    products = soup.find_all("div", class_="product-item")
                    
                    logger.info(f"Found {len(products)} products for '{query}'")
                    
                    for product in products[:5]:  # Limit to 5 results per query for demo
                        try:
                            price_data = self._extract_product_info(product, query)
                            if price_data:
                                all_prices.append(price_data)
                        except Exception as e:
                            logger.warning(f"Error extracting product info: {e}")
                            
                except requests.RequestException as e:
                    logger.error(f"Request error for '{query}': {e}")
                    
            return all_prices
            
        except Exception as e:
            logger.error(f"Error in scrape_prices: {e}")
            return []
    
    def _extract_product_info(self, product_element, product_type: str) -> PriceData:
        """
        Extract product name and price from a Carrefour product element.
        
        Note: CSS selectors need to be verified by inspecting the actual Carrefour page.
        """
        try:
            # Find product name
            name_elem = product_element.find("h3", class_="product-name")
            product_name = name_elem.text.strip() if name_elem else f"Unknown {product_type}"
            
            # Find price
            price_elem = product_element.find("span", class_="product-price")
            if price_elem:
                price_text = price_elem.text.strip()
                # Extract numeric value
                price_match = re.search(r"(\d+[.,]\d+|\d+)", price_text)
                if price_match:
                    price = float(price_match.group(1).replace(",", "."))
                else:
                    logger.warning(f"Could not parse price: {price_text}")
                    return None
            else:
                return None
            
            # Find product URL
            link_elem = product_element.find("a", class_="product-link")
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
        """Parse a single Carrefour product page"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Extract details (selectors need verification)
            name = soup.find("h1", class_="product-detail-name")
            price = soup.find("span", class_="product-detail-price")
            
            if name and price:
                return PriceData(
                    product_name=name.text.strip(),
                    price=float(price.text.strip()),
                    currency="MAD",
                    unit="piece",
                    source=self.source_name,
                    scrape_date=datetime.now(),
                    product_url=url
                )
        except Exception as e:
            logger.error(f"Error parsing product page: {e}")
        
        return None
