import re
import logging
from tqsdk.ta import EMA, MACD
from tqsdk import tafunc
from datetime import datetime
import xlwings as xw


class Trade_Book:

    def __init__(self, symbol):
        wb = xw.Book()
        sheet = wb.sheets[0]
        sheet.range('A1').value = 'No'
        sheet.range('B1').value = '合约名称'
        sheet.range('C1').value = '多空'
        sheet.range('D1').value = '买卖'
        sheet.range('E1').value = '开仓时间'
        sheet.range('F1').value = '开仓价格'
        sheet.range('G1').value = '开仓条件'
        sheet.range('H1').value = '平仓时间'
        sheet.range('I1').value = '平仓价格'
        sheet.range('J1').value = '平仓条件'
        sheet.range('K1').value = '手数'
        self.sheet = sheet
        self.count = 1
        self.wb = wb
        self.name = f'{symbol.replace(".", "_")}'

    def r_l_open_pos(self, symbol, t_time, d_cond, h2_cond, price, pos):
        self.count += 1
        st = self.sheet
        cond_str = '日线:{},2小时:{}'
        st.range((self.count, 1)).value = self.count - 1
        st.range((self.count, 2)).value = symbol
        st.range((self.count, 3)).value = '多'
        st.range((self.count, 4)).value = '买'
        st.range((self.count, 5)).value = t_time
        st.range((self.count, 6)).value = price
        st.range((self.count, 7)).value = cond_str.format(d_cond, h2_cond)
        st.range((self.count, 11)).value = pos
        return self.count - 1

    def r_l_sold_pos(self, symbol, num, t_time, sold_reason, price, pos):
        self.count += 1
        st = self.sheet
        st.range((self.count, 1)).value = num
        st.range((self.count, 2)).value = symbol
        st.range((self.count, 3)).value = '多'
        st.range((self.count, 4)).value = '卖'
        st.range((self.count, 8)).value = t_time
        st.range((self.count, 9)).value = price
        st.range((self.count, 10)).value = sold_reason
        st.range((self.count, 11)).value = pos

    def finish(self):
        self.wb.save(self.name)


def get_date_str(float_value):
    return tafunc.time_to_datetime(float_value).strftime("%Y-%m-%d %H:%M:%S")


def calc_date_delta(before_value, after_value):
    before = tafunc.time_to_datetime(before_value)
    after = tafunc.time_to_datetime(after_value)
    delta = after - before
    return delta.days


def is_zhulian_symbol(_symbol):
    pattern = re.compile(r'^(KQ.m@)(CFFEX|CZCE|DCE|INE|SHFE).(\w{1,2})$')
    return pattern.match(_symbol)


def examine_symbol(_symbol):
    pattern_dict_normal = {
        'CFFEX': re.compile(r'^(CFFEX).([A-Z]{1,2})(\d{4})$'),
        'CZCE': re.compile(r'^(CZCE).([A-Z]{2})(\d{3})$'),
        'DCE': re.compile(r'^(DCE).([a-z]{1,2})(\d{4})$'),
        'INE': re.compile(r'^(INE).([a-z]{2})(\d{4})$'),
        'SHFE': re.compile(r'^(SHFE).([a-z]{2})(\d{4})$'),
        # 'KQ.m': re.compile(r'^(KQ.m@)(CFFEX|CZCE|DCE|INE|SHFE).(\w{1,2})$')
        }

    for k, ipattern in pattern_dict_normal.items():
        matchsymbol = ipattern.match(_symbol)
        if matchsymbol:
            exchange, variety, expiry_month = \
                matchsymbol.group(1), matchsymbol.group(2), \
                matchsymbol.group(3)
            return [exchange, variety, expiry_month]
    return False


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


def calc_indicator(klines, is_daily_kline=False):
    calc_macd(klines)
    calc_ema22(klines)
    calc_ema60(klines)
    calc_ema9(klines)

    klines["l_qualified"] = 0
    klines["s_qualified"] = 0

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


def get_logger():
    return logging.getLogger(__name__)
