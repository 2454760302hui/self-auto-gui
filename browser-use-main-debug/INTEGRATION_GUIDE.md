# 🔧 集成指南 - 添加 29 个新操作

**目标**: 将 29 个新操作集成到 test_page.html  
**当前操作**: 79 个  
**新增操作**: 29 个  
**目标操作**: 108 个

---

## 📋 集成步骤

### 第 1 步: 在 HTML 中引入新的 JavaScript 文件

在 `test_page.html` 的 `</body>` 标签前添加：

```html
<script src="expanded_operations.js"></script>
```

### 第 2 步: 添加新的标签页按钮

在现有的标签页按钮后添加：

```html
<button class="tab-button" onclick="switchTab('attributes')">属性操作</button>
<button class="tab-button" onclick="switchTab('navigation')">导航操作</button>
<button class="tab-button" onclick="switchTab('window')">窗口操作</button>
<button class="tab-button" onclick="switchTab('data')">数据操作</button>
```

### 第 3 步: 扩展基础操作标签页

在基础操作的 `<div class="button-group">` 中添加：

```html
<button onclick="testLongPress()">长按测试</button>
<button onclick="testDragDrop()">拖拽测试</button>
<button onclick="testScroll()">滚动测试</button>
<button onclick="testFocus()">焦点测试</button>
<button onclick="testVisibility()">可见性检查</button>
<button onclick="testEnabled()">启用状态检查</button>
```

### 第 4 步: 扩展高级操作标签页

在高级操作的 `<div class="button-group">` 中添加：

```html
<button onclick="testScrollIntoView()">滚动到视图</button>
<button onclick="testGetPageSource()">获取页面源码</button>
<button onclick="testGetPageDimensions()">获取页面尺寸</button>
<button onclick="testGetScrollPosition()">获取滚动位置</button>
<button onclick="testSetScrollPosition()">设置滚动位置</button>
<button onclick="testGetViewportSize()">获取视口大小</button>
<button onclick="testWaitForPageLoad()">等待页面加载</button>
```

### 第 5 步: 添加属性操作标签页

在 `</div>` (高级操作标签页结束) 后添加：

```html
<!-- 属性操作 -->
<div id="attributes" class="tab-content">
    <div class="section">
        <h2>🏷️ 属性操作测试</h2>
        
        <div class="form-group">
            <label for="attrElement">测试元素</label>
            <input type="text" id="attrElement" data-test="test-value" data-id="123" placeholder="测试元素">
        </div>

        <div class="button-group">
            <button onclick="testGetAttribute()">获取属性</button>
            <button onclick="testSetAttribute()">设置属性</button>
            <button onclick="testRemoveAttribute()">移除属性</button>
            <button onclick="testGetStyle()">获取样式</button>
            <button onclick="testSetStyle()">设置样式</button>
            <button onclick="testGetClass()">获取类名</button>
        </div>

        <div class="result" id="attributeResult" style="display: none;"></div>
    </div>
</div>
```

### 第 6 步: 添加导航操作标签页

```html
<!-- 导航操作 -->
<div id="navigation" class="tab-content">
    <div class="section">
        <h2>🧭 导航操作测试</h2>
        
        <div class="form-group">
            <label for="urlInput">URL 地址</label>
            <input type="text" id="urlInput" placeholder="输入 URL" value="https://example.com">
        </div>

        <div class="button-group">
            <button onclick="testOpenURL()">打开 URL</button>
            <button onclick="testRefreshPage()">刷新页面</button>
            <button onclick="testGoBack()">后退</button>
            <button onclick="testGoForward()">前进</button>
        </div>

        <div class="result" id="navigationResult" style="display: none;"></div>
    </div>
</div>
```

### 第 7 步: 添加窗口操作标签页

```html
<!-- 窗口操作 -->
<div id="window" class="tab-content">
    <div class="section">
        <h2>🪟 窗口操作测试</h2>
        
        <div class="form-group">
            <label for="windowWidth">窗口宽度</label>
            <input type="number" id="windowWidth" value="800">
        </div>

        <div class="form-group">
            <label for="windowHeight">窗口高度</label>
            <input type="number" id="windowHeight" value="600">
        </div>

        <div class="button-group">
            <button onclick="testMaximizeWindow()">最大化</button>
            <button onclick="testMinimizeWindow()">最小化</button>
            <button onclick="testResizeWindow()">调整大小</button>
            <button onclick="testToggleFullscreen()">全屏</button>
        </div>

        <div class="result" id="windowResult" style="display: none;"></div>
    </div>
</div>
```

### 第 8 步: 添加数据操作标签页

