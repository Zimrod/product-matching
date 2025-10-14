import logging
from typing import List, Dict, Any, Optional
import httpx
import os
from datetime import datetime
from config import Config  # Import your config

logger = logging.getLogger(__name__)

# Use environment variables from config
SUPABASE_URL = Config.SUPABASE_URL
SUPABASE_KEY = Config.SUPABASE_KEY

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation" 
}


class MatchingService:
    def __init__(self):
        self.base_url = f"{SUPABASE_URL}/rest/v1"

    async def _get(self, table: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        url = f"{SUPABASE_URL}/rest/v1/{table}"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Accept": "application/json"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()

    async def _insert(self, table: str, data: Any) -> List[Dict[str, Any]]:
        """Generic INSERT request"""
        async with httpx.AsyncClient() as client:
            try:
                headers = {
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                }
                
                url = f"{self.base_url}/{table}"
                
                print("🔍 DEBUG _insert:")
                print(f"  URL: {url}")
                print(f"  Headers: {headers}")
                print(f"  Data: {data}")
                
                response = await client.post(
                    url,
                    headers=headers,
                    json=data,
                )
                
                print(f"🔍 DEBUG Response:")
                print(f"  Status: {response.status_code}")
                print(f"  Content: {response.text}")
                
                response.raise_for_status()
                result = response.json()
                print(f"✅ SUCCESS: {result}")
                return result
                
            except Exception as e:
                print(f"❌ Error: {str(e)}")
                raise

    async def find_matches_for_listing(self, listing_id: str) -> List[Dict[str, Any]]:
        """Find all buyer matches for a given listing"""
        try:
            print(f"🔍 DEBUG: Looking for listing ID: {listing_id}")
            print(f"🔍 DEBUG: Query params: {{'id': 'eq.{listing_id}'}}")
            
            listings = await self._get("listings", {"id": f"eq.{listing_id}"})
            
            print(f"🔍 DEBUG: Found {len(listings)} listings")
            for listing in listings:
                print(f"🔍 DEBUG: Listing ID: {listing.get('id')}")
            
            if not listings:
                logger.error(f"Listing {listing_id} not found")
                return []

            listing = listings[0]
            logger.info(f"Processing listing: {listing['product_data'].get('make')} {listing['product_data'].get('model')}")

            buyers = await self._get("buyers", {"select": "*"})
            matches = []

            for buyer in buyers:
                if self._is_match(listing, buyer):
                    match = self._create_match_record(listing, [buyer])
                    matches.append(match)

            if matches:
                await self._insert("matches", matches)
                logger.info(f"Created {len(matches)} matches for listing {listing_id}")

            return matches

        except Exception as e:
            logger.error(f"Error finding matches for listing {listing_id}: {str(e)}")
            return []

    def _is_match(self, listing: Dict[str, Any], buyer: Dict[str, Any]) -> bool:
        """Check if a listing matches buyer preferences"""
        try:
            preferences = buyer.get("preferences", {})
            product_data = listing.get("product_data", {})

            listing_make = str(product_data.get("make", "")).lower()
            listing_model = str(product_data.get("model", "")).lower()
            listing_price = float(product_data.get("price", 0))
            listing_year = product_data.get("year")

            buyer_makes = self._get_preference_values(preferences, "make")
            buyer_models = self._get_preference_values(preferences, "model")
            min_price = float(preferences.get("min_price", 0))
            max_price = float(preferences.get("max_price", float("inf")))
            min_year = preferences.get("min_year")

            if not listing_make or not listing_model or not listing_price:
                return False

            if buyer_makes and listing_make not in [m.lower() for m in buyer_makes]:
                return False

            if buyer_models and listing_model not in [m.lower() for m in buyer_models]:
                return False

            if not (min_price <= listing_price <= max_price):
                return False

            if min_year and listing_year and listing_year < min_year:
                return False

            logger.debug(f"Match found for buyer {buyer.get('name')} and listing {listing_make} {listing_model}")
            return True

        except Exception as e:
            logger.error(f"Error in match logic for buyer {buyer.get('name')}: {str(e)}")
            return False

    def _get_preference_values(self, preferences: Dict[str, Any], field: str) -> List[str]:
        """Extract values from preferences field, handling both arrays and scalar values"""
        value = preferences.get(field)
        if isinstance(value, list):
            return value
        elif value:
            return [value]
        else:
            return []

    def _create_match_record(self, listing: Dict[str, Any], buyers: Any) -> Dict[str, Any]:
        """Create a match record with one or multiple buyers"""
        if isinstance(buyers, dict):
            buyers = [buyers]
        
        buyer_data = []
        for buyer in buyers:
            buyer_data.append({
                "id": buyer["id"],
                "name": buyer["name"],
                "cell_number": buyer["cell_number"],
                "chat_id": buyer.get("chat_id")
            })
        
        return {
            "listing_id": listing["id"],
            "buyers": buyer_data,
            "product_data": listing["product_data"],
            "seller_id": listing.get("telegram_sender_id"),
            "seller_name": listing.get("seller_name", ""),
            "seller_contact": listing.get("seller_contact", ""),
            "matched_at": datetime.utcnow().isoformat(),
            "notified": False,
        }
    
    async def process_listing_and_match(self, listing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Complete workflow: create listing and find matches"""
        try:
            listing_insert = await self._insert("listings", listing_data)
            if not listing_insert:
                return {"success": False, "error": "Failed to create listing"}

            listing = listing_insert[0]
            matches = await self.find_matches_for_listing(listing["id"])

            return {
                "success": True,
                "listing": listing,
                "matches": matches,
                "match_count": len(matches),
            }

        except Exception as e:
            logger.error(f"Error in process_listing_and_match: {str(e)}")
            return {"success": False, "error": str(e)}
        
    async def get_existing_matches(self, listing_id: str = None, notified: bool = None) -> List[Dict[str, Any]]:
        """Get existing matches from the database (READ operation)"""
        try:
            params = {"select": "*"}
            
            if listing_id:
                params["listing_id"] = f"eq.{listing_id}"
            if notified is not None:
                params["notified"] = f"eq.{'true' if notified else 'false'}"
                
            matches = await self._get("matches", params)
            logger.info(f"Retrieved {len(matches)} existing matches from database")
            return matches
            
        except Exception as e:
            logger.error(f"Error fetching matches: {str(e)}")
            return []
        
    async def debug_insert(self):
        """Debug method to test basic insert"""
        try:
            test_data = {
                "category": "vehicles",  # Changed from "cars" to "vehicles"
                "product_data": {
                    "make": "Test",
                    "model": "Test Model",
                    "price": 1000
                }
            }
            
            print(f"🔍 DEBUG: Testing insert with data: {test_data}")
            print(f"🔍 DEBUG: Headers: {HEADERS}")
            print(f"🔍 DEBUG: URL: {self.base_url}/listings")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/listings",
                    headers=HEADERS,
                    json=test_data,
                )
                
                print(f"🔍 DEBUG: Response status: {response.status_code}")
                print(f"🔍 DEBUG: Response text: {response.text}")
                
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            print(f"❌ DEBUG ERROR: {str(e)}")
            raise

# Create singleton instance
matching_service = MatchingService()