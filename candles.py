from functools import partial
from requests import get
from datetime import datetime


API = '{node_url}/api/v2/candle?candleId={candle_id}&fromTimestamp={since_timestamp:.0f}&interval={interval}'.format
MARKETS = '{node_url}/api/v2/markets'.format

PRICE_FLOAT_FIELDS = ['open', 'close', 'high', 'low']
PRICE_INT_FIELDS = ['volume']

INTERVAL = {
	'INTERVAL_I1M': 60,
	'INTERVAL_I5M': 300,
	'INTERVAL_I15M': 900,
	'INTERVAL_I1H': 3_600,
	'INTERVAL_I6H': 21_600,
	'INTERVAL_I1D': 86_400
}

CANDLE_API_NAME = {
	'INTERVAL_I1M': '1_minute',
	'INTERVAL_I5M': '5_minutes',
	'INTERVAL_I15M': '15_minutes',
	'INTERVAL_I1H': '1_hour',
	'INTERVAL_I6H': '6_hours',
	'INTERVAL_I1D': '1_day'
}

def dumb_candle_id(market_id, interval):
	return f'trades_candle_{CANDLE_API_NAME[interval]}_{market_id}'


def candles(*, node_url, market_id, duration, granularity, decimals, step=1):
	'''
	Get candle data from the API and processes it to turn strings into numbers. 
	This function does *not* enrich the candles because you may want to zip them before doing that.
	'''
	period_start = (datetime.now().timestamp() - duration) * (10 ** 9) 
	candle_id = dumb_candle_id(market_id=market_id, interval=granularity)
	req = API(node_url=node_url, candle_id=candle_id, since_timestamp=period_start, interval=granularity)
	try:
		candles_resp = get(req).json()
		if len(candles := [c['node'] for c in candles_resp['candles']['edges']]) == 0: return None
		return list(map(partial(process_candle_data, decimals=decimals), candles))
	except:
		return None

def process_candle_data(candle, *, decimals):
	'''
	Turns strings in candle response into numbers.
	'''
	for k, v in candle.items():
		if k in PRICE_FLOAT_FIELDS:
			candle[k] = float(v) / (10 ** decimals) 
		elif k in PRICE_INT_FIELDS:
			candle[k] = int(v)
	return candle

def enrich_candle(candle):
	'''
	Adds fraction change and gainer/loser tag to processed candle data.
	'''
	candle ['change'] = (candle['close'] - candle['open']) / candle['open']
	candle['action'] = \
		'gainer' if candle['close'] > candle['open'] else \
		'loser' if candle['close'] < candle['open'] else 'no change'
	return candle

def zip_candles(candles, *, step=None):
	'''
	Combines processed candles into larger buckets, e.g. candles = 15 min candles and step = 2 returns 30 min candles.
	candles: list of input candle data
	step: number of input candles to combine together (combines the *entire*) input if None or omitted
	'''
	res, chunk, rest = [], [], list(candles or [])
	while len(rest) > 0:
		chunk, rest = rest[:step or len(candles)], rest[step or len(candles):]
		res.append({
			'datetime': chunk[-1]['start'],
			'open': chunk[0]['open'],
			'high': max(x['high'] for x in chunk),
			'low': min(x['low'] for x in chunk),
			'close': chunk[-1]['close'],
			'volume': sum(x['volume'] for x in chunk),
		})
	return res
