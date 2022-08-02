import json
import base64


console_root_url = 'https://console.fairground.wtf'
governance_root_url = 'https://token.fairground.wtf'
explorer_root_url = 'https://explorer.fairground.wtf'


# OLD - Console v1
# def view(root_url, view, **props):
#		encoded_props = str(base64.b64encode(json.dumps(props).encode('utf-8')), 'utf-8')
#		return f'{root_url}/?view={view}&props={encoded_props}'

def market_info(id):
	return f'{console_root_url}/markets/{id}'  # links to Consle V2, linking to a specific market not supported on explorer

def market(id):
	return f'{console_root_url}/markets/{id}'

def asset(id):
	return f'{explorer_root_url}/assets'  # linking to a specific asset not support on explorer

def proposal(id):
	return f'{governance_root_url}/governance/{id}'
