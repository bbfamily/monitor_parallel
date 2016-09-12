# -*- encoding:utf-8 -*-
import os
import subprocess
import logging

g_this_file = os.path.realpath(__file__)
g_this_folder = os.path.dirname(g_this_file)

def get_cpu_temp():
    cmd = g_this_folder + '/osx-cpu-temp-master/osx-cpu-temp'

    temp = 0.0
    try:
        temp_str = subprocess.check_output(cmd, shell=True).decode('gb2312')
        temp = float(temp_str[:-3])
    except Exception, e:
        logging.exception(e)

    return temp, temp_str
