from datetime import datetime
from requests import get
from news import NewsItem, ItemType
import console_urls


API = '{node_url}/api/v2/markets'.format


def proc_ts(ts):
	return int(ts) / 10**9


def get_market_news(m):
	name = m['tradableInstrument']['instrument']['code']
	state = m['state']
	ts = m['marketTimestamps']
	pending = proc_ts(ts['pending'])
	open = proc_ts(ts['open'])
	close = proc_ts(ts['close'])
	now = datetime.now().timestamp()
	if close > 0 and close < now:
		return NewsItem(
			timestamp=close,
			type=ItemType.market_status,
			subtype='closed',
			message=f'Market closed: {name}',
			subject=name,
			url=console_urls.market(m['id']))
	elif open < now and state == 'STATE_ACTIVE':
		return NewsItem(
			timestamp=open,
			type=ItemType.market_status,
			subtype='opened',
			message=f'Market created: {name}',
			subject=name,
			url=console_urls.market(m['id']))
	elif pending < now and state == 'STATE_PENDING':
		return NewsItem(
			timestamp=pending,
			type=ItemType.market_status,
			subtype='opening',
			subject=name,
			message=f'Market in opening auction: {name}',
			url=console_urls.market(m['id']))
	else:
		return None


def get_news(node_url):
	markets_resp = get(API(node_url=node_url)).json()
	markets = [m['node'] for m in markets_resp['markets']['edges']]
	return list(filter(lambda x: x is not None, map(get_market_news, markets)))


if __name__ == '__main__':
	print(get_news(node_url='https://lb.testnet.vega.xyz'))
