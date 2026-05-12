"""
browser-use Web UI 服务
端口: 9242
启动: python run.py
"""
import asyncio
import json
import logging
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from threading import Timer

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("run")

# 禁用系统代理（避免 VPN/代理干扰 LLM 调用）
for _k in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ.pop(_k, None)

BASE_DIR = Path(__file__).parent
TRACES_DIR = BASE_DIR / "traces"
TRACES_DIR.mkdir(exist_ok=True)

def _find_free_port(preferred: int = 9242) -> int:
    import socket
    for port in [preferred, 9243, 9244, 9245, 7860, 7861, 5001, 5002]:
        try:
            # 绑定 0.0.0.0 才能检测到所有网卡上的占用情况
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
            s.bind(('0.0.0.0', port))
            s.close()
            return port
        except OSError:
            continue
    raise RuntimeError("找不到可用端口")

PORT = _find_free_port(9242)
CDP_URL = os.getenv("CHROME_CDP_URL", "http://127.0.0.1:9222")

app = FastAPI(title="Browser-Use Web UI")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

# ─── LLM 配置加载 ────────────────────────────────────────────────────────────

def _get_llm_config() -> dict:
    from browser_use.config import CONFIG
    try:
        cfg = CONFIG.load_config()
        return cfg.get("llm", {})
    except Exception:
        return {}

def _build_llm():
    """根据 .env 配置构建 LLM 实例（禁用系统代理避免 VPN/代理干扰）"""
    from browser_use.llm.factory import create_llm_from_config
    import httpx

    cfg = _get_llm_config()
    if not cfg:
        raise RuntimeError("未找到 LLM 配置，请检查 .env 文件")

    # 创建无代理的 httpx 客户端，增加超时时间
    timeout = httpx.Timeout(connect=30.0, read=300.0, write=30.0, pool=60.0)
    http_client = httpx.AsyncClient(trust_env=False, timeout=timeout)

    # 传递无代理客户端给 LLM
    return create_llm_from_config(cfg, http_client=http_client)


# ─── GIF 生成 ──────────────────────────────────────────────────────────────

