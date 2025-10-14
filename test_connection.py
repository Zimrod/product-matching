import asyncio
import sys
import os

# Add your app directory to path
sys.path.append(os.path.dirname(__file__))

from app.services.matching_service import matching_service

async def test_connection():
    print("🔌 Testing Supabase connection...")
    
    try:
        # Test 1: Check if we can fetch buyers
        print("📋 Testing buyers table...")
        buyers = await matching_service._get("buyers", {"select": "*", "limit": "1"})
        print(f"✅ Buyers table accessible. Found {len(buyers)} buyers")
        
        # Test 2: Check if we can fetch listings
        print("📋 Testing listings table...")
        listings = await matching_service._get("listings", {"select": "*", "limit": "1"})
        print(f"✅ Listings table accessible. Found {len(listings)} listings")
        
        # Test 3: Check if we can fetch matches
        print("📋 Testing matches table...")
        matches = await matching_service._get("matches", {"select": "*", "limit": "1"})
        print(f"✅ Matches table accessible. Found {len(matches)} matches")
        
        print("\n🎉 All connection tests passed!")
        
        # Show sample data
        if buyers:
            print(f"\n📊 Sample buyer: {buyers[0]['name']} - {buyers[0].get('preferences', {})}")
        
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        print(f"🔧 Debug info:")
        print(f"   URL: {matching_service.base_url}")
        print(f"   Headers: {matching_service.HEADERS}")

if __name__ == "__main__":
    asyncio.run(test_connection())