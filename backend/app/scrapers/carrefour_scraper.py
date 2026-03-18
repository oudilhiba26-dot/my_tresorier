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

import asyncio
from playwright.async_api import async_playwright

async def scrape_carrefour():
    async with async_playwright() as p:
        # Launch browser (headless=True means no window will pop up)
        browser = await p.chromium.launch(headless=False) 
        page = await browser.new_page()
        
        # Go to a specific category (e.g., Crémerie)
        url = "https://carrefourmaroc.ma/frais/cremerie.html"
        print(f"Opening {url}...")
        await page.goto(url, wait_until="networkidle")

        # Wait for the product cards to appear in the HTML
        await page.wait_for_selector(".product-item")

        # Extract all product items
        products = await page.query_selector_all(".product-item")
        
        print(f"Found {len(products)} products. Extracting data...\n")

        for product in products:
            # Scrape the Name
            name_element = await product.query_selector(".product-item-link")
            name = await name_element.inner_text() if name_element else "N/A"

            # Scrape the Price
            price_element = await product.query_selector(".price")
            price = await price_element.inner_text() if price_element else "N/A"

            print(f"Product: {name.strip()}")
            print(f"Price: {price.strip()}")
            print("-" * 20)

        await browser.close()

# Run the script
asyncio.run(scrape_carrefour())