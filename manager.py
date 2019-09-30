# -*- coding: utf-8 -*-
from web import ChinaRailway


def run():
    cr = ChinaRailway()
    cr.login()
    cr.refresh()


if __name__ == '__main__':
    run()
