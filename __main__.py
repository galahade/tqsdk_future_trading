
import argparse
from datetime import date
import sys

_parser = argparse.ArgumentParser(prog="tqsdk_future_trade",
                                  description="使用天勤量化执行期货交易策略")

now = date.today()

_parser.add_argument("-l", "--log", choices=["warning", "info", "debug"],
                     help="日志级别，默认为warning", default="warning")

_bt_group = _parser.add_argument_group('回测参数分组', '如果进行回测，\
                                    使用该参数组指定相关参数')
_bt_group.add_argument("-t", "--backtest",
                       help="进行回测", action="store_true")

_bt_group.add_argument("-s", "--start_year",
                       type=int, default=now.year, help="backtest 开始年份")
_bt_group.add_argument("-e", "--end_year",
                       type=int, default=now.year, help="backtest 结束年份")

args = _parser.parse_args()

if args.backtest:
    if now.year < args.start_year:
        sys.exit(f"回测开始年份{args.start_year},晚于当前年份{now.year}，参数错误.")
    elif now.year < args.end_year:
        sys.exit(f"回测结束年份{args.end_year},晚于当前年份{now.year}，参数错误.")


print(f"日志级别：{args.log}")
print(f"是否进行回测：{args.backtest}")

if args.backtest:
    print(f"回测开始年份{args.start_year},结束年份{args.end_year}")
