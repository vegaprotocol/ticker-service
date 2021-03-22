from functools import partial
from requests import get
from datetime import datetime


API = '{node_url}/markets/{market_id}/candles?since_timestamp={since_timestamp:.0f}&interval={interval}'.format

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


def candles(*, node_url, market_id, duration, granularity, decimals, step=1):
	period_start = (datetime.now().timestamp() - duration) * (10 ** 9) 
	req = API(node_url=node_url, market_id=market_id, since_timestamp=period_start, interval=granularity)
	if len(c := get(req).json()['candles']) == 0: return None
	return list(map(partial(process_candle_data, decimals=decimals), c))

def process_candle_data(candle, *, decimals):
	del candle['timestamp']
	del candle['interval']
	for k, v in candle.items():
		if k in PRICE_FLOAT_FIELDS:
			candle[k] = float(v) / (10 ** decimals) 
		elif k in PRICE_INT_FIELDS:
			candle[k] = int(v)
	return candle

def enrich_candle(candle):
	candle ['change'] = (candle['close'] - candle['open']) / candle['open']
	candle['action'] = \
		'gainer' if candle['close'] > candle['open'] else \
		'loser' if candle['close'] < candle['open'] else 'no change'
	return candle

def zip_candles(candles, *, step=None):
	res, chunk, rest = [], [], list(candles or [])
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
