# sample.py
import asyncio
import httpx
import json
from pprint import pprint

async def test_api():
    async with httpx.AsyncClient() as client:
        # Test different platforms
        test_cases = [
            {
                "platform": "google",
                "country": "United States",
                "keyword": "smart watch",
                "timeframe": "today 3-m"
            },
            {
                "platform": "amazon",
                "country": "United States",
                "keyword": "smart watch"
            },
            {
                "platform": "ebay",
                "country": "United Kingdom",
                "keyword": "smart watch"
            },
            {
                "platform": "etsy",
                "country": "Canada",
                "keyword": "handmade jewelry"
            }
        ]

        for test_case in test_cases:
            try:
                response = await client.post(
                    "http://localhost:8000/trends/",
                    json=test_case
                )
                print(f"\nTesting {test_case['platform'].upper()} API:")
                print("Status Code:", response.status_code)
                if response.status_code == 200:
                    pprint(response.json())
                else:
                    print("Error:", response.text)
            except Exception as e:
                print(f"Error testing {test_case['platform']}: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_api())