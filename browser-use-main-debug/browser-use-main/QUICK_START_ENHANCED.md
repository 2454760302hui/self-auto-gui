# 快速开始 - 增强功能

本指南帮助你快速上手 browser-use 的增强功能。

## 5分钟快速开始

### 1. 安装

```bash
# 克隆项目
git clone https://github.com/browser-use/browser-use.git
cd browser-use

# 安装依赖
pip install -e .
```

### 2. 基础使用

#### 智能等待

```python
from browser_use.agent import Agent
from browser_use.browser import Browser

# 创建浏览器和Agent
browser = Browser()
agent = Agent(browser=browser)

# 使用智能等待
await agent.act("等待网络空闲")
await agent.act("等待DOM稳定")
await agent.act("等待元素可见")
```

#### 表单操作

```python
# 填充日期字段
await agent.act("填充日期字段为 2024-05-06")

# 填充时间字段
await agent.act("填充时间字段为 14:30")

# 填充数字字段
await agent.act("填充数字字段为 42")

# 填充颜色字段
await agent.act("填充颜色字段为红色")

# 设置范围滑块
await agent.act("设置范围滑块为 50")

# 添加标签
await agent.act("添加标签 python")

# 移除标签
await agent.act("移除标签 python")
```

### 3. 完整示例

```python
import asyncio
from browser_use.agent import Agent
from browser_use.browser import Browser

async def main():
    # 初始化浏览器
    browser = Browser()
    
    # 创建Agent
    agent = Agent(browser=browser)
    
    # 打开网页
    await agent.act("打开 https://example.com/form")
    
    # 填充表单
    await agent.act("填充客户名称为 李四")
    await agent.act("填充电话号码为 13900001111")
    await agent.act("填充邮箱为 li@example.com")
    
    # 选择选项
    await agent.act("选择披萨大小为 Medium")
    await agent.act("勾选配料 Onion")
    
    # 填充日期和时间
    await agent.act("填充配送日期为 2024-05-06")
    await agent.act("填充配送时间为 14:30")
    
    # 智能等待
    await agent.act("等待表单验证完成")
    
    # 提交表单
    await agent.act("点击提交按钮")
    
    # 等待结果
    await agent.act("等待网络空闲")
    
    # 获取结果
    result = await agent.act("获取页面标题")
    print(f"结果: {result}")

# 运行
asyncio.run(main())
```

## 常见场景

### 场景1: 填写订单表单

```python
# 1. 打开表单
await agent.act("打开订单表单")

# 2. 填充基本信息
await agent.act("填充客户名称")
await agent.act("填充电话号码")
await agent.act("填充邮箱地址")

# 3. 选择选项
await agent.act("选择产品类型")
await agent.act("选择配送方式")

# 4. 填充日期和时间
await agent.act("填充订单日期")
await agent.act("填充配送时间")

# 5. 等待验证
await agent.act("等待表单验证")

# 6. 提交
await agent.act("提交订单")
```

### 场景2: 处理异步加载

```python
# 1. 点击按钮触发加载
await agent.act("点击加载按钮")

# 2. 等待网络请求
await agent.act("等待网络空闲")

# 3. 等待DOM更新
await agent.act("等待DOM稳定")

# 4. 等待元素出现
await agent.act("等待结果显示")

# 5. 提取数据
result = await agent.act("获取结果内容")
```

### 场景3: 动态表单填充

```python
# 1. 检测字段类型
field_type = await agent.act("检测字段类型")

# 2. 根据类型填充
if "date" in field_type:
    await agent.act("填充日期字段")
elif "time" in field_type:
    await agent.act("填充时间字段")
elif "number" in field_type:
    await agent.act("填充数字字段")

# 3. 等待完成
await agent.act("等待表单保存")
```

## 等待策略对比

| 策略 | 用途 | 超时时间 | 示例 |
|------|------|---------|------|
| fixed | 固定延迟 | 1-5秒 | 等待3秒 |
| network_idle | 网络请求完成 | 10-30秒 | 等待API响应 |
| dom_stable | DOM稳定 | 5-10秒 | 等待页面渲染 |
| element_visible | 元素出现 | 5-10秒 | 等待模态框 |
| condition | 自定义条件 | 10-30秒 | 等待特定状态 |

## 表单控件类型

| 类型 | HTML | 示例 |
|------|------|------|
| 文本 | `<input type="text">` | 输入框 |
| 数字 | `<input type="number">` | 数字输入 |
| 日期 | `<input type="date">` | 日期选择 |
| 时间 | `<input type="time">` | 时间选择 |
| 颜色 | `<input type="color">` | 颜色选择 |
| 范围 | `<input type="range">` | 滑块 |
| 下拉 | `<select>` | 下拉菜单 |
| 复选 | `<input type="checkbox">` | 复选框 |
| 单选 | `<input type="radio">` | 单选框 |

## 调试技巧

### 1. 启用日志

```python
import logging

# 启用调试日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
```

### 2. 检查元素

```python
# 获取元素信息
element_info = await agent.act("获取元素信息")
print(element_info)
```

### 3. 截图

```python
# 截图当前页面
await agent.act("截图")
```

### 4. 检查网络

```python
# 等待网络空闲并显示日志
await agent.act("等待网络空闲")
```

## 性能优化

### 1. 使用合适的等待策略

```python
# ❌ 不推荐：固定等待
await asyncio.sleep(5)

# ✅ 推荐：智能等待
await agent.act("等待网络空闲")
```

### 2. 并行操作

```python
# 并行填充多个字段
await asyncio.gather(
    agent.act("填充字段1"),
    agent.act("填充字段2"),
    agent.act("填充字段3"),
)
```

### 3. 缓存结果

```python
# 缓存页面状态
page_state = await agent.act("获取页面状态")
# 重复使用 page_state
```

## 常见问题

### Q: 等待超时怎么办？

A: 尝试以下方法：
1. 增加超时时间
2. 检查网络连接
3. 尝试不同的等待策略
4. 检查页面是否正确加载

### Q: 表单字段填充失败？

A: 检查以下几点：
1. 元素索引是否正确
2. 字段是否被禁用
3. 字段是否隐藏
4. 字段类型是否正确

### Q: 日期格式错误？

A: 确保使用正确的格式：
- ISO格式: `YYYY-MM-DD`
- 欧洲格式: `DD/MM/YYYY`
- 美国格式: `MM/DD/YYYY`

### Q: 如何处理动态加载？

A: 使用智能等待：
```python
await agent.act("等待网络空闲")
await agent.act("等待DOM稳定")
```

## 下一步

- 查看 [完整文档](ENHANCED_FEATURES.md)
- 查看 [示例代码](examples/)
- 提交 [Issue](https://github.com/browser-use/browser-use/issues)
- 贡献 [代码](CONTRIBUTING.md)

## 获取帮助

- 📖 [文档](ENHANCED_FEATURES.md)
- 💬 [讨论](https://github.com/browser-use/browser-use/discussions)
- 🐛 [报告问题](https://github.com/browser-use/browser-use/issues)
- 📧 [联系我们](mailto:support@browser-use.com)

---

祝你使用愉快！🚀
