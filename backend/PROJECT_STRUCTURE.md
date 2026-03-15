# Project Structure Documentation

## Backend Architecture

```
backend/
├── main.py                      # Main FastAPI application entry point
├── demo.py                      # Demonstration script for testing scrapers
├── requirements.txt             # Python dependencies
├── .gitignore                   # Git ignore file
│
├── app/                         # Main application package
│   ├── __init__.py
│   │
│   ├── scrapers/               # Web scraping module
│   │   ├── __init__.py
│   │   ├── base_scraper.py     # Abstract base class for all scrapers
│   │   ├── jumia_food_scraper.py      # Jumia Food scraper
│   │   ├── marjane_scraper.py         # Marjane supermarket scraper
│   │   └── carrefour_scraper.py       # Carrefour supermarket scraper
│   │
│   ├── database/               # Database models and connections
│   │   ├── __init__.py
│   │   ├── models.py           # SQLAlchemy models (PriceRecord, BudgetRecord)
│   │   └── connection.py       # SQLite connection and initialization
│   │
│   └── api/                    # FastAPI routes (to be created in next step)
│       ├── __init__.py
│       ├── routes.py           # API endpoints

```

## Key Files

### Backend Core Files
- **main.py**: FastAPI application with all REST API endpoints
- **demo.py**: Test script to verify scrapers work correctly

### Scrapers (app/scrapers/)
- **base_scraper.py**: Abstract base class with common functionality
  - `PriceData` dataclass: Model for scraped prices
  - `BaseScraper`: Template with `scrape_prices()`, `parse_product_page()`, `calculate_average_price()`

- **jumia_food_scraper.py**: Scrapes Jumia Food (Morocco)
- **marjane_scraper.py**: Scrapes Marjane Supermarket (Morocco)
- **carrefour_scraper.py**: Scrapes Carrefour Morocco

### Database (app/database/)
- **models.py**: SQLAlchemy ORM models
  - `PriceRecord`: Stores scraped price data
  - `BudgetRecord`: Stores user budget calculations

- **connection.py**: SQLite database setup and session management

## How to Use

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Run the Demo (Test the Scrapers)
```bash
python demo.py
```

This will:
- Test individual scrapers (Marjane, Carrefour, Jumia)
- Aggregate prices from all sources
- Save data to SQLite database
- Display price statistics

### 3. Start the FastAPI Server
```bash
python main.py
```

The API will be available at `http://localhost:8000`
- API documentation: `http://localhost:8000/docs`
- OpenAPI schema: `http://localhost:8000/openapi.json`

### 4. API Endpoints

**Scraping Endpoints:**
- `POST /api/scrape/marjane?search_query=rice,milk` - Scrape Marjane
- `POST /api/scrape/carrefour?search_query=rice,milk` - Scrape Carrefour
- `POST /api/scrape/jumia?search_query=rice,milk` - Scrape Jumia Food

**Market Data Endpoints:**
- `GET /api/market_prices` - Get aggregated market prices
- `GET /api/market_prices?product_type=rice&days_back=7` - Filter by product and date range

**Budget Calculation Endpoints:**
- `POST /api/calculate_budget` - Calculate budget allocation based on capital and priorities
- `GET /api/budgets/{user_id}` - Get user's budget history

## Next Steps (Step 2)

1. **Smart Allocation Algorithm**: Enhance the budget calculation logic in `calculate_budget()` with:
   - Dynamic allocation based on market prices
   - Student priority preferences (leisure vs savings)
   - Financial safety recommendations

2. **Frontend Development**: Create React + Vite frontend with:
   - Landing page
   - Interactive budget form
   - Dashboard with visualizations (Chart.js)

## Important Notes

- **CSS Selectors**: The scrapers use CSS selectors to find elements. These may need to be adjusted if the websites change their HTML structure. Inspect the actual websites to verify/update selectors.

- **Dynamic Content**: Sites like Jumia Food use JavaScript to load products. For production, consider using Playwright instead of BeautifulSoup for better reliability.

- **Rate Limiting**: Be mindful of website rate limits. Add delays between requests if needed.

- **User-Agent Headers**: Websites may block requests without proper User-Agent headers (included in the scrapers).
