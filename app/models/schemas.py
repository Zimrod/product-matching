from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class TelegramMessage(BaseModel):
    text: str
    sender_id: Optional[int] = None
    sender_username: Optional[str] = None
    chat_id: Optional[int] = None
    chat_title: Optional[str] = None
    message_id: Optional[int] = None
    media_urls: List[str] = []

class RawMessageCreate(BaseModel):
    raw_text: str
    sender_id: Optional[int] = None
    sender_username: Optional[str] = None
    chat_id: Optional[int] = None
    chat_title: Optional[str] = None
    message_id: Optional[int] = None
    media_urls: List[str] = []
    extracted_data: Dict[str, Any] = {}

class MessageResponse(BaseModel):
    id: str
    raw_text: str
    chat_title: Optional[str] = None
    created_at: datetime
    processed: bool