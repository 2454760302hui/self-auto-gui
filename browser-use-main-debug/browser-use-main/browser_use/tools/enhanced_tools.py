"""
增强工具模块 - 集成智能等待和扩展表单操作
提供统一的接口供Agent使用
"""
import asyncio
import logging
from typing import Optional, Any
from pydantic import BaseModel, Field

from browser_use.tools.smart_wait import SmartWaiter, WaitConfig, WaitStrategy
from browser_use.tools.form_actions import FormActionHandler, FormControlType

logger = logging.getLogger(__name__)


# ============ 数据模型 ============

class SmartWaitAction(BaseModel):
    """智能等待动作"""
    strategy: str = Field(
        default="fixed",
        description="等待策略: fixed(固定时间), network_idle(网络空闲), dom_stable(DOM稳定), element_visible(元素可见), condition(自定义条件)",
    )
    timeout: float = Field(
        default=5.0,
        description="最大等待时间（秒）",
    )
    reason: str = Field(
        default="",
        description="等待原因（用于日志显示）",
    )


class FillDateFieldAction(BaseModel):
    """填充日期字段动作"""
    index: int = Field(description="元素索引")
    date_value: str = Field(description="日期值，格式: YYYY-MM-DD")
    format: str = Field(
        default="YYYY-MM-DD",
        description="日期格式",
    )


class FillTimeFieldAction(BaseModel):
    """填充时间字段动作"""
    index: int = Field(description="元素索引")
    time_value: str = Field(description="时间值，格式: HH:MM")
    format: str = Field(
        default="HH:MM",
        description="时间格式",
    )


class FillNumberFieldAction(BaseModel):
    """填充数字字段动作"""
    index: int = Field(description="元素索引")
    number_value: float = Field(description="数字值")
    min_value: Optional[float] = Field(
        default=None,
        description="最小值（可选）",
    )
    max_value: Optional[float] = Field(
        default=None,
        description="最大值（可选）",
    )


class FillColorFieldAction(BaseModel):
    """填充颜色字段动作"""
    index: int = Field(description="元素索引")
    color_value: str = Field(description="颜色值，格式: #RRGGBB 或 rgb(r,g,b)")


class SetRangeValueAction(BaseModel):
    """设置范围滑块值动作"""
    index: int = Field(description="元素索引")
    value: float = Field(description="滑块值")
    min_value: Optional[float] = Field(
        default=None,
        description="最小值（可选）",
    )
    max_value: Optional[float] = Field(
        default=None,
        description="最大值（可选）",
    )


class AddTagAction(BaseModel):
    """添加标签动作"""
    index: int = Field(description="元素索引")
    tag_value: str = Field(description="标签值")


class RemoveTagAction(BaseModel):
    """移除标签动作"""
    index: int = Field(description="元素索引")
    tag_value: str = Field(description="标签值")


class DetectFormFieldAction(BaseModel):
    """检测表单字段类型动作"""
    index: int = Field(description="元素索引")


# ============ 增强工具类 ============

