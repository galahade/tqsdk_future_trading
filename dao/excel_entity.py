from dao.entity import OpenPosInfo
from utils.common_tools import get_zl_symbol
import xlwings as xw


class Trade_Sheet:

    def __init__(self, book: xw.Book, future_config):
        self.sheet = book.sheets.add()
        self.future_config = future_config
        sheet = self.sheet
        sheet.range('A1').value = 'No'
        sheet.range('B1').value = '合约名称'
        sheet.range('C1').value = '多空'
        sheet.range('D1').value = '开仓时间'
        sheet.range('E1').value = '平仓时间'
        sheet.range('F1').value = '开仓条件'
        sheet.range('G1').value = '平仓指标'
        sheet.range('H1').value = '平仓条件'
        sheet.range('I1').value = '开仓价格'
        sheet.range('J1').value = '平仓价格'
        sheet.range('K1').value = '手数'
        sheet.range('L1').value = '浮动盈亏'
        sheet.range('M1').value = '手续费'
        sheet.range('N1').value = '账户权益'
        sheet.range('O1').value = '回撤'
        sheet.range('P1').value = '计算的盈亏'
        self.failback = 0
        self.maxfailback = 0
        self.total_profit = 0
        self.count = 2

    def record_line(self, opi: OpenPosInfo):
        close_price = ''
        close_reason = ''
        close_time = ''
        float_profit = 0
        commission = 0
        balance = 0
        cfp = self._calc_float_profit(opi)
        self.total_profit += cfp
        if self.failback + cfp > 0:
            self.failback = 0
        else:
            self.failback += cfp
        if self.failback < self.maxfailback:
            self.maxfailback = self.failback

        for index, cpi in enumerate(opi.close_pos_infos):
            close_price += f'{index+1}:{cpi.trade_price}-{cpi.trade_number},'
            close_reason += f'{index+1}:{cpi.close_reason},'
            close_time += f'{index+1}:{cpi.trade_date},'
            float_profit += cpi.float_profit
            commission += cpi.commission
            balance = cpi.current_balance
        st = self.sheet
        st.range((self.count, 1)).value = self.count - 1
        st.range((self.count, 2)).value = opi.symbol
        st.range((self.count, 3)).value = '多' if opi.l_or_s else '空'
        st.range((self.count, 4)).value = opi.trade_date
        st.range((self.count, 5)).value = close_time
        st.range((self.count, 6)).value = (f'日线{opi.daily_cond},'
                                           f'3小时线{opi.h3_cond}')
        st.range((self.count, 7)).value = (f'止损:{opi.stop_loss_price},'
                                           f'止盈:{opi.stop_profit_point}')
        st.range((self.count, 8)).value = close_reason
        st.range((self.count, 9)).value = opi.trade_price
        st.range((self.count, 10)).value = close_price
        st.range((self.count, 11)).value = opi.trade_number
        st.range((self.count, 12)).value = float_profit
        st.range((self.count, 13)).value = commission
        st.range((self.count, 14)).value = balance
        st.range((self.count, 15)).value = self.failback
        st.range((self.count, 16)).value = cfp
        st.autofit(axis="columns")
        self.count += 1

    def _calc_float_profit(self, opi) -> float:
        zl_symbol = get_zl_symbol(opi.symbol)
        c_m = 1
        for config in self.future_config:
            if config.symbol == zl_symbol:
                c_m = config.contract_m

        buy_total = opi.trade_price * opi.trade_number * c_m
        sell_total = 0
        for cpi in opi.close_pos_infos:
            sell_total += cpi.trade_price * cpi.trade_number * c_m
        result = (sell_total - buy_total if opi.l_or_s else
                  buy_total - sell_total)
        return 0 if sell_total == 0 else result

    def finish(self):
        st = self.sheet
        st.range((self.count, 2)).value = '总盈亏'
        st.range((self.count, 3)).value = self.total_profit
        st.range((self.count, 4)).value = '最大回撤'
        st.range((self.count, 5)).value = self.maxfailback


class Trade_Book:

    def __init__(self, db_name, future_config):
        self.wb = xw.Book()
        self.name = f'{db_name}.xlsx'
        self.sheet = Trade_Sheet(self.wb, future_config)

    def finish(self):
        self.sheet.finish()
        self.wb.save(self.name)
