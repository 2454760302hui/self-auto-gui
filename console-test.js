// 简单的浏览器控制台测试脚本
// 打开 http://localhost:3000/chat 后，在浏览器控制台粘贴此脚本运行

console.log('========================================');
console.log('AutoGLM Pro 功能测试');
console.log('========================================\n');

// 测试 1: 检查 DOM 元素
function testDOMElements() {
  console.log('测试 1: DOM 元素检查');
  console.log('----------------------------------------');
  
  const tests = [
    { name: '顶部导航栏', selector: 'header' },
    { name: 'Logo', selector: '.autoglm-gradient-text' },
    { name: '设备列表', selector: '.w-64.border-r' },
    { name: '设备信息栏', selector: '.px-6.py-4.border-b' },
    { name: '模式切换按钮', selector: '.flex.bg-secondary\\/50' },
  ];
  
  tests.forEach(test => {
    const element = document.querySelector(test.selector);
    const status = element ? '✅' : '❌';
    console.log(`${status} ${test.name}: ${element ? '存在' : '未找到'}`);
  });
  
  console.log('');
}

// 测试 2: API 连接测试
async function testAPI() {
  console.log('测试 2: API 连接测试');
  console.log('----------------------------------------');
  
  try {
    const response = await fetch('/api/devices');
    const data = await response.json();
    
    console.log(`✅ API 连接成功`);
    console.log(`   设备数量: ${data.devices?.length || 0}`);
    
    if (data.devices && data.devices.length > 0) {
      console.log(`   设备列表:`);
      data.devices.forEach((device: any) => {
        if (device.state !== 'disconnected') {
          console.log(`     - ${device.display_name || device.model} (${device.serial})`);
        }
      });
    }
  } catch (error) {
    console.log(`❌ API 连接失败: ${error}`);
  }
  
  console.log('');
}

// 测试 3: 配置获取
async function testConfig() {
  console.log('测试 3: 配置获取测试');
  console.log('----------------------------------------');
  
  try {
    const response = await fetch('/api/config');
    const config = await response.json();
    
    console.log(`✅ 配置获取成功`);
    console.log(`   Base URL: ${config.base_url || '未配置'}`);
    console.log(`   Model: ${config.model_name || '未配置'}`);
    console.log(`   视觉模式: ${config.supports_vision ? '启用' : '禁用'}`);
  } catch (error) {
    console.log(`❌ 配置获取失败: ${error}`);
  }
  
  console.log('');
}

// 测试 4: UI 交互测试
function testUIInteractions() {
  console.log('测试 4: UI 交互测试');
  console.log('----------------------------------------');
  
  // 测试设备选择
  const deviceButtons = document.querySelectorAll('button[class*="rounded-lg"]');
  console.log(`✅ 找到 ${deviceButtons.length} 个可点击元素`);
  
  // 测试模式切换按钮
  const modeButtons = document.querySelectorAll('button[class*="rounded-md"]');
  console.log(`✅ 找到 ${modeButtons.length} 个模式切换按钮`);
  
  // 测试设置按钮
  const settingsButton = document.querySelector('button[class*="gap-2"]');
  if (settingsButton && settingsButton.textContent?.includes('设置')) {
    console.log(`✅ 设置按钮存在`);
  }
  
  console.log('');
}

// 运行所有测试
async function runTests() {
  testDOMElements();
  await testAPI();
  await testConfig();
  testUIInteractions();
  
  console.log('========================================');
  console.log('测试完成！');
  console.log('========================================');
}

// 运行测试
runTests();
