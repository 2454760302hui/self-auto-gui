# 🚀 功能扩展计划 - 从 79 个操作扩展到 108 个

**目标**: 补充所有缺失的自动化操作  
**当前**: 79 个操作  
**目标**: 108 个操作  
**增加**: 29 个操作

---

## 📊 扩展清单

### 1️⃣ 基础操作 (4 → 10 个) +6

**当前** (4 个):
- ✅ 点击
- ✅ 双击
- ✅ 右键点击
- ✅ 悬停

**需要添加** (6 个):
- [ ] 长按 (Long Press)
- [ ] 拖拽 (Drag & Drop)
- [ ] 滚动 (Scroll)
- [ ] 焦点管理 (Focus)
- [ ] 元素可见性检查 (Visibility Check)
- [ ] 元素启用状态检查 (Enabled Check)

### 2️⃣ 高级操作 (6 → 14 个) +8

**当前** (6 个):
- ✅ 页面滚动
- ✅ JavaScript 执行
- ✅ 页面信息获取
- ✅ 截图
- ✅ 页面刷新
- ✅ 页面后退/前进

**需要添加** (8 个):
- [ ] 元素滚动到视图 (Scroll Into View)
- [ ] 获取页面源码 (Get Page Source)
- [ ] 获取页面高度 (Get Page Height)
- [ ] 获取页面宽度 (Get Page Width)
- [ ] 获取滚动位置 (Get Scroll Position)
- [ ] 设置滚动位置 (Set Scroll Position)
- [ ] 获取视口大小 (Get Viewport Size)
- [ ] 等待页面加载完成 (Wait for Page Load)

### 3️⃣ 属性操作 (0 → 6 个) +6

**需要添加** (6 个):
- [ ] 获取属性 (Get Attribute)
- [ ] 设置属性 (Set Attribute)
- [ ] 移除属性 (Remove Attribute)
- [ ] 获取样式 (Get Style)
- [ ] 设置样式 (Set Style)
- [ ] 获取类名 (Get Class)

### 4️⃣ 导航操作 (0 → 4 个) +4

**需要添加** (4 个):
- [ ] 打开 URL (Open URL)
- [ ] 页面刷新 (Refresh Page)
- [ ] 页面后退 (Go Back)
- [ ] 页面前进 (Go Forward)

### 5️⃣ 窗口操作 (0 → 4 个) +4

**需要添加** (4 个):
- [ ] 最大化窗口 (Maximize Window)
- [ ] 最小化窗口 (Minimize Window)
- [ ] 调整窗口大小 (Resize Window)
- [ ] 切换全屏 (Toggle Fullscreen)

### 6️⃣ 数据操作 (0 → 5 个) +5

**需要添加** (5 个):
- [ ] 获取表单数据 (Get Form Data)
- [ ] 获取表格数据 (Get Table Data)
- [ ] 获取列表数据 (Get List Data)
- [ ] 导出数据为 JSON (Export as JSON)
- [ ] 导出数据为 CSV (Export as CSV)

---

## 📈 操作统计

| 类别 | 当前 | 目标 | 增加 |
|------|------|------|------|
| 基础操作 | 4 | 10 | +6 |
| 表单操作 | 30 | 30 | - |
| 键盘操作 | 8 | 8 | - |
| 鼠标操作 | 6 | 6 | - |
| 文本操作 | 7 | 7 | - |
| 弹窗处理 | 6 | 6 | - |
| iframe处理 | 4 | 4 | - |
| 图片操作 | 4 | 4 | - |
| 等待操作 | 5 | 5 | - |
| 高级操作 | 6 | 14 | +8 |
| 属性操作 | 0 | 6 | +6 |
| 导航操作 | 0 | 4 | +4 |
| 窗口操作 | 0 | 4 | +4 |
| 数据操作 | 0 | 5 | +5 |
| **总计** | **79** | **108** | **+29** |

---

## 🎯 实现步骤

### 第 1 步: 扩展基础操作 (+6)

