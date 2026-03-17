# 📊 Tresorier - Student Budget Optimizer

> **Smart Budget Management for Moroccan University Students**

Tresorier is an intelligent web application that automatically analyzes real market prices and generates personalized monthly budgets for students. It uses web scraping to track prices across Moroccan supermarkets (Marjane, Carrefour, Jumia Food) and provides data-driven budget recommendations.

---

## ✨ Key Features

- 🔍 **Real-time Web Scraping** - Fetches current prices from Moroccan supermarkets
- 💰 **Smart Budget Allocation** - Generates personalized spending plans based on priorities
- 📈 **Market Analytics** - Aggregates and analyzes price data across sources
- 🎯 **Student-Focused** - Designed for budget constraints and student priorities
- 🔄 **Flexible Priorities** - Customize between savings, leisure, or balanced spending

---

## 🏗️ Tech Stack

| Category | Technologies |
|----------|--------------|
| **Backend** | FastAPI, Python, SQLite/PostgreSQL |
| **Scraping** | BeautifulSoup, Playwright |
| **Data** | Pandas, SciPy |
| **Frontend** | React 18, Vite, Tailwind CSS, Chart.js |

---

## 📁 Project Structure

```
my_tresorier/
├── backend/
│   ├── app/
│   │   ├── scrapers/           # Web scraping modules
│   │   │   ├── base_scraper.py
│   │   │   ├── marjane_scraper.py
│   │   │   ├── carrefour_scraper.py
│   │   │   └── jumia_food_scraper.py
│   │   └── database/           # Data models & connections
│   │       ├── models.py
│   │       └── connection.py
│   ├── main.py                 # FastAPI application
│   ├── demo.py                 # Testing & demonstration
│   └── requirements.txt         # Python dependencies
│
├── frontend/                   # React + Vite app (upcoming)
└── README.md                   # This file
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- pip or conda
- Git

### Installation & Setup

```bash
# Clone and navigate
git clone https://github.com/oudilhiba26-dot/my_tresorier.git


# Create virtual environment (recommended)
python -m venv venv
source venv/Scripts/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Application

**1. Test the Web Scrapers**
```bash
python demo.py
```
This will scrape prices from Marjane, Carrefour, and Jumia Food, then save them to the database.

**2. Start the FastAPI Server**
```bash
python main.py
```
Server runs at: `http://localhost:8000`
- **Interactive API Docs**: `http://localhost:8000/docs`
- **Health Check**: `http://localhost:8000/api/health`

**3. Test API Endpoints**
```bash
# Get aggregated market prices
curl http://localhost:8000/api/market_prices

# Scrape specific supermarket (e.g., Marjane)
curl -X POST "http://localhost:8000/api/scrape/marjane?search_query=rice,milk"

# Calculate budget for a student with 2000 MAD/month
curl -X POST http://localhost:8000/api/calculate_budget \
  -H "Content-Type: application/json" \
  -d '{"total_capital": 2000, "priority": "balanced"}'
```

---

## 📡 API Reference

### Scraping Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/scrape/marjane` | POST | Scrape Marjane prices |
| `/api/scrape/carrefour` | POST | Scrape Carrefour prices |
| `/api/scrape/jumia` | POST | Scrape Jumia Food prices |

### Market Data Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/market_prices` | GET | Get aggregated market prices |
| `/api/market_prices?product_type=rice` | GET | Filter by product |
| `/api/market_prices?days_back=7` | GET | Filter by date range |

### Budget Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/calculate_budget` | POST | Calculate budget allocation |
| `/api/budgets/{user_id}` | GET | Get user budget history |

---

## 🗄️ Database

The application uses **SQLite** for development (automatically created as `tresorier.db` on first run).

### Key Tables

**price_records** - Stores scraped prices
```
id | product_name | price | currency | unit | source | scrape_date | product_url
```

**budget_records** - Stores budget calculations
```
id | user_id | total_capital | priority | result_json | created_date
```

---

## 🔧 Development Phases

### Phase 1: Web Scraping Module ✅ COMPLETE
- [x] Project architecture
- [x] Base scraper class
- [x] Three supermarket scrapers (Marjane, Carrefour, Jumia)
- [x] SQLite database setup
- [x] FastAPI endpoints
- [x] Demo script

### Phase 2: Smart Allocation Algorithm (IN PROGRESS)
- [ ] Enhanced budget calculation logic
- [ ] Dynamic allocation based on real market prices
- [ ] Student priority preferences (leisure vs savings)
- [ ] Financial recommendations

### Phase 3: Frontend Development (UPCOMING)
- [ ] Landing page
- [ ] Interactive budget form
- [ ] Dashboard with visualizations
- [ ] Mobile responsive design

### Phase 4: Advanced Features (FUTURE)
- [ ] Historical price tracking
- [ ] Price alerts
- [ ] Student price community
- [ ] Housing market analysis

---

## ⚠️ Important Notes

### CSS Selectors
The scrapers use CSS selectors to extract price data. If websites change their HTML structure, selectors may need updating:

```python
# Example in marjane_scraper.py
products = soup.find_all("div", class_="product")  # May need updating
```

**To fix broken selectors:**
1. Visit the website (https://www.marjane.ma)
2. Right-click → **Inspect** to view HTML
3. Find the product container class name
4. Update the CSS selector in the scraper file
5. Test with `python demo.py`

### Website Compatibility
- **Marjane** - Static HTML (BeautifulSoup works well)
- **Carrefour** - Semi-dynamic (BeautifulSoup may need Playwright for reliability)
- **Jumia Food** - JavaScript-heavy (Playwright recommended for production)

---

## 🤝 Contributing

Contributions are welcome! Areas for improvement:
- Update scrapers when websites change
- Improve budget calculation algorithms
- Add new supermarket sources
- Build the React frontend
- Database optimizations
- Error handling improvements

---

## 📚 Additional Documentation

- [Backend Architecture](backend/PROJECT_STRUCTURE.md) - Detailed backend structure
- [Frontend Roadmap](frontend/STRUCTURE.md) - Frontend development plan

---

## 🆘 Troubleshooting

**Scraper returns 0 results?**
1. Run `python demo.py` to see error messages
2. Check if website HTML structure changed
3. Inspect the website and update CSS selectors
4. Verify User-Agent headers in scraper

**API server not starting?**
1. Ensure port 8000 is available
2. Check all dependencies are installed: `pip install -r requirements.txt`
3. Verify Python version: `python --version` (should be 3.8+)

**Database errors?**
1. Delete `tresorier.db` to reset
2. Run `python demo.py` to recreate database
3. Check file permissions in the directory

---

## 📞 Support & Questions

For issues or questions:
1. Check the [Backend Documentation](backend/PROJECT_STRUCTURE.md)
2. Review [Frontend Roadmap](frontend/STRUCTURE.md)
3. Create a GitHub issue with details

---

## 📝 License

This project is open source and available for educational purposes.

---

**Made with ❤️ for Moroccan University Students | Developed by Hiba OUDIL**