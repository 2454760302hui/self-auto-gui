from dingtalkchatbot.chatbot import DingtalkChatbot
import requests


def ding_ding_notify(
        access_token, secret=None, pc_slide=False, fail_notice=False,
        title="测试报告", text="## 测试报告", is_at_all=False,
        at_mobiles=None, at_dingtalk_ids=None, is_auto_at=True, *args, **kwargs):  # noqa
    """
    机器人初始化
        :param access_token: 钉钉群自定义机器人access_token
        :param secret: 机器人安全设置页面勾选"加签"时需要传入的密钥
        :param pc_slide: 消息链接打开方式，默认False为浏览器打开，设置为True时为PC端侧边栏打开
        :param fail_notice: 消息发送失败提醒，默认为False不提醒，
               开发者可以根据返回的消息发送结果自行判断和处理

    钉钉机器人通知报告
    markdown类型
            :param title: 首屏会话透出的展示内容
            :param text: markdown格式的消息内容
            :param is_at_all: @所有人时：true，否则为：false（可选）
            :param at_mobiles: 被@人的手机号
            :param at_dingtalk_ids: 被@用户的UserId（企业内部机器人可用，可选）
            :param is_auto_at: 是否自动在text内容末尾添加@手机号，默认自动添加，也可设置为False，
                   然后自行在text内容中自定义@手机号的位置，才有@效果，支持同时@多个手机号（可选）
            :return: 返回消息发送结果
    """
    webhook = f'https://oapi.dingtalk.com/robot/send?access_token={access_token}'
    ding = DingtalkChatbot(webhook=webhook, secret=secret, pc_slide=pc_slide, fail_notice=fail_notice)
    ding.send_markdown(
        title=title, text=text, is_at_all=is_at_all,
        at_mobiles=at_mobiles if at_mobiles else [],
        at_dingtalk_ids=at_dingtalk_ids if at_dingtalk_ids else [],
        is_auto_at=is_auto_at
    )


def fei_shu_notify(
        token, title="测试报告", text="报告内容", color="green", *args, **kwargs):
    """
    飞书机器人发送报告
    :param token: webhook 地址后面的token
    :param title: 报告的标题
    :param text: 报告内容
    :param color:  标题背景色 green 绿色  red 红色
    :return: 执行结果
    """
    url = f"https://open.feishu.cn/open-apis/bot/v2/hook/{token}"
    headers = {"Content-Type": "text/plain"}
    data = {
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode": True,    # 废弃字段
                "enable_forward": True,      # 允许转发
                "update_multi": True   # 是否共享卡片
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": title
                },
                "template": color
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",   # markdown 格式
                        "content": text
                    }
                }
            ]
        }
    }
    res = requests.post(url, headers=headers, json=data)
    return res.json()


def wecom_notify(
        token, msgtype="markdown", text="",
        mentioned_list=None, mentioned_mobile_list=None):
    """
      发送企业微信
    :param token: 企业微信 webhook 对应的key
    :param msgtype: 发送消息默认 markdown 类型，也可以支持text类型
    :param text: 消息内容
    :param mentioned_list: @谁，根据 userid
    :param mentioned_mobile_list: @all是全部["@all", ]，也可以根据手机号。如：["1500*******", ]
    :return:
    """
    url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={token}"  # 这里就是群机器人的Webhook地址
    data = {
        "msgtype": msgtype,

    }
    if msgtype == "markdown":
        data["markdown"] = {
                "content": text
        }
    if msgtype == "text":
        data["text"] = {
                "content": text,
                "mentioned_list": mentioned_list if mentioned_list else [],
                "mentioned_mobile_list": mentioned_mobile_list if mentioned_mobile_list else ["@all"]
        }
    print(data)
    resp = requests.post(url, json=data)
    return resp
