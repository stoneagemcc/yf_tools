import requests
import numpy as np
import pandas as pd
import time
import re
import json
from concurrent.futures import ThreadPoolExecutor
import builtins

try:
    from ._progress import _progress_status, _progress_bar
except ImportError:
    from _progress import _progress_status, _progress_bar





#-------------------------Description-------------------------#
if False:
    from yf_download_info import * # import itself functions

    symbols = ['Tsla', '3738.HK', 'NNDM', 'HKD=X', '^HSI', 'yyyyy', 'xxxx', 'zzzzzz', 'BTC-USD']
    
    
    # download instantenous info from API for many symbols (super fast)
    #   from 'https://query1.finance.yahoo.com/v7/finance/quote?symbols=tsm,tsla'
    info_df = download_info(symbols, max_url_len=8000, speed=0, retry=1, timeout=(3.05,5))

    # Inputs
    # url : url of filtered yf screener
    # count : num of symbols per page
    # speed : sec per requested download
    # retry : num of download retry (to maximize downloaded content)
    # timeout : sec to request timeout [specify sec / specify (sec: connect timeout, sec: response timeout)]

    # Output
    # pd.DataFrame of instantaneous stock info data

    # Main logic flow:
    # (1) cal remaining url len to append symbols
    # (2) cal lens required for each symbol (+1 for ',')
    # (3) Loop to initialize symbol groups for multiple requests
    #   (3-1) count symbols for each group (-1 to exclude final ',')
    #   (3-2) assign symbols into a group
    #   (3-3) update remaining ungrouped symbols
    # (4) create requests.Session for persisting connection
    # (5) create ThreadPoolExecutor for multi-thread downloads
    # (6) initilaize (i) container to accumulate extracted data (ii) outer loop index
    # (7) Outer loop to retry download & process
    #   (7-1) Inner loop for multi-thread downloads
    #     (7-1-1) speed control
    #     (7-1-2) sumbit download task
    #   (7-2) initialize new symbol groups of failed download for outer retry loop
    #   (7-3) Inner loop for processing downloads
    #     (7-3-1) try getting downloaded contents (0 content considered success)
    #     (7-3-2) accumulate extracted info data
    #     (7-3-e1) if download failed: insert symbol group in container (7-2)
    #   (7-4) speed control before next outer retry loop
    #   (7-5) update outer loop index
    #   (7-6) continue outer retry loop only if there remains symbol group in container (7-2)
    # (8) return: df of stock info data


    
    
    # download & scrape detailed info from HTML for many symbols
    #   from 'https://finance.yahoo.com/quote/tsm'
    info_df = download_details(symbols, speed=0.25, retry=0, timeout=(3.05,5), verbose=False)
    
    # Inputs
    # symbols : list of symbols (str)
    # speed : sec per requested download
    # retry : num of download retry (to maximize downloaded content)
    # timeout : sec to request timeout [specify: sec / (sec: connect timeout, sec: response timeout)]

    # Output
    # pd.DataFrame of detailed info data





#-------------------------Definition-------------------------#

'''
symbols=['Tsla', 'xxxx', '3738.HK', 'NNDM', 'HKD=X', '^HSI', 'BTC-USD']
symbols=['yyyyy', 'xxxx', 'zzzzzz', '3738.HK', 'NNDM', 'HKD=X', '^HSI', 'BTC-USD']
symbols='TSM,TSLA'
max_url_len=80
speed=0.1
retry=1
timeout=(3.05,5)
'''

