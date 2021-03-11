from typing import List, Literal, Optional, Set
from pydantic.main import BaseModel
from requests import get
from datetime import datetime
from functools import partial

import cachetools
from pydantic import BaseSettings


INTERVAL = {
	'INTERVAL_I1M': 60,
	'INTERVAL_I5M': 300,
	'INTERVAL_I15M': 900,
	'INTERVAL_I1H': 3_600,
	'INTERVAL_I6H': 21_600,
	'INTERVAL_I1D': 86_400
}


class Config(BaseSettings):
	node_url: str
	market_cache_ttl: int
	history_cache_ttl: int
	cache_size: int
	exclude_market_states: Set[str] 
	change_duration: int
	history_granularity: str
	history_step: int
	
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
	MARKET_CANDLES = (config.node_url + '/markets/{market_id}/candles?since_timestamp={since_timestamp:.0f}&interval={interval}').format


PRICE_FLOAT_FIELDS = ['open', 'close', 'high', 'low']
PRICE_INT_FIELDS = ['volume']


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
	price_data: PriceData
	history: Optional[List[float]]


class TickerService:
	@property
	def market_lookup(self):
		all_markets = get(API.MARKETS()).json()['markets']
		return { m['id']:m for m in all_markets if m['state'] not in config.exclude_market_states }

	def candles(self, *, market_id, duration, granularity, step=1):
		period_start = (datetime.now().timestamp() - duration) * (10 ** 9) 
		req = API.MARKET_CANDLES(market_id=market_id, since_timestamp=period_start, interval=granularity)
		if len(candles := get(req).json()['candles']) == 0: return None
		decimals = int(self.market_lookup[market_id]['decimalPlaces'])
		return list(map(partial(self.process_candle_data, decimals=decimals), candles))

	def process_candle_data(self, candle, decimals):
		del candle['timestamp']
		del candle['interval']
		for k, v in candle.items():
			if k in PRICE_FLOAT_FIELDS:
				candle[k] = float(v) / (10 ** decimals) 
			elif k in PRICE_INT_FIELDS:
				candle[k] = int(v)
		return candle

	def enrich_candle(self, candle):
		candle ['change'] = (candle['close'] - candle['open']) / candle['open']
		candle['action'] = \
			'gainer' if candle['close'] > candle['open'] else \
			'loser' if candle['close'] < candle['open'] else 'no change'
		return candle

	def zip_candles(self, candles, step=None):
		res, chunk, rest = [], [], list(candles)
		while len(rest) > 0:
			chunk, rest = rest[:step or len(candles)], rest[step or len(candles):]
			res.append({
				'datetime': chunk[-1]['datetime'],
				'open': chunk[0]['open'],
				'high': max(x['high'] for x in chunk),
				'low': min(x['low'] for x in chunk),
				'close': chunk[-1]['close'],
				'volume': sum(x['volume'] for x in chunk),
			})
		return res

	@cached(config.market_cache_ttl)
	def price_data_for_market(self, market_id):
		candles = self.candles(
			market_id=market_id, 
			duration=config.change_duration, 
			granularity=config.change_interval)
		return candles and self.enrich_candle(self.zip_candles(candles)[0])

	@cached(config.history_cache_ttl)
	def price_history(self, market_id):
		return [x['close'] for x in 
				self.zip_candles(
					self.candles(
							market_id=market_id, 
							duration=config.change_duration, 
							granularity=config.history_granularity), 
					step=config.history_step)]

	@cached(config.market_cache_ttl)
	def ticker(self, history=True):
		return [self.ticker_entry(market_id=id, history=history) for id in self.market_lookup.keys()]

	@cached(config.market_cache_ttl)
	def ticker_entry(self, market_id: str, history=True) -> TickerEntry:
		market = self.market_lookup.get(market_id, None)
		return market and {
			'id': market['id'],
			'code': market['tradableInstrument']['instrument']['code'],
			'name': market['tradableInstrument']['instrument']['name'],
			'price_data': self.price_data_for_market(market_id=market_id),
			**({ 'history': self.price_history(market_id=market_id) } if history else {})
		}

	@cached(config.market_cache_ttl)
	def markets(self):
		return list(self.market_lookup.values())