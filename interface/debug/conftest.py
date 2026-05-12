# pytest_plugins = ["hui_core.plugin"]
# ^ 注释掉: 非顶层 conftest 不能定义 pytest_plugins，会在 pytest 收集时报错

import time
import  datetime
import requests
import pytest
from hui_core import hui_builtins
from dateutil.relativedelta import relativedelta
import uuid
import random
from datetime import timedelta

#手动修改python 递归问题
import sys
sys.setrecursionlimit(10**5) #RecursionError: maximum recursion depth exceeded while calling a Python object

#解决 ssl
@pytest.fixture(scope="session",autouse=True)
def verify_sll(requests_session):
    requests_session.verify=False


# 获取今日时间戳0时0分-毫秒
def current_time_0():
    now = int(time.mktime(datetime.date.today().timetuple()))* 1000
    # print(f"当前时间0点开始：\n{now}")
    return now
# current_time_0()


#获取今日23：59分-毫秒
def current_finaly_time():
    # 获取当前时间
    now = datetime.datetime.now()
    # 获取今天零点
    zeroToday = now - datetime.timedelta(hours=now.hour, minutes=now.minute, seconds=now.second, microseconds=now.microsecond)
    # 获取23:59:59
    lastToday = zeroToday + datetime.timedelta(hours=23, minutes=59, seconds=59)

    dt = str(lastToday)
    ts = int(time.mktime(time.strptime(dt, "%Y-%m-%d %H:%M:%S"))) * 1000
    # print(f"当前时间23点59结束：\n{ts}")
    return ts


#获取昨天开始时间
def yesterday_start():
    import time
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    yesterday_start_time = int(time.mktime(time.strptime(str(yesterday), '%Y-%m-%d')))
    # print(f"昨天开始的时间：{yesterday_start_time *1000}")
    return  yesterday_start_time *1000
# yesterday_start()

#昨天结束时间23：59
def yesterday_over():
    import time
    today = datetime.date.today()
    yesterday_end_time = int(time.mktime(time.strptime(str(today), '%Y-%m-%d'))) - 1
    # print(f"昨天结束的时间：{yesterday_end_time *1000}")
    return yesterday_end_time *1000
# yesterday_over()

#本周开始时间
def current_week_start():
    current_date = datetime.datetime.now().date()
    delta = datetime.timedelta(days=1)
    seven_days_ago = current_date - delta
    seven_days_later = current_date + delta

    print(f"当前日期：{current_date}")
    print(f"本周开始的时间：{seven_days_ago}")
    # return seven_days_ago *1000
current_week_start()

#本周结束时间
def current_week_over():
    current_date = datetime.datetime.now().date()
    delta = datetime.timedelta(days=-5)
    seven_days_ago = current_date - delta
    seven_days_later = current_date + delta

    print(f"当前日期：{current_date}")
    print(f"本周结束的时间：{seven_days_ago}")
current_week_over()

#上周开始时间
def last_week_start():
    import time
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=11)
    yesterday_start_time = int(time.mktime(time.strptime(str(yesterday), '%Y-%m-%d')))
    # print(f"上周开始的时间：{yesterday_start_time * 1000}")
# last_week_start()
    return yesterday_start_time * 1000
#上周结束的时间
def last_week_over():
    import time
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=5)
    yesterday_start_time = int(time.mktime(time.strptime(str(yesterday), '%Y-%m-%d')))
    # print(f"上周结束的时间：{yesterday_start_time * 1000}")
# last_week_over()
    return yesterday_start_time * 1000

#本月开始时间
def current_30_start():
    import time
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=16) ############################################11月1
    yesterday_start_time = int(time.mktime(time.strptime(str(yesterday), '%Y-%m-%d')))
    # print(f"本月开始的时间：{yesterday_start_time * 1000}")
# current_30_start()
    return yesterday_start_time * 1000
#本月结束时间
def current_30_over():
    import time
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=-13)  ############################################11月30
    yesterday_start_time = int(time.mktime(time.strptime(str(yesterday), '%Y-%m-%d')))
    # print(f"本月结束的时间：{yesterday_start_time * 1000}")
# current_30_over()
    return yesterday_start_time * 1000


