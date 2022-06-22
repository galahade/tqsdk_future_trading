import xlwings as xw

'''
wb = xw.Book()
sheet = wb.sheets['future']
sheet.range('A1').value = 'No'
sheet.range('B1').value = '合约名称'
sheet.range('C1').value = '多空'
sheet.range('D1').value = '开仓时间'
sheet.range('E1').value = '开仓价格'
sheet.range('F1').value = '开仓条件'
sheet.range('G1').value = '平仓时间'
sheet.range('H1').value = '平仓价格'
sheet.range('I1').value = '平仓条件'
sheet.range('J1').value = '手数'
print(sheet.range((1, 1)).value)
wb.save('testExcel.xlsx')
'''


class Trade_Book:

    def __init__(self):
        wb = xw.Book()
        sheet = wb.sheets['future']
        sheet.range('A1').value = 'No'
        sheet.range('B1').value = '合约名称'
        sheet.range('C1').value = '多空'
        sheet.range('D1').value = '开仓时间'
        sheet.range('E1').value = '开仓价格'
        sheet.range('F1').value = '开仓条件'
        sheet.range('G1').value = '平仓时间'
        sheet.range('H1').value = '平仓价格'
        sheet.range('I1').value = '平仓条件'
        sheet.range('J1').value = '手数'
        self.sheet = sheet
        self.count = 1
        self.wb = wb

    def record_open_pos_long(self, symbol, t_time, d_cond, price, pos):
        self.count += 1
        st = self.sheet
        st.range((self.count, 1)).value = self.count - 1
        st.range((self.count, 2)).value = symbol
        st.range((self.count, 3)).value = '多'
        st.range((self.count, 4)).value = t_time
        st.range((self.count, 5)).value = price
        st.range((self.count, 6)).value = f'日线条件{d_cond}'
        st.range((self.count, 10)).value = pos

    def finish(self):
        self.wb.save('testExcel.xlsx')


book = Trade_Book()

book.record_open_pos_long('rb2210', '2022-02-19 22:32:43', 1, 4567, 56)
book.record_open_pos_long('rb2210', '2022-02-19 22:32:43', 3, 4567, 66)
book.record_open_pos_long('rb2210', '2022-02-19 22:32:43', 2, 4567, 26)
book.finish()
