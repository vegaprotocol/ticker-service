from typing import Literal, Set
from pydantic.main import BaseModel
from requests import get
from datetime import datetime

import cachetools
from pydantic import BaseSettings


class Config(BaseSettings):
	node_url: str
	cache_ttl_seconds: int
	cache_size: int
	exclude_market_states: Set[str] 

config = Config(_env_file='.env')


def cached(f):
	return cachetools.cached(cache=cachetools.TTLCache(config.cache_size, config.cache_ttl_seconds))(f)
	

class API:
	MARKETS = (config.node_url + '/markets').format
	MARKET_DATA = (config.node_url + '/markets-data/{market_id}').format
	MARKET_CANDLES = (config.node_url + '/markets/{market_id}/candles?since_timestamp={since_timestamp:.0f}&interval={interval}').format


INTERVAL_SECONDS = {
	'INTERVAL_I1M': 60,
	'INTERVAL_I5M': 300,
	'INTERVAL_I15M': 900,
	'INTERVAL_I1H': 3_600,
	'INTERVAL_I6H': 21_600,
	'INTERVAL_I1D': 86_400
}


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


class TickerService:
	@property
	@cached
	def market_lookup(self):
		all_markets = get(API.MARKETS()).json()['markets']
		return { m['id']:m for m in all_markets if m['state'] not in config.exclude_market_states }

	@cached
	def price_for_market(self, market_id, change_period='INTERVAL_I1D'):
		period_start = (datetime.now().timestamp()-(INTERVAL_SECONDS[change_period]*1.5)) * (10 ** 9) 
		req = API.MARKET_CANDLES(market_id=market_id, since_timestamp=period_start, interval=change_period)
		if len(candles := get(req).json()['candles']) == 0: return None
		return self.process_candle_data(candles[-1], int(self.market_lookup[market_id]['decimalPlaces']))

	def process_candle_data(self, candle, decimals):
		del candle['timestamp']
		del candle['interval']
		for k, v in candle.items():
			if k in PRICE_FLOAT_FIELDS:
				candle[k] = float(v) / (10 ** decimals) 
			elif k in PRICE_INT_FIELDS:
				candle[k] = int(v)
		candle ['change'] = (candle['close'] - candle['open']) / candle['open']
		candle['action'] = \
			'gainer' if candle['close'] > candle['open'] else \
			'loser' if candle['close'] < candle['open'] else 'no change'
		return candle

	@cached
	def ticker(self):
		return [self.ticker_entry(id) for id in self.market_lookup.keys()]

	def ticker_entry(self, market_id: str) -> TickerEntry:
		market = self.market_lookup.get(market_id, None)
		return market and {
			'id': market['id'],
			'code': market['tradableInstrument']['instrument']['code'],
			'name': market['tradableInstrument']['instrument']['name'],
			'price_data': self.price_for_market(market_id=market_id)
		}

	def markets(self):
		return list(self.market_lookup.values())