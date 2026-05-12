"""
启动 browser-use Agent，自动打开浏览器并执行任务。
使用 .env 中配置的 LLM（GLM-5.1 via Anthropic 兼容接口）。
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv()

from browser_use import Agent
from browser_use.browser import BrowserProfile, BrowserSession
from browser_use.llm.factory import create_llm_from_config
from browser_use.config import CONFIG


async def main():
	# 从 .env 加载 LLM 配置
	config = CONFIG.load_config()
	llm_config = config.get('llm', {})

	if not llm_config:
		print('❌ 未找到 LLM 配置，请检查 .env 文件')
		sys.exit(1)

	print(f'🤖 使用模型: {llm_config.get("model", "未知")} (provider: {llm_config.get("provider", "未知")})')

	llm = create_llm_from_config(llm_config)

	# 浏览器配置：非无头模式，自动打开窗口
	browser_profile = BrowserProfile(
		headless=False,
		keep_alive=True,
	)

	browser_session = BrowserSession(browser_profile=browser_profile)

	task = '打开 https://www.baidu.com，搜索"browser-use"，然后告诉我搜索结果的第一条标题'

	print(f'📋 任务: {task}')
	print('🚀 启动浏览器...\n')

	agent = Agent(
		task=task,
		llm=llm,
		browser=browser_session,
	)

	try:
		history = await agent.run(max_steps=10)
		result = history.final_result()
		print(f'\n✅ 任务完成！\n结果: {result}')
	except KeyboardInterrupt:
		print('\n⏹️  用户中断')
	finally:
		await browser_session.stop()


if __name__ == '__main__':
	asyncio.run(main())