#上月开始时间
def old_30_start():
    import time
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=47)  ############################################10月1
    yesterday_start_time = int(time.mktime(time.strptime(str(yesterday), '%Y-%m-%d')))
#     print(f"上月开始的时间：{yesterday_start_time * 1000}")
# old_30_start()
    return  yesterday_start_time * 1000
#上月结束时间
def old_30_over():
    import time
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=17)  ############################################10月30
    yesterday_start_time = int(time.mktime(time.strptime(str(yesterday), '%Y-%m-%d')))
#     print(f"上月结束的时间：{yesterday_start_time * 1000}")
# old_30_over()
    return yesterday_start_time * 1000

#最近7天开始时间
def recently_7_start():
    import time
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=6)  ############################################11月11
    yesterday_start_time = int(time.mktime(time.strptime(str(yesterday), '%Y-%m-%d')))
#     print(f"最近7天开始的时间：{yesterday_start_time * 1000}")
# recently_7_start()
    return yesterday_start_time * 1000
#最近7天结束时间
def recently_7_over():
    import time
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=0)  ############################################11月17
    yesterday_start_time = int(time.mktime(time.strptime(str(yesterday), '%Y-%m-%d')))
#     print(f"最近7天开始的时间：{yesterday_start_time * 1000}")
# recently_7_over()
    return yesterday_start_time * 1000

#最近30天开始时间-ing
def recently_30_start():
    import time
    import time
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=29)  ############################################10月22
    yesterday_start_time = int(time.mktime(time.strptime(str(yesterday), '%Y-%m-%d')))
# recently_7_start()
    return yesterday_start_time *1000
#最近30天结束时间
def recently_30_over():
    import time
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=0)  ############################################11月20
    yesterday_start_time = int(time.mktime(time.strptime(str(yesterday), '%Y-%m-%d')))
# recently_7_over()
    return yesterday_start_time *1000

import random
def _random():
    num = random.randint(1, 5)
    # print(f"随机整数为：{num}")
    return num
_random()





#注册到插件内置模块上
#今日开始时间和结束时间
hui_builtins.current_time_0 = current_time_0
hui_builtins.current_finaly_time = current_finaly_time
#昨日开始时间和结束时间
hui_builtins.yesterday_start=yesterday_start
hui_builtins.yesterday_over=yesterday_over
#本周开始时间和结束时间
hui_builtins.current_week_start=current_week_start
hui_builtins.current_week_over=current_week_over
#上周开始时间
hui_builtins.last_week_start=last_week_start
hui_builtins.last_week_over=last_week_over
#本月开始时间
hui_builtins.current_30_start=current_30_start
hui_builtins.current_30_over=current_30_over
#上月开始时间
hui_builtins.old_30_start=old_30_start
hui_builtins.old_30_over=old_30_over
#最近7天时间
hui_builtins.recently_7_start=recently_7_start
hui_builtins.recently_7_over=recently_7_over
#最近30天
hui_builtins.recently_30_start=recently_30_start
hui_builtins.recently_30_over=recently_30_over
#随机生成1-5 整数
hui_builtins._random=_random





if __name__ == '__main__':
    print(f"今日开始时间0点\n{current_time_0()}")
    print(f"今日结束时间23：59\n{current_finaly_time()}")

    print(f"昨天开始的时间\n{yesterday_start()}")
    print(f"昨天结束的时间\n{yesterday_over()}")

    # print(f"本周开始的时间\n{current_week_start}")
    # print(f"本周结束的时间\n{current_week_over}")

    print(f"上周开始的时间\n{last_week_start()}")
    print(f"上周结束的时间\n{last_week_over()}")

    print(f"本月开始的时间\n{current_30_start()}")
    print(f"本月结束的时间\n{current_30_over()}")

    print(f"上月开始的时间\n{old_30_start()}")
    print(f"上月结束的时间\n{old_30_over()}")

    print(f"最近7天开始的时间\n{recently_7_start()}")
    print(f"最近7天结束的时间\n{recently_7_over()}")

    print(f"最近30天开始时间\n{recently_30_start()}")
    print(f"最近30天结束时间\n{recently_30_over()}")

    print(f"随机整数为\n{_random()}")


