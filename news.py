
from datetime import datetime
from typing import  Optional
from pydantic.main import BaseModel
from enum import Enum


class ItemType(str, Enum):
	new_market = 'new_market'
	market_proposal = 'market_proposal'
	new_asset = 'new_asset'
	network_change = 'network_change'
	market_change = 'market_change'
	network_reset = 'network_reset'
	market_status = 'market_status'

class NewsItem(BaseModel):
	message: str
	timestamp: datetime
	type: ItemType
	subtype: Optional[str]
	url: Optional[str]