from news import NewsItem
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from tickerservice import TickerService, TickerEntry


app = FastAPI(
	title='Vega ticker service', version='0.0.1',
	docs_url=None, redoc_url='/docs',
)

app.add_middleware(CORSMiddleware, allow_origins=['*'])


ts = TickerService()


@app.get('/ticker', response_model=List[TickerEntry], response_model_exclude_unset=True)
def get_ticker(history: bool=True):
	"""
	Returns name, symbol (code) for active markets plus current (close) price and 24hr change and volume details.
	"""
	return ts.ticker(history=history)

@app.get('/ticker/{market_id}', response_model=TickerEntry, response_model_exclude_unset=True)
def get_ticker_entry(market_id: str, history: bool=True):
	"""
	Returns the ticker entry (name, code, price, 24hr change and volume) for a given market ID
	"""
	if (res := ts.ticker_entry(market_id=market_id, history=history)) is None:
		raise HTTPException(status_code=404, detail=f'No active market found: {market_id}')
	else:
		return res

@app.get('/markets')
def get_markets():
	"""
	Returns full details for all active markets on Fairground
	"""
	return ts.markets()

@app.get('/stats')
def get_stats():
	"""
	Returns Fairground network statistics
	"""
	return ts.stats()

@app.get('/news', response_model=List[NewsItem], response_model_exclude_unset=True)
def get_news():
	"""
	Returns news announcements
	"""
	return ts.news()