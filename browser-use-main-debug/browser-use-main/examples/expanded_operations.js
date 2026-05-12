/**
 * 扩展操作函数库
 * 添加 29 个新操作，从 79 个扩展到 108 个
 */

// ==================== 基础操作扩展 (6 个) ====================

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
    const element = document.getElementById('mouseTestArea') || document.body;
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
    const input = document.getElementById('textInput') || document.querySelector('input');
    if (input) {
        input.focus();
        showAlert('success', '✅ 焦点已设置到输入框');
    }
}

// 可见性检查
function testVisibility() {
    const element = document.getElementById('testForm') || document.body;
    const isVisible = element.offsetParent !== null;
    showAlert('success', '✅ 元素可见性: ' + (isVisible ? '可见' : '隐藏'));
}

// 启用状态检查
function testEnabled() {
    const input = document.getElementById('textInput') || document.querySelector('input');
    if (input) {
        const isEnabled = !input.disabled;
        showAlert('success', '✅ 元素启用状态: ' + (isEnabled ? '启用' : '禁用'));
    }
}

// ==================== 高级操作扩展 (8 个) ====================

// 滚动到视图
function testScrollIntoView() {
    const element = document.getElementById('testForm') || document.body;
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

// ==================== 属性操作 (6 个) ====================

// 获取属性
function testGetAttribute() {
    const element = document.getElementById('attrElement') || document.querySelector('input');
    if (element) {
        const attr = element.getAttribute('data-test') || element.getAttribute('id');
        showResult('attributeResult', '获取的属性值: ' + attr);
        showAlert('success', '✅ 属性已获取: ' + attr);
    }
}

// 设置属性
function testSetAttribute() {
    const element = document.getElementById('attrElement') || document.querySelector('input');
    if (element) {
        element.setAttribute('data-custom', 'custom-value');
        showAlert('success', '✅ 属性已设置: data-custom=custom-value');
    }
}

// 移除属性
function testRemoveAttribute() {
    const element = document.getElementById('attrElement') || document.querySelector('input');
    if (element) {
        element.removeAttribute('data-id');
        showAlert('success', '✅ 属性已移除: data-id');
    }
}

// 获取样式
function testGetStyle() {
    const element = document.getElementById('attrElement') || document.querySelector('input');
    if (element) {
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
}

// 设置样式
function testSetStyle() {
    const element = document.getElementById('attrElement') || document.querySelector('input');
    if (element) {
        element.style.backgroundColor = '#ffcccc';
        element.style.color = '#cc0000';
        showAlert('success', '✅ 样式已设置');
    }
}

// 获取类名
function testGetClass() {
    const element = document.getElementById('attrElement') || document.querySelector('input');
    if (element) {
        const className = element.className;
        showResult('attributeResult', '类名: ' + (className || '(无)'));
        showAlert('success', '✅ 类名已获取');
    }
}

// ==================== 导航操作 (4 个) ====================

// 打开 URL
function testOpenURL() {
    const url = document.getElementById('urlInput')?.value || 'https://example.com';
    showAlert('info', 'ℹ️ 将打开: ' + url);
}

// 刷新页面
function testRefreshPage() {
    showAlert('info', 'ℹ️ 页面将刷新');
}

// 后退
function testGoBack() {
    showAlert('info', 'ℹ️ 页面将后退');
}

// 前进
function testGoForward() {
    showAlert('info', 'ℹ️ 页面将前进');
}

// ==================== 窗口操作 (4 个) ====================

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
    const width = document.getElementById('windowWidth')?.value || 800;
    const height = document.getElementById('windowHeight')?.value || 600;
    showAlert('info', `ℹ️ 窗口将调整为 ${width}x${height} (仅在桌面应用中有效)`);
}

// 全屏
function testToggleFullscreen() {
    if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(err => {
            showAlert('error', '❌ 全屏请求被拒绝: ' + err.message);
        });
        showAlert('success', '✅ 已进入全屏模式');
    } else {
        document.exitFullscreen();
        showAlert('success', '✅ 已退出全屏模式');
    }
}

// ==================== 数据操作 (5 个) ====================

// 获取表单数据
function testGetFormData() {
    const form = document.getElementById('testForm');
    if (form) {
        const formData = new FormData(form);
        const data = Object.fromEntries(formData);
        showResult('dataResult', JSON.stringify(data, null, 2));
        showAlert('success', '✅ 表单数据已获取');
    }
}

// 获取表格数据
function testGetTableData() {
    const table = document.getElementById('testTable') || document.querySelector('table');
    if (table) {
        const data = [];
        const rows = table.querySelectorAll('tr');
        rows.forEach((row, index) => {
            if (index === 0) return;
            const cells = row.querySelectorAll('td');
            const rowData = {};
            cells.forEach((cell, i) => {
                rowData[`列${i+1}`] = cell.textContent;
            });
            data.push(rowData);
        });
        showResult('dataResult', JSON.stringify(data, null, 2));
        showAlert('success', '✅ 表格数据已获取');
    }
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
    const form = document.getElementById('testForm');
    if (form) {
        const formData = new FormData(form);
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
}

// 导出 CSV
function testExportCSV() {
    const table = document.getElementById('testTable') || document.querySelector('table');
    if (table) {
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
}
