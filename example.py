import pandas as pd

from yf_download_day import download_day
from yf_download_minute import download_minute
from yf_download_info import download_info, download_details
from yf_download_symbols import get_symbols_download_url, download_symbols


# Download stock symbol (ticker) list
url = get_symbols_download_url('US', retry=1, timeout=5) # set more retry & longer timeout if network is not good
symbols = download_symbols(url)


# Download stocks' instantaneous data into pd.DataFrame (super fast)
info_df = download_info(symbols)



symbols = ['TSLA', 'TSM', 'MARA', 'MRNA']

# Download comprehensive stocks' information into pd.DataFrame (beware of yf rate limit)
info_df = download_details(symbols)
info_df = download_details(symbols, speed=1.0) # 1.0 sec per download request


# Download daily historical data
tsm = download_day('TSM') # single stock, return pd.DataFrame
ohlcvs = download_day(symbols) # list of stocks, return dict of pd.DataFrame(s)
ohlcvs = download_day(symbols, speed=1.0) # 1.0 sec per download request
ohlcvs = download_day(symbols, retry=2) # set num of download retry if there is any failed
ohlcvs = download_day(symbols, verbose=True) # show detailed download info
ohlcvs = download_day(symbols, start='2020-08-01', end='2020-09-04') # a range of dates only (end day not included)
ohlcvs = download_day(symbols, show_actions=True) # includes devidends & split ratios


# Download historical data in minute frequency (yf allows download of recent 1 month minute data)
tsm = download_minute('TSM')
ohlcvs = download_minute(symbols)
ohlcvs = download_minute(symbols, show_prepost=True) # includes pre-market & post-market data


# Combine dict of ohlcvs into a single pd.DataFrame
ohlcvs_df = pd.concat(ohlcvs, axis=1)
