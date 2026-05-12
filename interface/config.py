
class Config:
    """环境配置"""
    version = "v1.0"
    #企业微信通知
    WE_COM = {
        "token": "fcfbb5a0-c4d1-413a-a6a2-2ee782fef0cb",
        # "text": "- 查看报告：[allure报告地址](http://172.16.211.12:8080/job/api/35/allure/)" #先写死，局域网可以查看，docker+jenkins-ing
        "text":"账号:ten_api@zhichi.com-v6版本"
    }

class SobotConfig(Config):
    """阿里云环境"""
    user_url = 'https://www.soboten.com' #多环境url切换


class SobotenConfig(Config):
    """腾讯云环境"""
    user_url = 'https://www.soboten.com' #多环境url切换


class SgConfig(Config):
    """新加坡环境"""

class UsConfig(Config):
    """北美环境"""

env = {
    "aliyun_api": SobotConfig,
    "sg_api": SgConfig,
    "ten_api":SobotenConfig,
    "us_api":UsConfig,
}

