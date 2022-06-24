import requests
import numpy as np
import pandas as pd
import re
import time
from concurrent.futures import ThreadPoolExecutor



#------------------------- Description -------------------------#

if False:
    from yf_download_symbols import * # import itself functions

    
    # get url of filtered US yf screener (for further symbols download)
    url = get_symbols_download_url(us_or_hk, retry=1, timeout=5)

    # Inputs
    # us_or_hk : 'US' or 'HK'

    # Outputs
    # url of filtered yf screener

    # Main logic flow (US for example):
    # (1) create Chrome webdriver
    # (2) get initial screener page: 'https://finance.yahoo.com/screener/equity/new'
    # (3) remove all initial choices
    # (4) click 'Add another filter'
    # (5) choose 'Region' & 'Exchange'
    # (6) click 'Close'
    # (7) click '+' of 'Region'
    # (8) search 'United States' in 'Region'
    # (9) choose 'United States' in 'Region'
    # (10) close 'Region' dropdown menu
    # (11) click '+' of 'Exchange'
    # (12) choose ['NasdaqGS', 'NasdaqCM', 'NYSE', 'NasdaqGM'] in 'Exchange'
    # (13) close 'Exchange' dropdown menu
    # (14) click 'Find Stocks'
    # (15) retrieve current url


    
    
    #download a list of symbols from yahoo finance screener
    symbols = download_symbols(url, count=250, speed=0.25, retry=0, timeout=(3.05,5))

    # Inputs
    # url : url of filtered yf screener
    # count : num of symbols per page
    # speed : sec per requested download
    # retry : num of download retry (to maximize downloaded content)
    # timeout : sec to request timeout [specify sec / specify (sec: connect timeout, sec: response timeout)]

    # Outputs
    # list of symbols [list of str]
    
    # Main logic flow:
    # (1) create requests.Session for persisting connection
    # (2) 1st request to get estimated num of symbols 
    # (3) create ThreadPoolExecutor for multi-thread downloads
    # (4) Outer loop for overall download retry
    #   (4-1) Inner loop for multi-thread downloads
    #     (4-1-1) speed control
    #     (4-1-2) sumbit download task
    #   (4-2) Inner loop for processing downloads
    #     (4-2-1) try getting downloaded contents
    #     (4-2-2) accumulate download symbols to list
    #   (4-3) speed control before next outer retry loop
    # (5) retrun: reduced unique symbol list, sorted by download order
    





#------------------------- Definition -------------------------#
    
'''
# for function testing only
url='https://finance.yahoo.com/screener/unsaved/90dec0d0-08a2-438c-a66b-6b37bff8f12c' # expire in few days
count=250 # num of symbols downloaded each time
speed=0.1
retry=1
timeout=(3.05,5)
'''

