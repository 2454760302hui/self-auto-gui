"""
语义解析器 - 将意图和实体转换为可执行的命令
"""
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import logging

from browser_use.nlp.intent import Intent, IntentClassifier, IntentMatch
from browser_use.nlp.entity import EntityExtractor, Entity, EntityType

logger = logging.getLogger(__name__)


class CommandType(Enum):
    """命令类型"""
    # 导航命令
    NAVIGATE = "navigate"
    BACK = "back"
    FORWARD = "forward"
    REFRESH = "refresh"
    
    # 页面操作命令
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    HOVER = "hover"
    SCROLL = "scroll"
    SCROLL_TO = "scroll_to"
    SCREENSHOT = "screenshot"
    
    # 输入命令
    INPUT = "input"
    CLEAR = "clear"
    PRESS_KEY = "press_key"
    SELECT = "select"
    
    # 获取命令
    GET_TEXT = "get_text"
    GET_URL = "get_url"
    GET_TITLE = "get_title"
    GET_ATTRIBUTE = "get_attribute"
    EXECUTE_JS = "execute_js"
    
    # 断言命令
    ASSERT_VISIBLE = "assert_visible"
    ASSERT_TEXT = "assert_text"
    ASSERT_URL = "assert_url"
    ASSERT_TITLE = "assert_title"
    
    # 标签页命令
    NEW_TAB = "new_tab"
    CLOSE_TAB = "close_tab"
    
    # 弹窗命令
    ACCEPT_ALERT = "accept_alert"
    DISMISS_ALERT = "dismiss_alert"
    
    # iframe 命令
    IFRAME = "iframe"
    IFRAME_INPUT = "iframe_input"
    IFRAME_CLICK = "iframe_click"
    EXIT_IFRAME = "exit_iframe"
    
    # 等待命令
    WAIT = "wait"
    WAIT_LOAD = "wait_load"
    WAIT_VISIBLE = "wait_visible"
    
    # 拖拽命令
    DRAG = "drag"
    
    # 表单命令
    UPLOAD = "upload"
    CHECK = "check"
    UNCHECK = "uncheck"
    
    # 搜索/提取命令
    SEARCH = "search"
    EXTRACT = "extract"
    
    # 元命令
    COMMENT = "comment"
    EMPTY = "empty"
    UNKNOWN = "unknown"


@dataclass
class ParsedCommand:
    """解析后的命令"""
    command_type: CommandType
    params: dict = field(default_factory=dict)
    original_text: str = ""
    confidence: float = 1.0
    warnings: list[str] = field(default_factory=list)
    
    def to_dsl(self) -> str:
        """转换为 DSL 命令"""
        cmd = self.command_type.value
        
        if not self.params:
            return cmd
        
        param_parts = []
        for key, value in self.params.items():
            # 跳过 selector 和 text 为空或为常见关键词的情况
            if value is None or value == "":
                continue
            if isinstance(value, bool):
                if value:
                    param_parts.append(key)
            elif isinstance(value, str):
                # 跳过包含意图关键词的值
                skip_keywords = ['打开', '点击', '输入', '等待', '滚动', '获取', '断言']
                if value.strip() in skip_keywords:
                    continue
                # 特殊处理 URL
                if key == "url":
                    param_parts.append(str(value))
                # 特殊处理选择器
                elif key == "selector":
                    # 标准化选择器格式
                    if value.startswith('#') or value.startswith('.'):
                        param_parts.append(value)
                    elif value.startswith('[') or value.startswith('role='):
                        param_parts.append(value)
                    elif ' ' in value or any(c in value for c in '#.[]'):
                        param_parts.append(f'"{value}"')
                    else:
                        param_parts.append(value)
                # 其他字符串参数
                elif ' ' in value:
                    param_parts.append(f'"{value}"')
                else:
                    param_parts.append(str(value))
            elif value is not None:
                param_parts.append(str(value))
        
        if not param_parts:
            return cmd
        
        return f"{cmd} {' '.join(param_parts)}"
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "command_type": self.command_type.value,
            "params": self.params,
            "original_text": self.original_text,
            "confidence": self.confidence,
            "warnings": self.warnings,
        }


