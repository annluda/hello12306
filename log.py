# -*- coding: utf-8 -*-
import logging
import os


def get_logger():
    file_path = os.path.dirname(__file__)
    log_path = os.path.abspath(os.path.join(file_path, 'logs/train.log'))
    logger = logging.getLogger('ChinaRailway')
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(log_path)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    logger.handlers = []
    logger.addHandler(handler)
    return logger
