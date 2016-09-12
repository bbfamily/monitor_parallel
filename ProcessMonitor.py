# -*- encoding:utf-8 -*-
"""

控制mul process挂起及恢复
避免长时间任务连续占据cpu，通过监控
classmethod add_procee进来的process
运行时间来确保cpu连续长时间稳定运行
ConfigParser+socket方式进程间传递消息，没有
使用Queue、Pipes目的一简单插入成熟模块
目的二适用于各个开源成熟并行框架如parallel等

"""
from __future__ import print_function

import ConfigParser
import datetime
import functools
import logging
import os
import socket
import textwrap
import threading
import time
from itertools import chain
from pprint import pprint

from enum import Enum

import ProcessHelper

__author__ = 'BBFamily'

K_DEFAULT_CT_WORK_PERIOD = 58 * 80  # 默认子进程最长工作时间
K_DEFAULT_REST_PERIOD = 58 * 12  # 默认子进程挂起休息时间

K_CMD_PNAME = 'data/p_cmd'
K_CMD_SOCKET_PNAME = 'data/p_cmd_socket'
K_CMD_PCMD = 'p_cmd'
K_CMD_PCMD_ADD_HEAD = 'add_pid'

K_CMD_UCMD = 'u_cmd'
K_CMD_UCMD_SA = 'stop_all'
K_CMD_UCMD_BA = 'begin_all'

g_loop_period = 1  # loop任务工作间隔
g_try_cnt = 3  # cf重试次数

dir_name = os.path.dirname(K_CMD_PNAME)
if not os.path.exists(dir_name):
    os.makedirs(dir_name)