def download_symbols(url, count=250, speed=0.25, retry=0, timeout=(3.05,5)):
    '''
    download a list of symbols from yahoo finance screener
    e.g. url='https://finance.yahoo.com/screener/unsaved/e7585fa5-86fc-40da-9202-b7ebeb3d7512' (will expire in few days)

    url : url of filtered yf screener
    count : num of symbols per page
    speed : sec per requested download
    retry : num of download retry (to maximize downloaded content)
    timeout : sec to request timeout [specify: sec / (sec: connect timeout, sec: response timeout)]
    
    -> list of symbols
    '''
    
    # process inputs
    count = int(np.clip(count, 1, 250)) # [1, 250] # [num of symbols per page]
    speed = float(max(speed, 0.0)) # [0.0, inf) # [sec per request]
    retry = int(max(retry, 0)) # [0, inf) # [num of retry]
    timeout = ( tuple( float(max(t, 0.0)) for t in timeout )
                   if isinstance(timeout, tuple)
                   else float(max(timeout, 0.0)) ) # [0.0, inf) # [sec to request timeout]

    
    # initialize
    regex = re.compile(r'">([-^=.A-Z0-9]+)</a><div class="')
    #regex = re.compile(r'/quote/([-.A-Z0-9]+)\?p=\1')
    symbols = []
    headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 \
                                (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}


    with requests.Session() as sess:
        
        # 1st download to extract symbol num
        html = sess.get(url, headers=headers, timeout=timeout).text
        regex_estimate = re.compile(r' of ([0-9]+) results') # extract symbol num
        estimated = int(regex_estimate.search(html).group(1))
        print('Estimated {} symbols will be downloaded'.format(estimated))
        
        
        with ThreadPoolExecutor() as executor:

            # initialize outer retry loop
            offsets = list(range(0, estimated, count))
            
            # outer loop to retry download & process contents
            for i_outer_loop in range(retry + 1):

                # initialize inner loops
                print('Loop {}'.format(i_outer_loop))
                pool = {} # container for threads
                t0 = time.perf_counter()

                # inner loop to download
                for i_wait, offset in enumerate(offsets):

                    # speed control
                    wait = max(0.0, speed*i_wait - (time.perf_counter()-t0) )
                    time.sleep(wait) 

                    # request download
                    params = {'offset': offset, 'count': count}
                    pool[offset] = executor.submit(sess.get, url, params=params,
                                                   headers=headers, timeout=timeout)
                    print('  Download {} ~ {} symbols'.format(offset+1,
                                                                 min(offset+count, estimated) ))
                    
                # inner loop to process downloaded contents
                for offset, job in pool.items():

                    # try getting downloaded contents
                    try:
                        matches = regex.findall(job.result().text)
                        if not matches:
                            raise Exception
                        symbols.extend(matches) # accumulate symbols
                        
                    # if download failed / no content  
                    except Exception:
                        print('    [Err] Failed at {} ~ {} symbols'.format(offset+1,
                                                     min(offset+count, estimated) ))
                        
                # speed control before next outer retry loop
                if i_outer_loop < retry:
                    i_wait += 1
                    wait = max(0.0, speed*i_wait - (time.perf_counter()-t0) )
                    time.sleep(wait)


    # final process
    syms_unique = list(set(symbols))
    print('Total {} unique symbols are downloaded (Estimated {} symbols)\n'.format(
                            len(syms_unique), estimated) ) # maybe more than estimated
    
    return sorted(syms_unique, key=symbols.index) # same order as downloaded






from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time