**添加到 test_page.html**:
```html
<!-- 长按操作 -->
<button onclick="testLongPress()">长按测试</button>

<!-- 拖拽操作 -->
<button onclick="testDragDrop()">拖拽测试</button>

<!-- 滚动操作 -->
<button onclick="testScroll()">滚动测试</button>

<!-- 焦点管理 -->
<button onclick="testFocus()">焦点测试</button>

<!-- 可见性检查 -->
<button onclick="testVisibility()">可见性检查</button>

<!-- 启用状态检查 -->
<button onclick="testEnabled()">启用状态检查</button>
```

### 第 2 步: 扩展高级操作 (+8)

**添加到 test_page.html**:
```html
<!-- 元素滚动到视图 -->
<button onclick="testScrollIntoView()">滚动到视图</button>

<!-- 获取页面源码 -->
<button onclick="testGetPageSource()">获取页面源码</button>

<!-- 获取页面尺寸 -->
<button onclick="testGetPageDimensions()">获取页面尺寸</button>

<!-- 获取滚动位置 -->
<button onclick="testGetScrollPosition()">获取滚动位置</button>

<!-- 设置滚动位置 -->
<button onclick="testSetScrollPosition()">设置滚动位置</button>

<!-- 获取视口大小 -->
<button onclick="testGetViewportSize()">获取视口大小</button>

<!-- 等待页面加载 -->
<button onclick="testWaitForPageLoad()">等待页面加载</button>
```

### 第 3 步: 添加属性操作标签页 (+6)

**新标签页**: 属性操作
```html
<button class="tab-button" onclick="switchTab('attributes')">属性操作</button>

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

### 第 4 步: 添加导航操作标签页 (+4)

**新标签页**: 导航操作
```html
<button class="tab-button" onclick="switchTab('navigation')">导航操作</button>

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

### 第 5 步: 添加窗口操作标签页 (+4)

**新标签页**: 窗口操作
```html
<button class="tab-button" onclick="switchTab('window')">窗口操作</button>

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

### 第 6 步: 添加数据操作标签页 (+5)

**新标签页**: 数据操作
```html
<button class="tab-button" onclick="switchTab('data')">数据操作</button>

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

## 📝 JavaScript 函数实现

### 基础操作扩展

```javascript
// 长按操作
function testLongPress() {
    const btn = event.target;
    btn.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
    setTimeout(() => {
        btn.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
        showAlert('success', '✅ 长按操作完成 (1秒)');
    }, 1000);
}

// 拖拽操作
function testDragDrop() {
    const element = document.getElementById('mouseTestArea');
    const dragStartEvent = new DragEvent('dragstart', { bubbles: true });
    const dragEndEvent = new DragEvent('dragend', { bubbles: true });
    element.dispatchEvent(dragStartEvent);
    element.dispatchEvent(dragEndEvent);
    showAlert('success', '✅ 拖拽操作完成');
}

// 滚动操作
function testScroll() {
    window.scrollBy(0, 300);
    showAlert('success', '✅ 页面已滚动 300px');
}

// 焦点管理
function testFocus() {
    const input = document.getElementById('textInput');
    input.focus();
    showAlert('success', '✅ 焦点已设置到输入框');
}

// 可见性检查
function testVisibility() {
    const element = document.getElementById('testForm');
    const isVisible = element.offsetParent !== null;
    showAlert('success', '✅ 元素可见性: ' + (isVisible ? '可见' : '隐藏'));
}

// 启用状态检查
function testEnabled() {
    const input = document.getElementById('textInput');
    const isEnabled = !input.disabled;
    showAlert('success', '✅ 元素启用状态: ' + (isEnabled ? '启用' : '禁用'));
}
```

### 高级操作扩展

