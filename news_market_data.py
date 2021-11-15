from requests import get
from news import NewsItem, ItemType
from functools import partial
import console_urls

DATA_API = '{node_url}/datanode/rest/markets-data'.format
MARKETS_API = '{node_url}/datanode/rest/markets'.format


def get_market_info(node_url):
	markets = get(MARKETS_API(node_url=node_url)).json()['markets']
	print(__file__ + '/get_market_info: Got markets: ' + ', '.join(m['id'] for m in markets))
	return { m['id']:m for m in markets }


def proc_ts(ts):
	return int(ts) / 10**9


def get_market_news(lookup, m):
	mkt = lookup[m['market']]
	name = mkt['tradableInstrument']['instrument']['code']
	auction_start = int(m['auctionStart']) / 10**9
	auction_trigger = m['trigger']
	if auction_start != 0 and auction_trigger == 'AUCTION_TRIGGER_LIQUIDITY':
		return NewsItem(
			timestamp=auction_start,
			type=ItemType.market_status,
			subtype='liquidity_auction',
			message=f'Market in liquidity  auction: {name}',
			subject=name,
			url=console_urls.market(mkt['id']))		
	elif auction_start != 0 and auction_trigger == 'AUCTION_TRIGGER_PRICE':
		return NewsItem(
			timestamp=auction_start,
			type=ItemType.market_status,
			subtype='price_auction',
			message=f'Market in price monitoring: {name}',
			subject=name,
			url=console_urls.market(mkt['id']))			
	else:
		return None


def get_news(node_url):
	lookup = get_market_info(node_url)
	market_data = get(DATA_API(node_url=node_url)).json()['marketsData']
	print(__file__ + '/get_news: Got market data: ' + ', '.join(repr((d['market'][:5]+'…', d['markPrice'])) for d in market_data))
	return list(filter(lambda x: x is not None, map(partial(get_market_news, lookup), market_data)))


if __name__ == '__main__':
	print(get_news(node_url='https://lb.testnet.vega.xyz'))