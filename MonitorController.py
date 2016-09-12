# -*- encoding:utf-8 -*-
"""
    封装process monitor的
    ui层，使用traitsui， chaco
"""

from __future__ import print_function

import os
import platform

from collections import deque
import numpy as np
from ProcessMonitor import ProcessMonitorClass
from ProcessMonitor import TaskEnum
from traits.api import HasTraits, Instance, List, Button, Str, Int
from traitsui.api import View, UItem, Item, ListStrEditor, Group

__author__ = 'BBFamily'

K_CPU_TEMP_CNT = 100

"""
    是否开启cpu及温度监控
"""
g_enable_cpu_monitor = False
if g_enable_cpu_monitor:
    """
        conda的chaco会导致问题如果是conda环境就不要开了
    """
    from chaco.api import Plot, ArrayPlotData
    import CpuHelper


class MonitorController(HasTraits):
    print_pool = List(Str)
    cpu_pool = List(Str)

    if g_enable_cpu_monitor:
        plot_cpu_temp = Instance(Plot)

    start_work = Button()
    end_work = Button()
    refresh_str = Button()
    refresh_call = Button()
    clear_pool = Button()
    suspend_all = Button()
    suspend_all_time = Button()
    kill_all = Button()
    resume_all = Button()

    manual_add = Button()
    manual_pid = Int

    def __init__(self):
        super(MonitorController, self).__init__()
        self.title = 'Process Monitor'
        run_task = dict()
        if g_enable_cpu_monitor:
            run_task.update({TaskEnum.E_WEEK_TASK: [self._cpu_change]})
            self._cpu_init()

        self.pMonitor = ProcessMonitorClass(self._add_print_pool, **run_task)

    def default_title(self):
        self.title = 'Process Monitor'

    def __do_cpu_temp_plot(self, temp):
        x = np.arange(0, len(self.deque_cpu))
        y = self.deque_cpu

        plot_data = ArrayPlotData(x=x, y=y)
        plot = Plot(plot_data)

        self.renderer = plot.plot(("x", "y"), color="blue")[0]
        plot.title = "cpu temperature: " + str(temp)
        self.plot_cpu_temp = plot

    def __do_cpu_inv(self):
        cpu_percent = CpuHelper.cpu_percent()
        self.cpu_pool = ['cpu  %d:  %f' % (cpu_index, percent) for cpu_index, percent in enumerate(cpu_percent)]
        self.cpu_pool.insert(0, 'mean cpu:  %f' % (np.mean(cpu_percent)))

    def _cpu_change(self):
        temp, temp_str = CpuHelper.get_cpu_temp_proxy()
        self.deque_cpu.append(temp)
        self.__do_cpu_temp_plot(temp)

        self.__do_cpu_inv()

    def _cpu_init(self):
        temp, temp_str = CpuHelper.get_cpu_temp_proxy()
        self.deque_cpu = deque(maxlen=K_CPU_TEMP_CNT)
        self.deque_cpu.extend((np.ones(K_CPU_TEMP_CNT) * temp).tolist())
        self.__do_cpu_temp_plot(temp)

        self.__do_cpu_inv()

    def _start_work_fired(self):
        self.pMonitor.start_work()

    def _end_work_fired(self):
        self.pMonitor.end_work()

    def _refresh_str_fired(self):
        self.print_pool.append(str(self.pMonitor))

    def _refresh_call_fired(self):
        self.pMonitor()

    def _suspend_all_fired(self):
        self.pMonitor.rest_all(rest_time=True)

    def _suspend_all_time_fired(self):
        self.pMonitor.rest_all()

    def _resume_all_fired(self):
        self.pMonitor.awake_all()

    def _kill_all_fired(self):
        self.pMonitor.kill_all()

    def _clear_pool_fired(self):
        self.print_pool = []
        cmd_clear = 'cls' if platform.system().lower().find("windows") >= 0 else 'clear'
        os.system(cmd_clear)

    def _manual_add_fired(self):
        self.pMonitor.manual_add_pid(self.manual_pid)

    def _add_print_pool(self, *args):
        self.print_pool.extend(args)

    view = View(
        Group(
            UItem('print_pool', editor=ListStrEditor(auto_add=False)),
            Item('start_work', label=u'监控开始', show_label=False),
            Item('end_work', label=u'监控结束', show_label=False),
            # Item('refresh_str', label=u'刷新str', show_label=False),
            Item('refresh_call', label=u'刷新call', show_label=False),
            Item('suspend_all', label=u'挂起所有', show_label=False),
            Item('suspend_all_time', label=u'挂起所有(定时失效)', show_label=False),
            Item('resume_all', label=u'恢复所有', show_label=False),
            Item('kill_all', label=u'杀死所有', show_label=False),
            Item('clear_pool', label=u'屏幕clear', show_label=False),

            Group(
                Item('manual_add', label=u'手动添加pid', show_label=False),
                Item('manual_pid', tooltip=u"输入pid后，按‘手动添加pid’", width=360, show_label=False),
                orientation='horizontal',
                show_border=True
            ),
            label=u'控制处理',
            show_border=True
        )

        #  如果打开cpu监控g_enable_cpu_monitor且安装了chaco等
        #  打开下面代码onda的chaco会导致问题如果是conda环境就不要开了
        # ,
        # Group(
        #     Item('temp', label=u'cpu温度监控关闭，g_enable_cpu_monitor控制', show_label=False,
        #         width=500, height=320),
        #     label = u'信息显示',
        #     show_border = True,

        #     Item('plot_cpu_temp', editor=ComponentEditor() if g_enable_cpu_monitor
        #           else label=u'cpu温度监控关闭，g_enable_cpu_monitor控制', show_label=False,
        #         width=500, height=320),
        #     UItem('cpu_pool', editor=ListStrEditor(auto_add=False)),
        #     label = u'信息显示',
        #     show_border = True,
        # ),
        # resizable = True,
    )


if __name__ == "__main__":
    MonitorController().configure_traits()
    # help(Item)
