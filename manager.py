# -*- coding: utf-8 -*-
from web import ChinaRailway
from requests.exceptions import ConnectionError
import traceback


def run():
    cr = ChinaRailway()
    cr.login()
    cr.refresh()


if __name__ == '__main__':
    while True:
        try:
            run()
            break
        except ConnectionError:
            traceback.print_exc()
            continue
        except Exception:
            raise
