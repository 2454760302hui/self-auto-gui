"""
扩展表单操作模块 - 支持更多表单控件和交互场景
包括：日期/时间选择、数字输入、颜色选择、范围滑块、标签输入等
"""
import asyncio
import logging
import json
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class FormControlType(Enum):
    """表单控件类型"""
    TEXT = "text"  # 文本输入
    NUMBER = "number"  # 数字输入
    EMAIL = "email"  # 邮箱输入
    PASSWORD = "password"  # 密码输入
    TEXTAREA = "textarea"  # 多行文本
    SELECT = "select"  # 下拉选择
    CHECKBOX = "checkbox"  # 复选框
    RADIO = "radio"  # 单选框
    DATE = "date"  # 日期选择
    TIME = "time"  # 时间选择
    DATETIME = "datetime"  # 日期时间选择
    COLOR = "color"  # 颜色选择
    RANGE = "range"  # 范围滑块
    FILE = "file"  # 文件上传
    COMBOBOX = "combobox"  # 自动完成/组合框
    TAG_INPUT = "tag_input"  # 标签输入
    RICH_TEXT = "rich_text"  # 富文本编辑器
    MULTI_SELECT = "multi_select"  # 多选下拉
    CASCADING_SELECT = "cascading_select"  # 级联选择
    TOGGLE = "toggle"  # 开关
    RATING = "rating"  # 评分
    SLIDER = "slider"  # 滑块


@dataclass
class FormFieldInfo:
    """表单字段信息"""
    index: int
    type: FormControlType
    label: str = ""
    placeholder: str = ""
    required: bool = False
    disabled: bool = False
    value: str = ""
    options: list[str] = None
    attributes: dict[str, str] = None
    
    def __post_init__(self):
        if self.options is None:
            self.options = []
        if self.attributes is None:
            self.attributes = {}


