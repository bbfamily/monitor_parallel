# -*- encoding:utf-8 -*-
import ZEnv


def show_msg(title, msg):
    if ZEnv.is_mac_os():
        import ShowMsgMac
        ShowMsgMac.show_msg(title, msg)
    else:
        import ShowMsgWin
        ShowMsgWin.show_msg(title, msg)


if __name__ == '__main__':
    show_msg("title", "popup info")
