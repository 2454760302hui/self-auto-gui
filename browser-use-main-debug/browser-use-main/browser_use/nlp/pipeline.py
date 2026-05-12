"""
NLP 管道 - 整合意图分类、实体识别、语义解析
提供完整的自然语言理解流程
"""
import logging
from typing import Optional, Union
from dataclasses import dataclass, field

from browser_use.nlp.intent import IntentClassifier, Intent, IntentMatch
from browser_use.nlp.entity import EntityExtractor, Entity
from browser_use.nlp.parser import SemanticParser, ParsedCommand, CommandType
from browser_use.nlp.exceptions import NLUPipelineError

logger = logging.getLogger(__name__)


@dataclass
class NLUPipelineResult:
    """NLP 管道处理结果"""
    # 原始输入
    original_text: str = ""
    
    # 解析后的命令
    commands: list[ParsedCommand] = field(default_factory=list)
    
    # 单条解析结果（如果输入是单句）
    single_command: Optional[ParsedCommand] = None
    
    # 意图分析
    intent_matches: list[IntentMatch] = field(default_factory=list)
    primary_intent: Optional[Intent] = None
    primary_intent_confidence: float = 0.0
    
    # 实体分析
    entities: list[Entity] = field(default_factory=list)
    
    # DSL 输出
    dsl_output: str = ""
    
    # 警告和错误
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    
    # 处理元信息
    use_llm: bool = False
    processing_time_ms: float = 0.0
    
    def is_success(self) -> bool:
        """是否成功解析"""
        return len(self.errors) == 0 and len(self.commands) > 0
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "original_text": self.original_text,
            "commands": [cmd.to_dict() for cmd in self.commands],
            "single_command": self.single_command.to_dict() if self.single_command else None,
            "primary_intent": self.primary_intent.value if self.primary_intent else None,
            "primary_intent_confidence": self.primary_intent_confidence,
            "entities": [e.to_dict() for e in self.entities],
            "dsl_output": self.dsl_output,
            "warnings": self.warnings,
            "errors": self.errors,
            "use_llm": self.use_llm,
            "processing_time_ms": self.processing_time_ms,
        }


class NLUPipeline:
    """
    自然语言理解管道
    
    整合意图分类、实体识别、语义解析，提供端到端的 NLP 处理能力
    
    使用方式:
    ```python
    from browser_use.nlp import NLUPipeline
    
    pipeline = NLUPipeline()
    result = pipeline.process("打开 https://example.com 然后点击登录按钮")
    print(result.dsl_output)
    ```
    """
    
    def __init__(
        self,
        intent_classifier: Optional[IntentClassifier] = None,
        entity_extractor: Optional[EntityExtractor] = None,
        semantic_parser: Optional[SemanticParser] = None,
        use_llm_fallback: bool = False,
        strict_mode: bool = False,
    ):
        """
        初始化 NLP 管道
        
        Args:
            intent_classifier: 意图分类器
            entity_extractor: 实体识别器
            semantic_parser: 语义解析器
            use_llm_fallback: 是否在规则无法识别时使用 LLM
            strict_mode: 是否使用严格模式
        """
        self.intent_classifier = intent_classifier or IntentClassifier(
            use_llm_fallback=use_llm_fallback
        )
        self.entity_extractor = entity_extractor or EntityExtractor(strict=strict_mode)
        self.semantic_parser = semantic_parser or SemanticParser(
            intent_classifier=self.intent_classifier,
            entity_extractor=self.entity_extractor
        )
        self.use_llm_fallback = use_llm_fallback
        self.strict_mode = strict_mode
    
    def process(self, text: str) -> NLUPipelineResult:
        """
        处理自然语言输入
        
        Args:
            text: 自然语言输入
            
        Returns:
            NLUPipelineResult: 处理结果
        """
        import time
        start_time = time.time()
        
        result = NLUPipelineResult()
        result.original_text = text
        
        try:
            # 1. 实体提取（先于意图分类，因为实体信息有助于意图理解）
            result.entities = self.entity_extractor.extract_all(text)
            
            # 2. 意图分类
            intent_matches = self.intent_classifier.detect_composite(text)
            result.intent_matches = intent_matches
            
            # 确定主要意图
            if intent_matches:
                # 选择置信度最高的意图
                best_match = max(intent_matches, key=lambda m: m.confidence)
                result.primary_intent = best_match.intent
                result.primary_intent_confidence = best_match.confidence
            
            # 3. 语义解析
            if len(text.strip().split('\n')) == 1 and len(intent_matches) == 1:
                # 单条指令
                result.commands = intent_matches
                cmd = self.semantic_parser.parse(text)
                result.commands = [cmd]
                result.single_command = cmd
            else:
                # 多条指令
                commands = self.semantic_parser.parse_composite(text)
                result.commands = commands
                if commands:
                    result.single_command = commands[0]
            
            # 4. 生成 DSL 输出
            result.dsl_output = self.semantic_parser.to_dsl(result.commands)
            
            # 5. 收集警告
            for cmd in result.commands:
                result.warnings.extend(cmd.warnings)
            
            # 6. 检查是否有未识别的指令
            unknown_count = sum(
                1 for cmd in result.commands 
                if cmd.command_type == CommandType.UNKNOWN
            )
            if unknown_count > 0:
                result.warnings.append(
                    f"{unknown_count} 条指令无法识别"
                )
            
        except Exception as e:
            logger.exception(f"NLP 管道处理错误: {e}")
            result.errors.append(str(e))
        
        result.processing_time_ms = (time.time() - start_time) * 1000
        result.use_llm = self.use_llm_fallback
        
        return result
    
    def process_single(self, text: str) -> ParsedCommand:
        """
        处理单条自然语言输入
        
        Args:
            text: 自然语言输入
            
        Returns:
            ParsedCommand: 解析后的命令
        """
        return self.semantic_parser.parse(text)
    
    def process_lines(self, text: str) -> list[ParsedCommand]:
        """
        处理多行文本
        
        Args:
            text: 多行文本
            
        Returns:
            ParsedCommand 列表
        """
        return self.semantic_parser.parse_lines(text)
    
    def to_dsl(self, text: str) -> str:
        """
        将自然语言转换为 DSL
        
        Args:
            text: 自然语言输入
            
        Returns:
            DSL 命令字符串
        """
        result = self.process(text)
        return result.dsl_output
    
    def add_custom_intent(
        self, 
        intent: Intent, 
        patterns: list[tuple[str, dict]]
    ) -> None:
        """
        添加自定义意图模式
        
        Args:
            intent: 意图类型
            patterns: 模式列表，每个元素为 (正则表达式, 参数字典)
        """
        self.intent_classifier.add_pattern(intent, patterns)
    
    def batch_process(self, texts: list[str]) -> list[NLUPipelineResult]:
        """
        批量处理自然语言输入
        
        Args:
            texts: 自然语言输入列表
            
        Returns:
            NLUPipelineResult 列表
        """
        return [self.process(text) for text in texts]


def create_nlp_pipeline(
    use_llm_fallback: bool = False,
    strict_mode: bool = False,
) -> NLUPipeline:
    """
    创建 NLP 管道的便捷函数
    
    Args:
        use_llm_fallback: 是否使用 LLM fallback
        strict_mode: 是否使用严格模式
        
    Returns:
        NLUPipeline 实例
    """
    return NLUPipeline(
        use_llm_fallback=use_llm_fallback,
        strict_mode=strict_mode,
    )
