"""
Demo Script: Test the Web Scraping Module
This script demonstrates how to use the scrapers to fetch and analyze food prices.
Run this to verify the scrapers work correctly with real Moroccan websites.
"""

import sys
from datetime import datetime
from app.scrapers import JumiaFoodScraper, MarjaneScraper
from app.scrapers.carrefour_scraper import CarrefourScraper
from app.database.models import PriceRecord
from app.database.connection import init_db, SessionLocal
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def calculate_average_price(prices):
    """Helper function to calculate average price from a list of price objects"""
    if not prices:
        return {"average": 0, "min": 0, "max": 0, "count": 0}
    
    price_list = [p.price for p in prices]
    return {
        "average": sum(price_list) / len(price_list),
        "min": min(price_list),
        "max": max(price_list),
        "count": len(price_list),
    }


def safe_save_to_db(prices, source_name):
    """Safely save price records to database"""
    if not prices:
        logger.warning(f"No prices to save from {source_name}")
        return 0
    
    db = SessionLocal()
    saved_count = 0
    try:
        for price in prices:
            # Handle both old and new PriceData formats
            record = PriceRecord(
                product_name=price.product_name,
                price=price.price,
                currency=getattr(price, 'currency', 'MAD'),
                unit=getattr(price, 'unit', 'piece'),
                source=getattr(price, 'source', source_name),
                product_url=getattr(price, 'product_url', ''),
                scrape_date=getattr(price, 'scrape_date', datetime.now())
            )
            db.add(record)
            saved_count += 1
        db.commit()
        logger.info(f"✓ Saved {saved_count} records from {source_name}")
    except Exception as e:
        logger.error(f"✗ Error saving records from {source_name}: {e}")
        db.rollback()
    finally:
        db.close()
    
    return saved_count


def demo_single_scraper():
    """Test a single scraper"""
    print("=" * 70)
    print("DEMO 1: Testing Individual Scrapers")
    print("=" * 70)
    
    # Test Marjane (static HTML, most reliable)
    print("\n[1] Scraping Marjane for 'rice, oil, milk'...")
    try:
        marjane = MarjaneScraper()
        marjane_prices = marjane.scrape_prices("rice, oil, milk")
        
        print(f"\nFound {len(marjane_prices)} prices from Marjane:")
        for price in marjane_prices:
            print(f"  • {price.product_name}: {price.price} {getattr(price, 'currency', 'MAD')}")
        
        # Calculate average
        if marjane_prices:
            avg = calculate_average_price(marjane_prices)
            print(f"\nAverage price: {avg['average']:.2f} MAD (Min: {avg['min']}, Max: {avg['max']})")
    except Exception as e:
        logger.error(f"Error with Marjane scraper: {e}")
        print(f"  ✗ Error: {e}")
    
    print("\n" + "-" * 70)
    
    # Test Carrefour (refactored with Playwright + API fallback)
    print("\n[2] Scraping Carrefour for 'rice, oil, milk'...")
    try:
        carrefour = CarrefourScraper()
        carrefour_prices = carrefour.scrape_prices("rice, oil, milk")
        
        print(f"\nFound {len(carrefour_prices)} prices from Carrefour:")
        for price in carrefour_prices:
            print(f"  • {price.product_name}: {price.price} {getattr(price, 'currency', 'MAD')}")
        
        if carrefour_prices:
            avg = calculate_average_price(carrefour_prices)
            print(f"\nAverage price: {avg['average']:.2f} MAD")
    except Exception as e:
        logger.error(f"Error with Carrefour scraper: {e}")
        print(f"  ✗ Error: {e}")


