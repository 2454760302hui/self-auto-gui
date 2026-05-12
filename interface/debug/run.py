import pytest
import os

if __name__ == '__main__':
    # 第一步：运行用例，生成 allure 数据
    pytest.main(['-sq', '--alluredir', 'results'])

    # 第二步：生成本地 html 报告
    os.system('allure generate -c results/ -o report/')