def _make_gif_from_screenshots(trace_dir: Path, fps: int = 2) -> str | None:
    """
    将 trace_dir 下的 screenshot_*.png 合并为一个 animated GIF。
    trace_dir 可以是绝对路径或相对路径（相对于 BASE_DIR）。
    """
    try:
        from PIL import Image
    except ImportError:
        logger.warning("Pillow not installed, skipping GIF generation")
        return None

    # 确保是绝对路径（subprocess 可能在 BASE_DIR 外执行）
    if not trace_dir.is_absolute():
        trace_dir = BASE_DIR / trace_dir

    if not trace_dir.exists():
        logger.warning(f"trace_dir 不存在: {trace_dir}")
        return None

    try:
        pngs = sorted(trace_dir.glob("screenshot_*.png"), key=lambda p: p.name)
        logger.info(f"找到 {len(pngs)} 张截图 in {trace_dir}")
        if len(pngs) < 2:
            logger.info(f"截图不足2张，跳过 GIF: {trace_dir.name} (仅有 {len(pngs)} 张)")
            return None

        frames = []
        for p in pngs:
            try:
                img = Image.open(p).convert("RGBA")
                frames.append(img)
            except Exception as img_err:
                logger.warning(f"加载截图失败 {p}: {img_err}")
                continue

        if len(frames) < 2:
            logger.warning("有效帧不足2张，跳过 GIF")
            return None

        gif_path = trace_dir / "recording.gif"
        frames[0].save(
            gif_path,
            save_all=True,
            append_images=frames[1:],
            duration=max(200, 1000 // fps),
            loop=0,
        )
        logger.info(f"GIF 生成成功: {gif_path} ({len(frames)} 帧)")
        return str(gif_path)
    except Exception as e:
        logger.warning(f"GIF 生成失败: {e}")
        import traceback
        traceback.print_exc()
        return None


# ─── DSL 解析器 ──────────────────────────────────────────────────────────────

DSL_DEMOS = {
    # ══════════════════════════════════════════════════════════════
    # 全覆盖综合演示 - 覆盖所有 30+ DSL 操作
    # ══════════════════════════════════════════════════════════════
    "【全操作】完整覆盖": """# 全操作演示：覆盖所有 DSL 指令
# ── 1. 导航 ──
打开 https://cn.bing.com
等待加载完成
获取标题
获取URL
截图

# ── 2. 输入 & 键盘 ──
输入 #sb_form_q Python教程
按键 Enter
等待加载完成
截图

# ── 3. 元素交互：点击/悬停 ──
悬停 h2
截图
按键 End
等待 500

# ── 4. 表单：勾选/选择 ──
打开 https://httpbin.org/forms/post
等待加载完成
输入 [name=custname] 张三
输入 [name=custtel] 13800138000
输入 [name=custemail] test@example.com
选择 [name=size] large
勾选 [value=bacon]
勾选 [value=cheese]
截图

# ── 5. 滚动操作 ──
滚动 上
等待 500
滚动 底部
等待 500
截图
滚动 顶部
等待 300

# ── 6. 断言验证 ──
断言可见 [name=custname]
断言标题 HTTPBin
获取URL
截图

# ── 7. 获取数据 ──
获取文本 [name=custname]
获取属性 [name=custname] value
截图

# ── 8. JS 执行 ──
执行JS document.title
打印 演示完成
截图""",

    # ══════════════════════════════════════════════════════════════
    # 导航 & 多标签页
    # ══════════════════════════════════════════════════════════════
    "【导航】多标签页操作": """# 多标签页演示
打开 https://cn.bing.com
等待加载完成
获取标题
截图
新标签页
打开 https://github.com
等待加载完成
获取标题
截图
新标签页
打开 https://httpbin.org/html
等待加载完成
获取标题
截图
关闭标签页
获取标题
截图""",

    "【导航】浏览器控制": """# 浏览器导航控制
打开 https://cn.bing.com
等待加载完成
获取标题
截图
打开 https://github.com
等待加载完成
获取标题
截图
返回
等待加载完成
获取标题
截图
前进
等待加载完成
获取标题
截图
刷新
等待加载完成
截图
获取URL""",

    # ══════════════════════════════════════════════════════════════
    # 点击 & 悬停系列
    # ══════════════════════════════════════════════════════════════
    "【点击】单击双击右键悬停": """# 多种点击方式
打开 https://the-internet.herokuapp.com/clickable
等待加载完成
截图
点击 文本=Click Button
等待 1
截图
双击 文本=Click Button
等待 1
截图
右键 文本=Context Menu
等待 1
截图
悬停 文本=Click Button
等待 1
截图
打印 点击操作演示完成""",

    # ══════════════════════════════════════════════════════════════
    # 表单 & 输入系列
    # ══════════════════════════════════════════════════════════════
    "【表单】输入框完整流程": """# 表单输入完整流程
打开 https://httpbin.org/forms/post
等待加载完成
输入 [name=custname] 李四
输入 [name=custtel] 13900001111
输入 [name=custemail] li@example.com
输入 [name=comments] 这是一条测试留言
截图
清空 [name=custname]
输入 [name=custname] 王五
截图
获取文本 [name=custname]
打印 表单填写完成""",

    "【表单】下拉框单选多选": """# 下拉框、单选、复选框完整演示
打开 https://httpbin.org/forms/post
等待加载完成
截图
# ── 下拉选择 ──
选择 [name=size] medium
截图
选择 [name=size] large
截图
# ── 单选按钮 ──
单选 [value=bacon]
截图
单选 [value=tortilla]
截图
# ── 多选（复选框）──
多选 [value=cheese]
截图
多选 [value=tortilla]
截图
# ── 取消勾选 ──
取消勾选 [value=tortilla]
截图
# ── 全选 & 取消全选 ──
全选 [name=size]
截图
取消全选 [name=size]
截图
打印 表单选择完成""",

    "【表单】开关与文本操作": """# 开关、选中文字、清空输入
打开 https://httpbin.org/forms/post
等待加载完成
截图
# 勾选复选框
勾选 [value=bacon]
截图
# 开关效果（再次点击即取消）
开关 [value=bacon]
截图
# 输入文字
输入 [name=custname] 李四
截图
# 选中输入框文字
选中文字 [name=custname]
截图
# 清空输入
清空 [name=custname]
截图
# 重新输入
输入 [name=custname] 王五
截图
打印 表单文本操作完成""",

    # ══════════════════════════════════════════════════════════════
    # 键盘操作
    # ══════════════════════════════════════════════════════════════
    "【键盘】输入文字按键": """# 键盘操作
打开 https://cn.bing.com
等待加载完成
截图
点击 #sb_form_q
输入文字 测试内容
截图
按键 Control+a
输入文字 新内容
截图
按键 End
输入文字 -追加
截图
按键 Control+a
按键 Delete
截图
按键 Escape
打印 键盘操作完成""",

    # ══════════════════════════════════════════════════════════════
    # 文件上传
    # ══════════════════════════════════════════════════════════════
    "【上传】文件上传": """# 文件上传演示（使用系统测试页面）
打开 https://the-internet.herokuapp.com/upload
等待加载完成
截图
# 上传本地测试文件（请替换为实际存在的文件路径）
上传 [id=file-upload] C:\\test.txt
截图
点击 文本=Upload
等待 2
截图
打印 文件上传演示完成""",

    # ══════════════════════════════════════════════════════════════
    # 滚动系列
    # ══════════════════════════════════════════════════════════════
    "【滚动】页面滚动截图": """# 页面滚动演示
打开 https://cn.bing.com
等待加载完成
截图
滚动 下
等待 500
截图
滚动 下
等待 500
截图
滚动 底部
等待 500
截图
滚动 顶部
等待 500
截图
打印 滚动演示完成""",

    "【拖拽】元素拖拽交换": """# 拖拽操作演示
打开 https://the-internet.herokuapp.com/drag_and_drop
等待加载完成
截图
拖拽 #column-a 到 #column-b
等待 500
截图
打印 拖拽操作完成""",

    "【滚动】滚动到指定元素": """# 滚动到指定元素
打开 https://the-internet.herokuapp.com/large
等待加载完成
截图
滚动 底部
等待 500
截图
滚动到 h3
等待 500
截图
打印 滚动到元素完成""",

    # ══════════════════════════════════════════════════════════════
    # iframe 操作
    # ══════════════════════════════════════════════════════════════
    "【iframe】嵌入框架操作": """# iframe 操作演示
打开 https://the-internet.herokuapp.com/iframe
等待加载完成
截图
iframe #mce_0_ifr
等待 500
iframe输入 body 这是在iframe中输入的文字
截图
iframe点击 文本=File
等待 500
截图
退出iframe
截图
打印 iframe操作完成""",

    # ══════════════════════════════════════════════════════════════
    # 断言验证系列
    # ══════════════════════════════════════════════════════════════
    "【断言】页面元素验证": """# 断言验证演示
打开 https://cn.bing.com
等待加载完成
断言可见 #sb_form_q
断言可见 #sb_form_go
断言标题 Bing
截图
输入 #sb_form_q Python
按键 Enter
等待加载完成
断言可见 #b_results
断言URL https://www.bing.com
截图
打印 断言验证完成""",

    "【断言】文本内容验证": """# 断言文本内容验证
打开 https://httpbin.org/html
等待加载完成
断言文本 body Herman Melville
截图
获取文本 h1
截图
打印 文本断言完成""",

    # ══════════════════════════════════════════════════════════════
    # 数据获取系列
    # ══════════════════════════════════════════════════════════════
    "【获取】页面数据提取": """# 页面数据提取演示
打开 https://cn.bing.com
等待加载完成
获取标题
获取URL
截图
输入 #sb_form_q 浏览器自动化
按键 Enter
等待加载完成
获取标题
获取URL
截图
打印 数据提取演示完成""",

    "【获取】元素属性文本": """# 元素属性和文本提取
打开 https://the-internet.herokuapp.com
等待加载完成
获取属性 a[href='/login'] href
获取文本 h2
获取标题
截图
打印 属性提取完成""",

    # ══════════════════════════════════════════════════════════════
    # JS 执行 & 打印
    # ══════════════════════════════════════════════════════════════
    "【JS】JavaScript执行": """# JavaScript 执行演示
打开 https://cn.bing.com
等待加载完成
执行JS document.title
执行JS window.innerWidth
执行JS window.innerHeight
执行JS document.getElementById('sb_form_q').placeholder = '已通过JS修改'
截图
打印 JS执行演示完成""",

    "【打印】调试信息输出": """# 打印调试信息
打印 开始演示
打开 https://cn.bing.com
等待加载完成
打印 页面已加载
获取标题
打印 标题获取完成
截图
打印 截图已保存
打印 演示全部完成""",

    # ══════════════════════════════════════════════════════════════
    # 等待策略
    # ══════════════════════════════════════════════════════════════
    "【等待】页面加载策略": """# 等待策略演示
打开 https://cn.bing.com
等待加载完成
截图
等待 1000
截图
等待 2000
截图
等待可见 #sb_form_q
截图
等待加载完成
打印 等待策略演示完成""",

    # ══════════════════════════════════════════════════════════════
    # 弹窗处理
    # ══════════════════════════════════════════════════════════════
    "【弹窗】JavaScript弹窗": """# JS 弹窗处理演示
打开 https://the-internet.herokuapp.com/javascript_alerts
等待加载完成
截图
点击 文本=Click for JS Alert
等待 1
截图
点击 文本=Click for JS Confirm
等待 1
截图
点击 文本=Click for JS Prompt
等待 1
截图
打印 弹窗处理演示完成""",

    # ══════════════════════════════════════════════════════════════
    # 综合实战
    # ══════════════════════════════════════════════════════════════
    "【实战】Bing搜索全流程": """# Bing 搜索完整流程
打开 https://cn.bing.com
等待加载完成
断言可见 #sb_form_q
截图
输入 #sb_form_q 人工智能发展趋势 2025
按键 Enter
等待加载完成
断言可见 #b_results
获取标题
截图
滚动 下
等待 500
截图
滚动 底部
等待 500
截图
打印 Bing搜索全流程完成""",

    "【实战】表单提交全流程": """# 表单填写提交完整流程
打开 https://httpbin.org/forms/post
等待加载完成
断言可见 [name=custname]
截图
输入 [name=custname] 赵六
输入 [name=custtel] 13612345678
输入 [name=custemail] zhao@example.com
输入 [name=comments] 请尽快处理，谢谢
选择 [name=size] small
勾选 [value=bacon]
勾选 [value=cheese]
截图
打印 表单填写完成
# 点击提交按钮
点击 [type=submit]
等待 2
截图
打印 表单提交流程完成""",

    "【实战】登录页面自动化": """# 模拟登录页面自动化
打开 https://the-internet.herokuapp.com/login
等待加载完成
截图
断言可见 [name=username]
输入 [name=username] tomsmith
输入 [name=password] SuperSecretPassword!
截图
点击 [type=submit]
等待加载完成
截图
断言可见 .flash.success
获取文本 .flash.success
截图
打印 登录流程完成""",

    "【实战】多页面数据采集": """# 多页面数据采集流程
打开 https://cn.bing.com
等待加载完成
输入 #sb_form_q Python
按键 Enter
等待加载完成
获取标题
截图
新标签页
打开 https://github.com
等待加载完成
输入 [placeholder=Search GitHub] browser-use
按键 Enter
等待加载完成
截图
关闭标签页
获取标题
截图
打印 多页面数据采集完成""",
}

def dsl_to_playwright_script(dsl: str, task_id: str, cdp_url: str) -> str:
    """将 NLP DSL 指令转换为 Playwright Python 脚本（支持全部指令）"""
    lines = [l.strip() for l in dsl.strip().splitlines() if l.strip() and not l.strip().startswith("#")]
    trace_dir = f"traces/{task_id}"
    screenshot_idx = [0]
    frame_var = ["page"]  # 当前操作对象（page 或 frame）
    body_lines = []       # ← 放在函数作用域内，循环结束后再组装

    def cur():
        return frame_var[0]

    def _sel(selector: str) -> str:
        """生成 locator 代码"""
        if selector.startswith("文本="):
            return f"{cur()}.get_by_text({selector[3:]!r}).first"
        elif selector.startswith("role="):
            import re as _re
            m = _re.match(r'role=(\w+)(?:\[name=(.+?)\])?', selector)
            if m:
                role, name = m.group(1), m.group(2)
                if name:
                    return f'{cur()}.get_by_role({role!r}, name={name!r}).first'
                return f'{cur()}.get_by_role({role!r}).first'
            return f"{cur()}.locator({selector!r}).first"
        elif selector.startswith("placeholder="):
            return f"{cur()}.get_by_placeholder({selector[12:]!r}).first"
        elif selector.startswith("label="):
            return f"{cur()}.get_by_label({selector[6:]!r}).first"
        elif selector.startswith("testid="):
            return f"{cur()}.get_by_test_id({selector[7:]!r}).first"
        elif selector.startswith("xpath="):
            return f"{cur()}.locator({selector!r}).first"
        elif selector.startswith("text="):
            return f"{cur()}.get_by_text({selector[5:]!r}).first"
        else:
            return f"{cur()}.locator({selector!r}).first"

    for line in lines:
        parts = line.split(None, 2)
        cmd = parts[0] if parts else ""

        # ── 导航 ──
        if cmd in ("打开", "open", "goto", "navigate"):
            url = parts[1] if len(parts) > 1 else "about:blank"
            frame_var[0] = "page"
            body_lines.append(f"        await stable_goto(page, {url!r})")

        elif cmd in ("等待加载完成", "waitload"):
            body_lines.append("        await wait_nav(page)")

        elif cmd in ("返回", "back", "goback", "后退"):
            body_lines.append("        await page.go_back()")
            body_lines.append("        await wait_nav(page)")

        elif cmd in ("前进", "forward", "goforward"):
            body_lines.append("        await page.go_forward()")
            body_lines.append("        await wait_nav(page)")

        elif cmd in ("刷新", "reload", "refresh"):
            body_lines.append("        await page.reload()")
            body_lines.append("        await wait_nav(page)")

        elif cmd in ("等待", "wait", "sleep"):
            val = parts[1] if len(parts) > 1 else "1"
            try:
                ms = int(float(val)) if float(val) > 100 else int(float(val) * 1000)
            except Exception:
                ms = 1000
            body_lines.append(f"        await page.wait_for_timeout({ms})")

        elif cmd in ("等待可见", "waitvisible"):
            selector = parts[1] if len(parts) > 1 else "body"
            body_lines.append(f"        await {_sel(selector)}.wait_for(state='visible', timeout=15000)")
            body_lines.append(f"        print('[OK] 等待可见: {selector}')")

        # ── 截图 ──
        elif cmd in ("截图", "screenshot"):
            screenshot_idx[0] += 1
            path = f"{trace_dir}/screenshot_{screenshot_idx[0]}.png"
            body_lines.append(f"        await page.screenshot(path=r{path!r})")
            body_lines.append(f"        print('[screenshot] 截图已保存: {path}')")

        # ── 点击 ──
        elif cmd in ("点击", "click"):
            selector = parts[1] if len(parts) > 1 else ""
            body_lines.append(f"        await {_sel(selector)}.wait_for(state='visible', timeout=15000)")
            body_lines.append(f"        await {_sel(selector)}.click()")

        elif cmd in ("双击", "dblclick"):
            selector = parts[1] if len(parts) > 1 else ""
            body_lines.append(f"        await {_sel(selector)}.wait_for(state='visible', timeout=15000)")
            body_lines.append(f"        await {_sel(selector)}.dbl_click()")

        elif cmd in ("右键", "rightclick"):
            selector = parts[1] if len(parts) > 1 else ""
            body_lines.append(f"        await {_sel(selector)}.wait_for(state='visible', timeout=15000)")
            body_lines.append(f"        await {_sel(selector)}.click(button='right')")

        elif cmd in ("悬停", "hover"):
            selector = parts[1] if len(parts) > 1 else ""
            body_lines.append(f"        await {_sel(selector)}.wait_for(state='visible', timeout=15000)")
            body_lines.append(f"        await {_sel(selector)}.hover()")

        elif cmd in ("拖拽",):
            src = parts[1] if len(parts) > 1 else ""
            dst = parts[2].replace("到 ", "").replace("到", "").strip() if len(parts) > 2 else ""
            body_lines.append(f"        await page.drag_and_drop({src!r}, {dst!r})")

        # ── 输入 ──
        elif cmd in ("输入", "input", "fill"):
            selector = parts[1] if len(parts) > 1 else ""
            text = parts[2] if len(parts) > 2 else ""
            body_lines.append(f"        await {_sel(selector)}.wait_for(state='visible', timeout=15000)")
            body_lines.append(f"        await {_sel(selector)}.fill({text!r})")

        elif cmd in ("清空", "clear"):
            selector = parts[1] if len(parts) > 1 else ""
            body_lines.append(f"        await {_sel(selector)}.wait_for(state='visible', timeout=15000)")
            body_lines.append(f"        await {_sel(selector)}.clear()")

        elif cmd in ("按键", "key", "press"):
            key = parts[1] if len(parts) > 1 else "Enter"
            body_lines.append(f"        await page.keyboard.press({key!r})")

        elif cmd in ("输入文字", "type"):
            text = " ".join(parts[1:]) if len(parts) > 1 else ""
            body_lines.append(f"        await page.keyboard.type({text!r})")

        # ── 表单 ──
        elif cmd in ("选择", "select"):
            selector = parts[1] if len(parts) > 1 else ""
            value = parts[2] if len(parts) > 2 else ""
            if value:
                body_lines.append(f"        await {_sel(selector)}.wait_for(state='visible', timeout=15000)")
                body_lines.append(f"""        _el = {_sel(selector)}
        _t = await _el.get_attribute('type')
        if _t == 'radio':
            await _el.check()
        else:
            await _el.select_option({value!r})""")
            else:
                body_lines.append(f"        await {_sel(selector)}.wait_for(state='visible', timeout=15000)")
                body_lines.append(f"        await {_sel(selector)}.select_option()")

        elif cmd in ("勾选", "check"):
            selector = parts[1] if len(parts) > 1 else ""
            body_lines.append(f"        await {_sel(selector)}.wait_for(state='visible', timeout=15000)")
            body_lines.append(f"""        _el = {_sel(selector)}
        _t = await _el.get_attribute('type')
        if _t in ('checkbox', 'radio'):
            await _el.click()
        else:
            try:
                await _el.check()
            except Exception:
                await _el.click()""")

        elif cmd in ("取消勾选", "uncheck"):
            selector = parts[1] if len(parts) > 1 else ""
            body_lines.append(f"        await {_sel(selector)}.wait_for(state='visible', timeout=15000)")
            body_lines.append(f"""        _el = {_sel(selector)}
        if await _el.is_checked():
            _t = await _el.get_attribute('type')
            if _t == 'checkbox':
                try:
                    await _el.uncheck()
                except Exception:
                    await _el.click()
            else:
                await _el.click()""")

        elif cmd in ("开关", "toggle", "switch"):
            selector = parts[1] if len(parts) > 1 else ""
            body_lines.append(f"        await {_sel(selector)}.wait_for(state='visible', timeout=15000)")
            body_lines.append(f"        await {_sel(selector)}.click()")

        elif cmd in ("上传", "upload"):
            selector = parts[1] if len(parts) > 1 else ""
            filepath = parts[2] if len(parts) > 2 else ""
            body_lines.append(f"        await {_sel(selector)}.wait_for(state='visible', timeout=15000)")
            body_lines.append(f"        await {_sel(selector)}.set_input_files({filepath!r})")

        elif cmd in ("拖放文件", "dropfiles"):
            selector = parts[1] if len(parts) > 1 else ""
            filepath = parts[2] if len(parts) > 2 else ""
            body_lines.append(f"        await {_sel(selector)}.wait_for(state='visible', timeout=15000)")
            body_lines.append(f"        await {_sel(selector)}.set_input_files({filepath!r})")

        elif cmd in ("单选", "radio"):
            # 单选：点击指定的 radio input（支持 value、label、name 等定位）
            selector = parts[1] if len(parts) > 1 else ""
            body_lines.append(f"        await {_sel(selector)}.wait_for(state='visible', timeout=15000)")
            body_lines.append(f"""        _el = {_sel(selector)}
        _t = await _el.get_attribute('type')
        if _t == 'radio':
            await _el.check()
        else:
            await _el.click()""")

        elif cmd in ("多选", "check-multi"):
            # 多选：勾选多个，支持用逗号分隔多个 selector 或依次列出
            # 格式: 多选 [value=a],[value=b]  或  多选 [value=a]\n多选 [value=b]
            selector = parts[1] if len(parts) > 1 else ""
            body_lines.append(f"        await {_sel(selector)}.wait_for(state='visible', timeout=15000)")
            body_lines.append(f"""        _el = {_sel(selector)}
        _t = await _el.get_attribute('type')
        if _t in ('checkbox', 'radio'):
            if not await _el.is_checked():
                await _el.click()
        else:
            try:
                if not await _el.is_checked():
                    await _el.check()
            except Exception:
                await _el.click()""")

        elif cmd in ("全选", "checkall", "selectall"):
            # 全选：select 下拉框选全部 或 checkbox 全勾
            selector = parts[1] if len(parts) > 1 else ""
            body_lines.append(f"        await {_sel(selector)}.wait_for(state='visible', timeout=15000)")
            body_lines.append(f"        await {_sel(selector)}.select_option()")

        elif cmd in ("取消全选", "uncheckall", "clear-select"):
            # 取消 select 选中（回到第一项）
            selector = parts[1] if len(parts) > 1 else ""
            body_lines.append(f"        await {_sel(selector)}.wait_for(state='visible', timeout=15000)")
            body_lines.append(f"        await {_sel(selector)}.select_option(index=0)")

        elif cmd in ("选中文字", "select-text"):
            # 选中输入框内文字
            selector = parts[1] if len(parts) > 1 else ""
            body_lines.append(f"        await {_sel(selector)}.wait_for(state='visible', timeout=15000)")
            body_lines.append(f"        await {_sel(selector)}.select_text()")

        elif cmd in ("按下", "press-key"):
            # 按下特定键组合
            key = parts[1] if len(parts) > 1 else "Enter"
            body_lines.append(f"        await page.keyboard.press({key!r})")

        elif cmd in ("悬停", "hover"):
            selector = parts[1] if len(parts) > 1 else ""
            body_lines.append(f"        await {_sel(selector)}.wait_for(state='visible', timeout=15000)")
            body_lines.append(f"        await {_sel(selector)}.hover()")

        elif cmd in ("拖拽",):
            # 拖拽 #src 到 #dst
            src = parts[1] if len(parts) > 1 else ""
            dst = parts[2].replace("到 ", "").replace("到", "").strip() if len(parts) > 2 else ""
            body_lines.append(f"        await page.drag_and_drop({src!r}, {dst!r})")

        # ── 滚动 ──
        elif cmd in ("滚动", "scroll"):
            direction = parts[1] if len(parts) > 1 else "下"
            if direction in ("下", "down"):
                body_lines.append("        await page.evaluate('window.scrollBy(0, 600)')")
            elif direction in ("上", "up"):
                body_lines.append("        await page.evaluate('window.scrollBy(0, -600)')")
            elif direction in ("底部", "bottom"):
                body_lines.append("        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')")
            elif direction in ("顶部", "top"):
                body_lines.append("        await page.evaluate('window.scrollTo(0, 0)')")

        elif cmd in ("滚动到", "scrollto"):
            selector = parts[1] if len(parts) > 1 else "body"
            body_lines.append(f"        await {_sel(selector)}.scroll_into_view_if_needed()")

        # ── 多标签页 ──
        elif cmd in ("新标签页", "newtab"):
            body_lines.append("        page = await ctx.new_page()")
            frame_var[0] = "page"

        elif cmd in ("关闭标签页", "closetab"):
            body_lines.append("        await page.close()")

        # ── iframe ──
        elif cmd in ("iframe",):
            selector = parts[1] if len(parts) > 1 else ""
            body_lines.append(f"        _frame = page.frame_locator({selector!r})")
            frame_var[0] = "_frame"

        elif cmd in ("iframe输入", "iframefill"):
            selector = parts[1] if len(parts) > 1 else "body"
            text = parts[2] if len(parts) > 2 else ""
            body_lines.append(f"        await _frame.locator({selector!r}).wait_for(state='visible', timeout=15000)")
            body_lines.append(f"        await _frame.locator({selector!r}).fill({text!r})")

        elif cmd in ("iframe点击", "iframeclick"):
            selector = parts[1] if len(parts) > 1 else ""
            body_lines.append(f"        await _frame.locator({selector!r}).wait_for(state='visible', timeout=15000)")
            body_lines.append(f"        await _frame.locator({selector!r}).click()")

        elif cmd in ("退出iframe", "exitiframe"):
            frame_var[0] = "page"

        # ── 获取 / 断言 ──
        elif cmd in ("获取文本", "gettext"):
            selector = parts[1] if len(parts) > 1 else "body"
            body_lines.append(f"        await {_sel(selector)}.wait_for(state='visible', timeout=15000)")
            body_lines.append(f"        _text = await {_sel(selector)}.inner_text()")
            body_lines.append("        print('获取文本:', _text[:500])")

        elif cmd in ("获取URL", "geturl"):
            body_lines.append("        print('当前URL:', page.url)")

        elif cmd in ("获取标题", "gettitle"):
            body_lines.append("        print('页面标题:', await page.title())")

        elif cmd in ("获取属性", "getattr"):
            selector = parts[1] if len(parts) > 1 else ""
            attr = parts[2] if len(parts) > 2 else "href"
            body_lines.append(f"        await {_sel(selector)}.wait_for(state='visible', timeout=15000)")
            body_lines.append(f"        _attr = await {_sel(selector)}.get_attribute({attr!r})")
            body_lines.append(f"        print('属性 {attr}:', _attr)")

        elif cmd in ("断言可见", "assertvisible"):
            selector = parts[1] if len(parts) > 1 else ""
            body_lines.append(f"        await {_sel(selector)}.wait_for(state='visible', timeout=10000)")
            body_lines.append(f"        print('[OK] 断言可见: {selector}')")

        elif cmd in ("断言文本", "asserttext"):
            selector = parts[1] if len(parts) > 1 else ""
            expected = parts[2] if len(parts) > 2 else ""
            body_lines.append(f"        await {_sel(selector)}.wait_for(state='visible', timeout=15000)")
            body_lines.append(f"        _t = await {_sel(selector)}.inner_text()")
            body_lines.append(f"        assert {expected!r} in _t, f'断言失败: 期望包含 {expected!r}, 实际: {{_t[:200]}}'")
            body_lines.append(f"        print('[OK] 断言文本包含: {expected!r}')")

        elif cmd in ("断言URL", "asserturl"):
            expected = parts[1] if len(parts) > 1 else ""
            body_lines.append(f"        assert {expected!r} in page.url, f'断言失败: 期望URL包含 {expected!r}, 实际: {{page.url}}'")
            body_lines.append(f"        print('[OK] 断言URL包含: {expected!r}')")

        elif cmd in ("断言标题", "asserttitle"):
            expected = parts[1] if len(parts) > 1 else ""
            body_lines.append(f"        _title = await page.title()")
            body_lines.append(f"        assert {expected!r} in _title, f'断言失败: 期望标题包含 {expected!r}, 实际: {{_title}}'")
            body_lines.append(f"        print('[OK] 断言标题包含: {expected!r}')")

        elif cmd in ("执行JS", "js", "eval"):
            js_code = " ".join(parts[1:]) if len(parts) > 1 else "document.title"
            body_lines.append(f"        _js_result = await page.evaluate({js_code!r})")
            body_lines.append("        print('JS结果:', _js_result)")

        elif cmd in ("打印",):
            msg = " ".join(parts[1:])
            body_lines.append(f"        print({msg!r})")

        else:
            body_lines.append(f"        # 未识别指令: {line}")

    # ── 组装完整脚本 ─────────────────────────────────────────────────────────
    header = f'''import asyncio
import sys
import os
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# 禁用系统代理（避免 VPN/代理干扰）
for _k in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ.pop(_k, None)

async def stable_goto(page, url, timeout=30000):
    await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
    except PlaywrightTimeoutError:
        pass

async def wait_nav(page, timeout=12000):
    try:
        await page.wait_for_load_state("networkidle", timeout=timeout)
    except PlaywrightTimeoutError:
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
        except PlaywrightTimeoutError:
            pass

async def main():
    async with async_playwright() as p:
        trace_dir = r"{trace_dir}"
        os.makedirs(trace_dir, exist_ok=True)
        browser = await p.chromium.launch(headless=False, args=["--no-sandbox", "--disable-proxy-server"])
        ctx = await browser.new_context()
        page = await ctx.new_page()
        _frame = None
'''

    footer = "        print('[done] DSL 执行完成')\n\nasyncio.run(main())\n"

    return header + "\n".join(body_lines) + "\n" + footer

# ─── NLP 模块 ──────────────────────────────────────────────────────────────────

def _get_nlp_pipeline():
    """获取 NLP 管道实例"""
    try:
        from browser_use.nlp import NLUPipeline
        return NLUPipeline()
    except ImportError:
        return None

def _nlp_to_dsl(text: str) -> str:
    """将自然语言转换为 DSL"""
    try:
        from browser_use.nlp.dsl_parser import natural_language_to_dsl
        return natural_language_to_dsl(text)
    except ImportError:
        return text

# ─── Pydantic 请求模型 ────────────────────────────────────────────────────────

class RunTaskRequest(BaseModel):
    task: str
    mode: str = "llm"          # "llm" | "dsl" | "cdp"
    cdp_url: str = ""
    task_id: str = ""
    max_steps: int = 20
    dsl: str = ""              # NLP 模式直接传 dsl

class RunPlaywrightRequest(BaseModel):
    script: str
    task_id: str = ""

class TestLLMRequest(BaseModel):
    config: str = ""

class RecordRequest(BaseModel):
    url: str
    task_id: str = ""

class ExportRequest(BaseModel):
    dsl: str
    format: str = "yaml"       # "yaml" | "pytest"

# ─── API 路由 ─────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    llm_cfg = _get_llm_config()
    model = llm_cfg.get("model", "未配置")
    status = "ready" if llm_cfg else "unconfigured"
    return {"success": True, "data": {
        "status": "ok",
        "llm": {"status": status, "model": model},
        "cdp_url": CDP_URL,
    }}

@app.get("/llm-status")
async def llm_status():
    cfg = _get_llm_config()
    if not cfg:
        return {"success": False, "data": {"configured": False, "status": "unconfigured"}}
    raw = json.dumps(cfg, ensure_ascii=False)
    return {"success": True, "data": {
        "configured": True,
        "status": "ready",
        "model": cfg.get("model", ""),
        "provider": cfg.get("provider", ""),
        "raw_config": raw,
    }}

@app.post("/test-llm")
async def test_llm(req: TestLLMRequest):
    try:
        llm = _build_llm()
        from browser_use.llm.messages import UserMessage
        from browser_use.llm.views import ContentPartTextParam
        msg = UserMessage(content=[ContentPartTextParam(type="text", text="回复 OK")])
        resp = await llm.ainvoke([msg])
        text = resp.content if hasattr(resp, "content") else str(resp)
        return {"success": True, "data": {"status_text": str(text)[:200]}}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/run-task")
async def run_task(req: RunTaskRequest):
    task_id = req.task_id or f"task-{time.strftime('%H%M%S')}"
    trace_dir = TRACES_DIR / task_id
    trace_dir.mkdir(exist_ok=True)
    start = time.time()

    mode = req.mode
    dsl_text = req.dsl or req.task

    # NLP / DSL / NLP 模式 - 优先尝试 NLP 转换
    if mode in ("dsl", "nlp", "natural"):
        # 尝试 NLP 转换
        try:
            nlp_result = _nlp_to_dsl(dsl_text)
            if nlp_result and nlp_result != dsl_text:
                dsl_text = nlp_result
                logger.info(f"NLP 转换结果: {dsl_text[:100]}...")
        except Exception as e:
            logger.warning(f"NLP 转换失败，使用原始输入: {e}")
        
        cdp = req.cdp_url or CDP_URL
        script = dsl_to_playwright_script(dsl_text, task_id, cdp)
        script_path = trace_dir / "script.py"
        script_path.write_text(script, encoding="utf-8")
        (trace_dir / "dsl.txt").write_text(dsl_text, encoding="utf-8")

        log_lines = []
        for line in dsl_text.strip().splitlines():
            log_lines.append(f"▶ {line.strip()}")

        try:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True, text=True, timeout=120,
                cwd=str(BASE_DIR)
            )
            stdout = result.stdout
            stderr = result.stderr
            success = result.returncode == 0

            # 把截图路径加入 log
            for l in stdout.splitlines():
                if "截图已保存" in l or "screenshot" in l.lower():
                    log_lines.append(f"  [screenshot] {l.strip()}")
                elif l.strip():
                    log_lines.append(f"  {l.strip()}")

            trace = {
                "task_id": task_id, "mode": mode,
                "success": success,
                "elapsed_ms": int((time.time() - start) * 1000),
                "dsl": dsl_text,
                "log": "\n".join(log_lines),
                "stdout": stdout[:2000],
                "stderr": stderr[:3000] if not success else "",
            }
            # GIF 生成（仅成功时）
            if success:
                gif_path = _make_gif_from_screenshots(trace_dir)
                if gif_path:
                    trace["gif_path"] = gif_path
                    trace["gif_url"] = f"/traces/{task_id}/recording.gif"
                    trace["has_gif"] = True
            (trace_dir / "trace.json").write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
            return {"success": True, "data": trace}

        except subprocess.TimeoutExpired:
            trace = {
                "task_id": task_id, "mode": mode, "success": False,
                "elapsed_ms": 120000, "dsl": dsl_text,
                "error": "执行超时(120s)",
                "log": "\n".join(log_lines),
            }
            # 超时也可能已有一些截图，尝试生成 GIF
            gif_path = _make_gif_from_screenshots(trace_dir)
            if gif_path:
                trace["gif_path"] = gif_path
                trace["gif_url"] = f"/traces/{task_id}/recording.gif"
                trace["has_gif"] = True
            (trace_dir / "trace.json").write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
            return {"success": False, "data": trace, "error": "执行超时(120s)"}

    # LLM 模式
    elif mode == "llm":
        try:
            from browser_use import Agent
            from browser_use.browser import BrowserProfile, BrowserSession

            llm = _build_llm()
            cdp = req.cdp_url or CDP_URL
            profile = BrowserProfile(headless=False, keep_alive=True)
            browser = BrowserSession(browser_profile=profile)

            agent = Agent(task=req.task, llm=llm, browser=browser)
            history = await agent.run(max_steps=req.max_steps)

            final = history.final_result() or ""
            errors = [e for e in (history.errors() or []) if e]
            steps = history.number_of_steps()
            success = history.is_successful() is not False

            trace = {
                "task_id": task_id, "mode": "llm",
                "success": success, "steps": steps,
                "elapsed_ms": int((time.time() - start) * 1000),
                "task": req.task,
                "final_result": final[:2000],
                "errors": [str(e)[:300] for e in errors[-3:]],
            }
            # GIF 生成（仅成功时）
            if success:
                gif_path = _make_gif_from_screenshots(trace_dir)
                if gif_path:
                    trace["gif_path"] = gif_path
                    trace["gif_url"] = f"/traces/{task_id}/recording.gif"
                    trace["has_gif"] = True
            (trace_dir / "trace.json").write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
            await browser.stop()
            return {"success": True, "data": trace}

        except Exception as e:
            trace = {"task_id": task_id, "mode": "llm", "success": False,
                     "elapsed_ms": int((time.time() - start) * 1000),
                     "task": req.task, "error": str(e)}
            (trace_dir / "trace.json").write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
            return {"success": False, "data": trace, "error": str(e)}

    return {"success": False, "error": f"未知模式: {mode}"}

