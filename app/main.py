from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.services.matching_service import matching_service
from config import Config
import asyncio
import os
import time
import httpx 

from app.services.telegram_monitor import TelegramMonitor

# Global telegram monitor instance
telegram_monitor = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global telegram_monitor
    
    print("🚀 Starting Message Processing Service...")
    
    try:
        # Re-enable Telegram monitor
        from app.services.telegram_monitor import TelegramMonitor
        telegram_monitor = TelegramMonitor()
        print("✅ Telegram monitor initialized")
        
        # Auto-start the Telegram monitor
        print("🔄 Auto-starting Telegram monitor...")
        asyncio.create_task(telegram_monitor.start())
        
    except Exception as e:
        print(f"❌ Failed to initialize Telegram monitor: {e}")
        telegram_monitor = None
    
    yield
    
    # Shutdown
    print("🛑 Shutting down Message Processing Service...")
    if telegram_monitor and telegram_monitor.is_running:
        print("🛑 Stopping Telegram monitor...")
        await telegram_monitor.stop()

app = FastAPI(
    title="Message Processing Service",
    description="Filter and forward messages to buyers",
    debug=Config.ENVIRONMENT == "development",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/")
async def root():
    return {
        "message": "App is running",
        "environment": Config.ENVIRONMENT,
        "supabase_configured": bool(Config.SUPABASE_URL)
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    try:
        telegram_status = "not_initialized"
        
        if telegram_monitor:
            # Check if the monitor has the get_status method
            if hasattr(telegram_monitor, 'get_status'):
                try:
                    status = telegram_monitor.get_status()
                    telegram_status = "running" if status.get("is_running") else "stopped"
                except Exception as e:
                    telegram_status = f"error: {str(e)}"
            else:
                # If no get_status method, check for is_running attribute
                if hasattr(telegram_monitor, 'is_running'):
                    telegram_status = "running" if telegram_monitor.is_running else "stopped"
                else:
                    telegram_status = "initialized (no status method)"
        
        return {
            "status": "healthy", 
            "service": "message-processor",
            "telegram_monitor": telegram_status,
            "environment": Config.ENVIRONMENT
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@app.post("/telegram/start")
async def start_telegram_monitor():
    """Start the Telegram monitor"""
    if not telegram_monitor:
        return {"status": "error", "message": "Telegram monitor not initialized"}
    
    if not telegram_monitor.is_running:
        asyncio.create_task(telegram_monitor.start())
        return {"status": "started", "message": "Telegram monitor starting..."}
    return {"status": "already_running", "message": "Telegram monitor is already running"}

@app.post("/telegram/stop")
async def stop_telegram_monitor():
    """Stop the Telegram monitor"""
    if telegram_monitor and telegram_monitor.is_running:
        await telegram_monitor.stop()
        return {"status": "stopped", "message": "Telegram monitor stopped"}
    return {"status": "not_running", "message": "Telegram monitor is not running"}

@app.post("/telegram/health-check")
async def health_check():
    """Endpoint for N8N to ping and keep monitor active"""
    if telegram_monitor and telegram_monitor.is_running:
        # Force message processing
        return {
            "status": "active", 
            "message_count": telegram_monitor._message_count,
            "timestamp": time.time()
        }
    else:
        # Try to restart if not running
        asyncio.create_task(telegram_monitor.start())
        return {"status": "restarting", "message": "Monitor was stopped, restarting..."}

@app.post("/process-listing")
async def process_listing(listing_data: dict):
    """Create listing + find matches + return matches"""
    return await matching_service.process_listing_and_match(listing_data)
    
@app.post("/debug-insert")
async def debug_insert():
    """Debug endpoint to test basic insert"""
    return await matching_service.debug_insert()

@app.get("/matches/{listing_id}")
async def get_matches(listing_id: str):
    """Get EXISTING matches for a listing from the database"""
    matches = await matching_service.get_existing_matches(listing_id=listing_id)
    return {"matches": matches}

@app.get("/unnotified-matches")
async def get_unnotified_matches():
    """Get all matches that haven't been notified yet"""
    matches = await matching_service.get_existing_matches(notified=False)
    return {
        "success": True,
        "matches": matches,
        "count": len(matches)
    }

@app.get("/test-connection")
async def test_connection():
    """Test endpoint to verify Supabase connection"""
    try:
        # Test buyers table
        buyers = await matching_service._get("buyers", {"select": "count", "limit": "1"})
        
        return {
            "status": "connected",
            "supabase_url": matching_service.base_url,
            "buyers_count": len(buyers),
            "message": "Supabase connection successful"
        }
    except Exception as e:
        return {
            "status": "error", 
            "error": str(e),
            "supabase_url": matching_service.base_url
        }

@app.post("/trigger-matching/{listing_id}")
async def trigger_matching(listing_id: str):
    """Trigger matching for an existing listing"""
    matches = await matching_service.find_matches_for_listing(listing_id)
    return {
        "success": True,
        "listing_id": listing_id,
        "matches": matches,
        "match_count": len(matches),
    }

@app.post("/create-test-buyer")
async def create_test_buyer():
    """Create a test buyer that matches Toyota Camry"""
    test_buyer = {
        "name": "Test Buyer",
        "cell_number": "+1234567890",
        "preferences": {
            "make": ["toyota", "honda"],
            "model": ["camry", "accord"],
            "min_price": 10000,
            "max_price": 20000,
            "min_year": 2018
        }
    }
    
    try:
        result = await matching_service._insert("buyers", test_buyer)
        return {"success": True, "buyer": result[0] if result else None}
    except Exception as e:
        return {"success": False, "error": str(e)}
    
@app.get("/listings")
async def get_all_listings():
    """Get all listings to verify IDs"""
    try:
        listings = await matching_service._get("listings", {"select": "id,category,product_data", "order": "extracted_at.desc"})
        return {
            "success": True,
            "count": len(listings),
            "listings": listings
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/test-listing-query/{listing_id}")
async def test_listing_query(listing_id: str):
    """Test direct listing query"""
    try:
        # Test the exact same query your matching service uses
        params = {"id": f"eq.{listing_id}"}
        print(f"🔍 Testing query with params: {params}")
        
        listings = await matching_service._get("listings", params)
        
        return {
            "success": True,
            "listing_id": listing_id,
            "found": len(listings) > 0,
            "listings": listings,
            "query_params": params
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/test-telegram-webhook")
async def test_telegram_webhook(payload: dict):
    """Test endpoint that simulates the exact format telegram_monitor sends"""
    try:
        # This should match what your telegram_monitor._send_to_n8n() sends
        message_data = {
            "raw_text": payload.get("raw_text", "Test message"),
            "sender_id": payload.get("sender_id", 123456789),
            "sender_username": payload.get("sender_username"),
            "sender_name": payload.get("sender_name", "TestUser"),
            "chat_id": payload.get("chat_id", -4846687198),
            "chat_title": payload.get("chat_title", "Test Group"),
            "message_id": payload.get("message_id", int(time.time())),
            "timestamp": payload.get("timestamp", time.time()),
            "extracted_data": {
                "has_price": payload.get("has_price", False),
                "has_contact": payload.get("has_contact", False),
                "has_car_terms": payload.get("has_car_terms", True),
                "word_count": payload.get("word_count", 0),
                "message_length": payload.get("message_length", 0)
            }
        }
        
        # Forward to your n8n webhook
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://specify.app.n8n.cloud/webhook/telegram-messages",
                json=message_data  # Send the correct format
            )
            
        return {
            "success": True,
            "sent_to_n8n": response.status_code == 200,
            "test_payload": message_data
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}