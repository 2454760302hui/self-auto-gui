"""
意图分类器 - 识别用户意图
支持规则-based + LLM fallback 的混合模式
"""
import re
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, TYPE_CHECKING
import logging

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
	from browser_use.llm.base import BaseChatModel
	from browser_use.llm.messages import BaseMessage, SystemMessage, UserMessage


class Intent(Enum):
    """支持的意图类型"""
    # 导航意图
    NAVIGATE = "navigate"                    # 打开/导航到网页
    NAVIGATE_BACK = "navigate_back"         # 返回上一页
    NAVIGATE_FORWARD = "navigate_forward"    # 前进到下一页
    NAVIGATE_REFRESH = "navigate_refresh"    # 刷新页面
    
    # 交互意图
    CLICK = "click"                          # 点击元素
    DOUBLE_CLICK = "double_click"           # 双击元素
    RIGHT_CLICK = "right_click"              # 右键点击
    HOVER = "hover"                          # 悬停/移入
    
    # 输入意图
    INPUT = "input"                          # 输入文本
    CLEAR = "clear"                          # 清空输入框
    TYPE = "type"                             # 键入文字（逐字）
    PRESS_KEY = "press_key"                  # 按键
    SELECT = "select"                         # 选择下拉选项
    
    # 页面操作意图
    SCROLL = "scroll"                        # 滚动页面
    SCROLL_TO = "scroll_to"                  # 滚动到指定元素
    SCREENSHOT = "screenshot"                # 截图
    
    # 获取信息意图
    GET_TEXT = "get_text"                    # 获取文本内容
    GET_URL = "get_url"                      # 获取 URL
    GET_TITLE = "get_title"                  # 获取页面标题
    GET_ATTRIBUTE = "get_attribute"           # 获取元素属性
    EXECUTE_JS = "execute_js"                # 执行 JavaScript
    
    # 断言意图
    ASSERT_VISIBLE = "assert_visible"         # 断言元素可见
    ASSERT_TEXT = "assert_text"               # 断言文本内容
    ASSERT_URL = "assert_url"                 # 断言 URL
    ASSERT_TITLE = "assert_title"             # 断言标题
    
    # 多标签页意图
    NEW_TAB = "new_tab"                      # 新建标签页
    CLOSE_TAB = "close_tab"                  # 关闭标签页
    SWITCH_TAB = "switch_tab"                # 切换标签页
    
    # 弹窗处理意图
    HANDLE_ALERT = "handle_alert"             # 处理弹窗
    ACCEPT_ALERT = "accept_alert"             # 接受弹窗
    DISMISS_ALERT = "dismiss_alert"          # 拒绝弹窗
    
    # iframe 意图
    IFRAME = "iframe"                        # 进入 iframe
    IFRAME_INPUT = "iframe_input"            # iframe 中输入
    IFRAME_CLICK = "iframe_click"             # iframe 中点击
    EXIT_IFRAME = "exit_iframe"              # 退出 iframe
    
    # 等待意图
    WAIT = "wait"                            # 等待固定时间
    WAIT_LOAD = "wait_load"                  # 等待加载完成
    WAIT_VISIBLE = "wait_visible"            # 等待元素可见
    
    # 拖拽意图
    DRAG = "drag"                            # 拖拽元素
    
    # 表单意图
    UPLOAD = "upload"                        # 上传文件
    CHECK = "check"                          # 勾选复选框
    UNCHECK = "uncheck"                      # 取消勾选
    
    # 复杂任务意图
    SEARCH = "search"                        # 搜索
    FILL_FORM = "fill_form"                  # 填写表单
    LOGIN = "login"                          # 登录
    LOGOUT = "logout"                        # 退出登录
    EXTRACT = "extract"                      # 提取信息
    
    # 未知意图
    UNKNOWN = "unknown"                      # 未知意图
    COMPOSITE = "composite"                  # 复合意图（多条指令）


@dataclass
class IntentMatch:
    """意图匹配结果"""
    intent: Intent
    confidence: float
    params: dict = field(default_factory=dict)
    original_text: str = ""
    
    def __str__(self) -> str:
        return f"IntentMatch({self.intent.value}, confidence={self.confidence:.2f})"


