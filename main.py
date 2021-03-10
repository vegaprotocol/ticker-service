from typing import List
from fastapi import FastAPI, HTTPException
from pydantic.types import Json
from starlette.responses import JSONResponse
from tickerservice import TickerService, TickerEntry


app = FastAPI(
	title='Vega ticker service', version='0.0.1',
	docs_url=None, redoc_url='/docs',
)


td = TickerService()

@app.get('/ticker', response_model=List[TickerEntry])
def get_ticker():
	"""
	Returns name, symbol (code) for active markets plus current (close) price and 24hr change and volume details.
	"""
	return td.ticker()

@app.get('/ticker/{market_id}', response_model=TickerEntry)
def get_ticker_entry(market_id: str):
	"""
	Returns the ticker entry (name, code, price, 24hr change and volume) for a given market ID
	"""
	if (res := td.ticker_entry(market_id=market_id)) is None:
		raise HTTPException(status_code=404, detail=f'No active market found: {market_id}')
	else:
		return res

@app.get('/markets')
def get_markets():
	"""
	Returns full details for all active markets on Fairground
	"""
	return td.markets()
