"""
SQLAlchemy Models for the database.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class PriceRecord(Base):
    """Model to store scraped price data"""
    __tablename__ = "price_records"
    
    id = Column(Integer, primary_key=True, index=True)
    product_name = Column(String(255), index=True, nullable=False)
    price = Column(Float, nullable=False)
    currency = Column(String(10), default="MAD")
    unit = Column(String(50), default="piece")
    source = Column(String(100), nullable=False, index=True)
    product_url = Column(Text, nullable=True)
    scrape_date = Column(DateTime, default=datetime.now, nullable=False, index=True)
    
    def __repr__(self):
        return f"<PriceRecord(product={self.product_name}, price={self.price} {self.currency}, source={self.source})>"


class BudgetRecord(Base):
    """Model to store user budget records and calculations"""
    __tablename__ = "budget_records"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    total_capital = Column(Float, nullable=False)
    priority = Column(String(50), default="balanced")  # "leisure", "savings", "balanced"
    result_json = Column(Text, nullable=True)  # Store the budget breakdown as JSON
    created_date = Column(DateTime, default=datetime.now, nullable=False, index=True)
    
    def __repr__(self):
        return f"<BudgetRecord(user={self.user_id}, capital={self.total_capital})>"
