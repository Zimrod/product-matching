import os
import asyncio
import time
import aiohttp
import json
from telethon import TelegramClient, events
from config import Config  # Import your config

class TelegramMonitor:
    def __init__(self):
        # Use environment variables from config
        self.api_id = int(Config.API_ID)  # Convert to int
        self.api_hash = Config.API_HASH
        
        self.client = None
        self.is_running = False
        self._monitor_task = None
        self._message_count = 0
        self._last_message_id = 0
        
        # Single group ID (you might want to move this to .env too)
        self.seller_group_id = Config.TELEGRAM_AUTOMOTA
        
        # Your n8n webhook URL (from the activated workflow)
        self.n8n_webhook_url = "https://specify.app.n8n.cloud/webhook/telegram-messages"
        
        print(f"🔧 TelegramMonitor initialized with API_ID: {self.api_id}")
    
    async def start(self):
        """Start the Telegram monitor"""
        if self.is_running:
            print("⚠️ Telegram monitor is already running")
            return True
            
        try:
            print("🔄 Starting Telegram monitor...")
            
            # Create client
            self.client = TelegramClient(
                "telegram_session",
                self.api_id, 
                self.api_hash
            )
            
            print("🔐 Connecting to Telegram...")
            await self.client.start()
            
            # Verify connection
            me = await self.client.get_me()
            print(f"✅ Connected as: {me.first_name}")
            
            # Verify group access
            try:
                group = await self.client.get_entity(self.seller_group_id)
                group_name = getattr(group, 'title', 'Unknown')
                print(f"🎯 Monitoring: {group_name}")
                
                # Get the last message ID to only process new messages
                async for message in self.client.iter_messages(group, limit=1):
                    self._last_message_id = message.id
                    print(f"📝 Last message ID in group: {self._last_message_id}")
                    
            except Exception as e:
                print(f"❌ Cannot access group: {e}")
                return False
            
            # Set up message handler for NEW messages only
            @self.client.on(events.NewMessage(chats=[self.seller_group_id]))
            async def handler(event):
                if event.message.id > self._last_message_id:
                    await self._handle_message(event)
                    self._last_message_id = event.message.id
                else:
                    print(f"⏩ Skipping old message ID: {event.message.id}")
            
            self.is_running = True
            self._message_count = 0
            
            print("👂 Listening for NEW messages only...")
            
            # Start the monitoring in background
            self._monitor_task = asyncio.create_task(self._keep_alive())
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to start Telegram monitor: {e}")
            self.is_running = False
            return False
    
    async def _keep_alive(self):
        """Keep the Telegram client running"""
        try:
            print("🚀 Telegram monitor running and waiting for new messages...")
            await self.client.run_until_disconnected()
        except Exception as e:
            print(f"🔴 Telegram client disconnected: {e}")
        finally:
            self.is_running = False
            print("🛑 Telegram monitor stopped")
    
    async def _handle_message(self, event):
        """Handle incoming messages and send to n8n"""
        try:
            self._message_count += 1
            sender = await event.get_sender()
            chat = await event.get_chat()
            
            message_text = event.message.text or ""
            preview = message_text[:100] + "..." if len(message_text) > 100 else message_text
            
            print(f"📨 NEW MESSAGE #{self._message_count} at {time.strftime('%H:%M:%S')}")
            print(f"   From: {chat.title}")
            print(f"   Sender: {sender.first_name} (ID: {sender.id})")
            print(f"   Message: {preview}")
            print(f"   Message ID: {event.message.id}")
            
            # Send to n8n for processing and storage
            success = await self._send_to_n8n(event, sender, chat, message_text)
            
            if success:
                print(f"   ✅ Sent to n8n → Supabase")
            else:
                print(f"   ❌ Failed to send to n8n")
            
            print("   " + "-" * 40)
            
        except Exception as e:
            print(f"❌ Error processing message: {e}")
    
    async def _send_to_n8n(self, event, sender, chat, message_text):
        """Send message data to n8n webhook"""
        try:
            message_data = {
                "raw_text": message_text,
                "sender_id": sender.id,
                "sender_username": getattr(sender, 'username', None),
                "sender_name": sender.first_name,
                "chat_id": chat.id,
                "chat_title": getattr(chat, 'title', 'Unknown'),
                "message_id": event.message.id,
                "timestamp": time.time(),
                "extracted_data": self._extract_product_data(message_text)
            }
            
            print(f"   📤 Sending to n8n (direct JSON, no wrapper)...")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.n8n_webhook_url, 
                    json=message_data,
                    timeout=10
                ) as response:
                    
                    response_text = await response.text()
                    
                    if response.status in [200, 201]:
                        print(f"   ✅ n8n response: {response.status}")
                        return True
                    else:
                        print(f"   ❌ n8n error {response.status}: {response_text}")
                        return False
                        
        except asyncio.TimeoutError:
            print("   ⏰ n8n request timeout")
            return False
        except Exception as e:
            print(f"   ❌ n8n error: {e}")
            return False
    
    def _extract_product_data(self, text):
        """Extract product information from message text"""
        text_lower = text.lower()
        
        extracted = {
            "has_price": any(word in text_lower for word in ["aed", "dhs", "dh", "price", "cost"]),
            "has_contact": any(word in text_lower for word in ["contact", "call", "whatsapp", "phone", "dm"]),
            "has_car_terms": any(term in text_lower for term in ["car", "vehicle", "auto", "bmw", "mercedes", "toyota"]),
            "word_count": len(text.split()),
            "message_length": len(text)
        }
        
        return extracted
    
    async def stop(self):
        """Stop the Telegram monitor"""
        print("🛑 Stopping Telegram monitor...")
        self.is_running = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        if self.client and self.client.is_connected():
            await self.client.disconnect()
        
        print("✅ Telegram monitor stopped")