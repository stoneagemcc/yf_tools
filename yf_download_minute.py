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
# By testing @ 2021-05-25: limit is 1.0 sec / request


if False:
    from yf_download_day import *

    tsm = download_minute('TSM')
                             

    symbols = ['AAPL', 'LMFA', 'XXXXX', 'MARA']
    #symbols=['AAPL', 'LMFA', 'MARA', 'TSM', 'XXXXX', 'GOOG', 'FB', 'MRNA', 'BB',
    #            'NOK', 'GME', 'AMC', 'NKE', 'BE', 'DQ', 'TTD', 'ZG', 'LB', 'SQ', 'SE']



    ohlcvs = download_minute(symbols,
                             #start='2022-03-15',
                             start=None,
                             #end='2022-04-27',
                             end=None,
                             show_prepost=True,
                             show_split=True,
                             speed=0.1,
                             retry=1,
                             timeout=(3.05,5),
                             verbose=True,
                             )


    # combine into a single df
    ohlcvs_df = pd.concat(ohlcvs, axis=1)




#-------------------------Definition-------------------------#

'''
symbols=['AAPL', 'LMFA', 'XXXXX', 'MARA']
start='2022-03-15'
end='2022-04-27' # not included
show_actions=True
show_adjclose=True
speed=0.2
retry=1
timeout=(3.05,5)
'''

def download_minute(symbols, start=None, end=None, show_prepost=False, show_split=False,
                    speed=0, retry=0, timeout=(3.05,5), verbose=False):

    '''
    download minute data for many symbols (data is raw, not adjusted for split)
    
    symbols : list of symbols (list of str)
    start : start date (str) / starting utc timestamp (int)
    end : end date (str) / ending utc timestamp (int)
    show_prepost : show pre & post market data ?
    show_split : show stock splits ?
    speed : sec per requested download
    retry : num of download retry if download fails
    timeout : sec to request timeout [specify: sec / (sec: connect timeout, sec: response timeout)]

    -> dict of ohlcvs (df)
    '''
    
    with requests.Session() as sess:
        
        # process inputs
        
        # symbol list
        single_symbol = None
        if isinstance(symbols, str):
            symbols = re.split(r'[\s,|;]+', symbols.strip('\n\t ,|;'))
            if len(symbols) == 1:
                single_symbol = symbols[0]
        symbols = [symbol.upper() for symbol in symbols]


        # start time
        now = pd.Timestamp.today(tz='utc').tz_convert(None)
        lower_bound = now.normalize() - pd.Timedelta('32d')
        
        if start is None:
            start = lower_bound
        elif isinstance(start, str):
            start = pd.Timestamp(start)
        else: # int / float / pd.Timestamp
            start = pd.Timestamp(start, unit='s')
        start = max(start, lower_bound)

        # search for valid start time
        keep_going = True 
        while keep_going:
            try:
                _download_minute_unit(symbol='^GSPC',
                                      start=start.timestamp(),
                                      end=(start + pd.offsets.BDay()).timestamp(),
                                      show_prepost=False,
                                      show_split=False,
                                      sess=sess,
                                      timeout=timeout)
                keep_going = False
            except Exception:
                start = start + pd.offsets.BDay()


        # end time
        if end is None:
            end = now # current time
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


        # segregate (start, end)
        starts = list(pd.date_range(start, end, freq='7d', closed='left'))
        ends = starts[1:]
        ends.append(end)
        
        print('Download start at : {} (in UTC time)'.format(str(start)))
        print('Download end at : {} (in UTC time)'.format(str(end)))
        print('Divided into {} parts:'.format(len(starts)))
        for j, (start, end) in enumerate(zip(starts, ends)):
            print('  {} : {} ~ {}'.format(j, str(start)[:10], str(end)[:10]))
        print('Download speed : {:.3f} sec/request'.format(round(speed, 2)))
        print()


        # main program
        with ThreadPoolExecutor() as executor:

            # initialize outer retry loop
            symbols_idx = [(symbol, j)
                           for symbol in symbols
                           for j in range(len(starts))]
            ohlcvs = {} # dict of list to accumulate extracted ohlcv
            i_outer_loop = 0
            

            # outer loop to retry download & process 
            while symbols_idx and (i_outer_loop <= retry):

                # initialize inner loops
                total = len(symbols_idx)
                print('Loop {} , total {} to download'.format(i_outer_loop, total) )
                pool = {} # container for threads
                t0 = time.perf_counter()


                # inner download loop
                for i, (symbol, j) in enumerate(symbols_idx):
                    
                    # speed control
                    wait = max(0.0, speed*i - (time.perf_counter()-t0) )
                    time.sleep(wait)
                    
                    # request download & extract data
                    pool[(symbol, j)] = executor.submit(_download_minute_unit, symbol,
                                               starts[j].timestamp(), ends[j].timestamp(),
                                               show_prepost, show_split, sess, timeout)

                    # show progress bar
                    if verbose:
                        _progress_status(i, total, prepend='  Requests Sent: ')
                    else:
                        _progress_bar(i, total)


                # list to store symbols of failed download
                failed_symbols_idx = []
                failed_print = {}
                

                # inner loop to check & store data
                for (symbol, j), job in pool.items():

                    # try getting downloaded contents
                    try:
                        ohlcv = job.result()
                        ohlcvs.setdefault(symbol, []).append(ohlcv)

                    # if download failed
                    except Exception:
                        failed_symbols_idx.append((symbol, j)) # insert (symbol,idx) if failed
                        failed_print.setdefault(symbol, []).append(str(j))


                # print symbols with indices of failed download
                if failed_print:
                    print('    Failed :', end=' ')
                    for symbol, indices in failed_print.items():
                        print(symbol+'[{}]'.format(','.join(indices)), end=' ')
                    print()

                # speed control before next outer retry loop
                if i_outer_loop < retry:
                    i += 1
                    wait = max(0.0, speed*i - (time.perf_counter()-t0) )
                    time.sleep(wait)
                    
                # update for next outer iteration
                i_outer_loop += 1
                symbols_idx = failed_symbols_idx
                

    # concatenate list of dfs
    ohlcvs = {symbol: pd.concat(ohlcv_list, axis=0).sort_index()
                  for symbol, ohlcv_list
                  in ohlcvs.items()}
    print('Total {} datasets have been downloaded'.format(len(ohlcvs)))
                
    if single_symbol:
        return ohlcvs[single_symbol]
    
    return ohlcvs # dict of df
                





