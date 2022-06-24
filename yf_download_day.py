import requests
import numpy as np
import pandas as pd
import time
import re
import os
from concurrent.futures import ThreadPoolExecutor
import builtins

try:
    from ._progress import _progress_status, _progress_bar
except ImportError:
    from _progress import _progress_status, _progress_bar





#-------------------------Description-------------------------#
# yf download rate limit: 2000 requests / hour (or 48,000 requests / day)

if False:
    from yf_download_day import *

    tsm = download_day('TSM')
    

    #symbols = ['AAPL', 'LMFA', 'XXXXX', 'MARA']
    symbols=['AAPL', 'LMFA', 'MARA', 'TSM', 'XXXXX', 'GOOG', 'FB', 'MRNA', 'BB',
                'NOK', 'GME', 'AMC', 'NKE', 'BE', 'DQ', 'TTD', 'ZG', 'LB', 'SQ', 'SE']
    
    ohlcvs = download_day(symbols,
                           start='2020-08-01',
                           end='2020-09-04', # not included
                           show_actions=True,
                           show_adjclose=True,
                           speed=0.1, # shortest interval (in seconds) between downloads
                           retry=1,
                           timeout=(3.05,5),
                           verbose=True,
                           )

    # Inputs
    # symbols : list of symbols (list of str)
    # start : start date (str) / starting utc timestamp (int)
    # end : end date (str) / ending utc timestamp (int)
    # show_actions : show stock splits & dividends ?
    # show_adjclose : show adjusted closing price ?
    # speed : sec per requested download
    # retry : num of download retry (to maximize downloaded content)
    # timeout : sec to request timeout [specify sec / specify (sec: connect timeout, sec: response timeout)]

    # Output
    # dict of ohlcvs (df)
    

    # combine into a single df
    ohlcvs_df = pd.concat(ohlcvs, axis=1)



    
    # to recover the original ohlcv + div before stock split
    recover_from_split(ohlcv)

    # calculate adusting ratio for prices (ohlc) due to dividend
    adjust_by_dividend(dividend)





#-------------------------Definition-------------------------#
    
'''
symbols=['AAPL', 'LMFA', 'XXXXX', 'MARA']
start='2021-05-05'
end='2021-05-12' # not included
show_actions=True
show_adjclose=True
speed=0.5
retry=1
timeout=(3.05,5)
'''

