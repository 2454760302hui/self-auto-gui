"""
增强的 DSL 解析器 - 支持更多指令和 NLP 语义解析
"""
import re
import time
import json
import logging
from pathlib import Path
from typing import Optional, Callable, Any

logger = logging.getLogger(__name__)


class EnhancedDSLParser:
    """
    增强的 DSL 解析器
    
    支持以下功能：
    - 基础 DSL 指令（与原有兼容）
    - 自然语言到 DSL 的转换
    - 智能选择器解析
    - 变量和宏定义
    - 条件执行
    - 循环执行
    """
    
    def __init__(self):
        """初始化增强 DSL 解析器"""
        self.variables: dict[str, str] = {}
        self.macros: dict[str, str] = {}
        
        # 导航指令
        self._nav_commands = {
            '打开': self._parse_open,
            'open': self._parse_open,
            'goto': self._parse_open,
            'navigate': self._parse_open,
            '访问': self._parse_open,
            '去': self._parse_open,
        }
        
        # 等待指令
        self._wait_commands = {
            '等待': self._parse_wait,
            'wait': self._parse_wait,
            'sleep': self._parse_wait,
            '等待加载完成': self._parse_wait_load,
            'waitload': self._parse_wait_load,
            '等待可见': self._parse_wait_visible,
            'waitvisible': self._parse_wait_visible,
        }
        
        # 点击指令
        self._click_commands = {
            '点击': self._parse_click,
            'click': self._parse_click,
            '单击': self._parse_click,
            '双击': self._parse_dblclick,
            'dblclick': self._parse_dblclick,
            '右键': self._parse_rightclick,
            'rightclick': self._parse_rightclick,
            '悬停': self._parse_hover,
            'hover': self._parse_hover,
            '按下': self._parse_hover,
        }
        
        # 输入指令
        self._input_commands = {
            '输入': self._parse_input,
            'fill': self._parse_input,
            '清空': self._parse_clear,
            'clear': self._parse_clear,
            '按键': self._parse_press,
            'press': self._parse_press,
            'key': self._parse_press,
            '选择': self._parse_select,
            'select': self._parse_select,
        }
        
        # 页面操作指令
        self._page_commands = {
            '截图': self._parse_screenshot,
            'screenshot': self._parse_screenshot,
            'scroll': self._parse_scroll,
            '滚动': self._parse_scroll,
            '滚动到': self._parse_scroll_to,
            'scrollto': self._parse_scroll_to,
            '返回': self._parse_back,
            'back': self._parse_back,
            'goback': self._parse_back,
            '前进': self._parse_forward,
            'forward': self._parse_forward,
            '刷新': self._parse_reload,
            'reload': self._parse_reload,
            'refresh': self._parse_reload,
        }
        
        # 获取信息指令
        self._get_commands = {
            '获取文本': self._parse_get_text,
            'gettext': self._parse_get_text,
            '提取文本': self._parse_get_text,
            '获取URL': self._parse_get_url,
            'geturl': self._parse_get_url,
            '获取标题': self._parse_get_title,
            'gettitle': self._parse_get_title,
            '获取属性': self._parse_get_attr,
            'getattr': self._parse_get_attr,
        }
        
        # 断言指令
        self._assert_commands = {
            '断言可见': self._parse_assert_visible,
            'assertvisible': self._parse_assert_visible,
            '验证可见': self._parse_assert_visible,
            '断言文本': self._parse_assert_text,
            'asserttext': self._parse_assert_text,
            '断言URL': self._parse_assert_url,
            'asserturl': self._parse_assert_url,
            '断言标题': self._parse_assert_title,
            'asserttitle': self._parse_assert_title,
        }
        
        # iframe 指令
        self._iframe_commands = {
            'iframe': self._parse_iframe,
            'iframe输入': self._parse_iframe_input,
            'iframefill': self._parse_iframe_input,
            'iframe点击': self._parse_iframe_click,
            'iframeclick': self._parse_iframe_click,
            '退出iframe': self._parse_exit_iframe,
        }
        
        # 标签页指令
        self._tab_commands = {
            '新标签页': self._parse_new_tab,
            'newtab': self._parse_new_tab,
            '关闭标签页': self._parse_close_tab,
            'closetab': self._parse_close_tab,
        }
        
        # 弹窗指令
        self._alert_commands = {
            '接受弹窗': self._parse_accept_alert,
            'accept': self._parse_accept_alert,
            '拒绝弹窗': self._parse_dismiss_alert,
            'dismiss': self._parse_dismiss_alert,
        }
        
        # 拖拽上传指令
        self._drag_upload_commands = {
            '拖拽': self._parse_drag,
            '上传': self._parse_upload,
            'upload': self._parse_upload,
            '勾选': self._parse_check,
            'check': self._parse_check,
            '取消勾选': self._parse_uncheck,
            'uncheck': self._parse_uncheck,
        }
        
        # JavaScript 指令
        self._js_commands = {
            '执行JS': self._parse_js,
            'js': self._parse_js,
            'eval': self._parse_js,
            '执行javascript': self._parse_js,
        }
        
        # 搜索和提取指令
        self._search_extract_commands = {
            '搜索': self._parse_search,
            'search': self._parse_search,
            '查找': self._parse_search,
            '提取': self._parse_extract,
            'extract': self._parse_extract,
        }
        
        # 其他指令
        self._other_commands = {
            '打印': self._parse_print,
            '变量': self._parse_variable,
            'set': self._parse_variable,
            '条件': self._parse_conditional,
            'if': self._parse_conditional,
            '循环': self._parse_loop,
            'for': self._parse_loop,
            'while': self._parse_loop,
        }
        
        # 合并所有命令
        self._all_commands = {}
        for cmd_dict in [
            self._nav_commands, self._wait_commands, self._click_commands,
            self._input_commands, self._page_commands, self._get_commands,
            self._assert_commands, self._iframe_commands, self._tab_commands,
            self._alert_commands, self._drag_upload_commands, self._js_commands,
            self._search_extract_commands, self._other_commands
        ]:
            self._all_commands.update(cmd_dict)
    
    def parse(self, dsl: str) -> list[dict]:
        """
        解析 DSL 返回指令列表
        
        Args:
            dsl: DSL 文本
            
        Returns:
            解析后的指令列表
        """
        lines = [l.strip() for l in dsl.strip().splitlines() if l.strip() and not l.strip().startswith("#")]
        instructions = []
        
        for line in lines:
            # 跳过注释
            if line.startswith('#') or line.startswith('//'):
                continue
            
            # 处理宏定义
            if line.startswith('!'):
                self._process_macro(line)
                continue
            
            # 处理变量定义
            if '=' in line and not line.startswith('"'):
                parts = line.split('=', 1)
                if parts[0].strip().isidentifier():
                    self.variables[parts[0].strip()] = parts[1].strip()
                    continue
            
            # 解析指令
            inst = self._parse_line(line)
            if inst:
                instructions.append(inst)
        
        return instructions
    
    def _parse_line(self, line: str) -> Optional[dict]:
        """解析单行指令"""
        parts = line.split(None, 2)
        cmd = parts[0] if parts else ""
        
        # 查找对应的解析器
        parser = self._all_commands.get(cmd)
        if parser:
            return parser(parts)
        
        # 尝试自然语言解析
        return self._parse_natural_language(line, parts)
    
    def _parse_natural_language(self, line: str, parts: list) -> Optional[dict]:
        """尝试自然语言解析"""
        # 模式匹配
        patterns = [
            # 点击模式
            (r'点击\s+(.+)', 'click'),
            (r'打开\s+(.+)', 'open'),
            (r'输入\s+(.+?)\s+(.+)', 'input'),
            (r'搜索\s+(.+)', 'search'),
            (r'滚动\s*(.*)', 'scroll'),
        ]
        
        for pattern, cmd_type in patterns:
            match = re.match(pattern, line, re.I)
            if match:
                groups = match.groups()
                if cmd_type == 'click':
                    return {'type': 'click', 'selector': self._normalize_selector(groups[0])}
                elif cmd_type == 'open':
                    return {'type': 'navigate', 'url': groups[0]}
                elif cmd_type == 'input':
                    if len(groups) >= 2:
                        return {'type': 'input', 'selector': self._normalize_selector(groups[0]), 'text': groups[1]}
                elif cmd_type == 'search':
                    return {'type': 'search', 'query': groups[0]}
                elif cmd_type == 'scroll':
                    direction = groups[0] if groups[0] else '下'
                    return {'type': 'scroll', 'direction': direction}
        
        return None
    
    def _normalize_selector(self, selector: str) -> str:
        """标准化选择器"""
        selector = selector.strip()
        
        # 已有的前缀选择器
        prefixes = ['文本=', 'text=', 'role=', 'placeholder=', 'label=', 'xpath=', 'css=', '#', '.']
        for prefix in prefixes:
            if selector.startswith(prefix):
                return selector
        
        # 如果包含空格，添加文本前缀
        if ' ' in selector:
            return f'文本={selector}'
        
        return selector
    
    # ── 导航指令解析器 ─────────────────────────────────────────────
    
    def _parse_open(self, parts: list) -> dict:
        """解析打开指令"""
        url = parts[1] if len(parts) > 1 else "about:blank"
        return {'type': 'navigate', 'url': url}
    
    def _parse_wait_load(self, parts: list) -> dict:
        """解析等待加载完成指令"""
        return {'type': 'wait_load'}
    
    def _parse_back(self, parts: list) -> dict:
        """解析返回指令"""
        return {'type': 'back'}
    
    def _parse_forward(self, parts: list) -> dict:
        """解析前进指令"""
        return {'type': 'forward'}
    
    def _parse_reload(self, parts: list) -> dict:
        """解析刷新指令"""
        return {'type': 'reload'}
    
    # ── 等待指令解析器 ─────────────────────────────────────────────
    
    def _parse_wait(self, parts: list) -> dict:
        """解析等待指令"""
        val = parts[1] if len(parts) > 1 else "1"
        try:
            ms = int(float(val)) if float(val) > 100 else int(float(val) * 1000)
        except Exception:
            ms = 1000
        return {'type': 'wait', 'duration': ms}
    
    def _parse_wait_visible(self, parts: list) -> dict:
        """解析等待可见指令"""
        selector = parts[1] if len(parts) > 1 else "body"
        return {'type': 'wait_visible', 'selector': selector}
    
    # ── 点击指令解析器 ─────────────────────────────────────────────
    
    def _parse_click(self, parts: list) -> dict:
        """解析点击指令"""
        selector = parts[1] if len(parts) > 1 else ""
        return {'type': 'click', 'selector': self._normalize_selector(selector)}
    
    def _parse_dblclick(self, parts: list) -> dict:
        """解析双击指令"""
        selector = parts[1] if len(parts) > 1 else ""
        return {'type': 'dblclick', 'selector': self._normalize_selector(selector)}
    
    def _parse_rightclick(self, parts: list) -> dict:
        """解析右键指令"""
        selector = parts[1] if len(parts) > 1 else ""
        return {'type': 'rightclick', 'selector': self._normalize_selector(selector)}
    
    def _parse_hover(self, parts: list) -> dict:
        """解析悬停指令"""
        selector = parts[1] if len(parts) > 1 else ""
        return {'type': 'hover', 'selector': self._normalize_selector(selector)}
    
    # ── 输入指令解析器 ─────────────────────────────────────────────
    
    def _parse_input(self, parts: list) -> dict:
        """解析输入指令"""
        selector = parts[1] if len(parts) > 1 else ""
        text = parts[2] if len(parts) > 2 else ""
        return {
            'type': 'input',
            'selector': self._normalize_selector(selector),
            'text': text
        }
    
    def _parse_clear(self, parts: list) -> dict:
        """解析清空指令"""
        selector = parts[1] if len(parts) > 1 else ""
        return {'type': 'clear', 'selector': self._normalize_selector(selector)}
    
    def _parse_press(self, parts: list) -> dict:
        """解析按键指令"""
        key = parts[1] if len(parts) > 1 else "Enter"
        return {'type': 'press', 'key': key}
    
    def _parse_select(self, parts: list) -> dict:
        """解析选择指令"""
        selector = parts[1] if len(parts) > 1 else ""
        value = parts[2] if len(parts) > 2 else ""
        return {
            'type': 'select',
            'selector': self._normalize_selector(selector),
            'value': value
        }
    
    # ── 页面操作指令解析器 ──────────────────────────────────────────
    
    def _parse_screenshot(self, parts: list) -> dict:
        """解析截图指令"""
        return {'type': 'screenshot'}
    
    def _parse_scroll(self, parts: list) -> dict:
        """解析滚动指令"""
        direction = parts[1] if len(parts) > 1 else "下"
        return {'type': 'scroll', 'direction': direction}
    
    def _parse_scroll_to(self, parts: list) -> dict:
        """解析滚动到指令"""
        selector = parts[1] if len(parts) > 1 else "body"
        return {'type': 'scroll_to', 'selector': selector}
    
    # ── 获取信息指令解析器 ──────────────────────────────────────────
    
    def _parse_get_text(self, parts: list) -> dict:
        """解析获取文本指令"""
        selector = parts[1] if len(parts) > 1 else "body"
        return {'type': 'get_text', 'selector': selector}
    
    def _parse_get_url(self, parts: list) -> dict:
        """解析获取URL指令"""
        return {'type': 'get_url'}
    
    def _parse_get_title(self, parts: list) -> dict:
        """解析获取标题指令"""
        return {'type': 'get_title'}
    
    def _parse_get_attr(self, parts: list) -> dict:
        """解析获取属性指令"""
        selector = parts[1] if len(parts) > 1 else ""
        attr = parts[2] if len(parts) > 2 else "href"
        return {
            'type': 'get_attribute',
            'selector': self._normalize_selector(selector),
            'attribute': attr
        }
    
    # ── 断言指令解析器 ─────────────────────────────────────────────
    
    def _parse_assert_visible(self, parts: list) -> dict:
        """解析断言可见指令"""
        selector = parts[1] if len(parts) > 1 else ""
        return {'type': 'assert_visible', 'selector': self._normalize_selector(selector)}
    
    def _parse_assert_text(self, parts: list) -> dict:
        """解析断言文本指令"""
        selector = parts[1] if len(parts) > 1 else ""
        expected = parts[2] if len(parts) > 2 else ""
        return {
            'type': 'assert_text',
            'selector': self._normalize_selector(selector),
            'expected': expected
        }
    
    def _parse_assert_url(self, parts: list) -> dict:
        """解析断言URL指令"""
        expected = parts[1] if len(parts) > 1 else ""
        return {'type': 'assert_url', 'expected': expected}
    
    def _parse_assert_title(self, parts: list) -> dict:
        """解析断言标题指令"""
        expected = parts[1] if len(parts) > 1 else ""
        return {'type': 'assert_title', 'expected': expected}
    
    # ── iframe 指令解析器 ────────────────────────────────────────────
    
    def _parse_iframe(self, parts: list) -> dict:
        """解析 iframe 指令"""
        selector = parts[1] if len(parts) > 1 else ""
        return {'type': 'iframe', 'selector': selector}
    
    def _parse_iframe_input(self, parts: list) -> dict:
        """解析 iframe 输入指令"""
        selector = parts[1] if len(parts) > 1 else ""
        text = parts[2] if len(parts) > 2 else ""
        return {
            'type': 'iframe_input',
            'selector': self._normalize_selector(selector),
            'text': text
        }
    
    def _parse_iframe_click(self, parts: list) -> dict:
        """解析 iframe 点击指令"""
        selector = parts[1] if len(parts) > 1 else ""
        return {'type': 'iframe_click', 'selector': self._normalize_selector(selector)}
    
    def _parse_exit_iframe(self, parts: list) -> dict:
        """解析退出 iframe 指令"""
        return {'type': 'exit_iframe'}
    
    # ── 标签页指令解析器 ──────────────────────────────────────────
    
    def _parse_new_tab(self, parts: list) -> dict:
        """解析新标签页指令"""
        return {'type': 'new_tab'}
    
    def _parse_close_tab(self, parts: list) -> dict:
        """解析关闭标签页指令"""
        return {'type': 'close_tab'}
    
    # ── 弹窗指令解析器 ─────────────────────────────────────────────
    
    def _parse_accept_alert(self, parts: list) -> dict:
        """解析接受弹窗指令"""
        return {'type': 'accept_alert'}
    
    def _parse_dismiss_alert(self, parts: list) -> dict:
        """解析拒绝弹窗指令"""
        return {'type': 'dismiss_alert'}
    
    # ── 拖拽上传指令解析器 ─────────────────────────────────────────
    
    def _parse_drag(self, parts: list) -> dict:
        """解析拖拽指令"""
        src = parts[1] if len(parts) > 1 else ""
        dst = parts[2].replace("到 ", "").replace("到", "").strip() if len(parts) > 2 else ""
        return {
            'type': 'drag',
            'source': self._normalize_selector(src),
            'target': self._normalize_selector(dst)
        }
    
    def _parse_upload(self, parts: list) -> dict:
        """解析上传指令"""
        selector = parts[1] if len(parts) > 1 else ""
        filepath = parts[2] if len(parts) > 2 else ""
        return {
            'type': 'upload',
            'selector': self._normalize_selector(selector),
            'filepath': filepath
        }
    
    def _parse_check(self, parts: list) -> dict:
        """解析勾选指令"""
        selector = parts[1] if len(parts) > 1 else ""
        return {'type': 'check', 'selector': self._normalize_selector(selector)}
    
    def _parse_uncheck(self, parts: list) -> dict:
        """解析取消勾选指令"""
        selector = parts[1] if len(parts) > 1 else ""
        return {'type': 'uncheck', 'selector': self._normalize_selector(selector)}
    
    # ── JavaScript 指令解析器 ───────────────────────────────────────
    
    def _parse_js(self, parts: list) -> dict:
        """解析执行 JS 指令"""
        code = parts[1] if len(parts) > 1 else ""
        return {'type': 'execute_js', 'code': code}
    
    # ── 搜索提取指令解析器 ─────────────────────────────────────────
    
    def _parse_search(self, parts: list) -> dict:
        """解析搜索指令"""
        query = parts[1] if len(parts) > 1 else ""
        return {'type': 'search', 'query': query}
    
    def _parse_extract(self, parts: list) -> dict:
        """解析提取指令"""
        query = parts[1] if len(parts) > 1 else ""
        return {'type': 'extract', 'query': query}
    
    # ── 其他指令解析器 ─────────────────────────────────────────────
    
    def _parse_print(self, parts: list) -> dict:
        """解析打印指令"""
        msg = parts[1] if len(parts) > 1 else ""
        return {'type': 'print', 'message': msg}
    
    def _parse_variable(self, parts: list) -> dict:
        """解析变量指令"""
        return None  # 在主循环中处理
    
    def _parse_conditional(self, parts: list) -> dict:
        """
        解析条件指令

        支持的格式：
        - 条件 if <condition> then <action>
        - 条件 if <condition> then <action> else <action>
        - 条件 if <condition> { actions }

        条件表达式支持：
        - url contains <text>
        - title contains <text>
        - element <selector> exists
        - element <selector> visible
        - element <selector> contains <text>
        """
        if len(parts) < 2:
            return None

        # 合并所有 parts
        full_line = ' '.join(parts[1:])

        # 解析条件表达式
        condition = None
        then_action = None
        else_action = None

        # 匹配 if <condition> then <action> [else <action>]
        import re

        # 模式1: 条件 条件 if <condition> then <action>
        pattern1 = re.compile(
            r'^if\s+(.+?)\s+then\s+(.+?)(?:\s+else\s+(.+))?$',
            re.IGNORECASE
        )
        match = pattern1.match(full_line)
        if match:
            condition = match.group(1).strip()
            then_action = match.group(2).strip()
            else_action = match.group(3).strip() if match.group(3) else None
        else:
            # 如果没有 then，认为整个是条件表达式
            condition = full_line

        # 构建条件执行指令
        instruction = {
            'type': 'conditional',
            'condition': condition,
            'then': then_action,
            'else': else_action,
        }

        return instruction

    def _parse_loop(self, parts: list) -> dict:
        """
        解析循环指令

        支持的格式：
        - 循环 <count> 次 { actions }
        - 循环 for <variable> in <items> { actions }
        - 循环 while <condition> { actions }

        示例：
        - 循环 3 次 { 点击 .next }
        - 循环 for item in [1,2,3] { 输入 .input item }
        - 循环 while element .loading visible { 等待 1 }
        """
        if len(parts) < 2:
            return None

        # 合并所有 parts
        full_line = ' '.join(parts[1:])

        import re

        # 模式1: 循环 <count> 次
        pattern1 = re.compile(
            r'^(\d+)\s*次\s*(?:\{(.+)\})?$',
            re.IGNORECASE
        )
        match = pattern1.match(full_line)
        if match:
            count = int(match.group(1))
            actions = match.group(2).strip() if match.group(2) else None
            return {
                'type': 'loop',
                'loop_type': 'count',
                'count': count,
                'actions': actions,
            }

        # 模式2: 循环 for <var> in <items>
        pattern2 = re.compile(
            r'^for\s+(\w+)\s+in\s+(.+?)(?:\s*\{(.+)\})?$',
            re.IGNORECASE
        )
        match = pattern2.match(full_line)
        if match:
            variable = match.group(1)
            items = match.group(2).strip()
            actions = match.group(3).strip() if match.group(3) else None
            return {
                'type': 'loop',
                'loop_type': 'for_each',
                'variable': variable,
                'items': items,
                'actions': actions,
            }

        # 模式3: 循环 while <condition>
        pattern3 = re.compile(
            r'^while\s+(.+?)(?:\s*\{(.+)\})?$',
            re.IGNORECASE
        )
        match = pattern3.match(full_line)
        if match:
            condition = match.group(1).strip()
            actions = match.group(2).strip() if match.group(2) else None
            return {
                'type': 'loop',
                'loop_type': 'while',
                'condition': condition,
                'actions': actions,
            }

        # 默认：认为是次数循环
        return {
            'type': 'loop',
            'loop_type': 'count',
            'count': 1,
            'actions': full_line,
        }

    def execute_conditional(
        self,
        instruction: dict,
        context: dict,
        executor: Optional[Callable] = None
    ) -> Any:
        """
        执行条件指令

        Args:
            instruction: 条件指令字典
            context: 执行上下文（包含页面状态等）
            executor: 动作执行器回调

        Returns:
            执行结果
        """
        condition = instruction.get('condition', '')
        then_action = instruction.get('then')
        else_action = instruction.get('else')

        # 评估条件
        if self._evaluate_condition(condition, context):
            if then_action and executor:
                return executor(then_action)
            return True
        else:
            if else_action and executor:
                return executor(else_action)
            return False

    def _evaluate_condition(self, condition: str, context: dict) -> bool:
        """
        评估条件表达式

        Args:
            condition: 条件表达式
            context: 执行上下文

        Returns:
            条件结果
        """
        import re

        condition = condition.strip()

        # url contains <text>
        pattern_url = re.compile(r'^url\s+contains\s+(.+)$', re.IGNORECASE)
        match = pattern_url.match(condition)
        if match:
            text = match.group(1).strip('"\'')
            current_url = context.get('url', '')
            return text.lower() in current_url.lower()

        # title contains <text>
        pattern_title = re.compile(r'^title\s+contains\s+(.+)$', re.IGNORECASE)
        match = pattern_title.match(condition)
        if match:
            text = match.group(1).strip('"\'')
            title = context.get('title', '')
            return text.lower() in title.lower()

        # element <selector> exists
        pattern_exists = re.compile(r'^element\s+(.+?)\s+exists$', re.IGNORECASE)
        match = pattern_exists.match(condition)
        if match:
            selector = match.group(1).strip()
            elements = context.get('elements', [])
            # 简单检查选择器是否在元素列表中
            return any(selector in str(el) for el in elements)

        # element <selector> visible
        pattern_visible = re.compile(r'^element\s+(.+?)\s+visible$', re.IGNORECASE)
        match = pattern_visible.match(condition)
        if match:
            selector = match.group(1).strip()
            visible_elements = context.get('visible_elements', [])
            return any(selector in str(el) for el in visible_elements)

        # element <selector> contains <text>
        pattern_contains = re.compile(
            r'^element\s+(.+?)\s+contains\s+(.+)$',
            re.IGNORECASE
        )
        match = pattern_contains.match(condition)
        if match:
            selector = match.group(1).strip()
            text = match.group(2).strip('"\'')
            elements = context.get('elements', [])
            return any(
                selector in str(el) and text.lower() in str(el).lower()
                for el in elements
            )

        # 默认返回 True
        logger.warning(f"未知的条件表达式: {condition}")
        return True

    def execute_loop(
        self,
        instruction: dict,
        context: dict,
        executor: Optional[Callable] = None
    ) -> list:
        """
        执行循环指令

        Args:
            instruction: 循环指令字典
            context: 执行上下文
            executor: 动作执行器回调

        Returns:
            执行结果列表
        """
        loop_type = instruction.get('loop_type', 'count')
        actions = instruction.get('actions')
        results = []

        if loop_type == 'count':
            count = instruction.get('count', 1)
            for i in range(count):
                if actions and executor:
                    result = executor(actions)
                    results.append(result)
                context['loop_index'] = i

        elif loop_type == 'for_each':
            variable = instruction.get('variable', 'item')
            items_str = instruction.get('items', '[]')

            # 解析 items
            import re
            # 尝试解析为列表
            if items_str.startswith('['):
                # JSON 格式的列表
                try:
                    import json
                    items = json.loads(items_str)
                except json.JSONDecodeError:
                    # 尝试简单分割
                    items = [item.strip() for item in items_str.strip('[]').split(',')]
            else:
                # 逗号分隔
                items = [item.strip() for item in items_str.split(',')]

            for i, item in enumerate(items):
                if actions and executor:
                    # 替换变量
                    action_with_var = actions.replace(f'${variable}', str(item))
                    result = executor(action_with_var)
                    results.append(result)
                context['loop_index'] = i
                context[variable] = item

        elif loop_type == 'while':
            condition = instruction.get('condition', '')
            max_iterations = instruction.get('max_iterations', 100)

            for i in range(max_iterations):
                if not self._evaluate_condition(condition, context):
                    break
                if actions and executor:
                    result = executor(actions)
                    results.append(result)
                context['loop_index'] = i

        return results
    
    # ── 宏定义处理 ────────────────────────────────────────────────
    
    def _process_macro(self, line: str) -> None:
        """处理宏定义"""
        # 移除 ! 并分割
        content = line[1:].strip()
        if ':' in content:
            name, body = content.split(':', 1)
            self.macros[name.strip()] = body.strip()
    
    def expand_macros(self, dsl: str) -> str:
        """展开宏"""
        for name, body in self.macros.items():
            dsl = dsl.replace(f'!{name}', body)
        return dsl


