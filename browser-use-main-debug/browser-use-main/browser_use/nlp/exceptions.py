"""NLP 模块异常定义"""


class NLPError(Exception):
    """NLP 模块基础异常"""
    pass


class IntentClassificationError(NLPError):
    """意图分类错误"""
    pass


class EntityExtractionError(NLPError):
    """实体提取错误"""
    pass


class SemanticParsingError(NLPError):
    """语义解析错误"""
    pass


class NLUPipelineError(NLPError):
    """NLP 管道执行错误"""
    pass
