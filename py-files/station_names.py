# -*- coding: utf-8 -*-
import requests


if __name__ == '__main__':

    text = requests.get('https://kyfw.12306.cn/otn/resources/js/framework/station_name.js?station_version=1.9109').text
    text = text.replace('var station_names =', '')

    stations = text.split('@')
    stations.pop(0)

    station_names = {}
    for line in stations:
        info = line.split('|')
        station_names[info[1]] = info[2]

    with open('stations.py', 'w', encoding='utf-8') as f:
        f.write(str(station_names))
