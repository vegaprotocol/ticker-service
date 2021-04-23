from typing import List, Literal, Optional, Set
from pydantic.main import BaseModel
from requests import get
from datetime import datetime


import cachetools
from pydantic import BaseSettings

from candles import *
import news_market_data
import news_markets
import news_proposals


class Config(BaseSettings):
	node_url: str
	market_cache_ttl: int
	history_cache_ttl: int
	news_cache_ttl: int
	stats_cache_ttl: int
	cache_size: int
	exclude_market_states: Set[str] 
	change_duration: int
	history_granularity: str
	history_step: int
	heartbeat_time: float

	@property
	def change_interval(self):
		return sorted([x for x in INTERVAL.items() if x[1] <= self.change_duration], key=lambda x: x[1])[-1][0]

config = Config(_env_file='.env')


def cached(ttl):
	def _cached(f):
		return cachetools.cached(cache=cachetools.TTLCache(config.cache_size, ttl))(f)
	return _cached


class API:
	MARKETS = (config.node_url + '/markets').format
	MARKET_DATA = (config.node_url + '/markets-data/{market_id}').format
	STATS = (config.node_url + '/statistics').format


class PriceData(BaseModel):
	datetime: datetime
	open: float
	high: float
	low: float
	close: float
	volume: int
	change: float
	action: Literal['gainer', 'loser', 'no change']


class TickerEntry(BaseModel):
	id: str
	code: str
	name: str
	status: str
	price_data: Optional[PriceData]
	history: Optional[List[float]]


class TickerService:
	@property
	def market_lookup(self):
		all_markets = get(API.MARKETS()).json()['markets']
		return { m['id']:m for m in all_markets if m['state'] not in config.exclude_market_states }

	@cached(config.market_cache_ttl)
	def price_data_for_market(self, market_id):
		c = candles(
			node_url=config.node_url,
			market_id=market_id, 
			duration=config.change_duration, 
			granularity=config.change_interval, 
			decimals=int(self.market_lookup[market_id]['decimalPlaces']))
		return c and enrich_candle(zip_candles(c)[0])

	@cached(config.history_cache_ttl)
	def price_history(self, market_id):
		return [x['close'] for x in 
				zip_candles(
					candles(
							node_url=config.node_url,
							market_id=market_id, 
							duration=config.change_duration, 
							granularity=config.history_granularity,
							decimals=int(self.market_lookup[market_id]['decimalPlaces'])), 
					step=config.history_step)]

	@cached(config.market_cache_ttl)
	def ticker(self, history=True):
		return [x for x in [self.ticker_entry(market_id=id, history=history) for id in self.market_lookup.keys()] if x['price_data']]

	@cached(config.market_cache_ttl)
	def ticker_entry(self, market_id: str, history=True) -> TickerEntry:
		market = self.market_lookup.get(market_id, None)
		return market and {
			'id': market['id'],
			'code': market['tradableInstrument']['instrument']['code'],
			'name': market['tradableInstrument']['instrument']['name'],
      'status': market['state'],
			'price_data': self.price_data_for_market(market_id=market_id),
			**({ 'history': self.price_history(market_id=market_id) } if history else {})
		}

	@cached(config.market_cache_ttl)
	def markets(self):
		return list(self.market_lookup.values())

	@cached(config.stats_cache_ttl)
	def stats(self):
		return get(API.STATS()).json()['statistics']	

	@cached(config.news_cache_ttl)
	def news(self):		
		sources = [news_market_data, news_markets, news_proposals]
		news = []
		for source in sources:
			news.extend(source.get_news(config.node_url))
		return sorted(news, key=lambda x: x.timestamp)
	