"""
Browser-Use NLP 模块
提供自然语言理解能力：意图分类、实体识别、语义解析
"""
from browser_use.nlp.pipeline import NLUPipeline
from browser_use.nlp.intent import IntentClassifier, Intent, IntentMatch
from browser_use.nlp.entity import EntityExtractor, Entity, EntityType
from browser_use.nlp.parser import SemanticParser, ParsedCommand, CommandType
from browser_use.nlp.dsl_parser import EnhancedDSLParser, natural_language_to_dsl
from browser_use.nlp.exceptions import NLPError, IntentClassificationError, EntityExtractionError

__all__ = [
    "NLUPipeline",
    "IntentClassifier",
    "Intent",
    "IntentMatch",
    "EntityExtractor",
    "Entity",
    "EntityType",
    "SemanticParser",
    "ParsedCommand",
    "CommandType",
    "EnhancedDSLParser",
    "natural_language_to_dsl",
    "NLPError",
    "IntentClassificationError",
    "EntityExtractionError",
]
