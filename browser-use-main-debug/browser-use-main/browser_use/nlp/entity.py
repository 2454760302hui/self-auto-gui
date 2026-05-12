"""
实体识别器 - 从文本中提取结构化实体
支持 URL、邮箱、手机号、选择器、变量等
"""
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Any
import logging

logger = logging.getLogger(__name__)


class EntityType(Enum):
    """实体类型"""
    URL = "url"                       # URL 地址
    EMAIL = "email"                   # 邮箱地址
    PHONE = "phone"                  # 电话号码
    CSS_SELECTOR = "css_selector"    # CSS 选择器
    XPATH = "xpath"                  # XPath 选择器
    TEXT_SELECTOR = "text_selector"  # 文本选择器
    ROLE_SELECTOR = "role_selector"  # Role 选择器
    NAME = "name"                    # 名称/人名
    NUMBER = "number"                # 数字
    DATE = "date"                    # 日期
    TIME = "time"                    # 时间
    DURATION = "duration"            # 持续时间
    FILE_PATH = "file_path"         # 文件路径
    KEY = "key"                      # 按键
    JS_CODE = "js_code"              # JavaScript 代码
    ATTRIBUTE = "attribute"          # HTML 属性
    VARIABLE = "variable"            # 变量名
    SEARCH_ENGINE = "search_engine"  # 搜索引擎
    SELECTOR_TYPE = "selector_type"  # 选择器类型
    DIRECTION = "direction"          # 方向
    OPERATOR = "operator"            # 操作符


@dataclass
class Entity:
    """识别的实体"""
    type: EntityType
    value: str
    start: int = 0
    end: int = 0
    confidence: float = 1.0
    metadata: dict = field(default_factory=dict)
    
    def __str__(self) -> str:
        return f"Entity({self.type.value}={self.value!r})"
    
    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "value": self.value,
            "start": self.start,
            "end": self.end,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