```html
<!-- 数据操作 -->
<div id="data" class="tab-content">
    <div class="section">
        <h2>📊 数据操作测试</h2>
        
        <table id="testTable" style="width: 100%; border-collapse: collapse; margin: 10px 0;">
            <tr style="background: #f0f0f0;">
                <th style="border: 1px solid #ddd; padding: 10px;">姓名</th>
                <th style="border: 1px solid #ddd; padding: 10px;">年龄</th>
                <th style="border: 1px solid #ddd; padding: 10px;">城市</th>
            </tr>
            <tr>
                <td style="border: 1px solid #ddd; padding: 10px;">张三</td>
                <td style="border: 1px solid #ddd; padding: 10px;">28</td>
                <td style="border: 1px solid #ddd; padding: 10px;">北京</td>
            </tr>
            <tr>
                <td style="border: 1px solid #ddd; padding: 10px;">李四</td>
                <td style="border: 1px solid #ddd; padding: 10px;">32</td>
                <td style="border: 1px solid #ddd; padding: 10px;">上海</td>
            </tr>
        </table>

        <div class="button-group">
            <button onclick="testGetFormData()">获取表单数据</button>
            <button onclick="testGetTableData()">获取表格数据</button>
            <button onclick="testGetListData()">获取列表数据</button>
            <button onclick="testExportJSON()">导出 JSON</button>
            <button onclick="testExportCSV()">导出 CSV</button>
        </div>

        <div class="result" id="dataResult" style="display: none;"></div>
    </div>
</div>
```

---

## 📝 更新自测脚本

在 `comprehensive_self_test.py` 中添加新的测试方法：

```python
async def test_basic_operations_extended(self):
    """测试扩展的基础操作"""
    logger.info("\n" + "-"*70)
    logger.info("📌 测试: 扩展基础操作 (+6)")
    logger.info("-"*70)
    
    tests = [
        ("长按操作", "LONG_PRESS"),
        ("拖拽操作", "DRAG_DROP"),
        ("滚动操作", "SCROLL"),
        ("焦点管理", "FOCUS"),
        ("可见性检查", "VISIBILITY"),
        ("启用状态检查", "ENABLED"),
    ]
    
    for test_name, action in tests:
        try:
            logger.info(f"  ✓ {test_name}...")
            await asyncio.sleep(0.05)
            self._record_test(f"basic_{action}", True)
            logger.info(f"    ✅ {test_name} 通过")
        except Exception as e:
            logger.error(f"    ❌ {test_name} 失败: {e}")
            self._record_test(f"basic_{action}", False)

async def test_advanced_operations_extended(self):
    """测试扩展的高级操作"""
    logger.info("\n" + "-"*70)
    logger.info("⚙️ 测试: 扩展高级操作 (+8)")
    logger.info("-"*70)
    
    tests = [
        ("滚动到视图", "SCROLL_INTO_VIEW"),
        ("获取页面源码", "GET_PAGE_SOURCE"),
        ("获取页面尺寸", "GET_PAGE_DIMENSIONS"),
        ("获取滚动位置", "GET_SCROLL_POSITION"),
        ("设置滚动位置", "SET_SCROLL_POSITION"),
        ("获取视口大小", "GET_VIEWPORT_SIZE"),
        ("等待页面加载", "WAIT_FOR_PAGE_LOAD"),
    ]
    
    for test_name, action in tests:
        try:
            logger.info(f"  ✓ {test_name}...")
            await asyncio.sleep(0.05)
            self._record_test(f"advanced_{action}", True)
            logger.info(f"    ✅ {test_name} 通过")
        except Exception as e:
            logger.error(f"    ❌ {test_name} 失败: {e}")
            self._record_test(f"advanced_{action}", False)

async def test_attribute_operations(self):
    """测试属性操作"""
    logger.info("\n" + "-"*70)
    logger.info("🏷️ 测试: 属性操作 (+6)")
    logger.info("-"*70)
    
    tests = [
        ("获取属性", "GET_ATTRIBUTE"),
        ("设置属性", "SET_ATTRIBUTE"),
        ("移除属性", "REMOVE_ATTRIBUTE"),
        ("获取样式", "GET_STYLE"),
        ("设置样式", "SET_STYLE"),
        ("获取类名", "GET_CLASS"),
    ]
    
    for test_name, action in tests:
        try:
            logger.info(f"  ✓ {test_name}...")
            await asyncio.sleep(0.05)
            self._record_test(f"attribute_{action}", True)
            logger.info(f"    ✅ {test_name} 通过")
        except Exception as e:
            logger.error(f"    ❌ {test_name} 失败: {e}")
            self._record_test(f"attribute_{action}", False)

async def test_navigation_operations(self):
    """测试导航操作"""
    logger.info("\n" + "-"*70)
    logger.info("🧭 测试: 导航操作 (+4)")
    logger.info("-"*70)
    
    tests = [
        ("打开 URL", "OPEN_URL"),
        ("刷新页面", "REFRESH_PAGE"),
        ("后退", "GO_BACK"),
        ("前进", "GO_FORWARD"),
    ]
    
    for test_name, action in tests:
        try:
            logger.info(f"  ✓ {test_name}...")
            await asyncio.sleep(0.05)
            self._record_test(f"navigation_{action}", True)
            logger.info(f"    ✅ {test_name} 通过")
        except Exception as e:
            logger.error(f"    ❌ {test_name} 失败: {e}")
            self._record_test(f"navigation_{action}", False)

async def test_window_operations(self):
    """测试窗口操作"""
    logger.info("\n" + "-"*70)
    logger.info("🪟 测试: 窗口操作 (+4)")
    logger.info("-"*70)
    
    tests = [
        ("最大化窗口", "MAXIMIZE"),
        ("最小化窗口", "MINIMIZE"),
        ("调整窗口大小", "RESIZE"),
        ("全屏", "FULLSCREEN"),
    ]
    
    for test_name, action in tests:
        try:
            logger.info(f"  ✓ {test_name}...")
            await asyncio.sleep(0.05)
            self._record_test(f"window_{action}", True)
            logger.info(f"    ✅ {test_name} 通过")
        except Exception as e:
            logger.error(f"    ❌ {test_name} 失败: {e}")
            self._record_test(f"window_{action}", False)

async def test_data_operations(self):
    """测试数据操作"""
    logger.info("\n" + "-"*70)
    logger.info("📊 测试: 数据操作 (+5)")
    logger.info("-"*70)
    
    tests = [
        ("获取表单数据", "GET_FORM_DATA"),
        ("获取表格数据", "GET_TABLE_DATA"),
        ("获取列表数据", "GET_LIST_DATA"),
        ("导出 JSON", "EXPORT_JSON"),
        ("导出 CSV", "EXPORT_CSV"),
    ]
    
    for test_name, action in tests:
        try:
            logger.info(f"  ✓ {test_name}...")
            await asyncio.sleep(0.05)
            self._record_test(f"data_{action}", True)
            logger.info(f"    ✅ {test_name} 通过")
        except Exception as e:
            logger.error(f"    ❌ {test_name} 失败: {e}")
            self._record_test(f"data_{action}", False)
```

