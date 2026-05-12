
'''
crontab 定时任务-未开始
'''
from crontab import CronTab

# 创建一个CronTab对象
cron = CronTab(user='myuser')

# 创建一个新的任务
job = cron.new(command='command_to_run')

# 设置任务执行的时间
job.setall('0 0 * * *')

# 使任务生效
cron.write()