'''
# https://www.nasdaq.com/market-activity/stock-splits
symbol='UK' # split @ 2022-03-17
start=pd.Timestamp('2022-04-21').timestamp()
end=pd.Timestamp('2022-04-28').timestamp() # not included
show_prepost=True
show_split=True
sess=requests.Session()
timeout=(3.05,5)
'''

def _download_minute_unit(symbol, start, end, show_prepost, show_split, sess, timeout):
    '''
    download minute data for single symbol in one request
    (ohlcv is original, not adjusted for split)
    
    symbol : stock (ticker) symbol (str)
    start : starting utc timestamp (int)
    end : ending utc timestamp (int)
    show_prepost : show pre & post market data ?
    show_split : show stock splits ?
    sess : requests.Session for persisting download
    timeout : sec to request timeout [specify sec / (sec: connect timeout, sec: response timeout)]

    -> df of ohlcv [index: localized datetime idx]
    '''

    # request config
    params = {'interval': '1m',
              'period1': int(start), # start
              'period2': int(end), # end, but not included
              'includePrePost': show_prepost,
              'events': 'splits',
              }
    headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 \
                                (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    url = 'https://query1.finance.yahoo.com/v8/finance/chart/{}'.format(symbol)

    # request download
    resp = sess.get(url, params=params, headers=headers, timeout=timeout)

    # extract data from response as dict
    data = resp.json()['chart']['result'][0]
    datetime_idx = pd.to_datetime(data['timestamp'], unit='s') # in UTC
    datetime_idx.name = 'datetime'
    ohlcv = data['indicators']['quote'][0] # {'open': [...], 'high': [...], ...}

    # variables included
    var_names = ['open', 'high', 'low', 'close', 'volume']
    
    # if split available
    is_split = ('events' in data) and ('splits' in data['events'])
    if is_split:
        split = data['events']['splits']
        split = pd.DataFrame(split.values()).set_index('date')
        split.index = pd.to_datetime(split.index, unit='s')
        split = split['numerator'] / split['denominator'] # used to recover ohlc later [series]

    # include split in result
    if show_split:
        var_names.append('split')
        if is_split:
            ohlcv['split'] = split
        else:
            ohlcv['split'] = np.nan

    # dict of ohlcv -> df of ohlcv (to be returned)
    ohlcv = pd.DataFrame(ohlcv, index=datetime_idx, columns=var_names, dtype=np.float64)

    # convert datetime idx to local time
    tz = data['meta']['exchangeTimezoneName']
    ohlcv.index = ohlcv.index.tz_localize(tz='utc').tz_convert(tz=tz) 

    # recover ohlc due to split
    if is_split:
        for datetime, ratio in split.items():
            date = (datetime - pd.Timedelta('1d')).strftime('%Y-%m-%d')
            ohlcv.loc[:date, ['open', 'high', 'low', 'close']] *= ratio
        # !!! volume is not adjusted in raw data, thus no need to recover !!!

    # drop rows with duplicated index
    duplicated = ohlcv.index.duplicated()
    if duplicated.any():
        ohlcv = duplicated.loc[~duplicated]
        
    return ohlcv










#------------------------- Testing -------------------------#
if False:

    sess = requests.Session()
    today = pd.Timestamp.today('utc').tz_convert(None).normalize()
    df = _download_minute_unit(symbol='TBLT', # split @ 2021-05-07
                                     start=(today - pd.Timedelta('7d')).timestamp(),
                                     end=today.timestamp(), # not included
                                     show_prepost=False,
                                     show_split=True,
                                     sess=sess,
                                     timeout=(3.05,5),
                                     )
    sess.close()




    from yf_download_day import *
    
    ohlcvs = download_day('TBLT',
                           start='2022-04-20',
                           end='2022-04-27', # not included
                           show_actions=True,
                           show_adjclose=True,
                           speed=0.2, # shortest interval (in seconds) between downloads
                           retry=1,
                           timeout=(3.05,5),
                           )




    ohlcvs = download_minute(symbols=['AAPL', 'catb', 'VXX'],
                                      start='2021-07-15',
                                      end=None,
                                      show_prepost=False,
                                      show_split=True,
                                      speed=0.2, # shortest interval (in seconds) between downloads)
                                      retry=1,
                                      timeout=(3.05,5),
                                      )























