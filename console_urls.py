import json
import base64


console_root_url = 'https://console.fairground.wtf'
governance_root_url = 'https://token.fairground.wtf'
explorer_root_url = 'https://explorer.fairground.wtf'


def market_info(id):
	return f'{console_root_url}/markets/{id}'  # links to Consle V2, linking to a specific market not supported on explorer

def market(id):
	return f'{console_root_url}/markets/{id}'

def asset(id):
	return f'{explorer_root_url}/assets'  # linking to a specific asset not support on explorer

def proposal(id):
	return f'{governance_root_url}/governance/{id}'
