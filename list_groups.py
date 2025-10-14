import asyncio
import os
from telethon import TelegramClient

# Your credentials
API_ID = 25449162  # Your API ID
API_HASH = "b0263ef40b8f973345b6ce0ed2888c21"  # Your API hash

async def main():
    print("🔍 Getting your group IDs and member info...")
    
    client = TelegramClient("telegram_session", API_ID, API_HASH)
    
    try:
        await client.start()
        print("✅ Connected to Telegram")
        
        me = await client.get_me()
        print(f"🤖 Logged in as: {me.first_name}")
        
        print("\n📋 Your Groups:")
        print("-" * 50)
        
        groups_found = []
        
        async for dialog in client.iter_dialogs():
            if dialog.is_group:
                groups_found.append({
                    'name': dialog.name,
                    'id': dialog.id,
                    'participants': getattr(dialog.entity, 'participants_count', 'Unknown')
                })
                print(f"🏠 Group: {dialog.name}")
                print(f"   ID: {dialog.id}")
                print(f"   Members: {getattr(dialog.entity, 'participants_count', 'Unknown')}")
                print()
        
        print("🎯 Add these IDs to your telegram_monitor.py:")
        print("self.seller_groups = [")
        for group in groups_found:
            print(f"    {group['id']},  # {group['name']}")
        print("]")
        
        # Get member information for a specific group
        if groups_found:
            print("\n👥 Getting member information for first group...")
            first_group = groups_found[0]
            
            try:
                # Get the group entity
                group_entity = await client.get_entity(first_group['id'])
                
                print(f"\n📊 Members of '{first_group['name']}':")
                print("-" * 50)
                
                member_count = 0
                async for user in client.iter_participants(group_entity, limit=20):  # Limit to first 20 members
                    member_count += 1
                    print(f"👤 Member {member_count}:")
                    print(f"   Name: {user.first_name} {user.last_name or ''}".strip())
                    print(f"   Username: @{user.username}" if user.username else "   Username: Not set")
                    print(f"   User ID: {user.id}")
                    print(f"   Is Bot: {user.bot}")
                    print(f"   Premium: {user.premium}")
                    print(f"   Last Seen: {user.status}")
                    print("   ---")
                    
                    if member_count >= 20:  # Stop after 20 members to avoid too much output
                        print("   ... (showing first 20 members only)")
                        break
                        
            except Exception as e:
                print(f"❌ Error getting members: {e}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())