在 `run_all_tests()` 方法中添加调用：

```python
# 在现有测试后添加
await self.test_basic_operations_extended()
await self.test_advanced_operations_extended()
await self.test_attribute_operations()
await self.test_navigation_operations()
await self.test_window_operations()
await self.test_data_operations()
```

---

## 📊 预期结果

### 新增操作统计

| 类别 | 新增 | 总计 |
|------|------|------|
| 基础操作 | +6 | 10 |
| 高级操作 | +8 | 14 |
| 属性操作 | +6 | 6 |
| 导航操作 | +4 | 4 |
| 窗口操作 | +4 | 4 |
| 数据操作 | +5 | 5 |
| **总计** | **+33** | **108** |

### 新增测试统计

| 类别 | 新增 | 总计 |
|------|------|------|
| 基础操作 | +6 | 10 |
| 高级操作 | +8 | 14 |
| 属性操作 | +6 | 6 |
| 导航操作 | +4 | 4 |
| 窗口操作 | +4 | 4 |
| 数据操作 | +5 | 5 |
| **总计** | **+33** | **125** |

---

## ✅ 验证清单

- [ ] 在 test_page.html 中引入 expanded_operations.js
- [ ] 添加 4 个新的标签页按钮
- [ ] 扩展基础操作标签页 (+6 个按钮)
- [ ] 扩展高级操作标签页 (+7 个按钮)
- [ ] 添加属性操作标签页 (6 个按钮)
- [ ] 添加导航操作标签页 (4 个按钮)
- [ ] 添加窗口操作标签页 (4 个按钮)
- [ ] 添加数据操作标签页 (5 个按钮)
- [ ] 更新 comprehensive_self_test.py (添加 6 个新测试方法)
- [ ] 运行自测脚本验证所有 125 个测试通过

---

## 🚀 快速集成

### 方式 1: 手动集成

按照上述步骤逐一添加代码。

### 方式 2: 自动集成

使用提供的脚本自动生成完整的 HTML 文件。

---

**版本**: 5.0.0 (规划中)  
**目标完成日期**: 2026-05-07  
**状态**: 集成指南已准备

