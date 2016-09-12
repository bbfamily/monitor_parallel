# -*- encoding:utf-8 -*-
from __future__ import print_function

import platform

import psutil
from osx_cpu_temp import get_cpu_temp

__author__ = 'BBFamily'


def get_cpu_temp_proxy():
    """
        暂时只支持mac，但是也会返回0.0，方便统一处理
    """
    if platform.system().lower().find("windows") >= 0:
        ret_text = 'get_cpu_temp only support mac now!'
        print(ret_text)
        return 0.0, ret_text
    return get_cpu_temp()


def cpu_times():
    return psutil.cpu_times()


def cpu_count(logical=True):
    return psutil.cpu_count(logical=logical)


def cpu_percent(times=False, interval=1, percpu=True):
    func = psutil.cpu_times_percent if times else psutil.cpu_percent

    return func(interval=interval, percpu=percpu)
