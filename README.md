# yf_tools
API of yahoo finance data

Multi-threaded yahoo finance data downloader on:
1) symbols (or tickers)
2) historical data (daily + minute frequency)
3) real-time market data (superfast, <1 sec for thousands of stocks)
4) detailed stock data (e.g. fundamental data)

Improvements over the exisiting Python package "yfinance" on:
1) allow you to set speed control to avoid hitting the server rate limit
2) allow you to set the number of retry to retry download if there is any download failed
3) allow you to set timeouts on download requests
4) able to download a list of tickers from Stock Screener (https://finance.yahoo.com/screener/equity/new)
5) able to download real-time market data given the tickers (superfast)
6) able to download 1 month of minute historical data in single run (only 7days fo "yfinance")



Examples of use:
import yf_tools as yf


### Download stock symbol (ticker) list
E.g. Download a list of 'US' stocks (Nasdaq & NYSE)
url = yf.get_symbols_download_url('US', retry=1, timeout=5)

you could increase retry & set longer timeout for unstable network
or you could browse "https://finance.yahoo.com/screener/equity/new" to set your screener & copy the link to url

# Download symbol list from the "url"
symbols = yf.download_symbols(url)
# you could set speed (num of request/sec) & retry, e.g.
symbols = yf.download_symbols(url, speed=0.1, retry=1)


### Download stocks' instantaneous data into pd.DataFrame (super fast)
info_df = yf.download_info(symbols)

# get instantaneous prices for all stocks in a pd.Series
info_df.regularMarketPrice


### Download comprehensive stocks' information into pd.DataFrame (beware of yf rate limit)
symbols = ['TSLA', 'TSM', 'MARA', 'MRNA']
info_df = yf.download_details(symbols, speed=1.0)

# get info by labels
info_df[['sector', 'industry', 'exDividendDate', 'sharesPercentSharesOut']]


### Download daily historical data

# single stock, return pd.DataFrame
tsm = download_day('TSM')

# given list of stocks, return dict of pd.DataFrame(s)
ohlcvs = download_day(symbols)

# 1.0 sec per download request (to avoid hitting rate limit)
ohlcvs = download_day(symbols, speed=1.0)

# set num of download retry for any failed download
ohlcvs = download_day(symbols, retry=2)

# show detailed download info
ohlcvs = download_day(symbols, verbose=True)

# set a range of dates only (end day not included)
ohlcvs = download_day(symbols, start='2020-08-01', end='2020-09-04')

# includes devidends & split ratios
ohlcvs = download_day(symbols, show_actions=True)

# Combine dict of ohlcvs into a single pd.DataFrame (beware of many null values)
ohlcvs_all = pd.concat(ohlcvs, axis=1)


### Download historical data in minute frequency
tsm = download_minute('TSM')
ohlcvs = download_minute(symbols)

# to include pre-market & post-market data
ohlcvs = download_minute(symbols, show_prepost=True)
