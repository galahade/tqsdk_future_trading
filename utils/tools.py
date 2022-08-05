import re
import logging
from tqsdk.ta import EMA, MACD
from tqsdk import tafunc
from datetime import datetime
import xlwings as xw


class Trade_Sheet:

    def __init__(self, symbol: str, sheet: xw.Sheet):
        sheet.range('A1').value = 'No'
        sheet.range('B1').value = '合约名称'
        sheet.range('C1').value = '多空'
        sheet.range('D1').value = '买卖'
        sheet.range('E1').value = '开仓时间'
        sheet.range('F1').value = '开仓价格'
        sheet.range('G1').value = '开仓条件'
        sheet.range('H1').value = '平仓价格'
        sheet.range('I1').value = '平仓时间'
        sheet.range('J1').value = '平仓价格'
        sheet.range('K1').value = '平仓条件'
        sheet.range('L1').value = '手数'
        self.sheet = sheet
        self.count = 1

    def r_l_open_pos(self, symbol, t_time, d_cond, h2_cond, sell_cond,
                     price, pos):
        self.count += 1
        st = self.sheet
        cond_str = '日线:{},2小时:{}'
        st.range((self.count, 1)).value = self.count - 2
        st.range((self.count, 2)).value = symbol
        st.range((self.count, 3)).value = '多'
        st.range((self.count, 4)).value = '买'
        st.range((self.count, 5)).value = t_time
        st.range((self.count, 6)).value = price
        st.range((self.count, 7)).value = cond_str.format(d_cond, h2_cond)
        st.range((self.count, 8)).value = sell_cond
        st.range((self.count, 12)).value = pos
        st.autofit(axis="columns")
        return self.count - 1

    def r_lv_open_pos(self, symbol, t_time, d_cond, h2_cond, sell_cond,
                      price, pos):
        self.count += 1
        st = self.sheet
        cond_str = '日线:{},2小时:{},虚拟开仓'
        st.range((self.count, 1)).value = self.count - 2
        st.range((self.count, 2)).value = symbol
        st.range((self.count, 3)).value = '多'
        st.range((self.count, 4)).value = '买'
        st.range((self.count, 5)).value = t_time
        st.range((self.count, 6)).value = price
        st.range((self.count, 7)).value = cond_str.format(d_cond, h2_cond)
        st.range((self.count, 8)).value = sell_cond
        st.range((self.count, 12)).value = pos
        return self.count - 1

    def r_sold_pos(self, symbol: str, num: int, t_time: str, sold_reason: str,
                   price: float, pos: int, l_or_s: bool):
        self.count += 1
        st = self.sheet
        st.range((self.count, 1)).value = num
        st.range((self.count, 2)).value = symbol
        if l_or_s:
            st.range((self.count, 3)).value = '多'
            st.range((self.count, 4)).value = '卖'
        else:
            st.range((self.count, 3)).value = '空'
            st.range((self.count, 4)).value = '买'
        st.range((self.count, 9)).value = t_time
        st.range((self.count, 10)).value = price
        st.range((self.count, 11)).value = sold_reason
        st.range((self.count, 12)).value = pos
        st.autofit(axis="columns")

    def r_s_open_pos(self, symbol, t_time, d_cond, sell_cond, price, pos):
        self.count += 1
        st = self.sheet
        cond_str = '日线:{}'
        st.range((self.count, 1)).value = self.count - 2
        st.range((self.count, 2)).value = symbol
        st.range((self.count, 3)).value = '空'
        st.range((self.count, 4)).value = '卖'
        st.range((self.count, 5)).value = t_time
        st.range((self.count, 6)).value = price
        st.range((self.count, 7)).value = cond_str.format(d_cond)
        st.range((self.count, 8)).value = sell_cond
        st.range((self.count, 12)).value = pos
        st.autofit(axis="columns")
        return self.count - 1

    def _get_name(self, zl_symbol) -> str:
        symbol_list = examine_symbol(zl_symbol)
        name = f'{symbol_list[2]}'
        return name


class Trade_Book:

    def __init__(self):
        wb = xw.Book()
        self.sheets: dict(str, Trade_Sheet) = {}
        self.name = 'future_test.xlsx'
        self.wb = wb

    def create_sheet(self, zl_symbol) -> Trade_Sheet:
        name = self._get_name(zl_symbol)
        if not self.sheets.get(name, 0):
            self.wb.sheets.add(name)
            self.sheets[name] = Trade_Sheet(zl_symbol, self.wb.sheets[name])
        return self.sheets[name]

    def _get_name(self, zl_symbol) -> str:
        symbol_list = examine_symbol(zl_symbol)
        name = f'{symbol_list[2]}'
        return name

    def get_sheet(self, symbol) -> Trade_Sheet:
        symbol_list = examine_symbol(symbol)
        return self.sheets[symbol_list[1]]

    def finish(self):
        self.wb.save(self.name)


def get_date_str(float_value):
    return tafunc.time_to_datetime(float_value).strftime("%Y-%m-%d %H:%M:%S")


def get_date(float_value):
    return tafunc.time_to_datetime(float_value).strftime("%Y-%m-%d")


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
        'KQ.m': re.compile(r'^(KQ.m@)(CFFEX|CZCE|DCE|INE|SHFE).(\w{1,2})$')
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


def calc_indicator(klines):
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


def is_nline(kline) -> bool:
    if kline.open > kline.close:
        return True
    else:
        return False


def is_decline_2p(kline, l_kline) -> bool:
    logger = get_logger()
    log_str = ('当前K线生成时间{},上一根K线生成时间{},'
               '当前K线收盘价{},上一根K线收盘价{}, 跌幅{}')

    result = (l_kline.close - kline.close)/l_kline.close
    logger.debug(log_str.format(
        get_date(kline.datetime),
        get_date(l_kline.datetime),
        kline.close, l_kline.close, result))
    if result > 0.02:
        return True
    return False


def get_logger():
    return logging.getLogger(__name__)


if __name__ == '__main__':
    tb = Trade_Book('KQ.m@DCE.p')
    print(tb.__dict__)
    tb.finish()