@app.post("/run-playwright")
async def run_playwright(req: RunPlaywrightRequest):
    task_id = req.task_id or f"pw-{time.strftime('%H%M%S')}"
    trace_dir = TRACES_DIR / task_id
    trace_dir.mkdir(exist_ok=True)
    start = time.time()

    script_path = trace_dir / "script.py"
    script_path.write_text(req.script, encoding="utf-8")

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True, text=True, timeout=120,
            cwd=str(BASE_DIR)
        )
        success = result.returncode == 0
        data = {
            "task_id": task_id, "success": success,
            "elapsed_ms": int((time.time() - start) * 1000),
            "stdout": result.stdout[:3000],
            "stderr": result.stderr[:1000] if not success else "",
            "error": result.stderr[:500] if not success else "",
        }
        # GIF 生成（仅成功时）
        if success:
            gif_path = _make_gif_from_screenshots(trace_dir)
            if gif_path:
                data["gif_path"] = gif_path
                data["gif_url"] = f"/traces/{task_id}/recording.gif"
                data["has_gif"] = True
        return {"success": True, "data": data}
    except subprocess.TimeoutExpired:
        return {"success": False, "data": {"task_id": task_id, "error": "超时"}}
    except Exception as e:
        return {"success": False, "data": {"task_id": task_id, "error": str(e)}}