def demo_all_scrapers():
    """Test all scrapers and aggregate results"""
    print("\n" + "=" * 70)
    print("DEMO 2: Aggregating Prices from All Sources")
    print("=" * 70)
    
    scrapers = {
        "Marjane": MarjaneScraper(),
        "Carrefour": CarrefourScraper(),
        "Jumia Food": JumiaFoodScraper()
    }
    
    search_items = ["rice", "milk"]
    all_results = {}
    
    for scraper_name, scraper in scrapers.items():
        print(f"\n[{scraper_name}] Fetching prices for '{', '.join(search_items)}'...")
        try:
            prices = scraper.scrape_prices(",".join(search_items))
            print(f"  ✓ Found {len(prices)} items")
            all_results[scraper_name] = prices
        except Exception as e:
            logger.error(f"Error with {scraper_name}: {e}")
            print(f"  ✗ Error: {e}")
            all_results[scraper_name] = []
    
    # Aggregate results
    print("\n" + "-" * 70)
    print("PRICE COMPARISON (by Product)")
    print("-" * 70)
    
    if any(all_results.values()):
        # Create a summary DataFrame
        rows = []
        for source_name, prices in all_results.items():
            for price in prices:
                rows.append({
                    "Source": source_name,
                    "Product": price.product_name,
                    "Price (MAD)": price.price,
                    "Date": getattr(price, 'scrape_date', datetime.now()).strftime("%Y-%m-%d") if hasattr(price, 'scrape_date') else datetime.now().strftime("%Y-%m-%d")
                })
        
        if rows:
            df = pd.DataFrame(rows)
            print(df.to_string(index=False))
            
            # Group by product and show averages
            print("\n" + "-" * 70)
            print("MARKET AVERAGE PRICES")
            print("-" * 70)
            avg_by_product = df.groupby("Product")["Price (MAD)"].agg(["mean", "min", "max", "count"])
            avg_by_product.columns = ["Average", "Min", "Max", "Sources"]
            print(avg_by_product.round(2))


def demo_save_to_database():
    """Demonstrate saving prices from all scrapers to database"""
    print("\n" + "=" * 70)
    print("DEMO 3: Saving Scraped Data to Database")
    print("=" * 70)
    
    # Initialize database
    print("\nInitializing database...")
    init_db()
    print("✓ Database initialized")
    
    scrapers = {
        "Marjane": MarjaneScraper(),
        "Carrefour": CarrefourScraper(),
        "Jumia Food": JumiaFoodScraper()
    }
    
    search_terms = "rice, milk"
    total_saved = 0
    
    print(f"\n\nScraping and saving prices for: '{search_terms}'")
    print("-" * 70)
    
    for scraper_name, scraper in scrapers.items():
        print(f"\n[{scraper_name}] Scraping...")
        try:
            prices = scraper.scrape_prices(search_terms)
            if prices:
                saved = safe_save_to_db(prices, scraper_name)
                total_saved += saved
            else:
                print(f"  (No prices found from {scraper_name})")
        except Exception as e:
            logger.error(f"Error scraping {scraper_name}: {e}")
            print(f"  ✗ Error: {e}")
    
    # Display database contents
    print("\n" + "-" * 70)
    print("Database Summary")
    print("-" * 70)
    
    db = SessionLocal()
    try:
        records = db.query(PriceRecord).all()
        print(f"\nTotal records in database: {len(records)}")
        
        if records:
            print("\nLatest 10 records:")
            for record in records[-10:]:
                print(f"  • {record.product_name:<35} {record.price:>8.2f} {record.currency:<4} ({record.source})")
    except Exception as e:
        logger.error(f"Error querying database: {e}")
        print(f"  ✗ Error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "TRESORIER - WEB SCRAPING MODULE DEMO" + " " * 16 + "║")
    print("║" + " " * 20 + "Moroccan Food Price Scraper" + " " * 21 + "║")
    print("║" + " " * 15 + "(Updated for new Carrefour & Jumia refactoring)" + " " * 2 + "║")
    print("╚" + "=" * 68 + "╝")
    
    try:
        # Run demos
        demo_single_scraper()
        demo_all_scrapers()
        demo_save_to_database()
        
        print("\n" + "=" * 70)
        print("✓ All demos completed successfully!")
        print("=" * 70 + "\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠ Demo interrupted by user.")
    except Exception as e:
        logger.error(f"Critical error: {e}", exc_info=True)
        print(f"\n\n✗ Critical Error: {e}")
        import traceback
        traceback.print_exc()