```javascript
// 滚动到视图
function testScrollIntoView() {
    const element = document.getElementById('testForm');
    element.scrollIntoView({ behavior: 'smooth' });
    showAlert('success', '✅ 元素已滚动到视图');
}

// 获取页面源码
function testGetPageSource() {
    const source = document.documentElement.outerHTML.substring(0, 200) + '...';
    showResult('advancedResult', '页面源码 (前 200 字符):\n' + source);
    showAlert('success', '✅ 页面源码已获取');
}

// 获取页面尺寸
function testGetPageDimensions() {
    const info = {
        '页面宽度': document.documentElement.scrollWidth,
        '页面高度': document.documentElement.scrollHeight,
        '视口宽度': window.innerWidth,
        '视口高度': window.innerHeight
    };
    showResult('advancedResult', JSON.stringify(info, null, 2));
    showAlert('success', '✅ 页面尺寸已获取');
}

// 获取滚动位置
function testGetScrollPosition() {
    const info = {
        '水平滚动': window.scrollX,
        '垂直滚动': window.scrollY
    };
    showResult('advancedResult', JSON.stringify(info, null, 2));
    showAlert('success', '✅ 滚动位置已获取');
}

// 设置滚动位置
function testSetScrollPosition() {
    window.scrollTo(0, 100);
    showAlert('success', '✅ 滚动位置已设置为 (0, 100)');
}

// 获取视口大小
function testGetViewportSize() {
    const info = {
        '视口宽度': window.innerWidth,
        '视口高度': window.innerHeight,
        '屏幕宽度': window.screen.width,
        '屏幕高度': window.screen.height
    };
    showResult('advancedResult', JSON.stringify(info, null, 2));
    showAlert('success', '✅ 视口大小已获取');
}

// 等待页面加载
function testWaitForPageLoad() {
    if (document.readyState === 'complete') {
        showAlert('success', '✅ 页面已加载完成');
    } else {
        window.addEventListener('load', () => {
            showAlert('success', '✅ 页面加载完成');
        });
    }
}
```

### 属性操作

```javascript
// 获取属性
function testGetAttribute() {
    const element = document.getElementById('attrElement');
    const attr = element.getAttribute('data-test');
    showResult('attributeResult', '获取的属性值: ' + attr);
    showAlert('success', '✅ 属性已获取: ' + attr);
}

// 设置属性
function testSetAttribute() {
    const element = document.getElementById('attrElement');
    element.setAttribute('data-custom', 'custom-value');
    showAlert('success', '✅ 属性已设置: data-custom=custom-value');
}

// 移除属性
function testRemoveAttribute() {
    const element = document.getElementById('attrElement');
    element.removeAttribute('data-id');
    showAlert('success', '✅ 属性已移除: data-id');
}

// 获取样式
function testGetStyle() {
    const element = document.getElementById('attrElement');
    const style = window.getComputedStyle(element);
    const info = {
        '颜色': style.color,
        '背景': style.backgroundColor,
        '字体大小': style.fontSize,
        '宽度': style.width
    };
    showResult('attributeResult', JSON.stringify(info, null, 2));
    showAlert('success', '✅ 样式已获取');
}

// 设置样式
function testSetStyle() {
    const element = document.getElementById('attrElement');
    element.style.backgroundColor = '#ffcccc';
    element.style.color = '#cc0000';
    showAlert('success', '✅ 样式已设置');
}

// 获取类名
function testGetClass() {
    const element = document.getElementById('attrElement');
    const className = element.className;
    showResult('attributeResult', '类名: ' + (className || '(无)'));
    showAlert('success', '✅ 类名已获取');
}
```

### 导航操作

```javascript
// 打开 URL
function testOpenURL() {
    const url = document.getElementById('urlInput').value;
    showAlert('info', 'ℹ️ 将打开: ' + url);
    // window.open(url); // 实际使用时取消注释
}

// 刷新页面
function testRefreshPage() {
    showAlert('info', 'ℹ️ 页面将刷新');
    // location.reload(); // 实际使用时取消注释
}

// 后退
function testGoBack() {
    showAlert('info', 'ℹ️ 页面将后退');
    // history.back(); // 实际使用时取消注释
}

// 前进
function testGoForward() {
    showAlert('info', 'ℹ️ 页面将前进');
    // history.forward(); // 实际使用时取消注释
}
```

