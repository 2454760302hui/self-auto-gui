
from hui_core.report_notify import wecom_notify
from pathlib import Path
import json
import os

pytest.main(['--alluredir', './report'])

# 第二步：生成allure报告（需要alure服务器）
os.system('allure generate ./report -c -o  ./report_html')


# 第三步 发企业微信token
# 从环境变量读取企业微信 webhook token，避免硬编码泄露
wx_token = os.environ.get('WECOM_WEBHOOK_TOKEN')
if not wx_token:
    raise RuntimeError(
        "WECOM_WEBHOOK_TOKEN environment variable is required. "
        "Set it to your WeChat Work webhook key before running this script."
    )

report_path = Path(__file__).parent.joinpath('report_html', 'widgets', 'summary.json')
print(f"allure 报告路径：{report_path}")

# 2.读取测试结果
with open(report_path, 'r', encoding='utf-8') as fp:
    result = json.load(fp)

# 3.通知内容自定义
markdown_text = f'''项目名称: 腾讯云-接口回归测试-账号：ten_api@zhichi.com
- 持续时间: {result['time']['duration']} 毫秒 

## 本次运行结果:
- 总用例数: {result['statistic']['total']} 
- 通过用例：{result['statistic']['passed']} 
- 跳过用例：{result['statistic']['skipped']} 
- 失败用例： {result['statistic']['failed']} 
- 异常用例： {result['statistic']['broken']}
- 通过率： {result['statistic']['passed']/result['statistic']['total']*100: .2f} % 
'''

# 4.发送通知
res = wecom_notify(wx_token, msgtype="markdown", text=markdown_text)
print(res.text)



