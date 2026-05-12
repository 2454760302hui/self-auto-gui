class ParserError(Exception):
    pass


class ExtractExpressionError(Exception):
    pass


class ConnectTimeout(Exception):
    pass


class MaxRetryError(Exception):
    pass


class ConnectError(Exception):
    pass


class RetryError(Exception):
    """用例重试次数耗尽"""
    pass


class SchemaValidationError(Exception):
    """JSON Schema 校验失败"""
    pass


class ResponseTimeError(Exception):
    """响应时间超出预期"""
    pass