### 窗口操作

```javascript
// 最大化窗口
function testMaximizeWindow() {
    showAlert('info', 'ℹ️ 窗口最大化 (仅在桌面应用中有效)');
}

// 最小化窗口
function testMinimizeWindow() {
    showAlert('info', 'ℹ️ 窗口最小化 (仅在桌面应用中有效)');
}

// 调整窗口大小
function testResizeWindow() {
    const width = document.getElementById('windowWidth').value;
    const height = document.getElementById('windowHeight').value;
    showAlert('info', `ℹ️ 窗口将调整为 ${width}x${height} (仅在桌面应用中有效)`);
}

// 全屏
function testToggleFullscreen() {
    if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen();
        showAlert('success', '✅ 已进入全屏模式');
    } else {
        document.exitFullscreen();
        showAlert('success', '✅ 已退出全屏模式');
    }
}
```

### 数据操作

```javascript
// 获取表单数据
function testGetFormData() {
    const formData = new FormData(document.getElementById('testForm'));
    const data = Object.fromEntries(formData);
    showResult('dataResult', JSON.stringify(data, null, 2));
    showAlert('success', '✅ 表单数据已获取');
}

// 获取表格数据
function testGetTableData() {
    const table = document.getElementById('testTable');
    const data = [];
    const rows = table.querySelectorAll('tr');
    rows.forEach((row, index) => {
        if (index === 0) return; // 跳过表头
        const cells = row.querySelectorAll('td');
        data.push({
            '姓名': cells[0].textContent,
            '年龄': cells[1].textContent,
            '城市': cells[2].textContent
        });
    });
    showResult('dataResult', JSON.stringify(data, null, 2));
    showAlert('success', '✅ 表格数据已获取');
}

// 获取列表数据
function testGetListData() {
    const lists = document.querySelectorAll('ul, ol');
    const data = [];
    lists.forEach(list => {
        const items = list.querySelectorAll('li');
        items.forEach(item => {
            data.push(item.textContent);
        });
    });
    showResult('dataResult', JSON.stringify(data, null, 2));
    showAlert('success', '✅ 列表数据已获取');
}

// 导出 JSON
function testExportJSON() {
    const formData = new FormData(document.getElementById('testForm'));
    const data = Object.fromEntries(formData);
    const json = JSON.stringify(data, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'data.json';
    a.click();
    showAlert('success', '✅ 数据已导出为 JSON');
}

// 导出 CSV
function testExportCSV() {
    const table = document.getElementById('testTable');
    let csv = '';
    const rows = table.querySelectorAll('tr');
    rows.forEach(row => {
        const cells = row.querySelectorAll('th, td');
        const rowData = Array.from(cells).map(cell => cell.textContent).join(',');
        csv += rowData + '\n';
    });
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'data.csv';
    a.click();
    showAlert('success', '✅ 数据已导出为 CSV');
}
```

---

## 📊 新增测试数

| 类别 | 新增测试 |
|------|---------|
| 基础操作 | +6 |
| 高级操作 | +8 |
| 属性操作 | +6 |
| 导航操作 | +4 |
| 窗口操作 | +4 |
| 数据操作 | +5 |
| **总计** | **+33** |

**新总测试数**: 92 + 33 = **125 个测试**

---

## ✅ 实现清单

- [ ] 扩展基础操作 (+6)
- [ ] 扩展高级操作 (+8)
- [ ] 添加属性操作标签页 (+6)
- [ ] 添加导航操作标签页 (+4)
- [ ] 添加窗口操作标签页 (+4)
- [ ] 添加数据操作标签页 (+5)
- [ ] 更新自测脚本 (125 个测试)
- [ ] 验证所有操作

---

**版本**: 5.0.0 (规划中)  
**目标完成日期**: 2026-05-07  
**状态**: 规划中

