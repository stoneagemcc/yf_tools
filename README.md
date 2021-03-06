# yf_tools
API of yahoo finance data

Required Packages:
numpy, pandas, requests, selenium, webdriver_manager

Multi-threaded yahoo finance data downloader on:
1) symbols (or tickers)
2) historical data (daily + minute frequency)
3) real-time market data (superfast, <1 sec for thousands of stocks)
4) detailed stock data (e.g. fundamental data)

Improvements over the exisiting Python package "yfinance":
1) allow you to set speed control to avoid hitting the server rate limit
2) allow you to set the number of retry to retry download if there is any download failed
3) allow you to set timeouts on download requests
4) able to download a list of tickers from Stock Screener (https://finance.yahoo.com/screener/equity/new)
5) able to download real-time market data given the tickers (superfast)
6) able to download 1 month of minute historical data in single run (only 7 days for "yfinance")



# Examples of use:
import yf_tools as yf


## 1) Download stock symbol (ticker) list:
### E.g. Download a list of 'US' stocks (Nasdaq & NYSE):
url = yf.get_symbols_download_url('US', retry=1, timeout=5)

(you could increase retry & set longer timeout for unstable network)

(It uses (i) selenium & (ii) webdriver_manager, please "pip install"
or you could skip this step by browsing "https://finance.yahoo.com/screener/equity/new" 
to set your screener on browser & copy the link to "url")
  
### Download symbol list from the "url":
symbols = yf.download_symbols(url)  

### You could set the speed (num of request/sec) & retry (num of additional download):
symbols = yf.download_symbols(url, speed=0.1, retry=1)  


## 2) Download instantaneous stocks' data into pd.DataFrame (super fast):
info_df = yf.download_info(symbols)

### Get instantaneous prices for all stocks in a pd.Series:
info_df.regularMarketPrice


## 3) Download comprehensive stocks' information into pd.DataFrame (beware of yf rate limit):
symbols = ['TSLA', 'TSM', 'MARA', 'MRNA']

info_df = yf.download_details(symbols, speed=1.0)

### Get info by labels:
info_df[['sector', 'industry', 'exDividendDate', 'sharesPercentSharesOut']]


## 4) Download daily historical data:
### Single stock, return pd.DataFrame:
tsm = yf.download_day('TSM')

### List of stocks, return dict of pd.DataFrame(s):
ohlcvs = yf.download_day(symbols)

### Set 1.0 sec per download request (to avoid hitting rate limit):
ohlcvs = yf.download_day(symbols, speed=1.0)

### Set num of download retry for any failed download:
ohlcvs = yf.download_day(symbols, retry=2)

### Show detailed download info:
ohlcvs = yf.download_day(symbols, verbose=True)

### Set a range of dates only (end day not included):
ohlcvs = yf.download_day(symbols, start='2020-08-01', end='2020-09-04')

### Includes devidends & split ratios:
ohlcvs = yf.download_day(symbols, show_actions=True)

### Combine dict of ohlcvs into a single pd.DataFrame (beware of many null values):
import pandas as pd

ohlcvs_all = pd.concat(ohlcvs, axis=1)


## 5) Download historical data in minute frequency:
tsm = yf.download_minute('TSM')

ohlcvs = yf.download_minute(symbols)

### Include pre-market & post-market data:
ohlcvs = yf.download_minute(symbols, show_prepost=True)
