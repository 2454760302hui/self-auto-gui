import datetime

'''过去7天-完'''
#过去7天开始时间
def old7_start():
    current_date = datetime.datetime.now().date()
    delta = datetime.timedelta(days=7)
    seven_days_ago = current_date - delta
    seven_days_later = current_date + delta

    # print(f"当前日期：{current_date}")
    print(f"过去7天的开始时间：{seven_days_ago}")
old7_start()

#过去7天的结束时间
def old7_over():
    current_date = datetime.datetime.now().date()
    delta = datetime.timedelta(days=1)
    seven_days_ago = current_date - delta
    seven_days_later = current_date + delta

    # print(f"当前日期：{current_date}")
    print(f"过去7天的结束时间：{seven_days_ago}")
old7_over()

'''最近7天-ing'''
#最近7天开始时间
def recently_7_start():
    import time
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=6)  ############################################11月11
    yesterday_start_time = int(time.mktime(time.strptime(str(yesterday), '%Y-%m-%d')))
    print(f"最近7天开始的时间：{yesterday_start_time * 1000}")
recently_7_start()
#过去7天结束时间
def recently_7_over():
    import time
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=0)  ############################################11月17
    yesterday_start_time = int(time.mktime(time.strptime(str(yesterday), '%Y-%m-%d')))
    print(f"最近7天开始的时间：{yesterday_start_time * 1000}")
recently_7_over()


'''过去30天-完'''
#过去30天开始时间
def old_30_start():
    current_date = datetime.datetime.now().date()
    delta = datetime.timedelta(days=30)
    seven_days_ago = current_date - delta
    seven_days_later = current_date + delta

    # print(f"当前日期：{current_date}")
    print(f"过去30天开始的时间：{seven_days_ago}")
old_30_start()

#过去30天的结束时间
def old_30_over():
    current_date = datetime.datetime.now().date()
    delta = datetime.timedelta(days=1)
    seven_days_ago = current_date - delta
    seven_days_later = current_date + delta

    # print(f"当前日期：{current_date}")
    print(f"过去30天结束的时间：{seven_days_ago}")
old_30_over()

'''最近30天-完'''
#最近30天开始时间
def recently_30_start():
    current_date = datetime.datetime.now().date()
    delta = datetime.timedelta(days=29)
    seven_days_ago = current_date - delta
    seven_days_later = current_date + delta

    # print(f"当前日期：{current_date}")
    print(f"最近30天开始的时间：{seven_days_ago}")
recently_30_start()
#最近30天结束时间
def recently_30_over():
    current_date = datetime.datetime.now().date()
    delta = datetime.timedelta(days=0)
    seven_days_ago = current_date - delta
    seven_days_later = current_date + delta

    # print(f"当前日期：{current_date}")
    print(f"最近30天结束的时间：{seven_days_ago}")
recently_30_over()

'''上月-ing'''
#上月开始时间
def old_30_start():
    import time
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=47)  ############################################10月1
    yesterday_start_time = int(time.mktime(time.strptime(str(yesterday), '%Y-%m-%d')))
    print(f"上月开始的时间：{yesterday_start_time * 1000}")
old_30_start()
#上月结束时间
def old_30_over():
    import time
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=17)  ############################################10月30
    yesterday_start_time = int(time.mktime(time.strptime(str(yesterday), '%Y-%m-%d')))
    print(f"上月结束的时间：{yesterday_start_time * 1000}")

old_30_over()

'''本月-完'''
#本月开始时间
def current_30_start():
    import time
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=16) ############################################11月1
    yesterday_start_time = int(time.mktime(time.strptime(str(yesterday), '%Y-%m-%d')))
    print(f"本月开始的时间：{yesterday_start_time * 1000}")
current_30_start()
#本月结束时间
def current_30_over():
    import time
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=-13)  ############################################11月30
    yesterday_start_time = int(time.mktime(time.strptime(str(yesterday), '%Y-%m-%d')))
    print(f"本月结束的时间：{yesterday_start_time * 1000}")
current_30_over()

'''上周-完'''
def last_week_start():
    import time
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=11)
    yesterday_start_time = int(time.mktime(time.strptime(str(yesterday), '%Y-%m-%d')))
    print(f"上周开始的时间：{yesterday_start_time * 1000}")
last_week_start()
#上周结束的时间
def last_week_over():
    import time
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=5)
    yesterday_start_time = int(time.mktime(time.strptime(str(yesterday), '%Y-%m-%d')))
    print(f"上周结束的时间：{yesterday_start_time * 1000}")
last_week_over()

# '''本周-debug'''
# now = datetime.datetime.now()
# last_week_start = now - datetime.timedelta(days=now.weekday()+7)
# last_week_end = now - datetime.timedelta(days=now.weekday()+1)
# print('上周开始时间：' + last_week_start.strftime('%Y%m%d'))
# print(' 上周结束时间：' + last_week_end.strftime('%Y%m%d'))
#

'''昨天-完'''
#昨天开始时间
def yesterday_start():
    import time
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    yesterday_start_time = int(time.mktime(time.strptime(str(yesterday), '%Y-%m-%d')))
    print(f"昨天开始的时间：{yesterday_start_time *1000}")
yesterday_start()

#昨天结束时间23：59
def yesterday_over():
    import time
    today = datetime.date.today()
    yesterday_end_time = int(time.mktime(time.strptime(str(today), '%Y-%m-%d'))) - 1
    print(f"昨天结束的时间：{yesterday_end_time *1000}")
yesterday_over()