def download_info(symbols, max_url_len=8000, speed=0, retry=1, timeout=(3.05,5)):
    '''
    download instantenous basic info for many symbols (super fast)
    from 'https://query1.finance.yahoo.com/v7/finance/quote?symbols=tsm,tsla'

    symbols : list of symbols (list of str)
    max_url_len : url length limit
    speed : sec per requested download
    retry : num of download retry if download fails
    timeout : sec to request timeout [specify: sec / (sec: connect timeout, sec: response timeout)]

    -> df of info data
    '''
    
    # process inputs
    if isinstance(symbols, str):
        symbols = re.split(r'[\s,|;]+', symbols.strip('\n\t ,|;')) # list of symbols (str)
    max_url_len = int(max(max_url_len, 1)) # [1, inf)
    speed = float(max(speed, 0.0)) # [0.0, inf) # [sec per request]
    retry = int(max(retry, 0)) # [0, inf) # [num of retry]
    timeout = ( tuple( float(max(t, 0.0)) for t in timeout )
                   if isinstance(timeout, tuple)
                   else float(max(timeout, 0.0)) ) # [0.0, inf) # [sec to request timeout]
               

    # initialize
    url_base = 'https://query1.finance.yahoo.com/v7/finance/quote?symbols='
    headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 \
                                (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    remain_url_len = max_url_len - len(url_base)
    

    # len required for each symbol (include ',')
    sym_lens = np.array([len(sym) + 1 for sym in symbols]) 


    # loop to prepare symbol groups for multiple requests
    sym_grps = []
    while symbols:
        
        # count symbols for each group (-1 to exclude ',')
        count = ( (sym_lens.cumsum() - 1) <= remain_url_len).sum() 
        count = max(count, 1) # at least one

        # assign symbols into group
        sym_grps.append( tuple(symbols[:count]) )

        # update remaining ungrouped symbols
        symbols = symbols[count:]
        sym_lens = sym_lens[count:]


    with requests.Session() as sess:
        with ThreadPoolExecutor() as executor:

            # initialize outer retry loop
            data = [] # list to accumulate extracted data
            i_outer_loop = 0

            # outer loop to retry download & process
            while sym_grps and (i_outer_loop <= retry):

                # initialize inner loops
                print('Loop {} , total {} info to download'.format(i_outer_loop,
                                            sum(len(sym_grp) for sym_grp in sym_grps) ) )
                pool = {} # container for threads
                t0 = time.perf_counter()
                
                # inner download loop
                for i_wait, sym_grp in enumerate(sym_grps):

                    # speed control
                    wait = max(0.0, speed*i_wait - (time.perf_counter()-t0) )
                    time.sleep(wait)

                    # request download
                    url = url_base + ','.join(sym_grp)
                    pool[sym_grp] = executor.submit(sess.get, url, headers=headers)
                    print('  Download {} info'.format(len(sym_grp)) )


                # list to store symbol groups of failed download
                failed_sym_grps = []

                # inner loop to process downloaded contents
                for sym_grp, job in pool.items():

                    # try getting downloaded contents (0 content considered success)
                    try:
                        list_of_dicts = job.result().json()['quoteResponse']['result']
                        data.extend( list_of_dicts ) # accumulate data
                        print('    {} info downloaded'.format(len(list_of_dicts)))

                    # if download failed
                    except Exception:
                        failed_sym_grps.append(sym_grp) # insert symbol group if failed
                        print('    [Err] No info data for [{}] !!!'.format(
                                    ','.join(sym_grp[:5]) + (',...' if sym_grp[5:] else '') ) )


                # speed control before next outer retry loop
                if i_outer_loop < retry:
                    i_wait += 1
                    wait = max(0.0, speed*i_wait - (time.perf_counter()-t0) )
                    time.sleep(wait)

                # update for next outer iteration
                i_outer_loop += 1
                sym_grps = failed_sym_grps


    # count total downloaded info
    print('Total {} info have been downloaded'.format(len(data)))
            
    return pd.DataFrame(data).set_index('symbol')
            





'''
symbols = ['TSLA', 'ASDASD', '0981.HK', 'AAPL', 'HKD=X', '^HSI']
speed = 0.5
retry = 1
timeout=(3.05,5)
'''

def download_details(symbols, speed=0.25, retry=0, timeout=(3.05,5), verbose=False):
    '''
    download detailed info for many symbols (quite slow)
    from 'https://finance.yahoo.com/quote/tsm'

    symbols : list of symbols (list of str)
    speed : sec per requested download
    retry : num of download retry (to maximize downloaded content)
    timeout : sec to request timeout [specify: sec / (sec: connect timeout, sec: response timeout)]
    
    -> df of detailed info data
    '''

    # process inputs
    if isinstance(symbols, str): 
        symbols = re.split(r'[\s,|;]+', symbols.strip('\n\t ,|;'))
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
        

    # initialize
    url_base = 'https://finance.yahoo.com/quote/'
    headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 \
                                (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    print('Start Download Detailed Info')
    print('Download speed : {} sec/download'.format(round(speed, 2)))
    print()

    
    with requests.Session() as sess:
        with ThreadPoolExecutor() as executor:

            # initialize outer retry loop
            data = [] # list to accumulate extracted data
            i_outer_loop = 0


            # outer loop to retry download & process
            while symbols and (i_outer_loop <= retry):

                # initialize inner loops
                total = len(symbols)
                print('Loop {} , total {} detailed info to download'.format(i_outer_loop, total) )
                pool = {} # container for threads
                t0 = time.perf_counter()


                # inner download loop
                for i, symbol in enumerate(symbols):

                    # speed control
                    wait = max(0.0, speed*i - (time.perf_counter()-t0) )
                    time.sleep(wait)

                    # request download html
                    url = url_base + symbol
                    pool[symbol] = executor.submit(sess.get, url, headers=headers)

                    # show progress status
                    if verbose:
                        _progress_status(i, total, prepend='  Requests Sent: ')
                    else:
                        _progress_bar(i, total)

                    
                # list to store symbols of failed download
                failed_symbols = []

                
                # inner loop to scrap downloaded htmls
                for symbol, job in pool.items():

                    # try getting downloaded contents (0 content considered success)
                    try:
                        html = job.result().text
                        data.append(_process_details(html))

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


    # count total downloaded info
    print('Total {} detailed info have been downloaded'.format(len(data)))
    
    return pd.DataFrame(data).set_index('symbol')

                        
def _process_details(html):
    '''helper function to transform html (str) into a dict'''
    data = html.split('root.App.main =')[1].split('(this)')[0].split(';\n}')[0].strip()
    data = json.loads(data)['context']['dispatcher']['stores']['QuoteSummaryStore']
    data = json.dumps(data).replace('{}', 'null')
    data = re.sub(r'\{[\'|\"]raw[\'|\"]:(.*?),(.*?)\}', r'\1', data)
    data = json.loads(data)

    data_dict = {}
    for item in data.values():
        if isinstance(item, dict): 
            for k, v in item.items():
                if (not isinstance(v, (dict,list))) and (v is not None):
                    data_dict[k] = v
    return data_dict







#------------------------- Testing -------------------------#
if False:
    info = download_info(symbols=['TSLA', '3738.HK', 'NNDM', 'HKD=X', '^HSI', 'BTC-USD'],
                         max_url_len=75)

    info = download_info(symbols='tsm \naapl, goog|fb ,  \n  ',
                         max_url_len=70)

    symbols = list(pd.read_csv('symbols.csv', header=None)[0])
    info = download_info(symbols, max_url_len=8000)


    



    details = download_details(['TSLA', 'ASDASD', '0981.HK', 'AAPL', 'HKD=X', '^HSI'],
                               speed=0.25, retry=1, parallel=False)
    
    details = download_details(['TSLA', 'ASDASD', '0981.HK', 'AAPL', 'HKD=X', '^HSI'],
                               speed=0.1, retry=1, parallel=True)


    headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 \
                                (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    html = requests.get('https://finance.yahoo.com/quote/tsm', headers=headers).text
    data_dict = _process_details(html)

    
















