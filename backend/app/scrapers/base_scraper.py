"""
Base Scraper Class - Abstract template for all food scrapers.
"""
from abc import ABC, abstractmethod
from typing import List, Dict
from dataclasses import dataclass
from datetime import datetime

@dataclass
class PriceData:
    """Model for scraped price data"""
    product_name: str
    price: float
    currency: str
    unit: str  # e.g., "kg", "liter", "piece"
    source: str  # e.g., "Jumia Food", "Marjane"
    scrape_date: datetime
    product_url: str = ""


class BaseScraper(ABC):
    """Abstract base class for all food price scrapers"""
    
    def __init__(self, source_name: str):
        self.source_name = source_name
        self.base_url = ""
        
    @abstractmethod
    def scrape_prices(self, search_query: str = None) -> List[PriceData]:
        """
        Scrape prices from the source.
        
        Args:
            search_query: Optional search term (e.g., "rice", "milk")
            
        Returns:
            List of PriceData objects
        """
        pass
    
    @abstractmethod
    def parse_product_page(self, url: str) -> PriceData:
        """Parse a single product page and extract price information"""
        pass
    
    def calculate_average_price(self, prices: List[PriceData]) -> Dict:
        """
        Calculate average price across products.
        
        Args:
            prices: List of PriceData objects
            
        Returns:
            Dict with average, min, max prices
        """
        if not prices:
            return {"average": 0, "min": 0, "max": 0, "count": 0}
        
        price_list = [p.price for p in prices]
        return {
            "average": sum(price_list) / len(price_list),
            "min": min(price_list),
            "max": max(price_list),
            "count": len(price_list),
            "currency": prices[0].currency if prices else "MAD"
        }
