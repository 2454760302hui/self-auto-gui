# 增强功能指南

本文档介绍了 browser-use 项目的增强功能，包括智能等待机制和扩展表单操作。

## 目录

1. [智能等待机制](#智能等待机制)
2. [扩展表单操作](#扩展表单操作)
3. [集成指南](#集成指南)
4. [使用示例](#使用示例)

---

## 智能等待机制

### 概述

智能等待机制提供了多种等待策略，可以根据不同的场景自动调整等待时间，而不是使用固定的延迟。这使得自动化流程更加高效和可靠。

### 等待策略

#### 1. 固定时间等待 (FIXED)
最基础的等待方式，等待指定的秒数。

```python
# 等待3秒
await smart_wait(SmartWaitAction(
    strategy="fixed",
    timeout=3,
    reason="等待页面加载"
))
```

#### 2. 网络空闲等待 (NETWORK_IDLE)
等待所有网络请求完成，适合异步加载的页面。

```python
# 等待网络空闲
await smart_wait(SmartWaitAction(
    strategy="network_idle",
    timeout=10,
    reason="等待API响应"
))
```

#### 3. DOM稳定等待 (DOM_STABLE)
等待DOM树不再变化，适合动态渲染的页面。

```python
# 等待DOM稳定
await smart_wait(SmartWaitAction(
    strategy="dom_stable",
    timeout=5,
    reason="等待动态内容加载"
))
```

#### 4. 元素可见等待 (ELEMENT_VISIBLE)
等待特定元素变为可见。

```python
# 等待元素可见
await smart_wait(SmartWaitAction(
    strategy="element_visible",
    timeout=5,
    reason="等待模态框出现"
))
```

#### 5. 自定义条件等待 (CONDITION)
等待自定义条件满足。

```python
# 等待自定义条件
await smart_wait(SmartWaitAction(
    strategy="condition",
    timeout=10,
    reason="等待特定状态"
))
```

### 可视化反馈

所有等待操作都会提供可视化反馈：

```
⏳ 等待 3s 等待页面加载
🌐 等待网络空闲 等待API响应
🔄 等待DOM稳定 等待动态内容加载
👁️ 等待元素可见 等待模态框出现
⚙️ 等待条件满足 等待特定状态
```

---

## 扩展表单操作

### 概述

扩展表单操作支持更多类型的表单控件，包括日期/时间选择器、数字输入、颜色选择、范围滑块等。

### 支持的表单控件类型

| 控件类型 | 说明 | 示例 |
|---------|------|------|
| TEXT | 文本输入 | `<input type="text">` |
| NUMBER | 数字输入 | `<input type="number">` |
| EMAIL | 邮箱输入 | `<input type="email">` |
| PASSWORD | 密码输入 | `<input type="password">` |
| TEXTAREA | 多行文本 | `<textarea>` |
| SELECT | 下拉选择 | `<select>` |
| CHECKBOX | 复选框 | `<input type="checkbox">` |
| RADIO | 单选框 | `<input type="radio">` |
| DATE | 日期选择 | `<input type="date">` |
| TIME | 时间选择 | `<input type="time">` |
| DATETIME | 日期时间选择 | `<input type="datetime-local">` |
| COLOR | 颜色选择 | `<input type="color">` |
| RANGE | 范围滑块 | `<input type="range">` |
| FILE | 文件上传 | `<input type="file">` |
| COMBOBOX | 自动完成 | `role="combobox"` |
| TAG_INPUT | 标签输入 | 自定义标签输入框 |
| RICH_TEXT | 富文本编辑器 | `contenteditable="true"` |
| MULTI_SELECT | 多选下拉 | `<select multiple>` |
| CASCADING_SELECT | 级联选择 | 多级联动选择 |
| TOGGLE | 开关 | 开关按钮 |
| RATING | 评分 | 星级评分 |
| SLIDER | 滑块 | 滑块控件 |

### 表单操作

#### 1. 检测表单字段类型

自动识别表单字段的类型。

```python
# 检测字段类型
result = await detect_form_field(DetectFormFieldAction(
    index=5  # 元素索引
))
# 返回: "✅ 字段类型: date"
```

#### 2. 填充日期字段

支持日期选择器和日期输入框。

```python
# 填充日期字段
result = await fill_date_field(FillDateFieldAction(
    index=5,
    date_value="2024-05-06",
    format="YYYY-MM-DD"
))
# 返回: "✅ Date field filled with 2024-05-06"
```

支持的日期格式：
- `YYYY-MM-DD` (ISO格式)
- `DD/MM/YYYY` (欧洲格式)
- `MM/DD/YYYY` (美国格式)

#### 3. 填充时间字段

支持时间选择器和时间输入框。

```python
# 填充时间字段
result = await fill_time_field(FillTimeFieldAction(
    index=6,
    time_value="14:30",
    format="HH:MM"
))
# 返回: "✅ Time field filled with 14:30"
```

支持的时间格式：
- `HH:MM` (小时:分钟)
- `HH:MM:SS` (小时:分钟:秒)

#### 4. 填充数字字段

支持数字输入框和范围验证。

```python
# 填充数字字段
result = await fill_number_field(FillNumberFieldAction(
    index=7,
    number_value=42,
    min_value=0,
    max_value=100
))
# 返回: "✅ Number field filled with 42"
```

#### 5. 填充颜色字段

支持颜色选择器。

```python
# 填充颜色字段
result = await fill_color_field(FillColorFieldAction(
    index=8,
    color_value="#FF0000"  # 或 "rgb(255,0,0)"
))
# 返回: "✅ Color field filled with #ff0000"
```

支持的颜色格式：
- 十六进制: `#RRGGBB` (如 `#FF0000`)
- RGB: `rgb(r,g,b)` (如 `rgb(255,0,0)`)

#### 6. 设置范围滑块值

支持范围输入和滑块控件。

```python
# 设置范围滑块值
result = await set_range_value(SetRangeValueAction(
    index=9,
    value=50,
    min_value=0,
    max_value=100
))
# 返回: "✅ Range slider set to 50"
```

#### 7. 添加标签

支持标签输入框。

```python
# 添加标签
result = await add_tag(AddTagAction(
    index=10,
    tag_value="python"
))
# 返回: "✅ Tag 'python' added"
```

#### 8. 移除标签

支持标签输入框。

```python
# 移除标签
result = await remove_tag(RemoveTagAction(
    index=10,
    tag_value="python"
))
# 返回: "✅ Tag 'python' removed"
```

---

## 集成指南

### 1. 导入模块

```python
from browser_use.tools.enhanced_tools import EnhancedTools
from browser_use.tools.smart_wait import SmartWaiter, WaitConfig, WaitStrategy
from browser_use.tools.form_actions import FormActionHandler, FormControlType
```

### 2. 初始化增强工具

在 `Tools` 类初始化时添加增强工具：

```python
class Tools:
    def __init__(self, registry, browser_session=None):
        # ... 现有初始化代码 ...
        
        # 初始化增强工具
        self.enhanced_tools = EnhancedTools(registry, browser_session)
```

### 3. 在Agent中使用

Agent 可以直接调用这些新工具：

```python
# 智能等待
await agent.act("等待网络空闲")

# 填充日期
await agent.act("填充日期字段为 2024-05-06")

# 填充时间
await agent.act("填充时间字段为 14:30")

# 填充数字
await agent.act("填充数字字段为 42")

# 填充颜色
await agent.act("填充颜色字段为红色")

# 设置范围
await agent.act("设置范围滑块为 50")

# 添加标签
await agent.act("添加标签 python")

# 移除标签
await agent.act("移除标签 python")
```

---

## 使用示例

### 示例1: 填写披萨订单表单

```python
# 场景：填写图中的披萨订单表单

# 1. 填充客户名称
await input(InputTextAction(index=0, text="李四"))

# 2. 填充电话号码
await input(InputTextAction(index=1, text="13900001111"))

# 3. 填充邮箱
await input(InputTextAction(index=2, text="li@example.com"))

# 4. 选择披萨大小（Medium）
await click(ClickElementAction(index=3))  # 点击Medium单选框

# 5. 选择配料（Onion）
await click(ClickElementAction(index=7))  # 点击Onion复选框

# 6. 填充配送时间
await fill_time_field(FillTimeFieldAction(
    index=8,
    time_value="14:30",
    format="HH:MM"
))

# 7. 填充配送说明
await input(InputTextAction(index=9, text="这是一条测试留言"))

# 8. 智能等待表单验证
await smart_wait(SmartWaitAction(
    strategy="dom_stable",
    timeout=2,
    reason="等待表单验证完成"
))

# 9. 提交订单
await click(ClickElementAction(index=10))  # 点击Submit按钮
```

### 示例2: 动态表单填充

```python
# 场景：填充包含多种控件的动态表单

# 1. 检测字段类型
field_type = await detect_form_field(DetectFormFieldAction(index=0))

# 2. 根据类型填充
if "date" in field_type:
    await fill_date_field(FillDateFieldAction(
        index=0,
        date_value="2024-05-06"
    ))
elif "time" in field_type:
    await fill_time_field(FillTimeFieldAction(
        index=0,
        time_value="14:30"
    ))
elif "number" in field_type:
    await fill_number_field(FillNumberFieldAction(
        index=0,
        number_value=42
    ))
elif "color" in field_type:
    await fill_color_field(FillColorFieldAction(
        index=0,
        color_value="#FF0000"
    ))

# 3. 智能等待
await smart_wait(SmartWaitAction(
    strategy="network_idle",
    timeout=5,
    reason="等待表单数据保存"
))
```

### 示例3: 高级等待策略

```python
# 场景：处理复杂的异步加载场景

# 1. 点击按钮触发加载
await click(ClickElementAction(index=0))

# 2. 等待网络请求完成
await smart_wait(SmartWaitAction(
    strategy="network_idle",
    timeout=10,
    reason="等待数据加载"
))

# 3. 等待DOM稳定
await smart_wait(SmartWaitAction(
    strategy="dom_stable",
    timeout=5,
    reason="等待页面渲染完成"
))

# 4. 等待特定元素出现
await smart_wait(SmartWaitAction(
    strategy="element_visible",
    timeout=5,
    reason="等待结果显示"
))

# 5. 提取结果
result = await get_text(GetTextAction(index=5))
```

---

## 最佳实践

### 1. 选择合适的等待策略

- **固定等待**: 用于已知延迟的场景
- **网络空闲**: 用于异步API调用
- **DOM稳定**: 用于动态渲染的页面
- **元素可见**: 用于模态框或弹窗
- **自定义条件**: 用于复杂的业务逻辑

### 2. 合理设置超时时间

- 网络请求: 10-30秒
- DOM渲染: 5-10秒
- 元素出现: 5-10秒
- 固定等待: 1-5秒

### 3. 提供清晰的等待原因

```python
# 好的做法
await smart_wait(SmartWaitAction(
    strategy="network_idle",
    timeout=10,
    reason="等待用户列表API响应"
))

# 不好的做法
await smart_wait(SmartWaitAction(
    strategy="network_idle",
    timeout=10,
    reason="等待"
))
```

### 4. 组合使用多个等待策略

```python
# 先等待网络空闲，再等待DOM稳定
await smart_wait(SmartWaitAction(
    strategy="network_idle",
    timeout=10,
    reason="等待API响应"
))

await smart_wait(SmartWaitAction(
    strategy="dom_stable",
    timeout=5,
    reason="等待页面渲染"
))
```

### 5. 错误处理

```python
try:
    result = await fill_date_field(FillDateFieldAction(
        index=5,
        date_value="2024-05-06"
    ))
    if not result.get("success"):
        logger.error(f"Failed to fill date: {result.get('error')}")
except Exception as e:
    logger.error(f"Error: {e}")
```

---

## 故障排除

### 问题1: 等待超时

**症状**: 等待操作超时

**解决方案**:
1. 增加超时时间
2. 检查网络连接
3. 检查页面是否加载完成
4. 尝试不同的等待策略

### 问题2: 表单字段填充失败

**症状**: 字段值未正确填充

**解决方案**:
1. 检查元素索引是否正确
2. 使用 `detect_form_field` 确认字段类型
3. 检查字段是否被禁用或隐藏
4. 尝试先点击字段获取焦点

### 问题3: 日期/时间格式错误

**症状**: 日期/时间未正确填充

**解决方案**:
1. 检查日期/时间格式是否正确
2. 确认浏览器的日期/时间格式设置
3. 尝试不同的格式

---

## 性能优化

### 1. 减少等待时间

使用更精确的等待策略而不是固定延迟：

```python
# 不推荐：固定等待5秒
await asyncio.sleep(5)

# 推荐：等待网络空闲
await smart_wait(SmartWaitAction(
    strategy="network_idle",
    timeout=5,
    reason="等待数据加载"
))
```

### 2. 并行执行

对于独立的操作，可以并行执行：

```python
# 并行填充多个字段
await asyncio.gather(
    fill_date_field(FillDateFieldAction(index=0, date_value="2024-05-06")),
    fill_time_field(FillTimeFieldAction(index=1, time_value="14:30")),
    fill_number_field(FillNumberFieldAction(index=2, number_value=42)),
)
```

### 3. 缓存字段类型

避免重复检测字段类型：

```python
# 缓存字段类型
field_types = {}
for i in range(10):
    if i not in field_types:
        field_types[i] = await detect_form_field(DetectFormFieldAction(index=i))
```

---

## 贡献指南

如果你想为增强功能做出贡献，请：

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 开启 Pull Request

---

## 许可证

本项目采用 MIT 许可证。详见 LICENSE 文件。

---

## 联系方式

如有问题或建议，请提交 Issue 或 Pull Request。
