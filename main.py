# main.py
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from api_handlers import EcommerceAPIHandler
import asyncio
from enum import Enum
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="E-commerce Trend Analyzer API",
    description="API for analyzing e-commerce trends across multiple platforms",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define enums for validation
class Platform(str, Enum):
    AMAZON = "amazon"
    EBAY = "ebay"
    GOOGLE = "google"

class TimeFrame(str, Enum):
    LAST_HOUR = "now 1-H"
    LAST_DAY = "now 1-d"
    LAST_WEEK = "now 7-d"
    LAST_MONTH = "today 1-m"
    LAST_3_MONTHS = "today 3-m"
    LAST_12_MONTHS = "today 12-m"
    LAST_5_YEARS = "today 5-y"

# Request models
class TrendRequest(BaseModel):
    platform: Platform
    country: str = Field(..., min_length=2, max_length=56)
    keyword: str = Field(..., min_length=1, max_length=100)
    timeframe: Optional[TimeFrame] = Field(default=TimeFrame.LAST_3_MONTHS)
    
    class Config:
        schema_extra = {
            "example": {
                "platform": "amazon",
                "country": "United States",
                "keyword": "wireless headphones",
                "timeframe": "today 3-m"
            }
        }

# Response models
class PriceRange(BaseModel):
    min: float
    max: float

class TrendData(BaseModel):
    platform: str
    country: str
    keyword: str
    timestamp: str
    trend_data: Dict[str, Any]
    price_range: Optional[PriceRange]
    search_volume: Optional[int]
    market_sentiment: Optional[float]
    error: Optional[str] = None

# API handler instance
api_handler = EcommerceAPIHandler()

# Dependency for rate limiting (implement if needed)
async def check_rate_limit():
    # Implement rate limiting logic here
    pass

# Helper function to calculate market sentiment
def calculate_market_sentiment(trend_data: Dict[str, Any], platform: str) -> float:
    try:
        if platform == Platform.AMAZON:
            # Calculate sentiment based on reviews and ratings
            review_metrics = trend_data.get("review_metrics", {})
            avg_rating = review_metrics.get("avg_rating", 0)
            return min(avg_rating / 5.0, 1.0)
        
        elif platform == Platform.EBAY:
            # Calculate sentiment based on price trends and condition distribution
            condition_dist = trend_data.get("condition_distribution", {})
            new_percentage = condition_dist.get("New", 0)
            return min(new_percentage / 100.0, 1.0)
        
        elif platform == Platform.GOOGLE:
            # Calculate sentiment based on interest over time
            trend_summary = trend_data.get("trend_summary", {})
            avg_interest = trend_summary.get("average_interest", 0)
            return min(avg_interest / 100.0, 1.0)
        
        return 0.5  # Default neutral sentiment
    
    except Exception:
        return 0.5

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "E-commerce Trend Analyzer API",
        "version": "1.0.0",
        "endpoints": [
            "/trends/",
            "/health/"
        ]
    }

@app.get("/health/")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

@app.post("/trends/", response_model=TrendData)
async def get_trends(
    request: TrendRequest,
    rate_limit: None = Depends(check_rate_limit)
):
    """
    Get trend data for a specific platform and keyword
    """
    try:
        logger.info(f"Processing trend request for {request.platform} - {request.keyword}")
        
        # Get the appropriate handler method
        handlers = {
            Platform.AMAZON: api_handler.fetch_amazon_trends,
            Platform.EBAY: api_handler.fetch_ebay_trends,
            Platform.GOOGLE: api_handler.fetch_google_trends,
        }
        
        handler = handlers.get(request.platform)
        if not handler:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported platform: {request.platform}"
            )

        # Fetch trend data
        if request.platform == Platform.GOOGLE:
            trend_data = await handler(
                request.keyword,
                request.country,
                request.timeframe
            )
        else:
            trend_data = await handler(
                request.keyword,
                request.country
            )

        # Calculate market sentiment
        market_sentiment = calculate_market_sentiment(trend_data, request.platform)

        # Prepare response
        response = TrendData(
            platform=request.platform,
            country=request.country,
            keyword=request.keyword,
            timestamp=datetime.now().isoformat(),
            trend_data=trend_data,
            price_range=PriceRange(
                min=trend_data.get("price_range", {}).get("min", 0),
                max=trend_data.get("price_range", {}).get("max", 0)
            ) if "price_range" in trend_data else None,
            search_volume=trend_data.get("total_products", 0),
            market_sentiment=market_sentiment
        )

        logger.info(f"Successfully processed trend request for {request.platform}")
        return response

    except Exception as e:
        logger.error(f"Error processing trend request: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing request: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Enable auto-reload during development
        log_level="info"
    )