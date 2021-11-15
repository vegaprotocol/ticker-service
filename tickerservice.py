from news import NewsItem
from typing import List, Literal, Optional, Set
from pydantic.main import BaseModel
from requests import get
from datetime import datetime
from time import sleep
import threading

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
	news_min_items: int
	news_safe_age: int
	update_freq: float

	@property
	def change_interval(self):
		return sorted([x for x in INTERVAL.items() if x[1] <= self.change_duration], key=lambda x: x[1])[-1][0]

config = Config(_env_file='.env')


def cached(ttl):
	def _cached(f):
		return cachetools.cached(cache=cachetools.TTLCache(config.cache_size, ttl))(f)
	return _cached


class API:
	MARKETS = (config.node_url + '/datanode/rest/markets').format
	MARKET_DATA = (config.node_url + '/datanode/rest/markets-data/{market_id}').format
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
	def __init__(self):
		self._timestamp = None
		self._data_mutex = threading.Lock()
		self.update()
		update_thread = threading.Thread(target=self.update_periodically, args=())
		update_thread.daemon = True
		update_thread.start()

	def update_periodically(self):
		while True:
			sleep(config.update_freq)
			try:
				self.update()
			finally:
				pass

	def update(self):
		print(f'Started updating ticker data')

		try:
			all_markets = get(API.MARKETS()).json()['markets']
			market_lookup = { m['id']:m for m in all_markets if m['state'] not in config.exclude_market_states }
			price_details = { id:self._get_price_data(id, int(market_lookup[id]['decimalPlaces'])) for id in market_lookup.keys() }
			price_history = { id:self._get_price_history(id, int(market_lookup[id]['decimalPlaces'])) for id in market_lookup.keys() }
			news = self._get_news()
		except Exception as e:
			print(__file__ + '/update: an error occurred: ' + repr(e))
			return
                
		with self._data_mutex:
			self._all_markets = None
			self._market_lookup = None
			self._price_details = None
			self._price_history = None
			self._news = None
			self._all_markets = all_markets
			self._market_lookup = market_lookup
			self._price_details = price_details
			self._price_history = price_history
			self._news = news
			self._timestamp = datetime.now()
		print(f'Update complete: {len(self._all_markets)} markets, {len(self._news)} news items')

	def _get_price_data(self, market_id, decimals):
		c = candles(
			node_url=config.node_url,
			market_id=market_id, 
			duration=config.change_duration, 
			granularity=config.change_interval, 
			decimals=decimals)
		return c and enrich_candle(zip_candles(c)[0])
	
	def _get_price_history(self, market_id, decimals):
		return [x['close'] for x in 
				zip_candles(
					candles(
							node_url=config.node_url,
							market_id=market_id, 
							duration=config.change_duration, 
							granularity=config.history_granularity,
							decimals=decimals), 
					step=config.history_step)]

	def _get_news(self):		
		sources = [news_market_data, news_markets, news_proposals]
		news: List[NewsItem] = []
		now = datetime.now().timestamp()
		for source in sources:
			news.extend(source.get_news(config.node_url))
		news.sort(key=lambda x: x.timestamp)
		while len(news) > config.news_min_items and now - news[0].timestamp.timestamp() > config.news_safe_age:
			del news[0]
		return news

	@cached(config.market_cache_ttl)
	def ticker(self, history=True) -> List[TickerEntry]:
		with self._data_mutex:
			market_ids = self._market_lookup.keys()
		return [x for x in [self.ticker_entry(market_id=id, history=history) for id in market_ids] if x['price_data']]

	@cached(config.market_cache_ttl)
	def ticker_entry(self, market_id: str, history=True) -> TickerEntry:
		with self._data_mutex:
			market = self._market_lookup.get(market_id, None)
			print(__file__ + '/ticker_entry: got price details for ' + market_id + ': ' + repr(self._price_details[market_id]))
			return market and {
				'id': market['id'],
				'code': market['tradableInstrument']['instrument']['code'],
				'name': market['tradableInstrument']['instrument']['name'],
				'status': market['state'],
				'price_data': self._price_details[market_id],
				**({ 'history': self._price_history[market_id] } if history else {})
			}

	@cached(config.market_cache_ttl)
	def news(self) -> List[NewsItem]:
		with self._data_mutex:
			return self._news

	@cached(config.market_cache_ttl)
	def markets(self):
		with self._data_mutex:
			return list(self._market_lookup.values())

	@cached(config.stats_cache_ttl)
	def stats(self):
		try:
			return get(API.STATS()).json()['statistics']	
		except:
			return dict(error='Error getting stats (node may be down)')
