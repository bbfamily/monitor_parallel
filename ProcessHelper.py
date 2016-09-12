# -*- encoding:utf-8 -*-
from __future__ import division

import psutil

__author__ = 'BBFamily'


def pids():
    return psutil.pids()


def is_living(pid):
    return pids().count(pid) > 0


def suspend(pid):
    if is_living(pid):
        p = psutil.Process(pid)
        p.suspend()


def resume(pid):
    if is_living(pid):
        p = psutil.Process(pid)
        p.resume()


def terminate(pid):
    if is_living(pid):
        p = psutil.Process(pid)
        p.terminate()


def info(pid):
    p = psutil.Process(pid)
    p_info = {}
    p_info.update(base_info(pid, p))
    p_info.update(run_info(pid, p))
    p_info.update(io_info(pid, p))
    p_info.update(core_info(pid, p))
    return p_info


def base_info(pid, p=None):
    if p is None:
        p = psutil.Process(pid)

    name = p.name()
    exe = p.exe()
    cwd = p.cwd()
    cmdline = p.cmdline()
    username = p.username()

    return {'name': name, 'exe': exe, 'cwd': cwd, 'cmdline': cmdline, 'username': username}


def run_info(pid, p=None):
    if p is None:
        p = psutil.Process(pid)

    status = p.status()
    create_time = p.create_time()
    uids = p.uids()
    gids = p.gids()

    return {'status': status, 'create_time': create_time, 'uids': uids, 'gids': gids}


def io_info(pid, p=None):
    if p is None:
        p = psutil.Process(pid)

    # io_counters = p.io_counters()
    open_files = p.open_files()
    connections = p.connections()
    num_threads = p.num_threads()
    num_fds = p.num_fds()
    # only sudo excute inner will raise exception
    # threads = p.threads()

    ppid = p.ppid()

    return {'open_files': open_files, 'connections': connections,
            'num_threads': num_threads, 'num_fds': num_fds, 'ppid': ppid}


def core_info(pid, p=None):
    if p is None:
        p = psutil.Process(pid)

    cpu_times = p.cpu_times()
    cpu_percent = p.cpu_percent(interval=1.0)

    memory_percent = p.memory_percent()
    memory_info = p.memory_info()
    # only sudo excute inner will raise exception
    # memory_maps = p.memory_maps()

    return {'cpu_times': cpu_times, 'cpu_percent': cpu_percent,
            'memory_percent': memory_percent, 'memory_info': memory_info}