@app.get("/traces")
async def list_traces():
    runs = []
    for d in sorted(TRACES_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        tf = d / "trace.json"
        if tf.exists():
            try:
                t = json.loads(tf.read_text(encoding="utf-8"))
                # 检查是否有 GIF
                has_gif = (d / "recording.gif").exists()
                runs.append({
                    "task_id": t.get("task_id", d.name),
                    "mode": t.get("mode", ""),
                    "success": t.get("success", False),
                    "steps": t.get("steps", 0),
                    "elapsed_ms": t.get("elapsed_ms", 0),
                    "task": t.get("task", t.get("dsl", ""))[:80],
                    "has_gif": has_gif,
                })
            except Exception:
                pass
    return {"success": True, "runs": runs}

@app.get("/traces/{task_id}/trace.json")
async def get_trace(task_id: str):
    tf = TRACES_DIR / task_id / "trace.json"
    if not tf.exists():
        raise HTTPException(404, "trace not found")
    return JSONResponse(json.loads(tf.read_text(encoding="utf-8")))

@app.get("/traces/{task_id}/{filename}")
async def get_trace_file(task_id: str, filename: str):
    fp = TRACES_DIR / task_id / filename
    if not fp.exists():
        raise HTTPException(404, "file not found")
    return FileResponse(str(fp))

@app.get("/dsl-demos")
async def dsl_demos():
    return {"success": True, "demos": DSL_DEMOS}

@app.post("/export")
async def export_dsl(req: ExportRequest):
    lines = [l.strip() for l in req.dsl.strip().splitlines() if l.strip()]
    now = time.strftime("%Y/%m/%d %H:%M:%S")
    if req.format == "yaml":
        yaml_lines = [
            f"# NLP 自动化测试 - 生成于 {now}",
            'version: "1.0"',
            "",
            "steps:",
        ]
        for l in lines:
            yaml_lines.append(f'  - "{l}"')
        return {"success": True, "content": "\n".join(yaml_lines)}
    elif req.format == "pytest":
        base_url = f"http://127.0.0.1:{PORT}"
        dsl_escaped = "\n".join(lines)
        py_lines = [
            '"""Auto-generated pytest from NLP instructions"""',
            "import pytest, requests, json",
            "",
            f'BASE = "{base_url}"',
            "",
            "def test_nlp():",
            '    """Execute NLP instructions via Self API"""',
            '    dsl = """',
        ]
        for l in lines:
            py_lines.append(f"    {l}")
        py_lines += [
            '    """',
            f'    resp = requests.post(BASE + "/run-dsl", json={{"dsl": dsl.strip()}}, timeout=120)',
            "    assert resp.status_code == 200",
            "    data = resp.json()",
            "    assert data.get('success'), f\"NLP failed: {data}\"",
        ]
        return {"success": True, "content": "\n".join(py_lines)}
    return {"success": False, "error": "未知格式"}

@app.post("/record/start")
async def record_start(req: RecordRequest):
    """启动录制（通过 CDP 监听用户操作生成 DSL）"""
    task_id = req.task_id or f"rec-{time.strftime('%H%M%S')}"
    return {"success": True, "data": {"task_id": task_id, "status": "recording", "url": req.url}}

@app.post("/record/stop")
async def record_stop():
    return {"success": True, "data": {"dsl": "# 录制功能需要浏览器扩展支持\n打开 https://bing.com\n等待加载完成\n截图"}}

@app.post("/run-dsl")
async def run_dsl_shortcut(req: RunTaskRequest):
    """NLP/DSL 快捷接口（pytest 导出使用）"""
    req.mode = "dsl"
    return await run_task(req)

@app.delete("/traces")
async def clear_traces():
    import shutil
    count = 0
    for d in TRACES_DIR.iterdir():
        if d.is_dir():
            shutil.rmtree(d, ignore_errors=True)
            count += 1
    return {"success": True, "cleared": count}

# ─── NLP 分析接口 ────────────────────────────────────────────────────────────────

class NLPAnalyzeRequest(BaseModel):
    text: str
    use_llm: bool = False

@app.post("/nlp/analyze")
async def nlp_analyze(req: NLPAnalyzeRequest):
    """分析自然语言输入，返回意图、实体和 DSL"""
    try:
        from browser_use.nlp import NLUPipeline
        pipeline = NLUPipeline(use_llm_fallback=req.use_llm)
        result = pipeline.process(req.text)
        return {
            "success": True,
            "data": {
                "original_text": result.original_text,
                "dsl_output": result.dsl_output,
                "primary_intent": result.primary_intent.value if result.primary_intent else None,
                "confidence": result.primary_intent_confidence,
                "entities": [e.to_dict() for e in result.entities],
                "commands": [cmd.to_dict() for cmd in result.commands],
                "warnings": result.warnings,
                "processing_time_ms": result.processing_time_ms,
            }
        }
    except ImportError:
        return {"success": False, "error": "NLP 模块未安装"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/nlp/to-dsl")
async def nlp_to_dsl(req: NLPAnalyzeRequest):
    """将自然语言转换为 DSL"""
    try:
        from browser_use.nlp import NLUPipeline
        pipeline = NLUPipeline()
        dsl = pipeline.to_dsl(req.text)
        return {"success": True, "data": {"dsl": dsl}}
    except ImportError:
        return {"success": False, "error": "NLP 模块未安装"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/nlp/intents")
async def nlp_intents():
    """获取支持的意图列表"""
    try:
        from browser_use.nlp import Intent
        intents = [i.value for i in Intent]
        return {"success": True, "data": {"intents": intents}}
    except ImportError:
        return {"success": False, "error": "NLP 模块未安装"}

@app.get("/nlp/status")
async def nlp_status():
    """获取 NLP 模块状态"""
    try:
        from browser_use.nlp import NLUPipeline
        return {
            "success": True,
            "data": {
                "available": True,
                "status": "ready",
                "features": [
                    "意图分类",
                    "实体识别",
                    "语义解析",
                    "自然语言转 DSL",
                ]
            }
        }
    except ImportError:
        return {
            "success": True,
            "data": {
                "available": False,
                "status": "not_installed",
                "features": []
            }
        }

# ─── 前端 HTML（从 webui/index.html 读取）────────────────────────────────────
_HTML_FILE = BASE_DIR / "webui" / "index.html"

def _get_html() -> str:
    return _HTML_FILE.read_text(encoding="utf-8")


@app.get("/", response_class=HTMLResponse)
async def index():
    return _get_html()

# ─── 启动入口 ─────────────────────────────────────────────────────────────────

def open_browser():
    webbrowser.open(f"http://127.0.0.1:{PORT}")

if __name__ == "__main__":
    import io
    import sys
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    print("[Browser-Use] Web UI 启动中...")
    print(f"   地址: http://127.0.0.1:{PORT}")
    print(f"   CDP:  {CDP_URL}")
    print(f"   按 Ctrl+C 停止\n")
    Timer(1.5, open_browser).start()
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")