class SemanticParser:
    """
    语义解析器
    
    将自然语言意图转换为可执行的命令对象
    """
    
    # 意图到命令类型的映射
    INTENT_TO_COMMAND: dict[Intent, CommandType] = {
        Intent.NAVIGATE: CommandType.NAVIGATE,
        Intent.NAVIGATE_BACK: CommandType.BACK,
        Intent.NAVIGATE_FORWARD: CommandType.FORWARD,
        Intent.NAVIGATE_REFRESH: CommandType.REFRESH,
        
        Intent.CLICK: CommandType.CLICK,
        Intent.DOUBLE_CLICK: CommandType.DOUBLE_CLICK,
        Intent.RIGHT_CLICK: CommandType.RIGHT_CLICK,
        Intent.HOVER: CommandType.HOVER,
        
        Intent.INPUT: CommandType.INPUT,
        Intent.CLEAR: CommandType.CLEAR,
        Intent.PRESS_KEY: CommandType.PRESS_KEY,
        Intent.SELECT: CommandType.SELECT,
        
        Intent.SCROLL: CommandType.SCROLL,
        Intent.SCROLL_TO: CommandType.SCROLL_TO,
        Intent.SCREENSHOT: CommandType.SCREENSHOT,
        
        Intent.GET_TEXT: CommandType.GET_TEXT,
        Intent.GET_URL: CommandType.GET_URL,
        Intent.GET_TITLE: CommandType.GET_TITLE,
        Intent.GET_ATTRIBUTE: CommandType.GET_ATTRIBUTE,
        Intent.EXECUTE_JS: CommandType.EXECUTE_JS,
        
        Intent.ASSERT_VISIBLE: CommandType.ASSERT_VISIBLE,
        Intent.ASSERT_TEXT: CommandType.ASSERT_TEXT,
        Intent.ASSERT_URL: CommandType.ASSERT_URL,
        Intent.ASSERT_TITLE: CommandType.ASSERT_TITLE,
        
        Intent.NEW_TAB: CommandType.NEW_TAB,
        Intent.CLOSE_TAB: CommandType.CLOSE_TAB,
        
        Intent.ACCEPT_ALERT: CommandType.ACCEPT_ALERT,
        Intent.DISMISS_ALERT: CommandType.DISMISS_ALERT,
        
        Intent.IFRAME: CommandType.IFRAME,
        Intent.IFRAME_INPUT: CommandType.IFRAME_INPUT,
        Intent.IFRAME_CLICK: CommandType.IFRAME_CLICK,
        Intent.EXIT_IFRAME: CommandType.EXIT_IFRAME,
        
        Intent.WAIT: CommandType.WAIT,
        Intent.WAIT_LOAD: CommandType.WAIT_LOAD,
        Intent.WAIT_VISIBLE: CommandType.WAIT_VISIBLE,
        
        Intent.DRAG: CommandType.DRAG,
        
        Intent.UPLOAD: CommandType.UPLOAD,
        Intent.CHECK: CommandType.CHECK,
        Intent.UNCHECK: CommandType.UNCHECK,
        
        Intent.SEARCH: CommandType.SEARCH,
        Intent.EXTRACT: CommandType.EXTRACT,
    }
    
    # 搜索引擎识别
    SEARCH_ENGINES = {
        'google': ['google', '谷歌'],
        'bing': ['bing', '必应'],
        'baidu': ['baidu', '百度'],
        'duckduckgo': ['duckduckgo', 'ddg'],
        'yahoo': ['yahoo'],
    }
    
    def __init__(self, intent_classifier: Optional[IntentClassifier] = None, 
                 entity_extractor: Optional[EntityExtractor] = None):
        """
        初始化语义解析器
        
        Args:
            intent_classifier: 意图分类器
            entity_extractor: 实体识别器
        """
        self.intent_classifier = intent_classifier or IntentClassifier()
        self.entity_extractor = entity_extractor or EntityExtractor()
    
    def parse(self, text: str) -> ParsedCommand:
        """
        解析自然语言文本为命令
        
        Args:
            text: 输入的自然语言文本
            
        Returns:
            ParsedCommand: 解析后的命令
        """
        text = text.strip()
        
        # 处理空行和注释
        if not text or text.startswith('#') or text.startswith('//'):
            return ParsedCommand(
                command_type=CommandType.EMPTY if text else CommandType.UNKNOWN,
                original_text=text,
                confidence=1.0 if text else 0.0
            )
        
        # 1. 意图分类
        intent_match = self.intent_classifier.classify(text)
        
        # 2. 实体提取
        entities = self.entity_extractor.extract_all(text)
        
        # 3. 构建命令
        return self._build_command(intent_match, entities, text)
    
    def _build_command(self, intent_match: IntentMatch, entities: list[Entity], 
                       text: str) -> ParsedCommand:
        """根据意图和实体构建命令"""
        command_type = self.INTENT_TO_COMMAND.get(
            intent_match.intent, 
            CommandType.UNKNOWN
        )
        
        params = {}
        warnings = []
        
        # 从意图参数中提取
        params.update(intent_match.params)
        
        # 从实体中补充参数
        for entity in entities:
            if entity.type == EntityType.URL and 'url' not in params:
                params['url'] = entity.value
            elif entity.type == EntityType.CSS_SELECTOR and 'selector' not in params:
                params['selector'] = self.entity_extractor.normalize_selector(entity.value)
            elif entity.type == EntityType.XPATH and 'selector' not in params:
                params['selector'] = f'xpath={entity.value}'
            elif entity.type == EntityType.TEXT_SELECTOR and 'selector' not in params:
                params['selector'] = f'文本={entity.value}'
            elif entity.type == EntityType.ROLE_SELECTOR and 'selector' not in params:
                params['selector'] = f'role={entity.value}'
            elif entity.type == EntityType.EMAIL:
                if 'text' not in params:
                    params['text'] = entity.value
            elif entity.type == EntityType.PHONE:
                if 'text' not in params:
                    params['text'] = entity.value
        
        # 特殊处理
        params = self._enhance_params(command_type, params, text)
        
        # 检测搜索意图
        if command_type == CommandType.SEARCH:
            command_type, params = self._parse_search(params, text)
        
        # 检测选择器类型
        params = self._detect_selector_type(params)
        
        return ParsedCommand(
            command_type=command_type,
            params=params,
            original_text=text,
            confidence=intent_match.confidence,
            warnings=warnings
        )
    
    def _enhance_params(self, command_type: CommandType, params: dict, text: str) -> dict:
        """增强参数处理"""
        # 如果没有 selector，尝试从文本中提取
        if 'selector' not in params and command_type in [
            CommandType.CLICK, CommandType.HOVER, CommandType.INPUT,
            CommandType.GET_TEXT, CommandType.ASSERT_VISIBLE
        ]:
            selector = self._extract_selector_from_text(text)
            if selector:
                params['selector'] = selector
        
        # 处理滚动方向
        if command_type == CommandType.SCROLL:
            direction = params.get('direction', 'down')
            if direction in ['下', 'down', 'downward']:
                params['direction'] = '下'
            elif direction in ['上', 'up', 'upward']:
                params['direction'] = '上'
            elif direction in ['底部', 'bottom']:
                params['direction'] = '底部'
            elif direction in ['顶部', 'top']:
                params['direction'] = '顶部'
        
        # 处理等待时间
        if command_type == CommandType.WAIT:
            duration = params.get('duration', 1)
            if isinstance(duration, str):
                try:
                    duration = float(duration)
                except ValueError:
                    duration = 1
            params['duration'] = duration
        
        return params
    
    def _extract_selector_from_text(self, text: str) -> Optional[str]:
        """从文本中提取选择器"""
        # 检查是否已经是完整选择器
        if text.startswith('#') or text.startswith('.') or text.startswith('['):
            return text
        
        # 检查是否有前缀
        for prefix in ['文本=', 'text=', 'role=', 'placeholder=', 'label=', 'xpath=']:
            if text.startswith(prefix):
                return text
        
        # 返回文本作为文本选择器
        return f'文本={text}'
    
    def _parse_search(self, params: dict, text: str) -> tuple[CommandType, dict]:
        """解析搜索命令"""
        query = params.get('query', '')
        if not query:
            # 尝试从文本中提取搜索词
            for engine_name, engine_aliases in self.SEARCH_ENGINES.items():
                for alias in engine_aliases:
                    if alias in text.lower():
                        # 找到搜索引擎，提取后面的内容作为查询
                        idx = text.lower().find(alias)
                        query = text[idx + len(alias):].strip()
                        query = query.lstrip('上搜索').strip()
                        break
        
        if query:
            params['query'] = query
        
        return CommandType.SEARCH, params
    
    def _detect_selector_type(self, params: dict) -> dict:
        """检测选择器类型并转换"""
        if 'selector' not in params:
            return params
        
        selector = params['selector']
        
        # 如果已经是标准化格式，直接返回
        for prefix in ['文本=', 'text=', 'role=', 'placeholder=', 'label=', 'xpath=', 'css=']:
            if selector.startswith(prefix):
                return params
        
        # 尝试检测类型并添加前缀
        if selector.startswith('#'):
            # ID 选择器
            pass  # 保持原样
        elif selector.startswith('.'):
            # Class 选择器
            pass  # 保持原样
        elif '/' in selector and (selector.startswith('//') or selector.startswith('/')):
            # XPath
            params['selector'] = f'xpath={selector}'
        elif ' ' in selector or len(selector.split()) > 1:
            # 可能是文本选择器
            params['selector'] = f'文本={selector}'
        
        return params
    
    def parse_lines(self, text: str) -> list[ParsedCommand]:
        """
        解析多行文本
        
        Args:
            text: 多行文本
            
        Returns:
            ParsedCommand 列表
        """
        commands = []
        for line in text.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            cmd = self.parse(line)
            commands.append(cmd)
        return commands
    
    def parse_composite(self, text: str) -> list[ParsedCommand]:
        """
        解析复合指令（支持自然段落格式）
        
        Args:
            text: 输入文本
            
        Returns:
            ParsedCommand 列表
        """
        # 首先尝试按行分割
        lines = text.strip().split('\n')
        
        # 如果只有一行，尝试智能分割
        if len(lines) == 1:
            # 尝试按句号、分号、换行符分割
            parts = re.split(r'[。;；\n]', text)
            lines = [p.strip() for p in parts if p.strip()]
        
        commands = []
        for line in lines:
            if not line or line.startswith('#') or line.startswith('//'):
                continue
            
            # 尝试解析为复合命令
            sub_commands = self._split_compound_command(line)
            for cmd_text in sub_commands:
                cmd_text = cmd_text.strip()
                if cmd_text:
                    cmd = self.parse(cmd_text)
                    commands.append(cmd)
        
        return commands
    
    def _split_compound_command(self, text: str) -> list[str]:
        """分割复合命令"""
        # 只移除以 # 开头的注释（行注释）
        stripped = text.strip()
        if stripped.startswith('#') or stripped.startswith('//'):
            return []
        # 移除行尾注释（但保留 # 在前面的 CSS 选择器）
        if '#' in text and not text.strip().startswith('#'):
            # 检查 # 是否是注释（后面有空格或行尾）
            parts = text.split('#')
            potential_comment_idx = None
            for i, part in enumerate(parts[1:], 1):
                # 如果 # 后面是空格或非选择器字符，则认为是注释
                if part and (part[0] == ' ' or part[0].isdigit()):
                    potential_comment_idx = i
                    break
            if potential_comment_idx is not None:
                text = '#'.join(parts[:potential_comment_idx])
        
        if '//' in text:
            text = text.split('//')[0].strip()
        
        # 尝试使用连接词分割
        separators = ['然后', '接下来', '之后', 'and', 'then', 'next', ',']
        for sep in separators:
            if sep in text:
                parts = text.split(sep)
                return [p.strip() for p in parts if p.strip()]
        
        # 返回单条命令
        return [text]
    
    def to_dsl(self, commands: list[ParsedCommand]) -> str:
        """将命令列表转换为 DSL 格式"""
        lines = []
        for cmd in commands:
            if cmd.command_type == CommandType.EMPTY:
                continue
            if cmd.command_type == CommandType.UNKNOWN:
                lines.append(f"# {cmd.original_text}")
                continue
            lines.append(cmd.to_dsl())
        return '\n'.join(lines)
