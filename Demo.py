# -*- encoding:utf-8 -*-
"""
    使用sklearn的parallel作为demo
"""
import numpy as np
from ProcessMonitor import add_process_wrapper
from sklearn.externals.joblib import Parallel
from sklearn.externals.joblib import delayed
import time

from concurrent.futures import ProcessPoolExecutor

__author__ = 'BBFamily'

"""
    只需要在具体process job @add_procee_wrapper就ok了
"""


@add_process_wrapper
def do_process_job(jb):
    c = count(jb)
    end_tick = 100
    for cb in c:
        time.sleep(1)
        if cb % 10 == 0:
            print(cb)
        if end_tick < cb:
            break
    return jb


def when_done(r):
    print('job {} done:'.format(r.result()))


def make_parallel_poll_jobs():
    with ProcessPoolExecutor() as pool:
        n_jobs = 10
        for jb in np.arange(0, n_jobs):
            future_result = pool.submit(do_process_job, jb)
            future_result.add_done_callback(when_done)


def make_parallel_jobs():
    n_jobs = 10
    parallel = Parallel(
        n_jobs=n_jobs, verbose=0, pre_dispatch='2*n_jobs')

    out = parallel(delayed(do_process_job)(jb) for jb in np.arange(0, n_jobs))
    return out


def count(n):
    while True:
        yield n
        n += 1


if __name__ == "__main__":
    make_parallel_jobs()
