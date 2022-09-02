from dao.entity import OpenPosInfo, ClosePosInfo
import xlwings as xw
from utils.tools import examine_symbol
from utils.tools import get_date_str


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
        sheet.range('M1').value = '浮动盈亏'
        sheet.range('N1').value = '手续费'
        sheet.range('O1').value = '账户权益'
        self.sheet = sheet
        self.count = 2

    def r_open_pos(self, symbol: str, t_time: str, open_cond: str,
                   sell_cond: str, price: float, pos: int, commission: float,
                   balance: float, l_or_s: bool):
        st = self.sheet
        st.range((self.count, 1)).value = self.count
        st.range((self.count, 2)).value = symbol
        if l_or_s:
            st.range((self.count, 3)).value = '多'
        else:
            st.range((self.count, 3)).value = '空'
        st.range((self.count, 4)).value = '开'
        st.range((self.count, 5)).value = t_time
        st.range((self.count, 6)).value = price
        st.range((self.count, 7)).value = open_cond
        st.range((self.count, 8)).value = sell_cond
        st.range((self.count, 12)).value = pos
        st.range((self.count, 14)).value = commission
        st.range((self.count, 15)).value = balance
        st.autofit(axis="columns")
        self.count += 1

    def r_sold_pos(self, symbol: str, t_time: str, sold_reason: str,
                   price: float, pos: int, float_profit: float,
                   commission: float, balance: float, l_or_s: bool):
        st = self.sheet
        st.range((self.count, 1)).value = self.count
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
        st.range((self.count, 13)).value = float_profit
        st.range((self.count, 14)).value = commission
        st.range((self.count, 15)).value = balance
        st.autofit(axis="columns")
        self.count += 1

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


trade_book: Trade_Book = None


def store_open_record(opi: OpenPosInfo) -> None:
    sell_cond_str = '止损:{},止盈:{}'
    open_cond = ''
    ts = None
    if opi.l_or_s:
        open_cond = '日线:{},2小时:{}'.format(opi.daily_cond, opi.h2_cond)
    else:
        open_cond = '日线:{}'.format(opi.daily_cond)
    if trade_book is not None:
        ts = trade_book.get_sheet(opi.symbol)
    ts.r_open_pos(
        opi.symbol, get_date_str(opi.trade_date), open_cond,
        sell_cond_str.format(opi.stop_loss_price, opi.stop_profit_point),
        opi.trade_price,
        opi.trade_number,
        opi.commission,
        opi.current_balance,
        opi.l_or_s
    )


def store_close_record(cpi: ClosePosInfo) -> None:
    ts = None
    if trade_book is not None:
        ts = trade_book.get_sheet(cpi.symbol)
    ts.r_sold_pos(
        cpi.symbol, get_date_str(cpi.trade_date), cpi.close_reason,
        cpi.trade_price,
        cpi.trade_number,
        cpi.float_profit,
        cpi.commission,
        cpi.current_balance,
        cpi.l_or_s
    )
