'''调试中'''
from apscheduler.schedulers.blocking import BlockingScheduler
import time
from apscheduler.schedulers.blocking import BlockingScheduler
def print_time():
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))

scheduler = BlockingScheduler()
scheduler.add_job(print_time, 'interval', minutes=1)
scheduler.start()