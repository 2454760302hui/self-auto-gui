// 自动化测试脚本 - 用于验证所有功能

interface TestResult {
  name: string;
  passed: boolean;
  error?: string;
  details?: string;
}

const testResults: TestResult[] = [];

// 测试 1: API 连接测试
async function testAPIConnection(): Promise<TestResult> {
  try {
    const response = await fetch('/api/devices');
    if (response.ok) {
      const data = await response.json();
      return {
        name: 'API 连接测试',
        passed: true,
        details: `成功获取 ${data.devices?.length || 0} 个设备`
      };
    } else {
      return {
        name: 'API 连接测试',
        passed: false,
        error: `HTTP ${response.status}: ${response.statusText}`
      };
    }
  } catch (error) {
    return {
      name: 'API 连接测试',
      passed: false,
      error: String(error)
    };
  }
}

// 测试 2: 设备列表获取
async function testDeviceList(): Promise<TestResult> {
  try {
    const response = await fetch('/api/devices');
    const data = await response.json();
    
    if (data.devices && Array.isArray(data.devices)) {
      const connectedDevices = data.devices.filter((d: any) => d.state !== 'disconnected');
      return {
        name: '设备列表获取',
        passed: true,
        details: `找到 ${connectedDevices.length} 个已连接设备`
      };
    } else {
      return {
        name: '设备列表获取',
        passed: false,
        error: '设备列表格式错误'
      };
    }
  } catch (error) {
    return {
      name: '设备列表获取',
      passed: false,
      error: String(error)
    };
  }
}

// 测试 3: 配置获取
async function testConfigFetch(): Promise<TestResult> {
  try {
    const response = await fetch('/api/config');
    if (response.ok) {
      const config = await response.json();
      return {
        name: '配置获取测试',
        passed: true,
        details: `Base URL: ${config.base_url || '未配置'}, Model: ${config.model_name || '未配置'}`
      };
    } else {
      return {
        name: '配置获取测试',
        passed: false,
        error: `HTTP ${response.status}`
      };
    }
  } catch (error) {
    return {
      name: '配置获取测试',
      passed: false,
      error: String(error)
    };
  }
}

// 测试 4: Socket.IO 连接
async function testSocketConnection(): Promise<TestResult> {
  return new Promise((resolve) => {
    try {
      const socket = new WebSocket('ws://localhost:8007/socket.io/?EIO=4&transport=websocket');
      
      const timeout = setTimeout(() => {
        socket.close();
        resolve({
          name: 'Socket.IO 连接测试',
          passed: false,
          error: '连接超时'
        });
      }, 3000);
      
      socket.onopen = () => {
        clearTimeout(timeout);
        socket.close();
        resolve({
          name: 'Socket.IO 连接测试',
          passed: true,
          details: 'WebSocket 连接成功'
        });
      };
      
      socket.onerror = () => {
        clearTimeout(timeout);
        resolve({
          name: 'Socket.IO 连接测试',
          passed: false,
          error: 'WebSocket 连接失败'
        });
      };
    } catch (error) {
      resolve({
        name: 'Socket.IO 连接测试',
        passed: false,
        error: String(error)
      });
    }
  });
}

// 运行所有测试
async function runAllTests(): Promise<void> {
  console.log('========================================');
  console.log('AutoGLM Pro 自动化测试');
  console.log('========================================\n');
  
  testResults.push(await testAPIConnection());
  testResults.push(await testDeviceList());
  testResults.push(await testConfigFetch());
  testResults.push(await testSocketConnection());
  
  console.log('\n测试结果汇总:');
  console.log('----------------------------------------');
  
  let passed = 0;
  let failed = 0;
  
  testResults.forEach((result, index) => {
    const status = result.passed ? '✅ PASS' : '❌ FAIL';
    console.log(`\n${index + 1}. ${result.name}: ${status}`);
    
    if (result.details) {
      console.log(`   详情: ${result.details}`);
    }
    
    if (result.error) {
      console.log(`   错误: ${result.error}`);
    }
    
    if (result.passed) {
      passed++;
    } else {
      failed++;
    }
  });
  
  console.log('\n----------------------------------------');
  console.log(`总计: ${testResults.length} 个测试`);
  console.log(`通过: ${passed} 个`);
  console.log(`失败: ${failed} 个`);
  console.log('========================================\n');
  
  // 将结果保存到 window 对象以便在控制台查看
  (window as any).testResults = testResults;
}

// 导出测试函数
(window as any).runTests = runAllTests;

// 自动运行测试（延迟 2 秒等待页面加载）
setTimeout(() => {
  runAllTests();
}, 2000);

console.log('测试脚本已加载。输入 runTests() 手动运行测试。');