def download_day(symbols, start=None, end=None, show_actions=False, show_adjclose=True,
                 speed=0, retry=0, timeout=(3.05,5), verbose=False):
    '''
    download daily data for many symbols (adjusted for split)
    download speed control by seconds / request
    
    symbols : list of symbols (list of str)
    start : start utc date (str) / utc timestamp (int)
    end : end utc date (str) / utc timestamp (int)
    show_actions : show stock splits & dividends ?
    show_adjclose : show adjusted closing price ?
    speed : sec per requested download
    retry : num of download retry if download fails
    timeout : sec to request timeout [specify: sec / (sec: connect timeout, sec: response timeout)]

    -> dict of ohlcvs (df)
    '''

    # process inputs

    # symbol list
    single_symbol = False
    if isinstance(symbols, str): 
        symbols = re.split(r'[\s,|;]+', symbols.strip('\n\t ,|;'))
        if len(symbols) == 1:
            single_symbol = symbols[0]
    symbols = [symbol.upper() for symbol in symbols]

        
    # start time
    if start is None: 
        start = pd.Timestamp('1900-01-01')
    elif isinstance(start, str):
        start = pd.Timestamp(start)
    else: # int / float / pd.Timestamp
        start = pd.Timestamp(start, unit='s')


    # end time
    if end is None: 
        end = pd.Timestamp.now(tz='utc').tz_convert(None) + pd.Timedelta('1d')
        end = end.normalize()
    elif isinstance(end, str):
        end = pd.Timestamp(end)
    else: # int / float / pd.Timestamp
        end = pd.Timestamp(end, unit='s')
    

    # download config
    speed = float(max(speed, 0.0)) # [0.0, inf) # [sec per request]
    retry = int(max(retry, 0)) # [0, inf) # [num of retry]
    timeout = ( tuple( float(max(t, 0.0)) for t in timeout )
                   if isinstance(timeout, tuple)
                   else float(max(timeout, 0.0)) ) # [0.0, inf) # [sec to request timeout]


    # print msg config
    if verbose:
        print = builtins.print
    else:
        def print(*args, **kwargs):
            pass
            
        
    print('Download start at : {} (in UTC time)'.format(str(start)))
    print('Download end at : {} (in UTC time)'.format(str(end)))
    print('Download speed : {:.3f} sec/request '.format(round(speed, 2)))
    print()


    # main program
    with requests.Session() as sess:
        with ThreadPoolExecutor() as executor:

            # initialize outer retry loop
            ohlcvs = {} # dict to accumulate extracted ohlcv
            i_outer_loop = 0
        
            # outer loop to retry download & process 
            while symbols and (i_outer_loop <= retry):

                # initialize inner loops
                total = len(symbols)
                print('Loop {} , total {} to download'.format(i_outer_loop, total) )
                pool = {} # container for threads
                t0 = time.perf_counter()

                
                # inner download loop
                for i, symbol in enumerate(symbols):
                    
                    # speed control
                    wait = max(0.0, speed*i - (time.perf_counter()-t0) )
                    time.sleep(wait)
                    
                    # request download & extract data
                    pool[symbol] = executor.submit(_download_day_unit, symbol,
                                                   start.timestamp(), end.timestamp(),
                                                   show_actions, show_adjclose, sess, timeout)

                    # show progress bar
                    if verbose:
                        _progress_status(i, total, prepend='  Requests Sent: ')
                    else:
                        _progress_bar(i, total)


                # list to store symbols of failed download
                failed_symbols = []

                # inner loop to check & store data
                for symbol, job in pool.items():

                    # try getting downloaded contents
                    try:
                        ohlcvs[symbol] = job.result()

                    # if download failed
                    except Exception:
                        failed_symbols.append(symbol) # insert symbol if failed

                        
                # print symbols of failed download
                if failed_symbols:
                    print('    Failed :', end=' ')
                    for symbol in failed_symbols:
                        print(symbol, end=' ')
                    print()
                
                # speed control before next outer retry loop
                if i_outer_loop < retry:
                    i += 1
                    wait = max(0.0, speed*i - (time.perf_counter()-t0) )
                    time.sleep(wait)

                # update for next outer iteration
                i_outer_loop += 1
                symbols = failed_symbols
                
    print('Total {} datasets have been downloaded'.format(len(ohlcvs)))

    if single_symbol:
        return ohlcvs[single_symbol]
    
    return ohlcvs # dict of df
    

        



'''
symbol='AAPL' # split @ 2020-08-20
start=pd.Timestamp('2020-08-01').timestamp()
end=pd.Timestamp('2022-09-10').timestamp() # not included
show_actions=True
show_adjclose=True
sess = requests.Session()
timeout=(3.05,5)
'''

