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
        sheet = wb.sheets[0]
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

    def finish(self):
        self.wb.save('data.xlsx')

    def r_open_pos_l(self, symbol, t_time, d_cond, h2_cond, price, pos):
        self.count += 1
        st = self.sheet
        cond_str = '日线:{},2小时:{}'
        st.range((self.count, 1)).value = self.count - 1
        st.range((self.count, 2)).value = symbol
        st.range((self.count, 3)).value = '多'
        st.range((self.count, 4)).value = t_time
        st.range((self.count, 5)).value = price
        st.range((self.count, 6)).value = cond_str.format(d_cond, h2_cond)
        st.range((self.count, 10)).value = pos
        return self.count - 1

    def r_sold_pos_l(self, symbol, num, t_time, sold_reason, price, pos):
        self.count += 1
        st = self.sheet
        st.range((self.count, 1)).value = num
        st.range((self.count, 2)).value = symbol
        st.range((self.count, 3)).value = '多'
        st.range((self.count, 7)).value = t_time
        st.range((self.count, 8)).value = price
        st.range((self.count, 9)).value = sold_reason
        st.range((self.count, 10)).value = pos


book = Trade_Book()

book.r_open_pos_l('rb2210', '2022-02-19 22:32:43', 1, 1, 4567, 56)
num = book.r_open_pos_l('rb2210', '2022-02-19 22:32:43', 2, 3, 4567, 66)
book.r_open_pos_l('rb2210', '2022-02-19 22:32:43', 2, 3, 4567, 26)
book.r_sold_pos_l('rb2210', num, '2022-02-20 13:00:00', '止赢1', 4460, 30)
book.finish()