def natural_language_to_dsl(text: str, parser: Optional['EnhancedDSLParser'] = None) -> str:
    """
    将自然语言转换为 DSL
    
    Args:
        text: 自然语言输入
        parser: DSL 解析器实例
        
    Returns:
        DSL 命令字符串
    """
    try:
        from browser_use.nlp.pipeline import NLUPipeline
        pipeline = NLUPipeline()
        result = pipeline.to_dsl(text)
        if result:
            return result
    except ImportError:
        pass
    except Exception:
        pass
    
    # 如果 NLP 不可用，使用简单的规则转换
    parser = parser or EnhancedDSLParser()
    lines = []
    
    for line in text.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        
        # 尝试规则转换
        converted = _convert_natural_language_line(line, parser)
        if converted:
            lines.append(converted)
        else:
            lines.append(line)  # 保留原始行
    
    return '\n'.join(lines)


def _convert_natural_language_line(line: str, parser: EnhancedDSLParser) -> Optional[str]:
    """转换单行自然语言为 DSL"""
    # 模式匹配
    patterns = [
        # 打开网页
        (r'打开?\s+(https?://\S+)', '打开 {url}'),
        (r'访问?\s+(https?://\S+)', '打开 {url}'),
        (r'去\s+(https?://\S+)', '打开 {url}'),
        
        # 点击
        (r'点击?\s+["\']?(.+?)["\']?$', '点击 {selector}'),
        (r'click\s+(.+)', '点击 {selector}'),
        
        # 输入
        (r'在\s+(.+?)\s+中?\s*输入\s+(.+)', '输入 {selector} {text}'),
        (r'输入\s+(.+)', '输入 {selector} {text}'),
        
        # 搜索
        (r'搜索\s+(.+)', '搜索 {query}'),
        (r'search\s+(.+)', '搜索 {query}'),
        
        # 滚动
        (r'滚动\s*(上|下|顶部|底部)?', '滚动 {direction}'),
        
        # 截图
        (r'截图', '截图'),
        (r'screenshot', '截图'),
    ]
    
    for pattern, template in patterns:
        match = re.match(pattern, line, re.I)
        if match:
            result = template
            groups = match.groups()
            for i, group in enumerate(groups, 1):
                result = result.replace(f'{{{chr(96 + i)}}}', group or '')
                result = result.replace(f'{{{i}}}', group or '')
            
            # 标准化选择器
            if '{selector}' in result:
                result = result.replace('{selector}', parser._normalize_selector(match.group(1)))
            
            return result
    
    return None