def _download_day_unit(symbol, start, end, show_actions, show_adjclose, sess, timeout):
    '''
    download daily data for single symbol in one request
    to get ohlcv [prices (open, high low, close) & volume have already been adjusted for split]

    symbol : stock (ticker) symbol (str)
    start : starting utc timestamp (int)
    end : ending utc timestamp (int)
    show_actions : show stock splits & dividends ?
    show_adjclose : show adjusted closing price ?
    sess : requests.Session for persisting download
    timeout : sec to request timeout [specify sec / (sec: connect timeout, sec: response timeout)]

    -> df of ohlcv [index: utc datetime idx]
    '''

    # request config
    params = {'interval': '1d',
              'period1': int(start),
              'period2': int(end),
              }
    if show_actions:
        params['events'] = 'splits,div'
    headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 \
                                (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    url = 'https://query1.finance.yahoo.com/v8/finance/chart/{}'.format(symbol)

    # request download
    resp = sess.get(url, params=params, headers=headers, timeout=timeout)

    # extract data from response as dict
    data = resp.json()['chart']['result'][0]
    datetime_idx = pd.to_datetime(data['timestamp'], unit='s').normalize()
    datetime_idx.name = 'datetime'
    ohlcv = data['indicators']['quote'][0] # {'open': [...], 'high': [...], ...}

    # variables included
    var_names = ['open', 'high', 'low', 'close', 'volume']

    # process adjclose
    if show_adjclose:
        var_names.append('adjclose')
        
        if 'adjclose' in data['indicators']:
            ohlcv.update(data['indicators']['adjclose'][0])
        else:
            ohlcv['adjclose'] = ohlcv['close']

    # process dividend & split
    if show_actions:
        var_names.extend(['dividend', 'split'])

        # if dividend available
        if ('events' in data) and ('dividends' in data['events']):
            div = data['events']['dividends']
            div = pd.DataFrame(div.values()).set_index('date')
            div.index = pd.to_datetime(div.index, unit='s').normalize()
            ohlcv['dividend'] = div['amount']
        else:
            ohlcv['dividend'] = np.nan

        # if split available
        if ('events' in data) and ('splits' in data['events']):
            split = data['events']['splits']
            split = pd.DataFrame(split.values()).set_index('date')
            split.index = pd.to_datetime(split.index, unit='s').normalize()
            ohlcv['split'] = split['numerator'] / split['denominator']
        else:
            ohlcv['split'] = np.nan

    # assemble data into df
    ohlcv = pd.DataFrame(ohlcv, index=datetime_idx, columns=var_names, dtype=np.float64)

    # drop rows with duplicated index (sometimes occur if last date is today)
    duplicated = ohlcv.index.duplicated()
    if duplicated.any():
        ohlcv = duplicated.loc[~duplicated]
        
    return ohlcv








#------------------------- Testing -------------------------#

if False:
    
    sess = requests.Session()
    ohlcv = _download_day_unit(symbol='AAPL', # split @ 2020-08-31
                               start=pd.Timestamp('2020-08-01').timestamp(),
                               end=pd.Timestamp('2020-09-04').timestamp(), # not included
                               show_actions=True,
                               show_adjclose=True,
                               sess=sess,
                               timeout=(3.05,5),
                               )

    ohlcv = _download_day_unit(symbol='AAPL',
                               start=pd.Timestamp('2021-08-01').timestamp(),
                               end=pd.Timestamp('2022-09-10').timestamp(), # not included
                               show_actions=True,
                               show_adjclose=True,
                               sess=sess,
                               timeout=(3.05,5),
                               )
    sess.close()



    ohlcvs = download_day(symbols=['AAPL', 'LMFA', 'XXXXX', 'MARA'],
                                   start='2021-05-05',
                                   end='2021-05-12', # not included
                                   show_actions=True,
                                   show_adjclose=True,
                                   speed=0.5, # shortest interval (in seconds) between downloads
                                   retry=1,
                                   timeout=(3.05,5),
                                   )

    # multiple threads
    ohlcvs, meta = download_day(symbols=['AAPL', 'LMFA', 'MARA', 'TSM', 'XXXXX', 'GOOG', 'FB', 'MRNA', 'BB',
                                            'NOK', 'GME', 'AMC', 'NKE', 'BE', 'DQ', 'TTD', 'ZG', 'LB', 'SQ', 'SE'],
                                   start='2021-05-05',
                                   end='2021-05-12', # not included
                                   show_actions=True,
                                   show_adjclose=True,
                                   speed=0.1, # shortest interval (in seconds) between downloads
                                   retry=1,
                                   parallel=True,
                                   )










### ------- Other Functions ------- ###

### recover original ohlc, vol, div from spliting
def recover_from_split(ohlcv):
    '''
    to recover the original ohlcv + div before stock split
    '''
    split = ohlcv['split']

    ratio = split.shift(-1) # shift upward by 1
    ratio = ratio.iloc[::-1].cumprod().iloc[::-1] # multiply backwards
    ratio = ratio.fillna(method='bfill').fillna(1.0)

    ohlcv_orig = ohlcv.loc[:, ['open', 'high', 'low', 'close', 'volume', 'dividend']]
    # prices (ohlc + div) multiplied by ratio
    ohlcv_orig.loc[:, ['open', 'high', 'low', 'close', 'dividend']] *= np.expand_dims(ratio, 1) 
    ohlcv_orig.loc[:, 'volume'] /= ratio # volume divided by ratio
    return ohlcv_orig


### calculate adjclose
def adjust_by_dividend(dividend):
    '''
    calculate adusting ratio for prices (ohlc) due to dividend
    (given prices has already been adjusted for split)
    (assuming re-investment after getting dividend)
    '''
    ratio = 1 - dividend.shift(-1) / close # multiplying factor for backward adjustment
    ratio = ratio.iloc[::-1].cumprod().iloc[::-1] # multiply backwards
    return ratio.fillna(method='bfill').fillna(1.0)


if False:
    ohlcvs, meta = download_day('aapl', show_actions=True)
    aapl = ohlcvs['AAPL']
    aapl_orig = recover_from_split(aapl)
    
    close = aapl['close']
    dividend = aapl['dividend']
    adjclose = close * adjust_by_dividend(dividend)






    