class EntityExtractor:
    """
    实体识别器
    
    支持从自然语言文本中提取：
    - URL
    - 邮箱
    - 电话号码
    - CSS/XPath/文本选择器
    - 日期/时间
    - 按键名称
    - 文件路径
    - 变量名
    等
    """
    
    # URL 模式
    URL_PATTERN = re.compile(
        r'https?://[^\s<>"{}|\\^`\[\]]+',
        re.I
    )
    
    # 邮箱模式
    EMAIL_PATTERN = re.compile(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    )
    
    # 电话号码模式
    PHONE_PATTERN = re.compile(
        r'(?:\+?86)?[-.\s]?1[3-9]\d{9}'
    )
    
    # CSS 选择器模式
    CSS_SELECTOR_PATTERN = re.compile(
        r'[.#@]?[\w-]+(?:\[[\w-]+(?:=["\']?[^"\'\]]+["\']?)?\])?(?::[\w-]+(?:\([^)]*\))?)*',
    )
    
    # XPath 模式
    XPATH_PATTERN = re.compile(
        r'//[\w\-\[\]@="\'\(\)]+'
    )
    
    # 日期模式
    DATE_PATTERNS = [
        re.compile(r'\d{4}-\d{1,2}-\d{1,2}'),      # 2024-01-01 (ISO格式)
        re.compile(r'\d{4}/\d{1,2}/\d{1,2}'),      # 2024/01/01
        re.compile(r'\d{1,2}-\d{1,2}-\d{2,4}'),   # 01-01-2024 或 1-1-24
        re.compile(r'\d{1,2}/\d{1,2}/\d{2,4}'),   # 01/01/2024 或 1/1/24
        re.compile(r'\d{4}年\d{1,2}月\d{1,2}日'),  # 2024年01月01日
        re.compile(r'\d{1,2}月\d{1,2}日'),           # 01月01日
    ]
    
    # 时间模式
    TIME_PATTERN = re.compile(
        r'\d{1,2}:\d{2}(?::\d{2})?(?:\s*[上午下午AMP]+\.?)?'
    )
    
    # 持续时间模式
    DURATION_PATTERN = re.compile(
        r'(\d+(?:\.\d+)?)\s*(秒|分钟|分|小时|时|ms|毫秒|s|m|h)'
    )
    
    # 按键名称映射
    KEY_NAMES = {
        'enter': 'Enter', 'return': 'Enter',
        'tab': 'Tab', 'escape': 'Escape', 'esc': 'Escape',
        'space': 'Space', ' ': 'Space',
        'backspace': 'Backspace',
        'delete': 'Delete', 'del': 'Delete',
        'arrowup': 'ArrowUp', 'up': 'ArrowUp',
        'arrowdown': 'ArrowDown', 'down': 'ArrowDown',
        'arrowleft': 'ArrowLeft', 'left': 'ArrowLeft',
        'arrowright': 'ArrowRight', 'right': 'ArrowRight',
        'home': 'Home', 'end': 'End',
        'pageup': 'PageUp', 'pagedown': 'PageDown',
        'ctrl': 'Control', 'control': 'Control',
        'alt': 'Alt', 'shift': 'Shift',
        'meta': 'Meta', 'command': 'Meta',
    }
    
    # 方向词汇
    DIRECTION_WORDS = {
        '上': 'up', 'up': 'up', 'upward': 'up',
        '下': 'down', 'down': 'down', 'downward': 'down',
        '左': 'left', 'left': 'left',
        '右': 'right', 'right': 'right',
        '底部': 'bottom', 'bottom': 'bottom',
        '顶部': 'top', 'top': 'top',
    }
    
    # 选择器前缀模式 - 按长度降序排列确保优先匹配
    SELECTOR_PREFIXES = {
        '文本=': EntityType.TEXT_SELECTOR,
        'text=': EntityType.TEXT_SELECTOR,
        'role=': EntityType.ROLE_SELECTOR,
        'placeholder=': EntityType.CSS_SELECTOR,
        'label=': EntityType.CSS_SELECTOR,
        'testid=': EntityType.CSS_SELECTOR,
        'xpath=': EntityType.XPATH,
        'css=': EntityType.CSS_SELECTOR,
    }
    
    # 特殊选择器模式（需要更复杂的正则）
    SPECIAL_SELECTOR_PATTERN = re.compile(
        r'(?:role|role=)([\w-]+)(?:\[name=([^\]]+)\])?'
    )
    
    def __init__(self, strict: bool = False):
        """
        初始化实体识别器
        
        Args:
            strict: 是否使用严格模式（更少误报）
        """
        self.strict = strict
    
    def extract_all(self, text: str) -> list[Entity]:
        """
        从文本中提取所有实体
        
        Args:
            text: 输入文本
            
        Returns:
            Entity 列表
        """
        entities = []
        
        # 按位置排序提取所有实体
        extractors = [
            (self._extract_urls, EntityType.URL),
            (self._extract_emails, EntityType.EMAIL),
            (self._extract_phones, EntityType.PHONE),
            (self._extract_selectors, EntityType.CSS_SELECTOR),
            (self._extract_dates, EntityType.DATE),
            (self._extract_times, EntityType.TIME),
            (self._extract_durations, EntityType.DURATION),
            (self._extract_file_paths, EntityType.FILE_PATH),
        ]
        
        for extractor, entity_type in extractors:
            extracted = extractor(text)
            entities.extend(extracted)
        
        # 按位置排序
        entities.sort(key=lambda e: e.start)
        
        # 去重（保留更长的）
        entities = self._deduplicate(entities)
        
        return entities
    
    def _deduplicate(self, entities: list[Entity]) -> list[Entity]:
        """去除重复的实体"""
        if not entities:
            return []
        
        result = []
        for entity in entities:
            is_duplicate = False
            for existing in result:
                # 检查是否重叠
                if (entity.start >= existing.start and entity.start < existing.end) or \
                   (entity.end > existing.start and entity.end <= existing.end):
                    # 保留更长的
                    if len(entity.value) > len(existing.value):
                        result.remove(existing)
                    else:
                        is_duplicate = True
                    break
            if not is_duplicate:
                result.append(entity)
        
        return result
    
    def _extract_urls(self, text: str) -> list[Entity]:
        """提取 URL"""
        entities = []
        for match in self.URL_PATTERN.finditer(text):
            entities.append(Entity(
                type=EntityType.URL,
                value=match.group(),
                start=match.start(),
                end=match.end(),
                confidence=0.95,
                metadata={"domain": self._extract_domain(match.group())}
            ))
        return entities
    
    def _extract_emails(self, text: str) -> list[Entity]:
        """提取邮箱"""
        entities = []
        for match in self.EMAIL_PATTERN.finditer(text):
            entities.append(Entity(
                type=EntityType.EMAIL,
                value=match.group(),
                start=match.start(),
                end=match.end(),
                confidence=0.95
            ))
        return entities
    
    def _extract_phones(self, text: str) -> list[Entity]:
        """提取电话号码"""
        entities = []
        for match in self.PHONE_PATTERN.finditer(text):
            value = match.group()
            # 标准化
            value = re.sub(r'[-.\s]', '', value)
            entities.append(Entity(
                type=EntityType.PHONE,
                value=value,
                start=match.start(),
                end=match.end(),
                confidence=0.85
            ))
        return entities
    
    def _extract_selectors(self, text: str) -> list[Entity]:
        """提取选择器"""
        entities = []
        
        # 检查前缀选择器（包括 role= 等格式）
        for prefix, selector_type in self.SELECTOR_PREFIXES.items():
            # 对于 role= 需要特殊处理，因为它可能包含 [name=xxx] 部分
            if prefix == 'role=':
                role_pattern = re.compile(r'role=([\w-]+)(?:\[name=([^\]]+)\])?')
                for match in role_pattern.finditer(text):
                    role = match.group(1)
                    name = match.group(2)
                    if name:
                        value = f"role={role}[name={name}]"
                    else:
                        value = f"role={role}"
                    entities.append(Entity(
                        type=selector_type,
                        value=value,
                        start=match.start(),
                        end=match.end(),
                        confidence=0.95,
                        metadata={"prefix": prefix, "role": role, "name": name}
                    ))
            else:
                pattern = re.compile(re.escape(prefix) + r'([^"\s]+|"[^"]+")')
                for match in pattern.finditer(text):
                    value = match.group(1).strip('"')
                    entities.append(Entity(
                        type=selector_type,
                        value=value,
                        start=match.start(),
                        end=match.end(),
                        confidence=0.95,
                        metadata={"prefix": prefix}
                    ))
        
        # 检查 #id 和 .class 选择器，以及 [attr=value] 格式
        selector_pattern = re.compile(
            r'(?<![.\w])#[\w-]+'
            r'|(?<![.\w])\.[\w-]+'
            r'|\[[\w-]+=[^\]]+\]'  # [name=value] 格式
        )
        for match in selector_pattern.finditer(text):
            value = match.group()
            # 验证是否为有效的 CSS 选择器
            if self._is_valid_css_selector(value):
                entities.append(Entity(
                    type=EntityType.CSS_SELECTOR,
                    value=value,
                    start=match.start(),
                    end=match.end(),
                    confidence=0.85
                ))
        
        return entities
    
    def _is_valid_css_selector(self, selector: str) -> bool:
        """验证是否为有效的 CSS 选择器"""
        if not selector:
            return False
        # 简单验证：不是纯数字
        if selector.isdigit():
            return False
        return True
    
    def _extract_dates(self, text: str) -> list[Entity]:
        """提取日期"""
        entities = []
        for pattern in self.DATE_PATTERNS:
            for match in pattern.finditer(text):
                entities.append(Entity(
                    type=EntityType.DATE,
                    value=match.group(),
                    start=match.start(),
                    end=match.end(),
                    confidence=0.9
                ))
        return entities
    
    def _extract_times(self, text: str) -> list[Entity]:
        """提取时间"""
        entities = []
        for match in self.TIME_PATTERN.finditer(text):
            entities.append(Entity(
                type=EntityType.TIME,
                value=match.group(),
                start=match.start(),
                end=match.end(),
                confidence=0.9
            ))
        return entities
    
    def _extract_durations(self, text: str) -> list[Entity]:
        """提取持续时间"""
        entities = []
        for match in self.DURATION_PATTERN.finditer(text):
            value = match.group()
            num = float(match.group(1))
            unit = match.group(2)
            
            # 转换为秒
            if unit in ['ms', '毫秒']:
                seconds = num / 1000
            elif unit in ['s', '秒']:
                seconds = num
            elif unit in ['m', '分', '分钟']:
                seconds = num * 60
            elif unit in ['h', '时', '小时']:
                seconds = num * 3600
            else:
                seconds = num
            
            entities.append(Entity(
                type=EntityType.DURATION,
                value=value,
                start=match.start(),
                end=match.end(),
                confidence=0.9,
                metadata={"seconds": seconds}
            ))
        return entities
    
    def _extract_file_paths(self, text: str) -> list[Entity]:
        """提取文件路径"""
        entities = []
        # Windows 路径
        win_pattern = re.compile(r'[A-Za-z]:\\(?:[^\\/:*?"<>|\r\n]+\\)*[^\\/:*?"<>|\r\n]*')
        # Unix 路径
        unix_pattern = re.compile(r'(?:/[^/\s]+)+')
        
        for pattern in [win_pattern, unix_pattern]:
            for match in pattern.finditer(text):
                value = match.group()
                # 验证是否为文件路径
                if self._is_likely_file_path(value):
                    entities.append(Entity(
                        type=EntityType.FILE_PATH,
                        value=value,
                        start=match.start(),
                        end=match.end(),
                        confidence=0.8
                    ))
        return entities
    
    def _is_likely_file_path(self, path: str) -> bool:
        """判断是否为可能的文件路径"""
        # 检查是否包含文件扩展名
        if '.' in path:
            ext = path.split('.')[-1].lower()
            if ext in ['py', 'txt', 'pdf', 'jpg', 'png', 'html', 'css', 'js', 'json', 'xml', 'csv']:
                return True
        # 检查是否看起来像路径
        if '/' in path or '\\' in path:
            return True
        return False
    
    def _extract_domain(self, url: str) -> str:
        """从 URL 提取域名"""
        match = re.match(r'https?://([^/]+)', url)
        return match.group(1) if match else ""
    
    def extract_selector(self, text: str) -> Optional[Entity]:
        """
        专门提取选择器
        
        Args:
            text: 输入文本
            
        Returns:
            第一个找到的选择器
        """
        entities = self._extract_selectors(text)
        return entities[0] if entities else None
    
    def extract_url(self, text: str) -> Optional[Entity]:
        """提取 URL"""
        entities = self._extract_urls(text)
        return entities[0] if entities else None
    
    def extract_query(self, text: str) -> str:
        """
        提取搜索查询词
        
        移除常见的动词前缀
        """
        query = text.strip()
        
        # 移除搜索前缀
        prefixes = ['搜索', 'search', '查找', 'find', 'look for', 'look up']
        for prefix in prefixes:
            if query.lower().startswith(prefix):
                query = query[len(prefix):].strip()
        
        return query
    
    def extract_key(self, text: str) -> Optional[str]:
        """
        提取按键名称
        
        Args:
            text: 输入文本
            
        Returns:
            标准化后的按键名称
        """
        text = text.strip().lower()
        
        # 检查是否为已知按键
        if text in self.KEY_NAMES:
            return self.KEY_NAMES[text]
        
        # 尝试直接返回（可能有特殊按键）
        return text if text else None
    
    def extract_direction(self, text: str) -> Optional[str]:
        """
        提取方向
        
        Args:
            text: 输入文本
            
        Returns:
            方向值 (up/down/left/right/top/bottom)
        """
        text = text.strip().lower()
        
        # 检查方向词汇
        if text in self.DIRECTION_WORDS:
            return self.DIRECTION_WORDS[text]
        
        # 尝试模糊匹配
        for word, direction in self.DIRECTION_WORDS.items():
            if word in text:
                return direction
        
        return None
    
    def normalize_selector(self, text: str) -> str:
        """
        标准化选择器
        
        Args:
            text: 选择器文本
            
        Returns:
            标准化后的选择器
        """
        text = text.strip()
        
        # 移除前缀
        for prefix in self.SELECTOR_PREFIXES.keys():
            if text.startswith(prefix):
                return text[len(prefix):].strip('"\'')
        
        return text
