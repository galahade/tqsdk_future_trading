from tqsdk import TqApi, TqBacktest, BacktestFinished
# from tqsdk2 import TqApi, TqBacktest, BacktestFinished
from utils.common import LoggerGetter
from trading_department.tools import StorageTool, AuthTool,\
        BackTestTool, TradeTool


class Manager:
    '''期货交易总负责人，负责根据指令的类型和交易方向分派任务给具体部门经理
    Attributes
    ----------
    direction: int - 交易方向：0:做空，1:做多，2:多空
    is_backtest: bool - 是否进行回测,默认情况为正常交易
    当进行回测时，需提供以下参数：
    s_year: int - 回测开始年份
    s_month: int - 回测开始月份
    end_year: int - 回测结束年份

    '''
    def __init__(self, direction=2, is_backtest=False,
                 s_year=2018, s_month=1, end_year=9999):
        authTool = AuthTool()
        storageTool = StorageTool(is_backtest)
        tradeTool = TradeTool(direction, storageTool)
        if is_backtest:
            btTool = BackTestTool(s_year, s_month, end_year, storageTool)
            self.staff = TestManager(btTool, tradeTool, authTool)
        else:
            self.staff = RManager(tradeTool, authTool)

    def start_trading(self):
        self.staff.trade()


class TestManager:
    '''测试部门经理，负责回测相关操作
    Attributes
    ----------
    btTool: tool.BackTestTool - 回测工具对象，提供回测所需相关数据
    storageTool: tool.StorageTool - MongoDB 工具，用来获取数据库
    authTool: tool.AuthTool - 交易账户和天勤账户相关信息
    '''
    logger = LoggerGetter()

    def __init__(self, btTool, tradeTool, authTool):
        self.bt_tool = btTool
        self.trade_Tool = tradeTool
        self.auth_tool = authTool

    def trade(self):
        logger = self.logger
        bt_tool = self.bt_tool
        logger.info(f"回测开始日期：{bt_tool.start_date}, 结束日期：{bt_tool.end_date}")
        try:
            # api = TqApi(bt_tool.account, web_gui=":10000",
            api = TqApi(bt_tool.account,
                        backtest=TqBacktest(
                            start_dt=bt_tool.start_date,
                            end_dt=bt_tool.end_date),
                        auth=self.auth_tool.tq_auth)
            self.trade_Tool.start_trading(api, is_backtest=True)

        except BacktestFinished:
            logger.info("回测完成")
            # api.close()
            # 打印回测的详细信息
            # print("trade log:", acc.trade_log)
            logger.info(bt_tool.account.trade_log)

            # 账户交易信息统计结果
            # print("tqsdk stat:", acc.tqsdk_stat)
            logger.info(bt_tool.account.tqsdk_stat)
            while True:
                api.wait_update()


class RManager:
    '''实盘操作部门经理,负责实盘操作工作
    Attributes
    ----------
    storageTool: tool.StorageTool - MongoDB 工具，用来获取数据库
    authTool: tool.AuthTool - 交易账户和天勤账户相关信息
    '''
    logger = LoggerGetter()

    def __init__(self, tradeTool, authTool):
        self.trade_Tool = tradeTool
        self.auth_tool = authTool

    def trade(self):
        logger = self.logger
        auth_tool = self.auth_tool
        api = TqApi(auth_tool.get_account(), auth=auth_tool.tq_auth)
        self.trade_Tool.start_trading(api, auth_tool.is_just_check())
