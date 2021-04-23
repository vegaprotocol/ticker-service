from datetime import datetime
from requests import get
from news import NewsItem, ItemType
import console_urls


API = '{node_url}/markets'.format


def proc_ts(ts):
	return int(ts) / 10**9


def get_market_news(m):
	name = m['tradableInstrument']['instrument']['name']
	ts = m['marketTimestamps']
	# proposed = proc_ts(ts['proposed'])
	pending = proc_ts(ts['pending'])
	open = proc_ts(ts['open'])
	close = proc_ts(ts['close'])
	now = datetime.now().timestamp()
	if close < now:
		return NewsItem(
			timestamp=close,
			type=ItemType.market_status,
			subtype='closed',
			message=f'Market closed for trading: {name}',
			url=console_urls.market(m['id']))
	elif open < now:
		return NewsItem(
			timestamp=open,
			type=ItemType.market_status,
			subtype='opened',
			message=f'New market open for trading: {name}',
			url=console_urls.market(m['id']))
	elif pending < now:
		return NewsItem(
			timestamp=pending,
			type=ItemType.market_status,
			subtype='opening',
			message=f'New market in opening auction: {name}',
			url=console_urls.market(m['id']))
	else:
		return None


def get_news(node_url):
	markets = get(API(node_url=node_url)).json()['markets']
	return list(filter(lambda x: x is not None, map(get_market_news, markets)))


if __name__ == '__main__':
	print(get_news(node_url='https://lb.testnet.vega.xyz'))