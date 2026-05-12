"""
Simple browser-use test script - opens a browser and navigates to Baidu
"""
import asyncio
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from browser_use import Agent, BrowserSession, BrowserProfile
from browser_use.llm.anthropic.chat import ChatAnthropic

async def main():
	print("Starting browser-use test...")

	# Create LLM - using the configured API
	print("Creating LLM...")
	llm = ChatAnthropic(
		model="glm-5.1",
		api_key="sk-vY5baxeQEMZVIAlaopGi3vvsrtc553Oq8NpCM5TSaoLwD4P1",
		base_url="https://mydamoxing.cn",
	)
	print(f"LLM created: {llm}")

	# Create agent with simple task
	print("Creating agent...")
	agent = Agent(
		task="Open https://www.baidu.com",
		llm=llm,
	)
	print(f"Agent created: {agent}")

	# Run the agent
	print("Running agent...")
	await agent.run()
	print("Done!")

if __name__ == "__main__":
	asyncio.run(main())
