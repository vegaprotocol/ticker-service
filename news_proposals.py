from datetime import datetime
from requests import get
from typing import  Optional
from pydantic.main import BaseModel
from news import NewsItem, ItemType
import console_urls


API = '{node_url}/governance/proposals'.format


class ProposalHandling(BaseModel):
	pre_ts: Optional[str]
	post_ts: Optional[str]
	action: str


PROPOSAL_MAPPING = {
	'STATE_FAILED': ProposalHandling(pre_ts='closingTimestamp', post_ts=None, action='failed'),
	'STATE_OPEN': ProposalHandling(pre_ts='timestamp', post_ts='closingTimestamp', action='voting'),
	'STATE_PASSED': ProposalHandling(pre_ts='closingTimestamp', post_ts='enactmentTimestamp', action='passed'),
	'STATE_DECLINED': ProposalHandling(pre_ts='closingTimestamp', post_ts=None, action='failed'),
	'STATE_ENACTED': ProposalHandling(pre_ts='closingTimestamp', post_ts=None, action='enacted'),
}


def get_news(node_url):
	proposals = get(API(node_url=node_url)).json()['data']
	for p in proposals:
		sort_timestamps(p)
	return list(filter(lambda x: x is not None, map(news_item, proposals)))


def sort_timestamps(proposal):
	proposal['proposal']['timestamp'] = int(proposal['proposal']['timestamp']) / 10**9
	proposal['proposal']['closingTimestamp'] = int(proposal['proposal']['terms']['closingTimestamp'])
	proposal['proposal']['enactmentTimestamp'] = int(proposal['proposal']['terms']['enactmentTimestamp'])


def get_countdown(p, ph):
	now = datetime.now().timestamp()
	since = max(now - p['proposal'][ph.pre_ts], 0) if ph.pre_ts else 0
	until = min(now - p['proposal'][ph.post_ts], 0) if ph.post_ts else 0
	return since, until


def get_type(p):
	if 'newMarket' in p['proposal']['terms']:
		return 'new_market'
	else:
		return 'proposal'


def new_market_news(p, ph):
	state = p['proposal']['state']
	since, until = get_countdown(p, ph)
	name = p['proposal']['terms']['newMarket']['changes']['instrument']['code']
	now = datetime.now().timestamp()
	if state in ['STATE_OPEN']:
		if abs(since) < abs(until):
			return NewsItem(
				timestamp=p['proposal']['timestamp'], 
				type=ItemType.market_proposal, 
				subtype='proposed', 
				message=f'Market proposed: {name}',
				subject=name,
				url=console_urls.proposal(p['proposal']['id']))
		else:
			return NewsItem(
				timestamp=now, 
				type=ItemType.market_proposal, 
				subtype='closing', 
				message=f'Voting now! Closing soon: {name}',
				subject=name,
				url=console_urls.proposal(p['proposal']['id']))
	elif state in ['STATE_DECLINED', 'STATE_FAILED']:
		return NewsItem(
			timestamp=p['proposal']['terms']['closingTimestamp'], 
			type=ItemType.market_proposal, 
			subtype='failed', 
			message=f'Market proposal failed: {name}',
				subject=name,
			url=console_urls.proposal(p['proposal']['id']))
	elif state in ['STATE_PASSED']:
		return NewsItem(
			timestamp=p['proposal']['terms']['closingTimestamp'], 
			type=ItemType.market_proposal, 
			subtype='passed', 
			message=f'New market approved: {name}',
				subject=name,
			url=console_urls.proposal(p['proposal']['id']))
	else:
		return None


def news_item(p):
	ph = PROPOSAL_MAPPING[p['proposal']['state']] if p['proposal']['state'] in PROPOSAL_MAPPING else None
	if ph and 'newMarket' in p['proposal']['terms']: 
		return new_market_news(p, ph)
	else:
		return None  #TODO: handle other proposal types


if __name__ == '__main__':
	print(get_news(node_url='https://lb.testnet.vega.xyz'))