def add_process_wrapper(func):
    """
        添加进程入口装饰器
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        ProcessMonitorClass.add_process(os.getpid())
        return func(*args, **kwargs)

    return wrapper


class TaskEnum(Enum):
    E_MONTH_TASK = 'month_task'
    E_WEEK_TASK = 'week_task'
    E_DAY_TASK = 'day_task'


class ProcessMonitorClass(object):
    @classmethod
    def add_process_by_socket(cls, pid):
        # noinspection PyBroadException
        try:
            client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client.connect(K_CMD_SOCKET_PNAME)
            client.send(str(pid))
            client.close()
        except Exception:
            '''
                如果是先跑多任务，后启动监控必然这里crash，这种只能依靠配置文件了
            '''
            pass
            # print('add_procee_by_scoket exception: ')

    s_added_pids = []

    @classmethod
    def add_process(cls, pid):
        """
            需要添加监控的进程唯一需要：ProcessMonitorClass.add_procee(os.getpid())
        """
        if pid <= 0:
            return

        cls.add_process_by_socket(pid)

        # noinspection PyBroadException
        try:
            if cls.s_added_pids.count(pid) > 0:
                '''
                    只针对添加进程的s_added_pids
                '''
                return

            cf = ConfigParser.ConfigParser()
            if not os.path.exists(K_CMD_PNAME):
                cls.__config_init(cf)
            else:
                try_cnt = 2 * g_try_cnt
                while try_cnt > 0:
                    sus = cf.read(K_CMD_PNAME)
                    if len(sus) > 0:
                        break
                    time.sleep(0.1)
                else:
                    return

            cls.s_added_pids.append(pid)
            option = K_CMD_PCMD_ADD_HEAD + str(pid)
            options = cf.options(K_CMD_PCMD)
            if options.count(option) > 0:
                return

            try_cnt = g_try_cnt
            while True:
                cf.read(K_CMD_PNAME)
                options = cf.options(K_CMD_PCMD)
                if options.count(option) > 0:
                    break

                if try_cnt <> g_try_cnt:
                    """
                        除来第一次之外都sleep一下
                    """
                    print('add_procee retry＝%d pid=%d' % (try_cnt, pid))
                    time.sleep(1)

                cf.set(K_CMD_PCMD, option, pid)

                with open(K_CMD_PNAME, 'w') as f:
                    cf.write(f)

                try_cnt -= 1
                if try_cnt == 0:
                    print('add_procee failed pid: ' + str(pid))
                    break
        except Exception:
            """
                不应该影响外部
            """
            pass
            # logging.exception(e)

    @classmethod
    def __config_init(cls, cf):
        cf.read(K_CMD_PNAME)

        try:
            """
                进程之间通信的cmd
            """
            if cf.sections().count(K_CMD_PCMD) == 0:
                cf.add_section(K_CMD_PCMD)

            """
                手动输入文件与主进程之间的cmd， 手动修改配置文件方式
                挂起，继续监控进程，不推荐
            """
            if cf.sections().count(K_CMD_UCMD) == 0:
                cf.add_section(K_CMD_UCMD)
            cf.set(K_CMD_UCMD, K_CMD_UCMD_SA, '0')
            cf.set(K_CMD_UCMD, K_CMD_UCMD_BA, '0')
        except Exception, e:
            logging.exception(e)

        with open(K_CMD_PNAME, 'w') as f:
            cf.write(f)

    def __init__(self, print_pool=None, max_ct_work_period=K_DEFAULT_CT_WORK_PERIOD,
                 rest_period=K_DEFAULT_REST_PERIOD, **kwargs):
        self.max_ct_work_period = max_ct_work_period
        self.rest_period = rest_period
        self.subprocess = {}
        self.rest_subprocess = {}

        self.cf = ConfigParser.ConfigParser()
        self.stop_all = 0
        self.begin_all = 0
        self.rest_time = False
        self.working_monitor = False
        self.print_pool = print_pool
        self.__init_kwags(**kwargs)
        ProcessMonitorClass.__config_init(self.cf)
        """
            ct_thread一直就运行，因为cpu温度等任务，开始，结束只是控制 
            ck_thread 也尽量只通过socket来传递消息
        """
        self._start_loop()

    def __enter__(self):
        pass

    def __exit__(self, *args):
        pass

    def __str__(self):
        if len(self.subprocess) > 0 or len(self.rest_subprocess) > 0:
            return ' len = ' + str(len(self.subprocess) + len(self.rest_subprocess)) + '\n' + \
                   ' awake: ' + str(self.subprocess) + '\n' + \
                   ' reset: ' + str(self.rest_subprocess) + '\n'
        return 'monitor process list is empty!'

    __repr__ = __str__

    def __iter__(self):
        for key in chain([self.subprocess.keys(), self.rest_subprocess.keys()]):
            yield (key, self[key])

    def __getitem__(self, pid):
        if len(self.subprocess) > 0 and pid in self.subprocess:
            return self.subprocess[pid]
        if len(self.rest_subprocess) > 0 and pid in self.rest_subprocess:
            return self.rest_subprocess[pid]
        return None

    def __len__(self):
        return len(self.subprocess) + len(self.rest_subprocess)

    def __call__(self):
        if len(self) == 0:
            self.__print_proxy('monitor process list is empty!')
            return

        self.__print_proxy(format('start', '*^26s'))
        for (pid, start_time) in self.subprocess.items():
            tips = ['doing', (pid, start_time), ProcessHelper.core_info(pid)]
            self.__print_proxy(':'.join(str(s) for s in tips))
        for (pid, start_time) in self.rest_subprocess.items():
            tips = ['reset', (pid, start_time), ProcessHelper.core_info(pid)]
            self.__print_proxy(':'.join(str(s) for s in tips))
        self.__print_proxy(format('end', '*^26s'))

    def end_work(self):
        """
        停止工作 对外
        :return:
        """
        if not self.working_monitor:
            return

        self.subprocess.clear()
        self.rest_subprocess.clear()
        self.working_monitor = False
        self.__print_proxy('process monitor will end work!')
        """
            采取结束监控也不销毁文件的方式
        """
        # if os.path.exists(K_CMD_PNAME):
        #     os.remove(K_CMD_PNAME)

    def start_work(self):
        """
        开始工作，对外
        :return:
        """
        if self.working_monitor:
            return

        self.working_monitor = True
        self.__print_proxy('process monitor working...')

    def rest_all(self, rest_time=False):
        """
        挂起所有，对外
        :param rest_time:
        :return:
        """
        self.rest_time = rest_time
        for pid in self.subprocess.keys():
            self._do_rest(pid)

    def awake_all(self):
        """
        恢复所有，对外
        :return:
        """
        self.rest_time = False
        for pid in self.rest_subprocess.keys():
            self._do_awake(pid)

    def kill_all(self):
        """
        结束所有，对外
        :return:
        """
        all_ps = chain(self.subprocess.keys(), self.rest_subprocess.keys())
        for pid in all_ps:
            ProcessHelper.terminate(pid)
        """
            TODO:
            1 有可能没有kill掉， 没有再次检查
            2 针对kill 添加kill －9增加kill在普通kill失败后
        """
        self.subprocess.clear()
        self.rest_subprocess.clear()

    def manual_add_pid(self, pid):
        """
        手动添加进程，对外
        :param pid:
        :return:
        """
        ProcessMonitorClass.add_process(pid)
        self._add_process(pid)

    def _check_living(self, pid, option=None):
        """
        进程活着就返回，否则尝试从config中remove
        :param pid:
        :param option:
        :return:
        """
        if ProcessHelper.is_living(pid):
            return True

        try_cnt = g_try_cnt
        while True:
            self.cf.read(K_CMD_PNAME)
            options = self.cf.options(K_CMD_PCMD)
            if option is None:
                option = K_CMD_PCMD_ADD_HEAD + str(pid)
            if options.count(option) == 0:
                break

            if try_cnt <> g_try_cnt:
                '''
                    除来第一次之外都sleep一下
                '''
                time.sleep(1)

            self.cf.remove_option(K_CMD_PCMD, option)
            with open(K_CMD_PNAME, 'w') as f:
                self.cf.write(f)

            try_cnt -= 1
            if try_cnt == 0:
                self.__print_proxy('check_living failed pid: ' + str(pid))
                break
        return False

    def __print_proxy(self, *args):
        if len(args) == 0:
            wt = textwrap.fill(args[0], 50, subsequent_indent='    ')
            pprint(wt)
            if self.print_pool is not None:
                self.print_pool(wt)
        else:
            pprint(*args)
            if self.print_pool is not None:
                self.print_pool(*args)

    def _pick_p_cmd(self):
        """
            试图拾起外部要监控的进程记录，如
            config中的已dead删除记录
            :return:
        """
        self.cf.read(K_CMD_PNAME)

        items = self.cf.items(K_CMD_PCMD)
        if len(items) <= 0:
            return

        for item in items:
            if not isinstance(item, tuple) or not len(item) == 2:
                return
            pid = int(item[1])
            option = item[0]
            if pid > 0:
                if self._check_living(pid, option):
                    self._add_process(pid)

    def _execute_u_cmd(self):
        """
         执行直接从外部命令文件设置的命令
        :return:
        """
        self.cf.read(K_CMD_PNAME)

        self.stop_all = self.cf.getint(K_CMD_UCMD, K_CMD_UCMD_SA)
        self.begin_all = self.cf.getint(K_CMD_UCMD, K_CMD_UCMD_BA)

        if self.stop_all > 0 & self.begin_all > 0:
            raise ValueError('stop_all and begin_all 0 0 !!!')

        if self.stop_all > 0:
            self.rest_all()

        if self.begin_all > 0:
            self.awake_all()

    def __check_doing_process(self):
        end_time = datetime.datetime.now()

        for (pid, start_time) in self.subprocess.items():
            if (end_time - start_time).seconds > self.max_ct_work_period:
                self._do_rest(pid)

    def __check_rest_process(self):
        end_time = datetime.datetime.now()
        for (pid, start_time) in self.rest_subprocess.items():
            if (end_time - start_time).seconds > self.rest_period:
                self._do_awake(pid)

    def __check_process_living(self):
        for (pid, start_time) in self.subprocess.items():
            if not self._check_living(pid):
                del self.subprocess[pid]
                self.__print_proxy('subprocess pid %d dead' % pid)

        for (pid, start_time) in self.rest_subprocess.items():
            if not self._check_living(pid):
                del self.rest_subprocess[pid]
                self.__print_proxy('rest_subprocess pid %d dead' % pid)

    def _do_awake(self, pid):

        if self.rest_time:
            """
                长暂停，只有手动继续才继续
            """
            return
        self.__resume(pid)
        if pid in self.rest_subprocess:
            del self.rest_subprocess[pid]

        if pid not in self.subprocess:
            start = datetime.datetime.now()
            self.subprocess[pid] = start

    def _do_rest(self, pid):
        self.__suspend(pid)
        if pid in self.subprocess:
            del self.subprocess[pid]

        if pid not in self.rest_subprocess:
            start = datetime.datetime.now()
            self.rest_subprocess[pid] = start

    def __suspend(self, pid):
        tips = 'pid %d suspend :%s' % (pid, str(datetime.datetime.now()))
        self.__print_proxy(tips)
        ProcessHelper.suspend(pid)

    def __resume(self, pid):
        tips = 'pid %d resume :%s' % (pid, str(datetime.datetime.now()))
        self.__print_proxy(tips)
        ProcessHelper.resume(pid)

    def do_loop_monitor(self):
        if self.working_monitor:
            self._pick_p_cmd()
            self.__check_doing_process()
            self.__check_rest_process()

    def __do_loop_day_work(self):
        for d_task in self.day_task:
            d_task()

    def __do_loop_week_work(self):
        for w_task in self.week_task:
            w_task()

    def __do_loop_month_work(self):
        for m_task in self.month_task:
            m_task()

    def _do_loop_work(self):
        """
        监控主执行部分，分为频繁任务与长非频繁任务
        :return:
        """
        loop_days = 1
        while True:
            self.__do_loop_day_work()
            if loop_days % 5 == 0:
                self.__do_loop_week_work()
            if loop_days % 30 == 0:
                self.__do_loop_month_work()

            loop_days = loop_days + 1 if loop_days < 30 else 1

            time.sleep(g_loop_period)

    def __init_kwags(self, **kwargs):
        """
        初始化内置任务队列
        :param kwargs:
        :return:
        """
        self.month_task = [self.__check_process_living]
        self.week_task = [self._execute_u_cmd]
        self.day_task = [self.do_loop_monitor]
        if kwargs is None:
            return

        for key in kwargs.keys():
            # noinspection PyUnresolvedReferences
            if key == TaskEnum.E_MONTH_TASK.value and isinstance(kwargs[key], list):
                self.month_task.extend(kwargs[key])
            elif key == TaskEnum.E_WEEK_TASK.value and isinstance(kwargs[key], list):
                self.week_task.extend(kwargs[key])
            elif key == TaskEnum.E_DAY_TASK.value and isinstance(kwargs[key], list):
                self.day_task.extend(kwargs[key])
            else:
                print(key)
                raise TypeError('__init_kwags pass error kwargs type!')

    def _do_socket_work(self):
        if os.path.exists(K_CMD_SOCKET_PNAME):
            os.unlink(K_CMD_SOCKET_PNAME)

        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(K_CMD_SOCKET_PNAME)
        server.listen(0)
        while True:
            self.__print_proxy('socket waiting...')
            connection, _ = server.accept()
            pid = connection.recv(1024)
            self.__print_proxy('recv pid by socket pid =' + pid)
            self._add_process(int(pid))
            connection.close()

    def _start_loop(self):
        ct_thread = threading.Thread(target=self._do_loop_work)
        ct_thread.setDaemon(True)
        ct_thread.start()

        sk_thread = threading.Thread(target=self._do_socket_work)
        sk_thread.setDaemon(True)
        sk_thread.start()

    def _add_process(self, pid):
        """
        加入内存中的监控队列
        :param pid:
        :return:
        """
        if pid in self.subprocess or pid in self.rest_subprocess:
            return
        start = datetime.datetime.now()
        self.subprocess[pid] = start
        self.__print_proxy('_add_process: ' + str(pid))
