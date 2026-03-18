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
import pandas as pd
from playwright.async_api import async_playwright

async def scrape_to_file():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Target a specific category
        url = "https://carrefourmaroc.ma/frais/cremerie.html"
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_selector(".product-item")

        products = await page.query_selector_all(".product-item")
        
        # 1. Create a list to store our data "rows"
        scraped_data = []

        for product in products:
            name_el = await product.query_selector(".product-item-link")
            price_el = await product.query_selector(".price")
            
            name = await name_el.inner_text() if name_el else "N/A"
            price = await price_el.inner_text() if price_el else "N/A"

            # 2. Append a dictionary for each product
            scraped_data.append({
                "Product Name": name.strip(),
                "Price (MAD)": price.strip()
            })

        await browser.close()

        # 3. Use Pandas to save the data
        df = pd.DataFrame(scraped_data)
        
        # Save as CSV
        df.to_csv("carrefour_products.csv", index=False, encoding="utf-8-sig")
        
        # Save as Excel (optional)
        # df.to_excel("carrefour_products.xlsx", index=False)

        print(f"✅ Success! Saved {len(df)} products to carrefour_products.csv")

asyncio.run(scrape_to_file())