class FormActionHandler:
    """表单操作处理器"""
    
    def __init__(self, browser_session: Optional[Any] = None):
        self.browser_session = browser_session
    
    async def detect_form_field_type(self, element: Any) -> FormControlType:
        """
        检测表单字段类型
        
        Args:
            element: DOM元素
            
        Returns:
            表单控件类型
        """
        try:
            tag_name = await self._get_tag_name(element)
            input_type = await self._get_attribute(element, "type")
            role = await self._get_attribute(element, "role")
            
            # 检测标签名
            if tag_name == "input":
                if input_type == "date":
                    return FormControlType.DATE
                elif input_type == "time":
                    return FormControlType.TIME
                elif input_type == "datetime-local":
                    return FormControlType.DATETIME
                elif input_type == "color":
                    return FormControlType.COLOR
                elif input_type == "range":
                    return FormControlType.RANGE
                elif input_type == "number":
                    return FormControlType.NUMBER
                elif input_type == "email":
                    return FormControlType.EMAIL
                elif input_type == "password":
                    return FormControlType.PASSWORD
                elif input_type == "checkbox":
                    return FormControlType.CHECKBOX
                elif input_type == "radio":
                    return FormControlType.RADIO
                elif input_type == "file":
                    return FormControlType.FILE
                else:
                    return FormControlType.TEXT
            
            elif tag_name == "select":
                # 检查是否是多选
                multiple = await self._get_attribute(element, "multiple")
                if multiple:
                    return FormControlType.MULTI_SELECT
                return FormControlType.SELECT
            
            elif tag_name == "textarea":
                return FormControlType.TEXTAREA
            
            elif tag_name == "button":
                return FormControlType.TOGGLE
            
            # 检测ARIA角色
            if role == "combobox":
                return FormControlType.COMBOBOX
            elif role == "listbox":
                return FormControlType.SELECT
            elif role == "checkbox":
                return FormControlType.CHECKBOX
            elif role == "radio":
                return FormControlType.RADIO
            elif role == "slider":
                return FormControlType.SLIDER
            
            # 检测contenteditable（富文本编辑器）
            contenteditable = await self._get_attribute(element, "contenteditable")
            if contenteditable:
                return FormControlType.RICH_TEXT
            
            return FormControlType.TEXT
        
        except Exception as e:
            logger.warning(f"Error detecting form field type: {e}")
            return FormControlType.TEXT
    
    async def fill_date_field(
        self,
        element: Any,
        date_value: str,
        format: str = "YYYY-MM-DD",
    ) -> dict[str, Any]:
        """
        填充日期字段
        
        Args:
            element: 日期输入元素
            date_value: 日期值（如 "2024-05-06"）
            format: 日期格式
            
        Returns:
            操作结果
        """
        try:
            # 解析日期值
            parsed_date = self._parse_date(date_value, format)
            
            # 尝试直接设置value属性
            await self._set_value(element, parsed_date)
            
            # 触发change事件
            await self._trigger_event(element, "change")
            await self._trigger_event(element, "input")
            
            logger.info(f"✅ 日期字段已填充: {parsed_date}")
            return {
                "success": True,
                "message": f"Date field filled with {parsed_date}",
                "value": parsed_date,
            }
        except Exception as e:
            logger.error(f"Error filling date field: {e}")
            return {
                "success": False,
                "error": str(e),
            }
    
    async def fill_time_field(
        self,
        element: Any,
        time_value: str,
        format: str = "HH:MM",
    ) -> dict[str, Any]:
        """
        填充时间字段
        
        Args:
            element: 时间输入元素
            time_value: 时间值（如 "14:30"）
            format: 时间格式
            
        Returns:
            操作结果
        """
        try:
            # 解析时间值
            parsed_time = self._parse_time(time_value, format)
            
            # 尝试直接设置value属性
            await self._set_value(element, parsed_time)
            
            # 触发change事件
            await self._trigger_event(element, "change")
            await self._trigger_event(element, "input")
            
            logger.info(f"✅ 时间字段已填充: {parsed_time}")
            return {
                "success": True,
                "message": f"Time field filled with {parsed_time}",
                "value": parsed_time,
            }
        except Exception as e:
            logger.error(f"Error filling time field: {e}")
            return {
                "success": False,
                "error": str(e),
            }
    
    async def fill_number_field(
        self,
        element: Any,
        number_value: float,
        min_val: Optional[float] = None,
        max_val: Optional[float] = None,
    ) -> dict[str, Any]:
        """
        填充数字字段
        
        Args:
            element: 数字输入元素
            number_value: 数字值
            min_val: 最小值
            max_val: 最大值
            
        Returns:
            操作结果
        """
        try:
            # 验证范围
            if min_val is not None and number_value < min_val:
                return {
                    "success": False,
                    "error": f"Value {number_value} is less than minimum {min_val}",
                }
            
            if max_val is not None and number_value > max_val:
                return {
                    "success": False,
                    "error": f"Value {number_value} is greater than maximum {max_val}",
                }
            
            # 设置值
            await self._set_value(element, str(number_value))
            
            # 触发change事件
            await self._trigger_event(element, "change")
            await self._trigger_event(element, "input")
            
            logger.info(f"✅ 数字字段已填充: {number_value}")
            return {
                "success": True,
                "message": f"Number field filled with {number_value}",
                "value": number_value,
            }
        except Exception as e:
            logger.error(f"Error filling number field: {e}")
            return {
                "success": False,
                "error": str(e),
            }
    
    async def fill_color_field(
        self,
        element: Any,
        color_value: str,
    ) -> dict[str, Any]:
        """
        填充颜色字段
        
        Args:
            element: 颜色输入元素
            color_value: 颜色值（如 "#FF0000" 或 "rgb(255,0,0)"）
            
        Returns:
            操作结果
        """
        try:
            # 转换为十六进制格式
            hex_color = self._normalize_color(color_value)
            
            # 设置值
            await self._set_value(element, hex_color)
            
            # 触发change事件
            await self._trigger_event(element, "change")
            await self._trigger_event(element, "input")
            
            logger.info(f"✅ 颜色字段已填充: {hex_color}")
            return {
                "success": True,
                "message": f"Color field filled with {hex_color}",
                "value": hex_color,
            }
        except Exception as e:
            logger.error(f"Error filling color field: {e}")
            return {
                "success": False,
                "error": str(e),
            }
    
    async def set_range_value(
        self,
        element: Any,
        value: float,
        min_val: Optional[float] = None,
        max_val: Optional[float] = None,
    ) -> dict[str, Any]:
        """
        设置范围滑块值
        
        Args:
            element: 范围滑块元素
            value: 滑块值
            min_val: 最小值
            max_val: 最大值
            
        Returns:
            操作结果
        """
        try:
            # 验证范围
            if min_val is not None and value < min_val:
                return {
                    "success": False,
                    "error": f"Value {value} is less than minimum {min_val}",
                }
            
            if max_val is not None and value > max_val:
                return {
                    "success": False,
                    "error": f"Value {value} is greater than maximum {max_val}",
                }
            
            # 设置值
            await self._set_value(element, str(value))
            
            # 触发change事件
            await self._trigger_event(element, "change")
            await self._trigger_event(element, "input")
            
            logger.info(f"✅ 范围滑块已设置: {value}")
            return {
                "success": True,
                "message": f"Range slider set to {value}",
                "value": value,
            }
        except Exception as e:
            logger.error(f"Error setting range value: {e}")
            return {
                "success": False,
                "error": str(e),
            }
    
    async def add_tag(
        self,
        element: Any,
        tag_value: str,
    ) -> dict[str, Any]:
        """
        添加标签
        
        Args:
            element: 标签输入元素
            tag_value: 标签值
            
        Returns:
            操作结果
        """
        try:
            # 获取当前标签列表
            current_tags = await self._get_tags(element)
            
            # 检查是否已存在
            if tag_value in current_tags:
                return {
                    "success": False,
                    "error": f"Tag '{tag_value}' already exists",
                }
            
            # 添加新标签
            current_tags.append(tag_value)
            await self._set_tags(element, current_tags)
            
            # 触发change事件
            await self._trigger_event(element, "change")
            
            logger.info(f"✅ 标签已添加: {tag_value}")
            return {
                "success": True,
                "message": f"Tag '{tag_value}' added",
                "tags": current_tags,
            }
        except Exception as e:
            logger.error(f"Error adding tag: {e}")
            return {
                "success": False,
                "error": str(e),
            }
    
    async def remove_tag(
        self,
        element: Any,
        tag_value: str,
    ) -> dict[str, Any]:
        """
        移除标签
        
        Args:
            element: 标签输入元素
            tag_value: 标签值
            
        Returns:
            操作结果
        """
        try:
            # 获取当前标签列表
            current_tags = await self._get_tags(element)
            
            # 移除标签
            if tag_value in current_tags:
                current_tags.remove(tag_value)
                await self._set_tags(element, current_tags)
                
                # 触发change事件
                await self._trigger_event(element, "change")
                
                logger.info(f"✅ 标签已移除: {tag_value}")
                return {
                    "success": True,
                    "message": f"Tag '{tag_value}' removed",
                    "tags": current_tags,
                }
            else:
                return {
                    "success": False,
                    "error": f"Tag '{tag_value}' not found",
                }
        except Exception as e:
            logger.error(f"Error removing tag: {e}")
            return {
                "success": False,
                "error": str(e),
            }
    
    # 辅助方法
    
    def _parse_date(self, date_value: str, format: str = "YYYY-MM-DD") -> str:
        """解析日期值"""
        try:
            # 支持多种格式
            if format == "YYYY-MM-DD":
                return date_value
            elif format == "DD/MM/YYYY":
                parts = date_value.split("/")
                return f"{parts[2]}-{parts[1]}-{parts[0]}"
            elif format == "MM/DD/YYYY":
                parts = date_value.split("/")
                return f"{parts[2]}-{parts[0]}-{parts[1]}"
            else:
                return date_value
        except Exception as e:
            logger.warning(f"Error parsing date: {e}")
            return date_value
    
    def _parse_time(self, time_value: str, format: str = "HH:MM") -> str:
        """解析时间值"""
        try:
            # 支持多种格式
            if format == "HH:MM":
                return time_value
            elif format == "HH:MM:SS":
                return time_value
            else:
                return time_value
        except Exception as e:
            logger.warning(f"Error parsing time: {e}")
            return time_value
    
    def _normalize_color(self, color_value: str) -> str:
        """规范化颜色值为十六进制格式"""
        try:
            # 如果已经是十六进制格式
            if color_value.startswith("#"):
                return color_value.lower()
            
            # 转换rgb格式
            if color_value.startswith("rgb"):
                # 提取RGB值
                import re
                match = re.search(r"rgb\((\d+),\s*(\d+),\s*(\d+)\)", color_value)
                if match:
                    r, g, b = int(match.group(1)), int(match.group(2)), int(match.group(3))
                    return f"#{r:02x}{g:02x}{b:02x}"
            
            return color_value
        except Exception as e:
            logger.warning(f"Error normalizing color: {e}")
            return color_value
    
    async def _get_tag_name(self, element: Any) -> str:
        """获取元素标签名"""
        # 这里需要实现实际的DOM操作
        return ""
    
    async def _get_attribute(self, element: Any, attr_name: str) -> str:
        """获取元素属性"""
        # 这里需要实现实际的DOM操作
        return ""
    
    async def _set_value(self, element: Any, value: str) -> None:
        """设置元素值"""
        # 这里需要实现实际的DOM操作
        pass
    
    async def _trigger_event(self, element: Any, event_name: str) -> None:
        """触发元素事件"""
        # 这里需要实现实际的DOM操作
        pass
    
    async def _get_tags(self, element: Any) -> list[str]:
        """获取标签列表"""
        # 这里需要实现实际的DOM操作
        return []
    
    async def _set_tags(self, element: Any, tags: list[str]) -> None:
        """设置标签列表"""
        # 这里需要实现实际的DOM操作
        pass
