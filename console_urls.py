import json
import base64


root_url = 'https://console.fairground.wtf'


def view(root_url, view, **props):
	encoded_props = str(base64.b64encode(json.dumps(props).encode('utf-8')), 'utf-8')
	return f'{root_url}/?view={view}&props={encoded_props}'

def market_info(id):
	return view(root_url, view='MarketDetail', marketId=id)

def market(id):
	return view(root_url, view='Market', marketId=id)

def asset(id):
	return view(root_url, view='AssetDetail', assetId=id)

def proposal(id):
	return view(root_url, view='Proposal', proposalId=id)