class EnhancedTools:
    """增强工具集合"""
    
    def __init__(self, registry: Any, browser_session: Optional[Any] = None):
        """
        初始化增强工具
        
        Args:
            registry: 工具注册表
            browser_session: 浏览器会话
        """
        self.registry = registry
        self.browser_session = browser_session
        self.smart_waiter = SmartWaiter(browser_session)
        self.form_handler = FormActionHandler(browser_session)
        
        # 注册所有增强工具
        self._register_smart_wait_tools()
        self._register_form_tools()
    
    def _register_smart_wait_tools(self) -> None:
        """注册智能等待工具"""
        
        @self.registry.action(
            '智能等待 - 支持多种等待策略（固定时间、网络空闲、DOM稳定等）',
            param_model=SmartWaitAction,
        )
        async def smart_wait(params: SmartWaitAction):
            """执行智能等待"""
            try:
                # 转换策略字符串为枚举
                strategy_map = {
                    "fixed": WaitStrategy.FIXED,
                    "network_idle": WaitStrategy.NETWORK_IDLE,
                    "dom_stable": WaitStrategy.DOM_STABLE,
                    "element_visible": WaitStrategy.ELEMENT_VISIBLE,
                    "condition": WaitStrategy.CONDITION,
                }
                
                strategy = strategy_map.get(params.strategy, WaitStrategy.FIXED)
                
                config = WaitConfig(
                    strategy=strategy,
                    timeout=params.timeout,
                    reason=params.reason,
                    show_progress=True,
                )
                
                result = await self.smart_waiter.wait(config)
                
                # 构建返回消息
                if result.get("success"):
                    msg = f"✅ {result.get('reason')} (耗时: {result.get('elapsed', 0):.2f}s)"
                else:
                    msg = f"⚠️ {result.get('reason')}"
                
                logger.info(msg)
                
                from browser_use.tools.service import ActionResult
                return ActionResult(
                    extracted_content=msg,
                    long_term_memory=msg,
                )
            except Exception as e:
                logger.error(f"Smart wait error: {e}")
                from browser_use.tools.service import ActionResult
                return ActionResult(error=str(e))
    
    def _register_form_tools(self) -> None:
        """注册表单工具"""
        
        @self.registry.action(
            '检测表单字段类型 - 自动识别输入框、下拉框、日期选择器等',
            param_model=DetectFormFieldAction,
        )
        async def detect_form_field(params: DetectFormFieldAction):
            """检测表单字段类型"""
            try:
                if not self.browser_session:
                    from browser_use.tools.service import ActionResult
                    return ActionResult(error="Browser session not available")
                
                # 获取元素
                node = await self.browser_session.get_element_by_index(params.index)
                if node is None:
                    from browser_use.tools.service import ActionResult
                    return ActionResult(
                        error=f"Element index {params.index} not available"
                    )
                
                # 检测字段类型
                field_type = await self.form_handler.detect_form_field_type(node)
                
                msg = f"✅ 字段类型: {field_type.value}"
                logger.info(msg)
                
                from browser_use.tools.service import ActionResult
                return ActionResult(
                    extracted_content=msg,
                    long_term_memory=msg,
                )
            except Exception as e:
                logger.error(f"Detect form field error: {e}")
                from browser_use.tools.service import ActionResult
                return ActionResult(error=str(e))
        
        @self.registry.action(
            '填充日期字段 - 支持日期选择器和日期输入框',
            param_model=FillDateFieldAction,
        )
        async def fill_date_field(params: FillDateFieldAction):
            """填充日期字段"""
            try:
                if not self.browser_session:
                    from browser_use.tools.service import ActionResult
                    return ActionResult(error="Browser session not available")
                
                # 获取元素
                node = await self.browser_session.get_element_by_index(params.index)
                if node is None:
                    from browser_use.tools.service import ActionResult
                    return ActionResult(
                        error=f"Element index {params.index} not available"
                    )
                
                # 填充日期
                result = await self.form_handler.fill_date_field(
                    node,
                    params.date_value,
                    params.format,
                )
                
                from browser_use.tools.service import ActionResult
                if result.get("success"):
                    return ActionResult(
                        extracted_content=result.get("message"),
                        long_term_memory=result.get("message"),
                    )
                else:
                    return ActionResult(error=result.get("error"))
            except Exception as e:
                logger.error(f"Fill date field error: {e}")
                from browser_use.tools.service import ActionResult
                return ActionResult(error=str(e))
        
        @self.registry.action(
            '填充时间字段 - 支持时间选择器和时间输入框',
            param_model=FillTimeFieldAction,
        )
        async def fill_time_field(params: FillTimeFieldAction):
            """填充时间字段"""
            try:
                if not self.browser_session:
                    from browser_use.tools.service import ActionResult
                    return ActionResult(error="Browser session not available")
                
                # 获取元素
                node = await self.browser_session.get_element_by_index(params.index)
                if node is None:
                    from browser_use.tools.service import ActionResult
                    return ActionResult(
                        error=f"Element index {params.index} not available"
                    )
                
                # 填充时间
                result = await self.form_handler.fill_time_field(
                    node,
                    params.time_value,
                    params.format,
                )
                
                from browser_use.tools.service import ActionResult
                if result.get("success"):
                    return ActionResult(
                        extracted_content=result.get("message"),
                        long_term_memory=result.get("message"),
                    )
                else:
                    return ActionResult(error=result.get("error"))
            except Exception as e:
                logger.error(f"Fill time field error: {e}")
                from browser_use.tools.service import ActionResult
                return ActionResult(error=str(e))
        
        @self.registry.action(
            '填充数字字段 - 支持数字输入框和范围验证',
            param_model=FillNumberFieldAction,
        )
        async def fill_number_field(params: FillNumberFieldAction):
            """填充数字字段"""
            try:
                if not self.browser_session:
                    from browser_use.tools.service import ActionResult
                    return ActionResult(error="Browser session not available")
                
                # 获取元素
                node = await self.browser_session.get_element_by_index(params.index)
                if node is None:
                    from browser_use.tools.service import ActionResult
                    return ActionResult(
                        error=f"Element index {params.index} not available"
                    )
                
                # 填充数字
                result = await self.form_handler.fill_number_field(
                    node,
                    params.number_value,
                    params.min_value,
                    params.max_value,
                )
                
                from browser_use.tools.service import ActionResult
                if result.get("success"):
                    return ActionResult(
                        extracted_content=result.get("message"),
                        long_term_memory=result.get("message"),
                    )
                else:
                    return ActionResult(error=result.get("error"))
            except Exception as e:
                logger.error(f"Fill number field error: {e}")
                from browser_use.tools.service import ActionResult
                return ActionResult(error=str(e))
        
        @self.registry.action(
            '填充颜色字段 - 支持颜色选择器',
            param_model=FillColorFieldAction,
        )
        async def fill_color_field(params: FillColorFieldAction):
            """填充颜色字段"""
            try:
                if not self.browser_session:
                    from browser_use.tools.service import ActionResult
                    return ActionResult(error="Browser session not available")
                
                # 获取元素
                node = await self.browser_session.get_element_by_index(params.index)
                if node is None:
                    from browser_use.tools.service import ActionResult
                    return ActionResult(
                        error=f"Element index {params.index} not available"
                    )
                
                # 填充颜色
                result = await self.form_handler.fill_color_field(
                    node,
                    params.color_value,
                )
                
                from browser_use.tools.service import ActionResult
                if result.get("success"):
                    return ActionResult(
                        extracted_content=result.get("message"),
                        long_term_memory=result.get("message"),
                    )
                else:
                    return ActionResult(error=result.get("error"))
            except Exception as e:
                logger.error(f"Fill color field error: {e}")
                from browser_use.tools.service import ActionResult
                return ActionResult(error=str(e))
        
        @self.registry.action(
            '设置范围滑块值 - 支持范围输入和滑块控件',
            param_model=SetRangeValueAction,
        )
        async def set_range_value(params: SetRangeValueAction):
            """设置范围滑块值"""
            try:
                if not self.browser_session:
                    from browser_use.tools.service import ActionResult
                    return ActionResult(error="Browser session not available")
                
                # 获取元素
                node = await self.browser_session.get_element_by_index(params.index)
                if node is None:
                    from browser_use.tools.service import ActionResult
                    return ActionResult(
                        error=f"Element index {params.index} not available"
                    )
                
                # 设置范围值
                result = await self.form_handler.set_range_value(
                    node,
                    params.value,
                    params.min_value,
                    params.max_value,
                )
                
                from browser_use.tools.service import ActionResult
                if result.get("success"):
                    return ActionResult(
                        extracted_content=result.get("message"),
                        long_term_memory=result.get("message"),
                    )
                else:
                    return ActionResult(error=result.get("error"))
            except Exception as e:
                logger.error(f"Set range value error: {e}")
                from browser_use.tools.service import ActionResult
                return ActionResult(error=str(e))
        
        @self.registry.action(
            '添加标签 - 支持标签输入框',
            param_model=AddTagAction,
        )
        async def add_tag(params: AddTagAction):
            """添加标签"""
            try:
                if not self.browser_session:
                    from browser_use.tools.service import ActionResult
                    return ActionResult(error="Browser session not available")
                
                # 获取元素
                node = await self.browser_session.get_element_by_index(params.index)
                if node is None:
                    from browser_use.tools.service import ActionResult
                    return ActionResult(
                        error=f"Element index {params.index} not available"
                    )
                
                # 添加标签
                result = await self.form_handler.add_tag(node, params.tag_value)
                
                from browser_use.tools.service import ActionResult
                if result.get("success"):
                    return ActionResult(
                        extracted_content=result.get("message"),
                        long_term_memory=result.get("message"),
                    )
                else:
                    return ActionResult(error=result.get("error"))
            except Exception as e:
                logger.error(f"Add tag error: {e}")
                from browser_use.tools.service import ActionResult
                return ActionResult(error=str(e))
        
        @self.registry.action(
            '移除标签 - 支持标签输入框',
            param_model=RemoveTagAction,
        )
        async def remove_tag(params: RemoveTagAction):
            """移除标签"""
            try:
                if not self.browser_session:
                    from browser_use.tools.service import ActionResult
                    return ActionResult(error="Browser session not available")
                
                # 获取元素
                node = await self.browser_session.get_element_by_index(params.index)
                if node is None:
                    from browser_use.tools.service import ActionResult
                    return ActionResult(
                        error=f"Element index {params.index} not available"
                    )
                
                # 移除标签
                result = await self.form_handler.remove_tag(node, params.tag_value)
                
                from browser_use.tools.service import ActionResult
                if result.get("success"):
                    return ActionResult(
                        extracted_content=result.get("message"),
                        long_term_memory=result.get("message"),
                    )
                else:
                    return ActionResult(error=result.get("error"))
            except Exception as e:
                logger.error(f"Remove tag error: {e}")
                from browser_use.tools.service import ActionResult
                return ActionResult(error=str(e))
