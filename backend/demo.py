"""
Demo Script: Test the Web Scraping Module
This script demonstrates how to use the scrapers to fetch and analyze food prices.
Run this to verify the scrapers work correctly with real Moroccan websites.
"""

import sys
from datetime import datetime
from app.scrapers import JumiaFoodScraper, MarjaneScraper, CarrefourScraper
from app.database.models import PriceRecord
from app.database.connection import init_db, SessionLocal
import pandas as pd


def demo_single_scraper():
    """Test a single scraper"""
    print("=" * 70)
    print("DEMO 1: Testing Individual Scrapers")
    print("=" * 70)
    
    # Test Marjane (most likely to work with BeautifulSoup)
    print("\n[1] Scraping Marjane for rice, oil, milk...")
    marjane = MarjaneScraper()
    marjane_prices = marjane.scrape_prices("rice, oil, milk")
    
    print(f"\nFound {len(marjane_prices)} prices from Marjane:")
    for price in marjane_prices:
        print(f"  • {price.product_name}: {price.price} {price.currency}")
    
    # Calculate average
    if marjane_prices:
        avg = marjane.calculate_average_price(marjane_prices)
        print(f"\nAverage price: {avg['average']:.2f} MAD (Min: {avg['min']}, Max: {avg['max']})")
    
    print("\n" + "-" * 70)
    
    # Test Carrefour
    print("\n[2] Scraping Carrefour for rice, oil, milk...")
    carrefour = CarrefourScraper()
    carrefour_prices = carrefour.scrape_prices("rice, oil, milk")
    
    print(f"\nFound {len(carrefour_prices)} prices from Carrefour:")
    for price in carrefour_prices:
        print(f"  • {price.product_name}: {price.price} {price.currency}")
    
    if carrefour_prices:
        avg = carrefour.calculate_average_price(carrefour_prices)
        print(f"\nAverage price: {avg['average']:.2f} MAD")


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
        print(f"\n[{scraper_name}] Fetching prices...")
        try:
            prices = scraper.scrape_prices(",".join(search_items))
            print(f"  ✓ Found {len(prices)} items")
            all_results[scraper_name] = prices
        except Exception as e:
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
                    "Date": price.scrape_date.strftime("%Y-%m-%d")
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
    """Demonstrate saving prices to database"""
    print("\n" + "=" * 70)
    print("DEMO 3: Saving Scraped Data to Database")
    print("=" * 70)
    
    # Initialize database
    print("\nInitializing database...")
    init_db()
    
    # Scrape some data
    print("Scraping Marjane...")
    scraper = MarjaneScraper()
    prices = scraper.scrape_prices("rice, milk")
    
    # Save to database
    print(f"\nSaving {len(prices)} records to database...")
    db = SessionLocal()
    try:
        for price in prices:
            record = PriceRecord(
                product_name=price.product_name,
                price=price.price,
                currency=price.currency,
                unit=price.unit,
                source=price.source,
                product_url=price.product_url,
                scrape_date=price.scrape_date
            )
            db.add(record)
        db.commit()
        print(f"✓ {len(prices)} records saved successfully!")
        
        # Query and display
        print("\nRetrieving records from database...")
        records = db.query(PriceRecord).all()
        print(f"Total records in database: {len(records)}")
        
        for record in records[-3:]:  # Show last 3
            print(f"  • {record.product_name} - {record.price} MAD (from {record.source})")
            
    finally:
        db.close()


if __name__ == "__main__":
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "TRESORIER - WEB SCRAPING MODULE DEMO" + " " * 16 + "║")
    print("║" + " " * 20 + "Moroccan Food Price Scraper" + " " * 21 + "║")
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
        print(f"\n\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
