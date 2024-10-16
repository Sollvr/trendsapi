# api_handlers.py
from typing import Dict, Any
import requests
from amazon_paapi import AmazonAPI
from ebaysdk.finding import Connection as Finding
from etsy_py.api import EtsyAPI
from pytrends.request import TrendReq
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

class EcommerceAPIHandler:
    def __init__(self):
        # Initialize Amazon API
        self.amazon = AmazonAPI(
            os.getenv('AMAZON_ACCESS_KEY'),
            os.getenv('AMAZON_SECRET_KEY'),
            os.getenv('AMAZON_PARTNER_TAG'),
            country=os.getenv('AMAZON_REGION', 'US')
        )

        # Initialize eBay API
        self.ebay = Finding(
            domain=os.getenv('EBAY_DOMAIN', 'svcs.ebay.com'),
            appid=os.getenv('EBAY_APP_ID'),
            config_file=None
        )

        # Initialize Etsy API
        self.etsy = EtsyAPI(
            api_key=os.getenv('ETSY_API_KEY'),
            api_secret=os.getenv('ETSY_API_SECRET')
        )

        # Initialize Google Trends
        self.pytrends = TrendReq(hl='en-US')

    async def fetch_amazon_trends(self, keyword: str, country: str) -> dict:
        """
        Fetch real Amazon trend data using Amazon's Product Advertising API
        """
        try:
            # Search for items
            items = self.amazon.search_items(keywords=keyword)

            prices = []
            total_reviews = 0
            total_rating = 0
            product_count = 0

            for item in items[:20]:  # Analyze top 20 products
                if item.offers:
                    prices.append(item.offers.listings[0].price.amount)
                if item.rating:
                    total_reviews += item.rating.count
                    total_rating += item.rating.value
                product_count += 1

            return {
                "avg_price": sum(prices) / len(prices) if prices else 0,
                "price_range": {
                    "min": min(prices) if prices else 0,
                    "max": max(prices) if prices else 0
                },
                "review_count": total_reviews,
                "avg_rating": total_rating / product_count if product_count > 0 else 0,
                "total_products": product_count
            }

        except Exception as e:
            raise Exception(f"Amazon API error: {str(e)}")

    async def fetch_ebay_trends(self, keyword: str, country: str) -> dict:
        """
        Fetch real eBay trend data using eBay Finding API
        """
        try:
            # Set up the search request
            search_request = {
                'keywords': keyword,
                'paginationInput': {'entriesPerPage': 100},
                'sortOrder': 'BestMatch'
            }

            # Add country filter if specified
            if country:
                search_request['itemFilter'] = [
                    {'name': 'LocatedIn', 'value': country}
                ]

            # Execute the search
            response = self.ebay.execute('findItemsAdvanced', search_request)
            results = response.reply.searchResult

            # Process active listings
            active_listings = int(results.totalEntries)
            prices = []
            
            # Get completed listings for sales data
            completed_request = search_request.copy()
            completed_request['itemFilter'] = [
                {'name': 'SoldItemsOnly', 'value': 'true'}
            ]
            completed_response = self.ebay.execute('findCompletedItems', completed_request)
            completed_results = completed_response.reply.searchResult

            # Calculate statistics
            for item in results.item:
                if hasattr(item, 'sellingStatus'):
                    price = float(item.sellingStatus.currentPrice.value)
                    prices.append(price)

            return {
                "active_listings": active_listings,
                "sold_last_month": len(completed_results.item) if hasattr(completed_results, 'item') else 0,
                "avg_price": sum(prices) / len(prices) if prices else 0,
                "price_range": {
                    "min": min(prices) if prices else 0,
                    "max": max(prices) if prices else 0
                },
                "total_results": len(results.item) if hasattr(results, 'item') else 0
            }

        except Exception as e:
            raise Exception(f"eBay API error: {str(e)}")

    async def fetch_etsy_trends(self, keyword: str, country: str) -> dict:
        """
        Fetch real Etsy trend data using Etsy API
        """
        try:
            # Search for active listings
            listings = self.etsy.findAllListings(
                keywords=keyword,
                limit=100,
                includes=['MainImage', 'Shop'],
                country=country if country else None
            )

            prices = []
            handmade_count = 0
            vintage_count = 0
            shop_locations = {'domestic': 0, 'international': 0}

            for listing in listings:
                prices.append(float(listing['price']))
                
                # Count handmade vs vintage
                if listing.get('is_handmade'):
                    handmade_count += 1
                if listing.get('is_vintage'):
                    vintage_count += 1
                
                # Track shop locations
                shop = listing.get('Shop', {})
                if shop.get('country_id') == country:
                    shop_locations['domestic'] += 1
                else:
                    shop_locations['international'] += 1

            total_listings = len(listings)
            
            return {
                "total_listings": total_listings,
                "avg_price": sum(prices) / len(prices) if prices else 0,
                "price_range": {
                    "min": min(prices) if prices else 0,
                    "max": max(prices) if prices else 0
                },
                "handmade_count": handmade_count,
                "vintage_count": vintage_count,
                "shop_location_distribution": {
                    "domestic": shop_locations['domestic'] / total_listings if total_listings > 0 else 0,
                    "international": shop_locations['international'] / total_listings if total_listings > 0 else 0
                }
            }

        except Exception as e:
            raise Exception(f"Etsy API error: {str(e)}")

    async def fetch_google_trends(self, keyword: str, country: str, timeframe: str) -> dict:
        """
        Fetch real Google Trends data using pytrends
        """
        try:
            country_code = {
                "united states": "US",
                "united kingdom": "GB",
                "canada": "CA",
                "australia": "AU",
                "germany": "DE",
                # Add more country mappings as needed
            }.get(country.lower(), "US")

            # Build the payload
            self.pytrends.build_payload(
                kw_list=[keyword],
                timeframe=timeframe,
                geo=country_code
            )

            # Get interest over time
            interest_data = self.pytrends.interest_over_time()
            
            # Get related queries
            related_queries = self.pytrends.related_queries()
            
            # Get related topics
            related_topics = self.pytrends.related_topics()

            return {
                "interest_over_time": {
                    "dates": interest_data.index.strftime('%Y-%m-%d').tolist(),
                    "values": interest_data[keyword].tolist()
                } if not interest_data.empty else {},
                "related_queries": {
                    "top": related_queries[keyword]['top'].to_dict('records') if related_queries[keyword]['top'] is not None else [],
                    "rising": related_queries[keyword]['rising'].to_dict('records') if related_queries[keyword]['rising'] is not None else []
                },
                "related_topics": {
                    "top": related_topics[keyword]['top'].to_dict('records') if related_topics[keyword]['top'] is not None else [],
                    "rising": related_topics[keyword]['rising'].to_dict('records') if related_topics[keyword]['rising'] is not None else []
                }
            }

        except Exception as e:
            raise Exception(f"Google Trends API error: {str(e)}")
