import os
from supabase import create_client
from app.models.schemas import RawMessageCreate
from config import Config

class DatabaseService:
    def __init__(self):
        try:
            # Get Supabase credentials from Config
            SUPABASE_URL = Config.SUPABASE_URL
            SUPABASE_KEY = Config.SUPABASE_KEY
            
            if not SUPABASE_URL or not SUPABASE_KEY:
                raise ValueError("Supabase credentials not found in environment variables")
            
            # Initialize with values from Config
            self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
            print("✅ DatabaseService initialized with environment variables")
            
            # Test connection
            test_response = self.supabase.table("raw_messages").select("count", count="exact").limit(1).execute()
            print(f"✅ Supabase connection test successful")
            
        except Exception as e:
            print(f"❌ DatabaseService initialization error: {e}")
            self.supabase = None
    
    async def store_raw_message(self, message: RawMessageCreate):
        if not self.supabase:
            print("❌ Database not initialized")
            return None
            
        try:
            response = self.supabase.table("raw_messages").insert({
                "raw_text": message.raw_text,
                "sender_id": message.sender_id,
                "sender_username": message.sender_username,
                "chat_id": message.chat_id,
                "chat_title": message.chat_title,
                "message_id": message.message_id,
                "media_urls": message.media_urls,
                "extracted_data": message.extracted_data,
                "processed": False
            }).execute()
            
            if response.data:
                print(f"✅ Message stored in database with ID: {response.data[0]['id']}")
                return response.data[0]
            else:
                print(f"❌ Failed to store message - no data returned")
                print(f"   Error: {response}")
                return None
                
        except Exception as e:
            print(f"❌ Database storage error: {e}")
            import traceback
            print(f"🔍 Full error: {traceback.format_exc()}")
            return None