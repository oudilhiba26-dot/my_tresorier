"""
Main FastAPI Application
Entry point for the REST API
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.database.connection import init_db, SessionLocal, get_db
from app.database.models import PriceRecord, BudgetRecord, Base
from app.scrapers import MarjaneScraper, CarrefourScraper, JumiaFoodScraper

# Initialize FastAPI app
app = FastAPI(
    title="Tresorier API",
    description="Budget optimization API for university students with web scraping engine",
    version="0.1.0"
)

# Add CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
def startup_event():
    """Initialize database on application startup"""
    init_db()
    print("✓ FastAPI server started - Database initialized")


# ==================== Pydantic Models ====================

class PriceResponseModel(BaseModel):
    """Response model for price data"""
    product_name: str
    price: float
    currency: str
    unit: str
    source: str
    scrape_date: datetime
    product_url: Optional[str] = None
    
    class Config:
        from_attributes = True


class MarketPriceStats(BaseModel):
    """Market price statistics"""
    product_type: str
    average_price: float
    min_price: float
    max_price: float
    price_count: int
    sources_count: int
    currency: str


class BudgetRequest(BaseModel):
    """Request model for budget calculation"""
    total_capital: float
    priority: str = "balanced"  # "leisure", "savings", "balanced"
    location: str = "Morocco"
    

class BudgetResponse(BaseModel):
    """Response model for budget breakdown"""
    total_capital: float
    priority: str
    allocations: dict
    market_prices: dict
    recommendations: list
    

# ==================== Endpoints ====================

@app.get("/")
def read_root():
    """Welcome endpoint"""
    return {
        "message": "Welcome to Tresorier - Student Budget Optimizer",
        "description": "Use /docs for API documentation",
        "version": "0.1.0"
    }


@app.get("/api/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now()}


# ==================== Web Scraping Endpoints ====================

@app.post("/api/scrape/marjane")
def scrape_marjane(
    search_query: Optional[str] = None,
    db: Session = Depends(get_db)
) -> List[PriceResponseModel]:
    """
    Scrape prices from Marjane supermarket
    
    Args:
        search_query: Comma-separated products (e.g., "rice,milk,oil")
    
    Returns:
        List of prices found
    """
    try:
        scraper = MarjaneScraper()
        prices = scraper.scrape_prices(search_query or "rice,milk,oil")
        
        # Save to database
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
        
        return prices
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/scrape/carrefour")
def scrape_carrefour(
    search_query: Optional[str] = None,
    db: Session = Depends(get_db)
) -> List[PriceResponseModel]:
    """
    Scrape prices from Carrefour supermarket
    
    Args:
        search_query: Comma-separated products
    
    Returns:
        List of prices found
    """
    try:
        scraper = CarrefourScraper()
        prices = scraper.scrape_prices(search_query or "rice,milk,oil")
        
        # Save to database
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
        
        return prices
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/scrape/jumia")
def scrape_jumia(
    search_query: Optional[str] = None,
    db: Session = Depends(get_db)
) -> List[PriceResponseModel]:
    """
    Scrape prices from Jumia Food
    
    Args:
        search_query: Comma-separated products
    
    Returns:
        List of prices found
    """
    try:
        scraper = JumiaFoodScraper()
        prices = scraper.scrape_prices(search_query or "rice,milk,oil")
        
        # Save to database
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
        
        return prices
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/market_prices")
def get_market_prices(
    product_type: Optional[str] = None,
    days_back: int = 7,
    db: Session = Depends(get_db)
) -> dict:
    """
    Get market price statistics from database
    
    Args:
        product_type: Filter by product type (e.g., "rice")
        days_back: Only include prices from last N days
    
    Returns:
        Price statistics and market averages
    """
    try:
        # Build query
        cutoff_date = datetime.now() - timedelta(days=days_back)
        query = db.query(PriceRecord).filter(PriceRecord.scrape_date >= cutoff_date)
        
        if product_type:
            query = query.filter(PriceRecord.product_name.ilike(f"%{product_type}%"))
        
        records = query.all()
        
        if not records:
            return {"message": "No price data found", "products": []}
        
        # Group by product and calculate stats
        products_dict = {}
        for record in records:
            key = record.product_name
            if key not in products_dict:
                products_dict[key] = {
                    "prices": [],
                    "sources": set(),
                    "currency": record.currency
                }
            products_dict[key]["prices"].append(record.price)
            products_dict[key]["sources"].add(record.source)
        
        # Calculate statistics
        stats = []
        for product, data in products_dict.items():
            prices = data["prices"]
            stats.append({
                "product": product,
                "average_price": round(sum(prices) / len(prices), 2),
                "min_price": min(prices),
                "max_price": max(prices),
                "price_count": len(prices),
                "sources": list(data["sources"]),
                "sources_count": len(data["sources"]),
                "currency": data["currency"]
            })
        
        return {
            "stats": stats,
            "total_products": len(stats),
            "date_range": f"Last {days_back} days",
            "data_points": len(records)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Budget Endpoints ====================

@app.post("/api/calculate_budget")
def calculate_budget(
    budget_req: BudgetRequest,
    db: Session = Depends(get_db)
) -> BudgetResponse:
    """
    Calculate budget allocation based on student preferences and market prices
    
    Args:
        budget_req: Budget request with capital and priorities
    
    Returns:
        Detailed budget breakdown and recommendations
    """
    try:
        # Get current market prices
        records = db.query(PriceRecord).all()
        
        # Simple allocation logic (will be enhanced in next step)
        total_capital = budget_req.total_capital
        
        # Default Moroccan student budget allocation
        allocations = {
            "rent": total_capital * 0.35,
            "food": total_capital * 0.25,
            "utilities": total_capital * 0.10,
            "transportation": total_capital * 0.10,
            "education": total_capital * 0.10,
            "leisure": total_capital * 0.05,
            "savings": total_capital * 0.05
        }
        
        # Adjust based on priority
        if budget_req.priority == "leisure":
            allocations["leisure"] = total_capital * 0.15
            allocations["savings"] = total_capital * 0.02
        elif budget_req.priority == "savings":
            allocations["savings"] = total_capital * 0.15
            allocations["leisure"] = total_capital * 0.02
        
        # Get market prices for food recommendation
        food_prices = db.query(PriceRecord).filter(
            PriceRecord.source.in_(["Marjane", "Carrefour", "Jumia Food"])
        ).all()
        
        market_prices_dict = {}
        if food_prices:
            for record in food_prices:
                if record.product_name not in market_prices_dict:
                    market_prices_dict[record.product_name] = []
                market_prices_dict[record.product_name].append(record.price)
        
        response = BudgetResponse(
            total_capital=total_capital,
            priority=budget_req.priority,
            allocations=allocations,
            market_prices={k: round(sum(v) / len(v), 2) for k, v in market_prices_dict.items()},
            recommendations=[
                "Focus on bulk buying for staple foods to reduce costs",
                "Use student discounts at Marjane and Carrefour",
                "Check prices across multiple supermarkets before buying",
                "Track your expenses weekly to stay within budget"
            ]
        )
        
        return response
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/budgets/{user_id}")
def get_user_budget(user_id: str, db: Session = Depends(get_db)):
    """Get user's budget history"""
    try:
        budgets = db.query(BudgetRecord).filter(
            BudgetRecord.user_id == user_id
        ).order_by(BudgetRecord.created_date.desc()).all()
        
        return {"user_id": user_id, "budgets_count": len(budgets), "budgets": budgets}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Error Handlers ====================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    return {
        "error": str(exc),
        "status": "error"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
