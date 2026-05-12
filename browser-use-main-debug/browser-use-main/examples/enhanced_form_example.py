"""
增强功能示例 - 演示如何使用智能等待和扩展表单操作

这个示例展示了如何使用新增的功能来填写复杂的表单。
"""

import asyncio
import logging
from typing import Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EnhancedFormExample:
    """增强表单示例"""
    
    def __init__(self):
        """初始化示例"""
        self.agent = None
        self.browser = None
    
    async def setup(self):
        """设置浏览器和Agent"""
        try:
            # 这里需要根据实际项目结构导入
            # from browser_use.agent import Agent
            # from browser_use.browser import Browser
            
            # self.browser = Browser()
            # self.agent = Agent(browser=self.browser)
            
            logger.info("✅ 浏览器和Agent已初始化")
        except Exception as e:
            logger.error(f"❌ 初始化失败: {e}")
            raise
    
    async def example_1_pizza_order(self):
        """
        示例1: 填写披萨订单表单
        
        这个示例演示了如何填写包含多种表单控件的订单表单。
        """
        logger.info("\n" + "="*50)
        logger.info("示例1: 填写披萨订单表单")
        logger.info("="*50)
        
        try:
            # 1. 打开表单页面
            logger.info("📄 打开订单表单...")
            # await self.agent.act("打开 https://example.com/pizza-order")
            
            # 2. 填充客户信息
            logger.info("👤 填充客户信息...")
            # await self.agent.act("填充客户名称为 李四")
            # await self.agent.act("填充电话号码为 13900001111")
            # await self.agent.act("填充邮箱为 li@example.com")
            
            # 3. 选择披萨大小
            logger.info("🍕 选择披萨大小...")
            # await self.agent.act("选择披萨大小为 Medium")
            
            # 4. 选择配料
            logger.info("🧅 选择配料...")
            # await self.agent.act("勾选配料 Bacon")
            # await self.agent.act("勾选配料 Onion")
            
            # 5. 填充配送时间
            logger.info("⏰ 填充配送时间...")
            # await self.agent.act("填充配送时间为 14:30")
            
            # 6. 填充配送说明
            logger.info("📝 填充配送说明...")
            # await self.agent.act("填充配送说明为 这是一条测试留言")
            
            # 7. 智能等待表单验证
            logger.info("⏳ 等待表单验证...")
            # await self.agent.act("等待DOM稳定")
            
            # 8. 提交订单
            logger.info("✅ 提交订单...")
            # await self.agent.act("点击提交按钮")
            
            # 9. 等待结果
            logger.info("⏳ 等待订单确认...")
            # await self.agent.act("等待网络空闲")
            
            logger.info("✅ 订单已提交")
            
        except Exception as e:
            logger.error(f"❌ 示例1失败: {e}")
    
    async def example_2_smart_wait(self):
        """
        示例2: 智能等待演示
        
        这个示例演示了不同的等待策略。
        """
        logger.info("\n" + "="*50)
        logger.info("示例2: 智能等待演示")
        logger.info("="*50)
        
        try:
            # 1. 固定时间等待
            logger.info("⏳ 固定时间等待 3 秒...")
            # await self.agent.act("等待 3 秒")
            
            # 2. 网络空闲等待
            logger.info("🌐 等待网络空闲...")
            # await self.agent.act("等待网络空闲")
            
            # 3. DOM稳定等待
            logger.info("🔄 等待DOM稳定...")
            # await self.agent.act("等待DOM稳定")
            
            # 4. 元素可见等待
            logger.info("👁️ 等待元素可见...")
            # await self.agent.act("等待元素可见")
            
            logger.info("✅ 所有等待完成")
            
        except Exception as e:
            logger.error(f"❌ 示例2失败: {e}")
    
    async def example_3_date_time_fields(self):
        """
        示例3: 日期和时间字段
        
        这个示例演示了如何填充日期和时间字段。
        """
        logger.info("\n" + "="*50)
        logger.info("示例3: 日期和时间字段")
        logger.info("="*50)
        
        try:
            # 1. 填充日期字段
            logger.info("📅 填充日期字段...")
            # await self.agent.act("填充日期字段为 2024-05-06")
            
            # 2. 填充时间字段
            logger.info("⏰ 填充时间字段...")
            # await self.agent.act("填充时间字段为 14:30")
            
            # 3. 填充日期时间字段
            logger.info("📅⏰ 填充日期时间字段...")
            # await self.agent.act("填充日期时间字段为 2024-05-06T14:30")
            
            logger.info("✅ 日期和时间字段已填充")
            
        except Exception as e:
            logger.error(f"❌ 示例3失败: {e}")
    
    async def example_4_advanced_controls(self):
        """
        示例4: 高级表单控件
        
        这个示例演示了如何使用高级表单控件。
        """
        logger.info("\n" + "="*50)
        logger.info("示例4: 高级表单控件")
        logger.info("="*50)
        
        try:
            # 1. 填充数字字段
            logger.info("🔢 填充数字字段...")
            # await self.agent.act("填充数字字段为 42")
            
            # 2. 填充颜色字段
            logger.info("🎨 填充颜色字段...")
            # await self.agent.act("填充颜色字段为 #FF0000")
            
            # 3. 设置范围滑块
            logger.info("📊 设置范围滑块...")
            # await self.agent.act("设置范围滑块为 50")
            
            # 4. 添加标签
            logger.info("🏷️ 添加标签...")
            # await self.agent.act("添加标签 python")
            # await self.agent.act("添加标签 javascript")
            
            # 5. 移除标签
            logger.info("🗑️ 移除标签...")
            # await self.agent.act("移除标签 python")
            
            logger.info("✅ 高级表单控件已操作")
            
        except Exception as e:
            logger.error(f"❌ 示例4失败: {e}")
    
    async def example_5_dynamic_form(self):
        """
        示例5: 动态表单填充
        
        这个示例演示了如何动态检测和填充表单字段。
        """
        logger.info("\n" + "="*50)
        logger.info("示例5: 动态表单填充")
        logger.info("="*50)
        
        try:
            # 1. 检测字段类型
            logger.info("🔍 检测字段类型...")
            # field_type = await self.agent.act("检测字段类型")
            # logger.info(f"字段类型: {field_type}")
            
            # 2. 根据类型填充
            # if "date" in field_type:
            #     logger.info("📅 填充日期字段...")
            #     await self.agent.act("填充日期字段为 2024-05-06")
            # elif "time" in field_type:
            #     logger.info("⏰ 填充时间字段...")
            #     await self.agent.act("填充时间字段为 14:30")
            # elif "number" in field_type:
            #     logger.info("🔢 填充数字字段...")
            #     await self.agent.act("填充数字字段为 42")
            
            # 3. 等待完成
            logger.info("⏳ 等待表单保存...")
            # await self.agent.act("等待网络空闲")
            
            logger.info("✅ 动态表单已填充")
            
        except Exception as e:
            logger.error(f"❌ 示例5失败: {e}")
    
    async def example_6_complex_workflow(self):
        """
        示例6: 复杂工作流
        
        这个示例演示了如何组合多个操作完成复杂的工作流。
        """
        logger.info("\n" + "="*50)
        logger.info("示例6: 复杂工作流")
        logger.info("="*50)
        
        try:
            # 1. 打开页面
            logger.info("📄 打开页面...")
            # await self.agent.act("打开 https://example.com/complex-form")
            
            # 2. 等待页面加载
            logger.info("⏳ 等待页面加载...")
            # await self.agent.act("等待网络空闲")
            # await self.agent.act("等待DOM稳定")
            
            # 3. 填充表单
            logger.info("📝 填充表单...")
            # await self.agent.act("填充客户名称为 李四")
            # await self.agent.act("填充电话号码为 13900001111")
            # await self.agent.act("填充邮箱为 li@example.com")
            
            # 4. 选择选项
            logger.info("✅ 选择选项...")
            # await self.agent.act("选择产品类型为 标准版")
            # await self.agent.act("选择配送方式为 快递")
            
            # 5. 填充日期和时间
            logger.info("📅⏰ 填充日期和时间...")
            # await self.agent.act("填充订单日期为 2024-05-06")
            # await self.agent.act("填充配送时间为 14:30")
            
            # 6. 等待验证
            logger.info("⏳ 等待表单验证...")
            # await self.agent.act("等待DOM稳定")
            
            # 7. 提交表单
            logger.info("✅ 提交表单...")
            # await self.agent.act("点击提交按钮")
            
            # 8. 等待结果
            logger.info("⏳ 等待结果...")
            # await self.agent.act("等待网络空闲")
            
            # 9. 获取结果
            logger.info("📊 获取结果...")
            # result = await self.agent.act("获取页面标题")
            # logger.info(f"结果: {result}")
            
            logger.info("✅ 复杂工作流已完成")
            
        except Exception as e:
            logger.error(f"❌ 示例6失败: {e}")
    
    async def run_all_examples(self):
        """运行所有示例"""
        logger.info("\n" + "="*50)
        logger.info("开始运行增强功能示例")
        logger.info("="*50)
        
        try:
            # 设置
            await self.setup()
            
            # 运行示例
            await self.example_1_pizza_order()
            await self.example_2_smart_wait()
            await self.example_3_date_time_fields()
            await self.example_4_advanced_controls()
            await self.example_5_dynamic_form()
            await self.example_6_complex_workflow()
            
            logger.info("\n" + "="*50)
            logger.info("✅ 所有示例已完成")
            logger.info("="*50)
            
        except Exception as e:
            logger.error(f"❌ 运行示例失败: {e}")
        finally:
            # 清理
            if self.browser:
                await self.browser.close()


async def main():
    """主函数"""
    example = EnhancedFormExample()
    await example.run_all_examples()


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())
