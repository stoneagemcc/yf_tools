# show currently done progress
# (i_done=0, n_total=10) shows 1/10 or 10%
# i_done=9, n_total=10) shows 10/10 or 100%



#------------------------- Description -------------------------#
if False:
    
    ### _progress_status(i_done, n_total, max_steps) ###
    n_total = 7
    for i_done in range(n_total):
        _progress_status(i_done, n_total, max_steps=4, pct=True)
    


    ### _progress_bar(i_done, n_total, width) ###
    import time
    n_total = 7
    for i_done in range(n_total):
        time.sleep(0.5)
        _progress_bar(i_done, n_total, width=30, symbol='.')



        
#------------------------- Definition -------------------------#
def _progress_status(i_done, n_total, max_steps=100,
                   prepend='Progress: ', postpend='', pct=False, n_digit=2):
    '''helper function to show currently done progress'''
    curr_idx = ((i_done + 1) * max_steps) // n_total
    prev_idx = (i_done * max_steps) // n_total
    
    if curr_idx > prev_idx:
        if pct:
            pct_value = round(100 * (i_done + 1) / n_total, n_digit)
            print(f'{prepend}{pct_value:.{n_digit}f}%{postpend}')
        else:
            print(f'{prepend}{i_done + 1}/{n_total}{postpend}')
            


def _progress_bar(i_done, n_total, width=30, n_digit=2, symbol='.'):
    '''update progress bar when called'''
    n_left = ((i_done + 1) * width) // n_total
    n_right = width - n_left
    pct_value = round(100 * (i_done + 1) / n_total, n_digit)
    
    # format: [...............               ] 50%
    print(f'\r[{symbol*n_left}{" "*n_right}] {pct_value:.{n_digit}f}%',
          sep='', end='', flush=True)
    
    if (i_done + 1) == n_total:
        print()
  


        

"""
def _show_progress(i, N, max_steps=100, prepend='Progress: ', postpend='', pct=False):
    '''helper function to show current progress'''
    step_now = int( ((i+1)/N) * max_steps )
    step_prev = int( (i/N) * max_steps )
    if step_now != step_prev:
        if pct:
            print(prepend + str(round(100 * step_now / max_steps, 2)) + '%' + postpend)
        else:
            print(prepend + '{} / {}'.format(i+1, N) + postpend)
    return None



def _show_progress_bar(i, N,  width=30, num_dp=2, symbol='.'):
    '''update progress bar by calling it'''
    pct = (i+1) / N
    n_left = round(width * pct)
    n_right = width - n_left
    # format: [...............               ] 50%
    print('\r[{a}{b}] {c:.{num_dp}f}%'.format(
             a=symbol*n_left,
             b=' '*n_right,
             c=round(pct*100, num_dp),
             num_dp=num_dp
             ),
             sep='', end='', flush=True)
    if N-i == 1:
        print()
"""
  
    
