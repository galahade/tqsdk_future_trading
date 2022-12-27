import logging
import re
from tqsdk.ta import EMA, MACD
from tqsdk import tafunc
from datetime import datetime
import yaml
import requests


def send_msg(title: str, content: str) -> None:
    ''' 使用 Server Chan 发送相关消息。
    参考地址：https://sct.ftqq.com/after
    '''
    logger = get_logger()
    send_key = 'SCT172591Tn14G9JYc890AUJyvsNUiuCcL'
    url = f'https://sctapi.ftqq.com/{send_key}.send'
    headers = {"content-type": "application/x-www-form-urlencoded"}
    data = {'title': title, 'channel': 9, 'desp': content}
    try:
        requests.post(url, data=data, headers=headers)
    except Exception as e:
        logger.exception(e)


def get_date_str(float_value):
    ''' 返回格式为：年-月-日 时:分:秒 的字符串
    '''
    return tafunc.time_to_datetime(float_value).strftime("%Y-%m-%d %H:%M:%S")


def get_date_str_short(float_value):
    return tafunc.time_to_datetime(float_value).strftime("%Y-%m-%d")


def calc_date_delta(before_value, after_value):
    before = tafunc.time_to_datetime(before_value)
    after = tafunc.time_to_datetime(after_value)
    delta = after - before
    return delta.days


def is_zhulian_symbol(_symbol):
    pattern = re.compile(r'^(KQ.m@)(CFFEX|CZCE|DCE|INE|SHFE).(\w{1,2})$')
    return pattern.match(_symbol)


def get_date_from_kline(kline):
    return datetime.fromtimestamp(kline.datetime/1e9)


def calc_ema9(klines):
    ema = EMA(klines, 9)
    klines["ema9"] = ema.ema


def calc_ema22(klines):
    ema22 = EMA(klines, 22)
    klines["ema22"] = ema22.ema


def calc_ema60(klines):
    ema60 = EMA(klines, 60)
    klines["ema60"] = ema60.ema


def calc_macd(klines):
    macd = MACD(klines, 12, 24, 4)
    # 用 K 线图模拟 MACD 指标柱状图
    klines["MACD.open"] = 0.0
    klines["MACD.close"] = macd["bar"]
    klines["MACD.high"] = klines["MACD.close"].where(
        klines["MACD.close"] > 0, 0)
    klines["MACD.low"] = klines["MACD.close"].where(
        klines["MACD.close"] < 0, 0)
    klines["diff"] = macd["diff"]
    klines["dea"] = macd["dea"]


def calc_indicator(klines):
    calc_macd(klines)
    calc_ema22(klines)
    calc_ema60(klines)
    calc_ema9(klines)

    klines["ema22.board"] = "MAIN"
    klines["ema22.color"] = "red"
    klines["ema60.board"] = "MAIN"
    klines["ema60.color"] = "green"
    klines["ema9.board"] = "MAIN"
    klines["ema9.color"] = "blue"

    klines["MACD.board"] = "MACD"
    # 在 board=MACD 上添加 diff、dea 线
    klines["diff.board"] = "MACD"
    klines["diff.color"] = "gray"
    klines["dea.board"] = "MACD"
    klines["dea.color"] = "rgb(255,128,0)"


def diff_two_value(first, second):
    return abs(first - second) / second * 100


def is_nline(kline) -> bool:
    if kline.open > kline.close:
        return True
    else:
        return False


def is_decline_2p(kline, l_kline) -> bool:
    # logger = get_logger()
    # log_str = ('当前K线生成时间{},上一根K线生成时间{},'
    #            '当前K线收盘价{},上一根K线收盘价{}, 跌幅{}')

    result = (l_kline.close - kline.close)/l_kline.close
    # logger.debug(log_str.format(
    #     get_date(kline.datetime),
    #     get_date(l_kline.datetime),
    #     kline.close, l_kline.close, result))
    if result > 0.02:
        return True
    return False


def get_logger():
    return logging.getLogger(__name__)


def get_yaml_config(path: str) -> dict:
    with open(path, 'r') as f:
        yaml_config = yaml.safe_load(f.read())
        return yaml_config


def get_date_from_symbol(symbol_last_part):
    temp = int(symbol_last_part)
    year = int(temp / 100) + 2000
    month = temp % 100
    day = 1
    return datetime(year, month, day, 0, 0, 0)
