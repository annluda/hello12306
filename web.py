# -*- coding: utf-8 -*-
"""
Author: An Lu Da
date: 2019-09-12
"""
import requests
import time
import urllib
import json
from lxml import etree

import urls
import settings
import chrome
from captcha.image import CaptchaImage
from stations import station_codes
from logger import get_logger


class ChinaRailway:
    def __init__(self):
        self.logger = get_logger()
        self.conf = settings
        self.urls = urls
        self.session = requests.Session()
        self._set_cookies()

    def _set_cookies(self):
        cookies = chrome.get_cookies(self)
        for c in cookies:
            self.session.cookies.set(c['name'], c['value'])

    def check_captcha(self, module='login'):
        """
        打码
        """
        # 获取验证码图片
        if module == 'login':
            image_url = 'https://kyfw.12306.cn/passport/captcha/captcha-image64?login_site=E&module=login&rand=sjrand'
        else:
            # module == 'passenger'
            image_url = ''  # TODO 订单页验证码URL
        response = self.session.get(image_url).json()
        image64 = response['image']

        # 识别验证码
        captcha = CaptchaImage(image64)
        answer = captcha.bypass()

        # 验证
        check_url = 'https://kyfw.12306.cn/passport/captcha/captcha-check'
        data = {
            'answer': answer,
            'login_site': 'E',
            'rand': 'sjrand'
        }
        response = self.session.post(check_url, data=data).json()
        if response['result_code'] == '4':
            self.logger.info('验证码 √')
            return answer
        else:
            self.logger.warning('验证码 ×')
            self.logger.warning(response)
            return False

    def login(self):
        """
        账号登录
        """
        captcha_answer = None
        while not captcha_answer:
            captcha_answer = self.check_captcha('login')
            if captcha_answer:
                form_data = {
                    'username': self.conf.username,
                    'password': self.conf.password,
                    'appid': 'otn',
                    'answer': captcha_answer
                }

                login_resp = self.session.post(self.urls.login, data=form_data).json()
                if login_resp['result_code'] == 0:
                    if self._uamtk():
                        self.logger.info('登录 √')
                    else:
                        self.logger.warning('登录 ×')
                else:
                    self.logger.warning('登录 ×', login_resp)

    def _uamtk(self):
        data = {'appid': 'otn'}
        uamtk_resp = self.session.post(self.urls.uamtk, data=data).json()
        if uamtk_resp['result_code'] == 0:
            data = {'tk': uamtk_resp['newapptk']}
            uamauthclient_resp = self.session.post(self.urls.uamauthclient, data=data).json()
            if uamauthclient_resp['result_code'] == 0:
                return True
            else:
                self.logger.warning('uamauthclient ×', uamauthclient_resp)
        else:
            self.logger.warning('uamtk ×', uamtk_resp)
        return False

    def query(self):
        """
        查询余票
        """
        params = {
            'leftTicketDTO.train_date': self.conf.train_date,
            'leftTicketDTO.from_station': station_codes[self.conf.from_station],
            'leftTicketDTO.to_station': station_codes[self.conf.to_station],
            'purpose_codes': 'ADULT'
        }

        response = self.session.get(self.urls.queryA, params=params).json()
        result = response['data']['result']

        seat = [('O', '二等座', 30), ('1', '硬座', 29), ('3', '硬卧', 28), ('1', '无座', 26), ('M', '一等座', 31)]
        train_type_letter = {'高铁': 'CG', '城际': 'CG', '动车': 'D', '直达': 'Z', '特快': 'T', '快速其他': 'K'}
        selected_train_type = ''.join([train_type_letter[k] for k in self.conf.train_type])
        selected_seat = [x for x in seat if x[1] in self.conf.seat_type]
        if result:
            for line in result:
                info = line.split('|')
                if (
                        info[3][0] in selected_train_type
                        and self.conf.start_time[0] < int(info[8][:2]) < self.conf.start_time[1]
                ) or info[3] in self.conf.train_no:
                    for seat_type, seat_type_cn, index in selected_seat:
                        if info[index] == '有' or info[index].isdigit():
                            ticket = {
                                'station_train_code': info[3],
                                seat_type_cn: info[index],
                                'secret_str': info[0],
                                'seat_type': seat_type
                            }
                            self.logger.info('*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*')
                            self.logger.info('余票 √ (车次: %s, 席别: %s)' % (info[3], seat_type_cn))
                            self.logger.info('*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*')
                            return ticket
        else:
            self.logger.warning('很抱歉，按您的查询条件，当前未找到从<%s>到><%s>的列车。'
                                '请从浏览器打开<https://kyfw.12306.cn/otn/leftTicket/init>'
                                '手动查询确认' % (self.conf.from_station, self.conf.to_station)
                                )
        return

    def _get_passenger(self):
        resp = self.session.post(self.urls.getPassengerDTOs, data={'_json_att': ''}).json()
        if resp.get('data'):
            passengers = resp['data']['normal_passengers']
            for psg in passengers:
                if psg['passenger_name'] == self.conf.passenger:
                    passenger_ticket = [psg['passenger_flag'], psg['passenger_type'], psg['passenger_name'],
                                        psg['passenger_id_type_code'],psg['passenger_id_no'], psg['mobile_no'],
                                        psg['isYongThan14'], psg['allEncStr']]
                    passenger_ticket_str = ','.join(passenger_ticket)
                    old_passenger = [psg['passenger_name'], psg['passenger_id_type_code'], psg['passenger_id_no'],
                                     psg['passenger_type'] + '_']
                    old_passenger_str = ','.join(old_passenger)
                    self._passenger_ticket_str = passenger_ticket_str
                    self._old_passenger_str = old_passenger_str

    def _submit_order(self, secret_str):
        form_data = {
            'secretStr': urllib.parse.unquote(secret_str),
            'train_date': self.conf.train_date,
            'back_train_date': time.strftime('%Y-%m-%d', time.localtime()),
            'tour_flag': 'dc',
            'purpose_codes': 'ADULT',
            'query_from_station_name': self.conf.from_station,
            'query_to_station_name': self.conf.to_station,
            'undefined': ''
        }
        resp = self.session.post(self.urls.submitOrderRequest, data=form_data).json()
        if resp.get('data') == 'N':
            return True
        else:
            self.logger.warning('submit ×')
            self.logger.warning(resp)
            return False

    def _check_order(self, seat_type):
        self._get_passenger()
        form_data = {
            'cancel_flag': 2,
            'bed_level_order_num': '000000000000000000000000000000',
            'passengerTicketStr': seat_type + ',' + self._passenger_ticket_str,
            'oldPassengerStr': self._old_passenger_str,
            'tour_flag': 'dc',
            'randCode': '',
            'whatsSelect': 1,
            '_json_att': '',
            'REPEAT_SUBMIT_TOKEN': self._repeat_submit_token
        }

        resp = self.session.post(self.urls.checkOrderInfo, data=form_data).json()
        if resp['data']['submitStatus']:
            return True
        else:
            self.logger.warning('check ×')
            self.logger.warning(resp)
            return False

    def _init_dc(self):
        resp = self.session.post(self.urls.initDc, data={'_json_att': ''})
        html = etree.HTML(resp.content)
        cdata = html.xpath('//script[1]/text()')[0]
        repeat_submit_token = cdata.split(';\n var ')[1].split(' = ')[1].strip("'")
        preserve = html.xpath('//script[1]/text()')[2]
        ticket_info_for_passenger_form = json.loads(preserve.split(';\n\n           var ')[4][27:].replace("'", '"'))
        order_request_dto = json.loads(preserve.split(';\n\n           var ')[5][16:].replace("'", '"'))
        self._repeat_submit_token = repeat_submit_token
        self._ticket_info_for_passenger_form = ticket_info_for_passenger_form
        self._order_request_dto = order_request_dto

    def _get_queue_count(self, seat_type):
        format_train_date = time.strftime(
            '%a %d %b %Y %H:%M:%S GMT+0800 (中国标准时间)', time.strptime(self.conf.train_date, '%Y-%m-%d')
        )
        query_left_ticket_request_dto = self._ticket_info_for_passenger_form['queryLeftTicketRequestDTO']
        form_data = {
            'train_date': format_train_date,
            'train_no': query_left_ticket_request_dto['train_no'],
            'stationTrainCode': query_left_ticket_request_dto['station_train_code'],
            'seatType': seat_type,
            'fromStationTelecode': query_left_ticket_request_dto['from_station'],
            'toStationTelecode': query_left_ticket_request_dto['to_station'],
            'leftTicket': self._ticket_info_for_passenger_form['leftTicketStr'],
            'purpose_codes': query_left_ticket_request_dto['purpose_codes'],
            'train_location': self._ticket_info_for_passenger_form['train_location'],
            '_json_att': '',
            'REPEAT_SUBMIT_TOKEN': self._repeat_submit_token,
        }
        resp = self.session.post(self.urls.getQueueCount, data=form_data).json()
        if int(resp['data']['ticket']) > 0:
            return True
        else:
            self.logger.warning('queue ×')
            self.logger.warning(resp)
            return False

    def _confirm_single_for_queue(self, seat_type):
        form_data = {
            'passengerTicketStr': seat_type + ',' + self._passenger_ticket_str,
            'oldPassengerStr': self._old_passenger_str,
            'randCode': '',
            'purpose_codes': self._ticket_info_for_passenger_form['purpose_codes'],
            'key_check_isChange': self._ticket_info_for_passenger_form['key_check_isChange'],
            'leftTicketStr': self._ticket_info_for_passenger_form['leftTicketStr'],
            'train_location': self._ticket_info_for_passenger_form['train_location'],
            'choose_seats': '',
            'seatDetailType': '000',
            'whatsSelect': 1,
            'roomType': '00',
            'dwAll': 'N',
            '_json_att': '',
            'REPEAT_SUBMIT_TOKEN': self._repeat_submit_token,
        }
        resp = self.session.post(self.urls.confirmSingleForQueue, data=form_data).json()
        if resp['data']['submitStatus']:
            return True
        else:
            self.logger.warning('confirm ×')
            self.logger.warning(resp)
            return False

    def _query_order(self):
        resp = self.session.post(self.urls.queryOrderWaitTime, data={'tourFlag': 'dc'}).json()
        # {"validateMessagesShowId":"_validatorMessage","status":true,"httpstatus":200,"data":{"queueWaitTime":0,"queueWaitCount":0,"queueRequestId":6584385718456211304,"queueCount":0,"tourFlag":"dc","status":8},"messages":[],"validateMessages":{}}

    def order(self, ticket):
        if self._submit_order(ticket['secret_str']):
            self._init_dc()
            if self._check_order(ticket['seat_type']):
                if self._get_queue_count(ticket['seat_type']):
                    if self._confirm_single_for_queue(ticket['seat_type']):
                        self.logger.info('提交订单 √')
                        self.logger.info('请从浏览器打开<https://kyfw.12306.cn/otn/view/train_order.html>,'
                                         '登录查看排队情况'
                                         )
                        self.sms()
                        return True
        self.logger.warning('提交订单 ×')
        return False

    def sms(self):
        """
        微信通知
        配置方法: http://sc.ftqq.com/3.version
        """
        url = 'https://sc.ftqq.com/SCU63343T9a6f2e55bf7effcf2351b669af3dfc2e5d956d4f73d75.send'
        params = {'text': '恭喜，抢到票了！',
                  'desp': '\n\n>>> 请登录12306查看\n\n'
                  }
        _ = requests.get(url, params=params)
        self.logger.info('微信推送 √')

    def refresh(self):
        """
        刷票
        """
        self.logger.info('刷票模式 √')
        self.logger.info('开始持续查询<%s>从<%s>开往<%s>的车票' %
                         (self.conf.train_date, self.conf.from_station, self.conf.to_station)
                         )
        clock = time.time()
        while True:
            ticket = self.query()
            if ticket:
                if self.order(ticket):
                    break
                else:
                    self.logger.info('继续查询')
            else:
                now = time.time()
                if now - clock > 60:
                    self.logger.info('正在持续查询')
                    clock = now
                # time.sleep(0.1)

    def book(self, start_time):
        """
        预约，开售自动抢
        :param start_time: 开售时间，格式：2019-08-08 12:12
        :return:
        """
        _start_time = time.mktime(time.strptime(start_time, '%Y-%m-%d  %H:%M'))
        now = time.time()

        if now > _start_time:
            print('开售时间%s已过，进入刷票模式' % _start_time)
            self.refresh()

        while now < _start_time:
            now = time.time()

        while '':
            self.query()

        return
