"""
Scraper Utilities - Common functions for error handling, retries, and fallback data.
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
import logging
from typing import Callable, TypeVar, Optional
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')

# List of user agents to rotate for avoiding 403 errors
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0",
]


class ScraperError(Exception):
    """Base exception for scraper-related errors"""
    pass


class NetworkError(ScraperError):
    """Network connectivity errors (DNS, timeout, connection refused)"""
    pass


class AuthenticationError(ScraperError):
    """Authentication/authorization errors (403, 401)"""
    pass


class ParsingError(ScraperError):
    """HTML parsing or data extraction errors"""
    pass


def create_session_with_retries(
    retries: int = 3,
    backoff_factor: float = 0.5,
    status_forcelist: tuple = (429, 500, 502, 503, 504)
) -> requests.Session:
    """
    Create a requests session with automatic retries.
    
    Args:
        retries: Number of retries
        backoff_factor: Backoff factor for exponential backoff
        status_forcelist: HTTP status codes to retry on
        
    Returns:
        Configured requests.Session object
    """
    session = requests.Session()
    
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=list(status_forcelist),
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session


def retry_with_backoff(
    max_retries: int = 3,
    backoff_factor: float = 1.0,
    exceptions: tuple = (Exception,)
) -> Callable:
    """
    Decorator for retrying a function with exponential backoff.
    
    Args:
        max_retries: Maximum number of retries
        backoff_factor: Multiplier for exponential backoff
        exceptions: Tuple of exceptions to catch and retry on
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                    
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        logger.error(f"All {max_retries + 1} attempts failed for {func.__name__}")
                        raise
                    
                    # Calculate backoff time
                    wait_time = backoff_factor * (2 ** attempt)
                    logger.warning(
                        f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)[:100]}. "
                        f"Retrying in {wait_time:.1f}s..."
                    )
                    time.sleep(wait_time)
            
            raise last_exception
        
        return wrapper
    
    return decorator


def categorize_request_error(error: Exception) -> type:
    """
    Categorize a request error to determine retry strategy.
    
    Returns:
        Error class (NetworkError, AuthenticationError, etc.)
    """
    error_str = str(error).lower()
    
    # Network connectivity issues
    if any(term in error_str for term in ["nameresolutionerror", "connection refused", "failed to resolve"]):
        return NetworkError
    
    # Timeout
    if "timeout" in error_str or "timed out" in error_str:
        return NetworkError
    
    # Authentication/authorization
    if "403" in error_str or "401" in error_str:
        return AuthenticationError
    
    # Generic network error
    if "connectionerror" in error_str or "connection" in error_str:
        return NetworkError
    
    return ScraperError


def get_fallback_mock_data(search_query: str, source_name: str):
    """
    Return mock data for demo purposes when real scraping fails.
    
    Args:
        search_query: Product name (e.g., "rice", "milk", "oil")
        source_name: Name of the source (e.g., "Marjane", "Carrefour")
        
    Returns:
        Tuple of (product_name, price) or None
    """
    mock_data = {
        "rice": [
            ("Basmati Rice 1kg", 45.99),
            ("Long Grain Rice 2kg", 52.50),
            ("Jasmine Rice 1kg", 48.75),
        ],
        "oil": [
            ("Olive Oil 1L", 89.99),
            ("Argan Oil 250ml", 75.50),
            ("Sunflower Oil 2L", 42.00),
        ],
        "milk": [
            ("Fresh Milk 1L", 9.99),
            ("Skimmed Milk 1L", 8.50),
            ("Organic Milk 1L", 12.75),
        ],
        "flour": [
            ("Wheat Flour 1kg", 12.50),
            ("All-Purpose Flour 2kg", 22.00),
            ("Whole Wheat Flour 1kg", 15.75),
        ],
        "sugar": [
            ("White Sugar 1kg", 15.99),
            ("Brown Sugar 500g", 13.50),
            ("Cane Sugar 1kg", 16.75),
        ],
    }
    
    # Normalize search query
    query = search_query.lower().strip() if search_query else "rice"
    
    if query in mock_data:
        return mock_data[query]
    
    # Default fallback
    return [
        (f"{query.capitalize()} - Default Product", 29.99),
        (f"{query.capitalize()} - Premium Grade", 39.99),
    ]


def log_error_with_context(error: Exception, context: str, logger_obj) -> None:
    """
    Log an error with additional context information.
    
    Args:
        error: The exception that occurred
        context: Context description (e.g., "scraping rice from Marjane")
        logger_obj: Logger instance
    """
    error_type = categorize_request_error(error)
    error_type_name = error_type.__name__
    error_message = str(error)[:200]  # Truncate long messages
    
    logger_obj.error(
        f"[{error_type_name}] While {context}: {error_message}"
    )
