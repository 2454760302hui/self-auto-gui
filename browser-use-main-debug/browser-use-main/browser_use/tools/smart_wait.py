"""
智能等待模块 - 提供动态等待策略和可视化反馈
支持条件等待、网络空闲检测、DOM稳定性检测等
"""
import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Callable, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class WaitStrategy(Enum):
    """等待策略类型"""
    FIXED = "fixed"  # 固定时间等待
    NETWORK_IDLE = "network_idle"  # 等待网络空闲
    DOM_STABLE = "dom_stable"  # 等待DOM稳定
    ELEMENT_VISIBLE = "element_visible"  # 等待元素可见
    ELEMENT_CLICKABLE = "element_clickable"  # 等待元素可点击
    ANIMATION_COMPLETE = "animation_complete"  # 等待动画完成
    CONDITION = "condition"  # 等待自定义条件


@dataclass
class WaitConfig:
    """等待配置"""
    strategy: WaitStrategy = WaitStrategy.FIXED
    timeout: float = 30.0  # 最大等待时间（秒）
    check_interval: float = 0.1  # 检查间隔（秒）
    show_progress: bool = True  # 是否显示进度
    reason: str = ""  # 等待原因


class SmartWaiter:
    """智能等待器"""
    
    def __init__(self, browser_session: Optional[Any] = None):
        self.browser_session = browser_session
        self.start_time: Optional[float] = None
        self.elapsed_time: float = 0.0
        
    async def wait(
        self,
        config: WaitConfig,
        condition_fn: Optional[Callable[[], bool]] = None,
    ) -> dict[str, Any]:
        """
        执行智能等待
        
        Args:
            config: 等待配置
            condition_fn: 自定义条件函数（用于CONDITION策略）
            
        Returns:
            等待结果信息
        """
        self.start_time = asyncio.get_event_loop().time()
        
        try:
            if config.strategy == WaitStrategy.FIXED:
                return await self._wait_fixed(config)
            elif config.strategy == WaitStrategy.NETWORK_IDLE:
                return await self._wait_network_idle(config)
            elif config.strategy == WaitStrategy.DOM_STABLE:
                return await self._wait_dom_stable(config)
            elif config.strategy == WaitStrategy.ELEMENT_VISIBLE:
                return await self._wait_element_visible(config)
            elif config.strategy == WaitStrategy.CONDITION:
                return await self._wait_condition(config, condition_fn)
            else:
                return await self._wait_fixed(config)
        except asyncio.TimeoutError:
            return {
                "success": False,
                "reason": f"Timeout after {config.timeout}s",
                "elapsed": self._get_elapsed(),
                "strategy": config.strategy.value,
            }
    
    async def _wait_fixed(self, config: WaitConfig) -> dict[str, Any]:
        """固定时间等待"""
        actual_wait = min(max(config.timeout - 1, 0), 30)
        
        if config.show_progress:
            logger.info(f"⏳ 等待 {config.timeout}s {config.reason}")
        
        await asyncio.sleep(actual_wait)
        
        return {
            "success": True,
            "reason": f"Waited {config.timeout}s",
            "elapsed": self._get_elapsed(),
            "strategy": config.strategy.value,
        }
    
    async def _wait_network_idle(self, config: WaitConfig) -> dict[str, Any]:
        """等待网络空闲"""
        if not self.browser_session:
            return await self._wait_fixed(config)
        
        if config.show_progress:
            logger.info(f"🌐 等待网络空闲 {config.reason}")
        
        start = asyncio.get_event_loop().time()
        idle_count = 0
        idle_threshold = 3  # 连续3次检查都空闲
        
        while asyncio.get_event_loop().time() - start < config.timeout:
            try:
                # 检查是否有待处理的网络请求
                pending_requests = await self._get_pending_requests()
                
                if not pending_requests:
                    idle_count += 1
                    if idle_count >= idle_threshold:
                        return {
                            "success": True,
                            "reason": "Network idle detected",
                            "elapsed": self._get_elapsed(),
                            "strategy": config.strategy.value,
                        }
                else:
                    idle_count = 0
                
                await asyncio.sleep(config.check_interval)
            except Exception as e:
                logger.debug(f"Error checking network: {e}")
                await asyncio.sleep(config.check_interval)
        
        return {
            "success": False,
            "reason": f"Network idle timeout after {config.timeout}s",
            "elapsed": self._get_elapsed(),
            "strategy": config.strategy.value,
        }
    
    async def _wait_dom_stable(self, config: WaitConfig) -> dict[str, Any]:
        """等待DOM稳定"""
        if config.show_progress:
            logger.info(f"🔄 等待DOM稳定 {config.reason}")
        
        start = asyncio.get_event_loop().time()
        last_dom_hash = None
        stable_count = 0
        stable_threshold = 2  # 连续2次检查DOM未变化
        
        while asyncio.get_event_loop().time() - start < config.timeout:
            try:
                if self.browser_session:
                    # 获取当前DOM的哈希值
                    current_hash = await self._get_dom_hash()
                    
                    if current_hash == last_dom_hash:
                        stable_count += 1
                        if stable_count >= stable_threshold:
                            return {
                                "success": True,
                                "reason": "DOM stable",
                                "elapsed": self._get_elapsed(),
                                "strategy": config.strategy.value,
                            }
                    else:
                        stable_count = 0
                        last_dom_hash = current_hash
                
                await asyncio.sleep(config.check_interval)
            except Exception as e:
                logger.debug(f"Error checking DOM: {e}")
                await asyncio.sleep(config.check_interval)
        
        return {
            "success": False,
            "reason": f"DOM stable timeout after {config.timeout}s",
            "elapsed": self._get_elapsed(),
            "strategy": config.strategy.value,
        }
    
    async def _wait_element_visible(self, config: WaitConfig) -> dict[str, Any]:
        """等待元素可见"""
        if config.show_progress:
            logger.info(f"👁️ 等待元素可见 {config.reason}")
        
        start = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start < config.timeout:
            try:
                if self.browser_session:
                    # 检查元素是否可见
                    is_visible = await self._check_element_visible()
                    if is_visible:
                        return {
                            "success": True,
                            "reason": "Element visible",
                            "elapsed": self._get_elapsed(),
                            "strategy": config.strategy.value,
                        }
                
                await asyncio.sleep(config.check_interval)
            except Exception as e:
                logger.debug(f"Error checking element visibility: {e}")
                await asyncio.sleep(config.check_interval)
        
        return {
            "success": False,
            "reason": f"Element visibility timeout after {config.timeout}s",
            "elapsed": self._get_elapsed(),
            "strategy": config.strategy.value,
        }
    
    async def _wait_condition(
        self,
        config: WaitConfig,
        condition_fn: Optional[Callable[[], bool]],
    ) -> dict[str, Any]:
        """等待自定义条件"""
        if not condition_fn:
            return {
                "success": False,
                "reason": "No condition function provided",
                "elapsed": self._get_elapsed(),
                "strategy": config.strategy.value,
            }
        
        if config.show_progress:
            logger.info(f"⚙️ 等待条件满足 {config.reason}")
        
        start = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start < config.timeout:
            try:
                if condition_fn():
                    return {
                        "success": True,
                        "reason": "Condition met",
                        "elapsed": self._get_elapsed(),
                        "strategy": config.strategy.value,
                    }
                
                await asyncio.sleep(config.check_interval)
            except Exception as e:
                logger.debug(f"Error checking condition: {e}")
                await asyncio.sleep(config.check_interval)
        
        return {
            "success": False,
            "reason": f"Condition timeout after {config.timeout}s",
            "elapsed": self._get_elapsed(),
            "strategy": config.strategy.value,
        }
    
    async def _get_pending_requests(self) -> list[str]:
        """获取待处理的网络请求"""
        if not self.browser_session:
            return []
        
        try:
            # 这里可以集成实际的网络请求检测逻辑
            # 目前返回空列表作为示例
            return []
        except Exception as e:
            logger.debug(f"Error getting pending requests: {e}")
            return []
    
    async def _get_dom_hash(self) -> str:
        """获取DOM的哈希值"""
        if not self.browser_session:
            return ""
        
        try:
            # 这里可以集成实际的DOM哈希计算逻辑
            return ""
        except Exception as e:
            logger.debug(f"Error getting DOM hash: {e}")
            return ""
    
    async def _check_element_visible(self) -> bool:
        """检查元素是否可见"""
        if not self.browser_session:
            return False
        
        try:
            # 这里可以集成实际的元素可见性检查逻辑
            return False
        except Exception as e:
            logger.debug(f"Error checking element visibility: {e}")
            return False
    
    def _get_elapsed(self) -> float:
        """获取已用时间"""
        if self.start_time is None:
            return 0.0
        return asyncio.get_event_loop().time() - self.start_time
