# -*- coding: utf-8 -*-
import os
import sys
import time
from selenium import webdriver


def get_cookies(cls):
    """
    利用selenium获取cookies
    """
    _file_path = os.path.dirname(__file__)
    driver_path = os.path.abspath(os.path.join(_file_path, 'chromedriver'))
    driver = webdriver.Chrome(executable_path=driver_path)
    driver.get('https://www.12306.cn/index/index.html')

    # 等待页面加载
    _ = time.clock()
    cookies_num = len(driver.get_cookies())
    while cookies_num < 5:
        time.sleep(1)
        cookies_num = len(driver.get_cookies())
        if time.clock() > 10:
            cls.logger.warning('获取cookies超时 ×')
            sys.exit()

    cookies = []
    for c in driver.get_cookies():
        if c.get('name') in ['RAIL_DEVICEID', 'RAIL_EXPIRATION']:
            cookies.append(c)

    cls.logger.info('获取cookies √')
    return cookies