def get_symbols_download_url(us_or_hk, retry=1, timeout=5):
    '''
    get url of filtered yf screener (for further symbols download)

    us_or_hk: 'US' or 'HK'
    retry : num of download retry if failed
    timeout : sec to timeout for loading page
    
    -> url of filtered yf screener
    '''
    us_or_hk = str.lower(us_or_hk)
    url = None
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    #chrome_options.add_argument("--disable-gpu")
    #chrome_options.add_argument("--window-size=1280,800")
    #chrome_options.add_argument("--allow-insecure-localhost")

    #driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)
    driver = webdriver.Chrome(ChromeDriverManager().install())
    driver.set_page_load_timeout(timeout)


    while (url is None) and (retry >= 0):
        retry -= 1

        try:
            driver.get('https://finance.yahoo.com/screener/equity/new')
            
            while True:
                try:
                    # remove all default choices
                    elem = driver.find_element_by_xpath("//button[@data-test='remove-filter']")
                    elem.click()
                except:
                    break


            # click 'Add another filter'
            #elem = driver.find_element_by_xpath("//span[contains(text(), 'Add another filter')]/../..")
            elem = driver.find_element_by_xpath("//span[text()='Add another filter']/../..")
            elem.click()


            # choose 'Region' & 'Exchange'
            elem = driver.find_element_by_xpath("//span[contains(text(), 'Region')]/../..")
            elem = elem.find_element_by_tag_name('input')
            elem.click()

            elem = driver.find_element_by_xpath("//span[contains(text(), 'Exchange')]/../..")
            elem = elem.find_element_by_tag_name('input')
            elem.click()

            # click 'Close'
            #elem = driver.find_element_by_xpath("//span[text()='Close']/..")
            #elem.click()
            elem = driver.find_element_by_xpath("//div[@data-test='filter-menu']")
            elem = elem.find_element_by_tag_name('button')
            elem.click()


            # click '+' of 'Region'
            elem = driver.find_element_by_xpath("//span[text()='Region']/../../..")
            elem = elem.find_element_by_tag_name('path')
            elem.click()

            if us_or_hk == 'us':
                # search 'United States' in 'Region'
                elem = driver.find_element_by_xpath("//input[@placeholder='Find filters']")
                elem.clear()
                elem.send_keys("United States")


                # choose 'United States' in 'Region'
                elem = driver.find_element_by_xpath("//span[text()='United States']/..")
                elem = elem.find_element_by_tag_name('input')
                elem.click()
            else:
                # search 'Hong Kong' in 'Region'
                elem = driver.find_element_by_xpath("//input[@placeholder='Find filters']")
                elem.clear()
                elem.send_keys("Hong Kong")


                # choose 'Hong Kong SAR China' in 'Region'
                elem = driver.find_element_by_xpath("//span[text()='Hong Kong SAR China']/..")
                elem = elem.find_element_by_tag_name('input')
                elem.click()
                

            # close 'Region' dropdown menu
            elem = driver.find_element_by_xpath("//div[@data-test='region-filter-dd-menu']")
            elem = elem.find_element_by_tag_name('button')
            elem.click()


            if us_or_hk == 'us':
                # click '+' of 'Exchange'
                elem = driver.find_element_by_xpath("//span[text()='Exchange']/../../..")
                elem = elem.find_element_by_tag_name('path')
                elem.click()


                # choose ['NasdaqGS', 'NasdaqCM', 'NYSE', 'NasdaqGM'] in 'Exchange'
                elem = driver.find_element_by_xpath("//span[text()='NasdaqGS']/..")
                elem = elem.find_element_by_tag_name('input')
                elem.click()

                elem = driver.find_element_by_xpath("//span[text()='NasdaqCM']/..")
                elem = elem.find_element_by_tag_name('input')
                elem.click()

                elem = driver.find_element_by_xpath("//span[text()='NYSE']/..")
                elem = elem.find_element_by_tag_name('input')
                elem.click()

                elem = driver.find_element_by_xpath("//span[text()='NasdaqGM']/..")
                elem = elem.find_element_by_tag_name('input')
                elem.click()


                # close 'Exchange' dropdown menu
                elem = driver.find_element_by_xpath("//div[@data-test='exchange-filter-dd-menu']")
                elem = elem.find_element_by_tag_name('button')
                elem.click()

            time.sleep(1)

            # click 'Find Stocks'
            elem = driver.find_element_by_xpath("//button[@data-test='find-stock']")
            elem.click()

            # avoid page being closed before getting the url
            time.sleep(2)
            url = driver.current_url
            print('url is successfully retrieved\n')
            
        except:
            print('timeout') # stop further loading if timeout

    driver.quit()
    if url is None:
        print('Failed to retrieve URL!!')
    return url





#------------------------- Testing -------------------------#
if False:
    # US - NYSE, NasdaqGS, NasdaqCM, NasdaqGM
    #symbols = download_symbols(url_us)

    # HK
    #symbols = download_symbols(url_hk)
    url_us = 'https://finance.yahoo.com/screener/unsaved/c52b99a7-d65d-4e1c-926c-ef7531b0689f' # US @ 2021-09-09
    url_hk = 'https://finance.yahoo.com/screener/unsaved/c0d84689-aded-41ef-84ca-25a9b1bf9f78' # HK @ 2021-09-09
    url='https://finance.yahoo.com/screener/unsaved/720f6779-31f1-41bb-b7fb-0558bd4af3a7' # expire in few days
    symbols = download_symbols(url, speed=0.0, retry=3)

    #pd.Series(list(symbols)).to_csv('symbols.csv', header=False, index=False)



