class IntentClassifier:
	"""
	意图分类器

	支持两种模式：
	1. 规则模式（快速，基于正则和关键词）
	2. LLM 模式（更准确，需要 LLM 支持）

	默认使用规则模式，规则无法识别时可选使用 LLM 模式
	"""

	# 意图模式定义
	INTENT_PATTERNS: dict[Intent, list[tuple[str, re.Pattern, dict]]] = {
        # 导航意图
        Intent.NAVIGATE: [
            (r"打开\s+(.+)", re.compile(r"打开\s+(.+)", re.I), {}),
            (r"访问\s+(.+)", re.compile(r"访问\s+(.+)", re.I), {}),
            (r"去\s+(.+)", re.compile(r"去\s+(.+)", re.I), {}),
            (r"goto\s+(.+)", re.compile(r"goto\s+(.+)", re.I), {}),
            (r"navigate\s+to\s+(.+)", re.compile(r"navigate\s+to\s+(.+)", re.I), {}),
            (r"^(https?://.+)$", re.compile(r"^(https?://.+)$"), {}),
        ],
        Intent.NAVIGATE_BACK: [
            (r"返回", re.compile(r"返回|后退|后退一页|上一页"), {}),
            (r"back", re.compile(r"^back$", re.I), {}),
            (r"go\s*back", re.compile(r"go\s*back", re.I), {}),
        ],
        Intent.NAVIGATE_FORWARD: [
            (r"前进", re.compile(r"前进|下一页|下一页面"), {}),
            (r"forward", re.compile(r"^forward$", re.I), {}),
            (r"go\s*forward", re.compile(r"go\s*forward", re.I), {}),
        ],
        Intent.NAVIGATE_REFRESH: [
            (r"刷新", re.compile(r"刷新|重新加载|refresh"), {}),
            (r"reload", re.compile(r"^reload$", re.I), {}),
        ],
        
        # 交互意图
        Intent.CLICK: [
            # 带 CSS 选择器的点击：点击 #btn
            (r"点击\s+(#\S+)", re.compile(r"点击\s+(#\S+)", re.I), {}),
            # 带类选择器的点击：点击 .btn
            (r"点击\s+(\.\S+)", re.compile(r"点击\s+(\.\S+)", re.I), {}),
            # 中文选择器点击（无空格）：点击登录按钮
            (r"点击([\u4e00-\u9fa5]+)", re.compile(r"点击([\u4e00-\u9fa5]+)", re.I), {}),
            (r"单击([\u4e00-\u9fa5]+)", re.compile(r"单击([\u4e00-\u9fa5]+)", re.I), {}),
            # 标准格式
            (r"点击\s+(.+)", re.compile(r"点击\s+(.+)", re.I), {}),
            (r"单击\s+(.+)", re.compile(r"单击\s+(.+)", re.I), {}),
            (r"click\s+(.+)", re.compile(r"click\s+(.+)", re.I), {}),
            (r"press\s+(.+)", re.compile(r"press\s+(.+)", re.I), {}),
            (r"tap\s+(.+)", re.compile(r"tap\s+(.+)", re.I), {}),
        ],
        Intent.DOUBLE_CLICK: [
            (r"双击\s+(.+)", re.compile(r"双击\s+(.+)", re.I), {}),
            (r"dblclick\s+(.+)", re.compile(r"dblclick\s+(.+)", re.I), {}),
            (r"double\s*click\s+(.+)", re.compile(r"double\s*click\s+(.+)", re.I), {}),
        ],
        Intent.RIGHT_CLICK: [
            (r"右键\s+(.+)", re.compile(r"右键\s+(.+)", re.I), {}),
            (r"rightclick\s+(.+)", re.compile(r"rightclick\s+(.+)", re.I), {}),
        ],
        Intent.HOVER: [
            (r"悬停\s+(.+)", re.compile(r"悬停\s+(.+)", re.I), {}),
            (r"hover\s+(.+)", re.compile(r"hover\s+(.+)", re.I), {}),
            (r"移入\s+(.+)", re.compile(r"移入\s+(.+)", re.I), {}),
        ],
        
        # 输入意图
        Intent.INPUT: [
            # 带选择器的输入：输入 #username admin 或 输入 [name=x] admin
            # CSS 选择器格式：输入 #selector text
            (r"输入\s+([#\.][^\s]+)\s+(.+)", re.compile(r"输入\s+([#\.][^\s]+)\s+(.+)", re.I), {}),
            # 属性选择器格式：输入 [name=x] text
            (r"输入\s+(\[[^\]]+\])\s+(.+)", re.compile(r"输入\s+(\[[^\]]+\])\s+(.+)", re.I), {}),
            # 中文选择器输入（无空格）：输入用户名admin
            (r"输入([\u4e00-\u9fa5]+)(.+)", re.compile(r"输入([\u4e00-\u9fa5]+)(.+)", re.I), {}),
            # 标准格式
            (r"输入\s+(.+?)\s+(.+)", re.compile(r"输入\s+(.+?)\s+(.+)", re.I), {}),
            (r"fill\s+(.+?)\s+(.+)", re.compile(r"fill\s+(.+?)\s+(.+)", re.I), {}),
            (r"type\s+in\s+(.+?)\s+(.+)", re.compile(r"type\s+in\s+(.+?)\s+(.+)", re.I), {}),
        ],
        Intent.CLEAR: [
            (r"清空\s+(.+)", re.compile(r"清空\s+(.+)", re.I), {}),
            (r"clear\s+(.+)", re.compile(r"clear\s+(.+)", re.I), {}),
        ],
        Intent.PRESS_KEY: [
            (r"按键\s+(.+)", re.compile(r"按键\s+(.+)", re.I), {}),
            (r"press\s+(.+)", re.compile(r"press\s+(.+)", re.I), {}),
            (r"key\s+(.+)", re.compile(r"key\s+(.+)", re.I), {}),
        ],
        Intent.SELECT: [
            (r"选择\s+(.+?)\s+(.+)", re.compile(r"选择\s+(.+?)\s+(.+)", re.I), {}),
            (r"select\s+(.+?)\s+(.+)", re.compile(r"select\s+(.+?)\s+(.+)", re.I), {}),
        ],
        
        # 页面操作意图
        Intent.SCROLL: [
            (r"滚动\s*(上|下|底部|顶部)?", re.compile(r"滚动\s*(上|下|底部|顶部)?", re.I), {}),
            (r"scroll\s*(up|down|top|bottom)?", re.compile(r"scroll\s*(up|down|top|bottom)?", re.I), {}),
        ],
        Intent.SCROLL_TO: [
            (r"滚动到\s+(.+)", re.compile(r"滚动到\s+(.+)", re.I), {}),
            (r"scroll\s*to\s+(.+)", re.compile(r"scroll\s*to\s+(.+)", re.I), {}),
            (r"scrollIntoView\s+(.+)", re.compile(r"scrollIntoView\s+(.+)", re.I), {}),
        ],
        Intent.SCREENSHOT: [
            (r"截图", re.compile(r"截图|capture|screenshot", re.I), {}),
            (r"capture", re.compile(r"^capture$", re.I), {}),
            (r"screenshot", re.compile(r"^screenshot$", re.I), {}),
        ],
        
        # 获取信息意图
        Intent.GET_TEXT: [
            (r"获取文本\s*(.+)?", re.compile(r"获取文本\s*(.+)?", re.I), {}),
            (r"gettext\s*(.+)?", re.compile(r"gettext\s*(.+)?", re.I), {}),
            (r"提取文本\s+(.+)", re.compile(r"提取文本\s+(.+)", re.I), {}),
        ],
        Intent.GET_URL: [
            (r"获取URL", re.compile(r"获取URL|获取链接|当前地址", re.I), {}),
            (r"geturl", re.compile(r"^geturl$", re.I), {}),
        ],
        Intent.GET_TITLE: [
            (r"获取标题", re.compile(r"获取标题|页面标题|title", re.I), {}),
            (r"gettitle", re.compile(r"^gettitle$", re.I), {}),
        ],
        Intent.GET_ATTRIBUTE: [
            (r"获取属性\s+(.+?)\s+(.+)", re.compile(r"获取属性\s+(.+?)\s+(.+)", re.I), {}),
            (r"getattr\s+(.+?)\s+(.+)", re.compile(r"getattr\s+(.+?)\s+(.+)", re.I), {}),
        ],
        Intent.EXECUTE_JS: [
            (r"执行JS\s*(.+)?", re.compile(r"执行JS\s*(.+)?", re.I), {}),
            (r"js\s*(.+)?", re.compile(r"js\s*(.+)?", re.I), {}),
            (r"eval\s*(.+)?", re.compile(r"eval\s*(.+)?", re.I), {}),
        ],
        
        # 断言意图
        Intent.ASSERT_VISIBLE: [
            (r"断言可见\s+(.+)", re.compile(r"断言可见\s+(.+)", re.I), {}),
            (r"assertvisible\s+(.+)", re.compile(r"assertvisible\s+(.+)", re.I), {}),
            (r"验证可见\s+(.+)", re.compile(r"验证可见\s+(.+)", re.I), {}),
        ],
        Intent.ASSERT_TEXT: [
            (r"断言文本\s+(.+?)\s+(.+)", re.compile(r"断言文本\s+(.+?)\s+(.+)", re.I), {}),
            (r"asserttext\s+(.+?)\s+(.+)", re.compile(r"asserttext\s+(.+?)\s+(.+)", re.I), {}),
        ],
        Intent.ASSERT_URL: [
            (r"断言URL\s+(.+)", re.compile(r"断言URL\s+(.+)", re.I), {}),
            (r"asserturl\s+(.+)", re.compile(r"asserturl\s+(.+)", re.I), {}),
        ],
        Intent.ASSERT_TITLE: [
            (r"断言标题\s+(.+)", re.compile(r"断言标题\s+(.+)", re.I), {}),
            (r"asserttitle\s+(.+)", re.compile(r"asserttitle\s+(.+)", re.I), {}),
        ],
        
        # 多标签页意图
        Intent.NEW_TAB: [
            (r"新标签页", re.compile(r"新标签页|新建标签|新开页面", re.I), {}),
            (r"newtab", re.compile(r"^newtab$", re.I), {}),
            (r"new\s*tab", re.compile(r"new\s*tab", re.I), {}),
        ],
        Intent.CLOSE_TAB: [
            (r"关闭标签页", re.compile(r"关闭标签页|关闭页面", re.I), {}),
            (r"closetab", re.compile(r"^closetab$", re.I), {}),
        ],
        
        # 弹窗意图
        Intent.ACCEPT_ALERT: [
            (r"接受弹窗", re.compile(r"接受弹窗|确认弹窗|确定弹窗", re.I), {}),
            (r"accept", re.compile(r"^accept$", re.I), {}),
        ],
        Intent.DISMISS_ALERT: [
            (r"拒绝弹窗", re.compile(r"拒绝弹窗|取消弹窗", re.I), {}),
            (r"dismiss", re.compile(r"^dismiss$", re.I), {}),
        ],
        
        # iframe 意图
        Intent.IFRAME: [
            (r"iframe\s+(.+)", re.compile(r"iframe\s+(.+)", re.I), {}),
            (r"进入iframe\s+(.+)", re.compile(r"进入iframe\s+(.+)", re.I), {}),
        ],
        Intent.IFRAME_INPUT: [
            (r"iframe输入\s+(.+?)\s+(.+)", re.compile(r"iframe输入\s+(.+?)\s+(.+)", re.I), {}),
        ],
        Intent.IFRAME_CLICK: [
            (r"iframe点击\s+(.+)", re.compile(r"iframe点击\s+(.+)", re.I), {}),
        ],
        Intent.EXIT_IFRAME: [
            (r"退出iframe", re.compile(r"退出iframe|离开iframe", re.I), {}),
        ],
        
        # 等待意图
        Intent.WAIT: [
            (r"等待\s*(\d+)?", re.compile(r"等待\s*(\d+)?", re.I), {}),
            (r"wait\s*(\d+)?", re.compile(r"wait\s*(\d+)?", re.I), {}),
            (r"sleep\s*(\d+)?", re.compile(r"sleep\s*(\d+)?", re.I), {}),
        ],
        Intent.WAIT_LOAD: [
            (r"等待加载完成", re.compile(r"等待加载完成|load完成|加载完成", re.I), {}),
            (r"waitload", re.compile(r"^waitload$", re.I), {}),
        ],
        Intent.WAIT_VISIBLE: [
            (r"等待可见\s+(.+)", re.compile(r"等待可见\s+(.+)", re.I), {}),
            (r"waitvisible\s+(.+)", re.compile(r"waitvisible\s+(.+)", re.I), {}),
        ],
        
        # 拖拽意图
        Intent.DRAG: [
            (r"拖拽\s+(.+)\s+到\s+(.+)", re.compile(r"拖拽\s+(.+)\s+到\s+(.+)", re.I), {}),
            (r"drag\s+(.+)\s+to\s+(.+)", re.compile(r"drag\s+(.+)\s+to\s+(.+)", re.I), {}),
        ],
        
        # 表单意图
        Intent.UPLOAD: [
            (r"上传\s+(.+?)\s+(.+)", re.compile(r"上传\s+(.+?)\s+(.+)", re.I), {}),
            (r"upload\s+(.+?)\s+(.+)", re.compile(r"upload\s+(.+?)\s+(.+)", re.I), {}),
        ],
        Intent.CHECK: [
            (r"勾选\s+(.+)", re.compile(r"勾选\s+(.+)", re.I), {}),
            (r"check\s+(.+)", re.compile(r"check\s+(.+)", re.I), {}),
        ],
        Intent.UNCHECK: [
            (r"取消勾选\s+(.+)", re.compile(r"取消勾选\s+(.+)", re.I), {}),
            (r"uncheck\s+(.+)", re.compile(r"uncheck\s+(.+)", re.I), {}),
        ],
        
        # 搜索意图
        Intent.SEARCH: [
            (r"搜索\s+(.+)", re.compile(r"搜索\s+(.+)", re.I), {}),
            (r"search\s+(.+)", re.compile(r"search\s+(.+)", re.I), {}),
            (r"查找\s+(.+)", re.compile(r"查找\s+(.+)", re.I), {}),
        ],
        
        # 提取意图
        Intent.EXTRACT: [
            (r"提取\s+(.+)", re.compile(r"提取\s+(.+)", re.I), {}),
            (r"extract\s+(.+)", re.compile(r"extract\s+(.+)", re.I), {}),
            (r"爬取\s+(.+)", re.compile(r"爬取\s+(.+)", re.I), {}),
        ],
    }
    
    # 意图优先级（用于模糊匹配时排序）
    INTENT_PRIORITY: dict[Intent, int] = {
        Intent.NAVIGATE: 100,
        Intent.NAVIGATE_BACK: 100,
        Intent.NAVIGATE_FORWARD: 100,
        Intent.NAVIGATE_REFRESH: 100,
        Intent.SEARCH: 95,
        Intent.CLICK: 90,
        Intent.DOUBLE_CLICK: 90,
        Intent.RIGHT_CLICK: 90,
        Intent.HOVER: 90,
        Intent.INPUT: 85,
        Intent.CLEAR: 85,
        Intent.SELECT: 85,
        Intent.PRESS_KEY: 85,
        Intent.SCREENSHOT: 80,
        # 滚动相关 - 更具体的滚动意图优先级更高
        Intent.SCROLL_TO: 78,
        Intent.SCROLL: 75,
        # 等待相关 - 更具体的等待意图优先级更高
        Intent.WAIT_LOAD: 68,
        Intent.WAIT_VISIBLE: 68,
        Intent.WAIT: 65,
        # 断言相关
        Intent.ASSERT_VISIBLE: 70,
        Intent.ASSERT_TEXT: 70,
        Intent.ASSERT_URL: 70,
        Intent.ASSERT_TITLE: 70,
        # 获取信息
        Intent.GET_TEXT: 70,
        Intent.GET_URL: 70,
        Intent.GET_TITLE: 70,
        Intent.GET_ATTRIBUTE: 70,
        # iframe 和标签页
        Intent.IFRAME: 85,
        Intent.IFRAME_INPUT: 85,
        Intent.IFRAME_CLICK: 85,
        Intent.EXIT_IFRAME: 85,
        Intent.NEW_TAB: 80,
        Intent.CLOSE_TAB: 80,
        # 弹窗
        Intent.ACCEPT_ALERT: 85,
        Intent.DISMISS_ALERT: 85,
        # 其他
        Intent.EXTRACT: 60,
        Intent.EXECUTE_JS: 60,
        Intent.DRAG: 60,
        Intent.UPLOAD: 60,
        Intent.CHECK: 60,
        Intent.UNCHECK: 60,
    }
    
    def __init__(self, use_llm_fallback: bool = False, llm: Optional['BaseChatModel'] = None):
        """
        初始化意图分类器

        Args:
            use_llm_fallback: 是否在规则无法识别时使用 LLM
            llm: LLM 实例，用于 LLM 意图分类
        """
        self.use_llm_fallback = use_llm_fallback
        self.llm = llm
    
    def classify(self, text: str) -> IntentMatch:
        """
        对输入文本进行意图分类
        
        Args:
            text: 输入的自然语言文本
            
        Returns:
            IntentMatch: 意图匹配结果
        """
        text = text.strip()
        if not text:
            return IntentMatch(Intent.UNKNOWN, 0.0, {}, text)
        
        # 先尝试精确匹配 DSL 命令
        dsl_match = self._try_dsl_exact(text)
        if dsl_match:
            return dsl_match
        
        # 使用规则模式进行分类
        rule_match = self._classify_by_rules(text)
        if rule_match and rule_match.confidence >= 0.8:
            return rule_match
        
        # 如果规则匹配度不够，尝试 LLM 模式
        if self.use_llm_fallback and rule_match and rule_match.confidence < 0.8:
            llm_match = self._classify_by_llm(text)
            if llm_match and llm_match.confidence > rule_match.confidence:
                return llm_match
        
        # 返回规则匹配结果或未知意图
        return rule_match or IntentMatch(Intent.UNKNOWN, 0.0, {}, text)
    
    def _try_dsl_exact(self, text: str) -> Optional[IntentMatch]:
        """尝试精确匹配 DSL 命令"""
        text = text.strip()
        for intent, patterns in self.INTENT_PATTERNS.items():
            for _, pattern, params in patterns:
                # 使用 fullmatch 确保整个文本匹配
                match = pattern.fullmatch(text)
                if match:
                    # 计算置信度
                    if match.groups():
                        # 有捕获组，说明提取了参数，置信度高
                        confidence = 0.95
                    else:
                        # 无捕获组，精确命令
                        confidence = 1.0
                    
                    # 提取参数
                    extracted_params = self._extract_params(intent, match)
                    
                    return IntentMatch(
                        intent=intent,
                        confidence=confidence,
                        params=extracted_params,
                        original_text=text
                    )
        return None
    
    def _classify_by_rules(self, text: str) -> Optional[IntentMatch]:
        """使用规则进行意图分类"""
        best_match: Optional[IntentMatch] = None
        best_score = 0.0
        
        for intent, patterns in self.INTENT_PATTERNS.items():
            for _, pattern, params in patterns:
                match = pattern.search(text)
                if match:
                    # 计算匹配分数
                    score = self._calculate_match_score(intent, match, text)
                    
                    # 匹配长度加权：完整匹配整个文本优先
                    text_len = len(text.strip())
                    match_len = match.end() - match.start()
                    if match.start() == 0 and match.end() == text_len:
                        # 完整匹配，给予最高优先级加权
                        score = min(score + 0.2, 1.0)
                    elif match.start() == 0:
                        # 从头匹配，中等加权
                        score = min(score + 0.1, 1.0)
                    elif match_len > text_len * 0.8:
                        # 匹配了大部分文本
                        score = min(score + 0.05, 1.0)
                    
                    # 考虑意图优先级
                    priority = self.INTENT_PRIORITY.get(intent, 50)
                    final_score = score * (priority / 100.0)
                    
                    if final_score > best_score:
                        best_score = final_score
                        extracted_params = self._extract_params(intent, match)
                        best_match = IntentMatch(
                            intent=intent,
                            confidence=score,
                            params=extracted_params,
                            original_text=text
                        )
        
        return best_match
    
    def _calculate_match_score(self, intent: Intent, match: re.Match, text: str) -> float:
        """计算匹配分数"""
        # 如果是精确匹配（从头开始匹配）
        if match.start() == 0:
            base_score = 0.95
        else:
            # 文本中包含该模式
            base_score = 0.7
        
        # 有捕获组时增加分数
        if match.groups():
            non_empty_groups = sum(1 for g in match.groups() if g)
            if non_empty_groups > 0:
                base_score += 0.05 * min(non_empty_groups, 2)
        
        return min(base_score, 1.0)
    
    def _extract_params(self, intent: Intent, match: re.Match) -> dict:
        """从匹配结果中提取参数"""
        params = {}
        groups = match.groups()
        
        if not groups:
            return params
        
        # 根据意图类型提取参数
        if intent in [Intent.NAVIGATE]:
            params["url"] = groups[0].strip() if groups else None
            
        elif intent in [Intent.CLICK, Intent.HOVER, Intent.DOUBLE_CLICK, Intent.RIGHT_CLICK]:
            params["selector"] = groups[0].strip() if groups else None
            
        elif intent in [Intent.INPUT]:
            if len(groups) >= 2:
                params["selector"] = groups[0].strip()
                params["text"] = groups[1].strip()
            elif len(groups) == 1:
                params["selector"] = groups[0].strip()
                
        elif intent in [Intent.SELECT]:
            if len(groups) >= 2:
                params["selector"] = groups[0].strip()
                params["value"] = groups[1].strip()
                
        elif intent in [Intent.SCROLL]:
            direction = groups[0].strip().lower() if groups and groups[0] else "下"
            params["direction"] = direction
            
        elif intent in [Intent.WAIT]:
            params["duration"] = int(groups[0]) if groups and groups[0] else 1
            
        elif intent in [Intent.GET_TEXT, Intent.ASSERT_VISIBLE]:
            params["selector"] = groups[0].strip() if groups else None
            
        elif intent in [Intent.GET_ATTRIBUTE]:
            if len(groups) >= 2:
                params["selector"] = groups[0].strip()
                params["attribute"] = groups[1].strip()
                
        elif intent in [Intent.DRAG]:
            if len(groups) >= 2:
                params["source"] = groups[0].strip()
                params["target"] = groups[1].strip()
                
        elif intent in [Intent.UPLOAD]:
            if len(groups) >= 2:
                params["selector"] = groups[0].strip()
                params["filepath"] = groups[1].strip()
                
        elif intent in [Intent.CHECK, Intent.UNCHECK, Intent.CLEAR]:
            params["selector"] = groups[0].strip() if groups else None
            
        elif intent in [Intent.ASSERT_TEXT]:
            if len(groups) >= 2:
                params["selector"] = groups[0].strip()
                params["expected"] = groups[1].strip()
            elif len(groups) == 1:
                params["expected"] = groups[0].strip()
                
        elif intent in [Intent.IFRAME]:
            params["selector"] = groups[0].strip() if groups else None
            
        elif intent in [Intent.IFRAME_INPUT]:
            if len(groups) >= 2:
                params["selector"] = groups[0].strip()
                params["text"] = groups[1].strip()
                
        elif intent in [Intent.SEARCH]:
            params["query"] = groups[0].strip() if groups else None
            
        elif intent in [Intent.EXTRACT]:
            params["query"] = groups[0].strip() if groups else None
            
        elif intent in [Intent.PRESS_KEY]:
            params["key"] = groups[0].strip() if groups else "Enter"
            
        elif intent in [Intent.EXECUTE_JS]:
            params["code"] = groups[0].strip() if groups else None
            
        elif intent in [Intent.ASSERT_URL, Intent.ASSERT_TITLE]:
            params["expected"] = groups[0].strip() if groups else None
            
        return params
    
    def _classify_by_llm(self, text: str) -> Optional[IntentMatch]:
        """
        使用 LLM 进行意图分类

        使用 few-shot prompt 来分类意图，需要配置 LLM。

        Args:
            text: 输入的自然语言文本

        Returns:
            IntentMatch: 意图匹配结果，失败返回 None
        """
        if not self.llm:
            logger.debug("LLM 未配置，无法进行 LLM 意图分类")
            return None

        # 构建意图列表描述
        intent_list = []
        for intent in Intent:
            if intent not in [Intent.UNKNOWN, Intent.COMPOSITE]:
                # 使用中文描述
                description = self._get_intent_description(intent)
                intent_list.append(f"- {intent.value}: {description}")

        intent_list_str = "\n".join(intent_list)

        # Few-shot prompt
        system_prompt = f"""你是一个意图分类器。根据用户输入的文本，识别出用户的意图。

支持的意图类型：
{intent_list_str}

输出格式要求：
- 返回单个意图的 value 值（如：click, input, navigate）
- 如果输入是多个指令，用 | 分隔（如：click|input|navigate）
- 如果无法识别意图，返回 unknown

示例：
输入：点击登录按钮
输出：click

输入：打开 https://example.com 然后点击搜索框并输入 hello
输出：navigate|click|input

输入：这是一个随机的句子
输出：unknown
"""

        user_prompt = f"输入：{text}\n输出："

        try:
            from browser_use.llm.messages import SystemMessage, UserMessage

            messages = [
                SystemMessage(content=system_prompt),
                UserMessage(content=user_prompt),
            ]

            logger.debug(f"LLM 意图分类请求: {text}")

            # 同步调用（如果需要异步，子类可覆盖）
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                # 在异步上下文中，使用 asyncio.to_thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.llm.ainvoke(messages)
                    )
                    response = future.result(timeout=30)
            except RuntimeError:
                # 没有运行中的事件循环，直接调用
                response = asyncio.run(self.llm.ainvoke(messages))

            result = response.completion.strip().lower()

            logger.debug(f"LLM 意图分类结果: {result}")

            # 解析结果
            intent_values = [v.strip() for v in result.split("|")]

            # 检查是否识别成功
            valid_intents = []
            for value in intent_values:
                try:
                    intent = Intent(value)
                    if intent not in [Intent.UNKNOWN, Intent.COMPOSITE]:
                        valid_intents.append(intent)
                except ValueError:
                    # 尝试用中文描述匹配
                    matched = self._match_intent_by_description(value)
                    if matched:
                        valid_intents.append(matched)

            if not valid_intents:
                return None

            # 如果只有一个意图
            if len(valid_intents) == 1:
                return IntentMatch(
                    intent=valid_intents[0],
                    confidence=0.85,
                    params={},
                    original_text=text
                )

            # 如果有多个意图，返回复合意图
            return IntentMatch(
                intent=Intent.COMPOSITE,
                confidence=0.85,
                params={"intents": valid_intents},
                original_text=text
            )

        except Exception as e:
            logger.warning(f"LLM 意图分类失败: {e}")
            return None

    def _get_intent_description(self, intent: Intent) -> str:
        """获取意图的中文描述"""
        descriptions = {
            Intent.NAVIGATE: "打开/导航到网页",
            Intent.NAVIGATE_BACK: "返回上一页",
            Intent.NAVIGATE_FORWARD: "前进到下一页",
            Intent.NAVIGATE_REFRESH: "刷新页面",
            Intent.CLICK: "点击元素",
            Intent.DOUBLE_CLICK: "双击元素",
            Intent.RIGHT_CLICK: "右键点击",
            Intent.HOVER: "悬停/移入",
            Intent.INPUT: "输入文本",
            Intent.CLEAR: "清空输入框",
            Intent.TYPE: "键入文字（逐字）",
            Intent.PRESS_KEY: "按键",
            Intent.SELECT: "选择下拉选项",
            Intent.SCROLL: "滚动页面",
            Intent.SCROLL_TO: "滚动到指定元素",
            Intent.SCREENSHOT: "截图",
            Intent.GET_TEXT: "获取文本内容",
            Intent.GET_URL: "获取 URL",
            Intent.GET_TITLE: "获取页面标题",
            Intent.GET_ATTRIBUTE: "获取元素属性",
            Intent.EXECUTE_JS: "执行 JavaScript",
            Intent.ASSERT_VISIBLE: "断言元素可见",
            Intent.ASSERT_TEXT: "断言文本内容",
            Intent.ASSERT_URL: "断言 URL",
            Intent.ASSERT_TITLE: "断言标题",
            Intent.NEW_TAB: "新建标签页",
            Intent.CLOSE_TAB: "关闭标签页",
            Intent.SWITCH_TAB: "切换标签页",
            Intent.HANDLE_ALERT: "处理弹窗",
            Intent.ACCEPT_ALERT: "接受弹窗",
            Intent.DISMISS_ALERT: "拒绝弹窗",
            Intent.IFRAME: "进入 iframe",
            Intent.IFRAME_INPUT: "iframe 中输入",
            Intent.IFRAME_CLICK: "iframe 中点击",
            Intent.EXIT_IFRAME: "退出 iframe",
            Intent.WAIT: "等待固定时间",
            Intent.WAIT_LOAD: "等待加载完成",
            Intent.WAIT_VISIBLE: "等待元素可见",
            Intent.DRAG: "拖拽元素",
            Intent.UPLOAD: "上传文件",
            Intent.CHECK: "勾选复选框",
            Intent.UNCHECK: "取消勾选",
            Intent.SEARCH: "搜索",
            Intent.FILL_FORM: "填写表单",
            Intent.LOGIN: "登录",
            Intent.LOGOUT: "退出登录",
            Intent.EXTRACT: "提取信息",
            Intent.UNKNOWN: "未知意图",
            Intent.COMPOSITE: "复合意图（多条指令）",
        }
        return descriptions.get(intent, intent.value)

    def _match_intent_by_description(self, description: str) -> Optional[Intent]:
        """根据描述匹配意图"""
        description = description.lower().strip()

        # 简单关键词匹配
        keyword_map = {
            "打开": Intent.NAVIGATE,
            "访问": Intent.NAVIGATE,
            "去": Intent.NAVIGATE,
            "导航": Intent.NAVIGATE,
            "返回": Intent.NAVIGATE_BACK,
            "后退": Intent.NAVIGATE_BACK,
            "前进": Intent.NAVIGATE_FORWARD,
            "刷新": Intent.NAVIGATE_REFRESH,
            "点击": Intent.CLICK,
            "单击": Intent.CLICK,
            "双击": Intent.DOUBLE_CLICK,
            "右键": Intent.RIGHT_CLICK,
            "悬停": Intent.HOVER,
            "输入": Intent.INPUT,
            "填写": Intent.INPUT,
            "清空": Intent.CLEAR,
            "按键": Intent.PRESS_KEY,
            "选择": Intent.SELECT,
            "滚动": Intent.SCROLL,
            "截图": Intent.SCREENSHOT,
            "获取文本": Intent.GET_TEXT,
            "获取url": Intent.GET_URL,
            "获取链接": Intent.GET_URL,
            "获取标题": Intent.GET_TITLE,
            "获取属性": Intent.GET_ATTRIBUTE,
            "执行js": Intent.EXECUTE_JS,
            "断言可见": Intent.ASSERT_VISIBLE,
            "验证可见": Intent.ASSERT_VISIBLE,
            "断言文本": Intent.ASSERT_TEXT,
            "断言url": Intent.ASSERT_URL,
            "断言标题": Intent.ASSERT_TITLE,
            "新标签页": Intent.NEW_TAB,
            "关闭标签页": Intent.CLOSE_TAB,
            "接受弹窗": Intent.ACCEPT_ALERT,
            "拒绝弹窗": Intent.DISMISS_ALERT,
            "iframe": Intent.IFRAME,
            "等待": Intent.WAIT,
            "等待加载": Intent.WAIT_LOAD,
            "等待可见": Intent.WAIT_VISIBLE,
            "拖拽": Intent.DRAG,
            "上传": Intent.UPLOAD,
            "勾选": Intent.CHECK,
            "取消勾选": Intent.UNCHECK,
            "搜索": Intent.SEARCH,
            "查找": Intent.SEARCH,
            "填写表单": Intent.FILL_FORM,
            "登录": Intent.LOGIN,
            "退出登录": Intent.LOGOUT,
            "提取": Intent.EXTRACT,
        }

        for keyword, intent in keyword_map.items():
            if keyword in description:
                return intent

        return None

    async def aclassify(self, text: str) -> IntentMatch:
        """
        异步版本的意图分类

        支持异步 LLM 调用，适合在异步环境中使用。

        Args:
            text: 输入的自然语言文本

        Returns:
            IntentMatch: 意图匹配结果
        """
        text = text.strip()
        if not text:
            return IntentMatch(Intent.UNKNOWN, 0.0, {}, text)

        # 先尝试精确匹配 DSL 命令
        dsl_match = self._try_dsl_exact(text)
        if dsl_match:
            return dsl_match

        # 使用规则模式进行分类
        rule_match = self._classify_by_rules(text)
        if rule_match and rule_match.confidence >= 0.8:
            return rule_match

        # 如果规则匹配度不够，尝试 LLM 模式
        if self.use_llm_fallback and self.llm:
            if rule_match and rule_match.confidence < 0.8:
                llm_match = await self._aclassify_by_llm(text)
                if llm_match and llm_match.confidence > rule_match.confidence:
                    return llm_match
            elif not rule_match:
                # 完全没有规则匹配，也尝试 LLM
                llm_match = await self._aclassify_by_llm(text)
                if llm_match:
                    return llm_match

        # 返回规则匹配结果或未知意图
        return rule_match or IntentMatch(Intent.UNKNOWN, 0.0, {}, text)

    async def _aclassify_by_llm(self, text: str) -> Optional[IntentMatch]:
        """
        异步版本的 LLM 意图分类

        Args:
            text: 输入的自然语言文本

        Returns:
            IntentMatch: 意图匹配结果，失败返回 None
        """
        if not self.llm:
            logger.debug("LLM 未配置，无法进行 LLM 意图分类")
            return None

        # 构建意图列表描述
        intent_list = []
        for intent in Intent:
            if intent not in [Intent.UNKNOWN, Intent.COMPOSITE]:
                description = self._get_intent_description(intent)
                intent_list.append(f"- {intent.value}: {description}")

        intent_list_str = "\n".join(intent_list)

        # Few-shot prompt
        system_prompt = f"""你是一个意图分类器。根据用户输入的文本，识别出用户的意图。

支持的意图类型：
{intent_list_str}

输出格式要求：
- 返回单个意图的 value 值（如：click, input, navigate）
- 如果输入是多个指令，用 | 分隔（如：click|input|navigate）
- 如果无法识别意图，返回 unknown

示例：
输入：点击登录按钮
输出：click

输入：打开 https://example.com 然后点击搜索框并输入 hello
输出：navigate|click|input

输入：这是一个随机的句子
输出：unknown
"""

        user_prompt = f"输入：{text}\n输出："

        try:
            from browser_use.llm.messages import SystemMessage, UserMessage

            messages = [
                SystemMessage(content=system_prompt),
                UserMessage(content=user_prompt),
            ]

            logger.debug(f"LLM 异步意图分类请求: {text}")

            response = await self.llm.ainvoke(messages)
            result = response.completion.strip().lower()

            logger.debug(f"LLM 意图分类结果: {result}")

            # 解析结果
            intent_values = [v.strip() for v in result.split("|")]

            # 检查是否识别成功
            valid_intents = []
            for value in intent_values:
                try:
                    intent = Intent(value)
                    if intent not in [Intent.UNKNOWN, Intent.COMPOSITE]:
                        valid_intents.append(intent)
                except ValueError:
                    # 尝试用中文描述匹配
                    matched = self._match_intent_by_description(value)
                    if matched:
                        valid_intents.append(matched)

            if not valid_intents:
                return None

            # 如果只有一个意图
            if len(valid_intents) == 1:
                return IntentMatch(
                    intent=valid_intents[0],
                    confidence=0.85,
                    params={},
                    original_text=text
                )

            # 如果有多个意图，返回复合意图
            return IntentMatch(
                intent=Intent.COMPOSITE,
                confidence=0.85,
                params={"intents": valid_intents},
                original_text=text
            )

        except Exception as e:
            logger.warning(f"LLM 意图分类失败: {e}")
            return None
    
    def batch_classify(self, texts: list[str]) -> list[IntentMatch]:
        """
        批量进行意图分类
        
        Args:
            texts: 输入的自然语言文本列表
            
        Returns:
            IntentMatch 列表
        """
        return [self.classify(text) for text in texts]
    
    def add_pattern(self, intent: Intent, pattern: str, params: dict = None) -> None:
        """
        添加自定义意图模式
        
        Args:
            intent: 意图类型
            pattern: 正则表达式模式
            params: 额外的参数
        """
        if intent not in self.INTENT_PATTERNS:
            self.INTENT_PATTERNS[intent] = []
        
        compiled = re.compile(pattern, re.I)
        self.INTENT_PATTERNS[intent].append((pattern, compiled, params or {}))
    
    def detect_composite(self, text: str) -> list[IntentMatch]:
        """
        检测复合指令（多条指令）
        
        Args:
            text: 输入的文本
            
        Returns:
            IntentMatch 列表
        """
        # 按行分割
        lines = text.strip().split("\n")
        results = []
        
        for line in lines:
            line = line.strip()
            # 跳过注释行
            if line.startswith("#") or line.startswith("//"):
                continue
            # 跳过空行
            if not line:
                continue
            # 分类单条指令
            match = self.classify(line)
            results.append(match)
        
        return results
