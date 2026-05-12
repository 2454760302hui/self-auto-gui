# Mobile — 移动端自动化测试框架

> 支持 Android / iOS / HarmonyOS，不依赖 Appium，使用原生驱动直连，比 Appium 轻量 10 倍。
> 复用 dsl 的 YAML DSL 设计，用 yml 文件描述测试用例，零 Python 代码。

## 技术选型

| 平台 | 驱动方案 | 说明 |
|------|---------|------|
| Android | uiautomator2 (u2) | Google 官方 UIAutomator2，ADB 直驱，无需 Appium Server |
| iOS | facebook-wda (wda) | Facebook WebDriverAgent，直连 WDA，无需 Appium |
| HarmonyOS | HDC + hmdriver2 | 华为 HDC 工具链，原生驱动 |

## 项目结构

```
mobile/
  run.py                    CLI 入口
  conftest.py               pytest fixture
  config/                   YAML 用例目录
    test_android_login.yml
    test_ios_login.yml
    test_harmony_login.yml
  core/
    errors.py                错误体系 (MobileError/ConfigError/LocatorError/...)
    config.py                配置加载与验证 (ConfigLoader/ConfigValidator)
    variable.py              变量解析 (VariableResolver: ${var}, @{data})
    locator.py               智能定位器 (SmartLocator + 11种策略)
    runner.py                Runner 主执行器 (基于 OperationRegistry 分发)
  drivers/
    base.py                  PlatformDriver 抽象基类
    android.py               AndroidDriver (uiautomator2)
    ios.py                   IOSDriver (facebook-wda)
    harmony.py               HarmonyDriver (hmdriver2 + HDC)
  operations/
    registry.py              OperationRegistry + @operation 装饰器
    base.py                  OperationBase + OperationResult
    app.py                   启动应用/关闭应用/安装/卸载
    tap.py                   点击/长按/双击
    input.py                 输入/按键/清空
    swipe.py                 滑动/滚动/捏合/放大
    assert_op.py             断言 (visible/text/attribute/exists)
    wait.py                  等待/等待元素
    screenshot.py            截图
    device.py                设备信息/旋转/硬件按键
    file.py                  拉取/推送文件
  testcases/
    test_mobile.py           pytest 参数化桥接
```

## 快速开始

```bash
pip install -r requirements.txt

# 列出所有流程
python run.py --list

# 验证配置文件
python run.py --validate

# 列出所有已注册操作
python run.py --operations

# 执行指定流程
python run.py test_login

# 执行所有流程
python run.py --all

# 指定平台和设备
python run.py --platform ios --device localhost:8100 test_login

# pytest 方式执行
pytest testcases/test_mobile.py -v

# 指定配置文件
MOBILE_CONFIG=config/test_ios_login.yml pytest testcases/test_mobile.py -v
```

## YAML 用例示例

```yaml
# config/test_android_login.yml
config:
  name: 登录测试
  platform: android
  device: 127.0.0.1:5555   # ADB 设备地址
  app: com.example.app      # 包名（可选，不填则操作当前前台应用）

locators:
  用户名输入框:
    primary: "rid=com.example:id/et_username"
    fallback:
      - "text=用户名"
      - "className=android.widget.EditText"
  密码输入框:
    primary: "rid=com.example:id/et_password"
  登录按钮:
    primary: "rid=com.example:id/btn_login"
    fallback:
      - "text=登录"

aliases:
  用户名: 用户名输入框

test_login:
  - name: 启动应用
    launch_app:
      package: com.example.app
      activity: .MainActivity

  - name: 输入用户名
    input:
      element: 用户名输入框
      value: test@example.com

  - name: 输入密码
    input:
      element: 密码输入框
      value: password123

  - name: 点击登录
    tap:
      element: 登录按钮

  - name: 验证登录成功
    assert:
      element: 首页标题
      visible: true

  - name: 关闭应用
    close_app:
      package: com.example.app
```

## 定位器格式

| 前缀 | 说明 | 示例 |
|------|------|------|
| `rid=` | Android resource-id | `rid=com.example:id/btn` |
| `aid=` | Accessibility ID | `aid=login_button` |
| `text=` | 精确文本 | `text=登录` |
| `textContains=` | 包含文本 | `textContains=录` |
| `desc=` | Description | `desc=提交按钮` |
| `className=` | 类名 | `className=android.widget.Button` |
| `xpath=` | XPath | `xpath=//Button[@text='登录']` |
| `predicate=` | iOS NSPredicate | `predicate=name == 'login'` |
| `classChain=` | iOS class chain | `classChain=**/Button` |
| `coord=` | 坐标 | `coord=100,200` |
| `image=` | 图像匹配 (OpenCV) | `image=template.png` |

## 支持的操作 (47个)

| 类别 | 操作 |
|------|------|
| 应用 | 启动应用/launch_app, 关闭应用/close_app, 安装应用/install_app, 卸载应用/uninstall_app |
| 点击 | 点击/tap, 长按/long_press, 双击/double_tap |
| 输入 | 输入/input, 按键/press_key, 清空/clear |
| 滑动 | 滑动/swipe, 滚动/scroll, 捏合/pinch, 放大/zoom |
| 断言 | 断言/assert/验证 (支持 visible/text/attribute/exists) |
| 等待 | 等待/wait, 等待元素/wait_for |
| 截图 | 截图/screenshot |
| 设备 | 获取设备信息/get_device_info, 旋转设备/rotate_device, 硬件按键/hardware_key |
| 文件 | 拉取文件/pull_file, 推送文件/push_file |

## 变量系统

- `${变量名}` — 运行时变量引用
- `@{数据名}` — 测试数据引用（列表类型随机选取）
- `${date}` — 当前日期 (YYYY-MM-DD)
- `${datetime}` — 当前日期时间
- `${timestamp}` — 当前时间戳
- `${random}` — 4位随机数
