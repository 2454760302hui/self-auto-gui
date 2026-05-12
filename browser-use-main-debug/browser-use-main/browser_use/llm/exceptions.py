"""LLM-related exceptions for browser-use."""


class ModelError(Exception):
	"""Base class for all LLM model errors."""

	pass


class ModelProviderError(ModelError):
	"""Exception raised when a model provider returns an error."""

	def __init__(
		self,
		message: str,
		status_code: int = 502,
		model: str | None = None,
	):
		super().__init__(message)
		self.message = message
		self.status_code = status_code
		self.model = model


class ModelRateLimitError(ModelProviderError):
	"""Exception raised when a model provider returns a rate limit error."""

	def __init__(
		self,
		message: str,
		status_code: int = 429,
		model: str | None = None,
	):
		super().__init__(message, status_code, model)


class ModelTimeoutError(ModelProviderError):
	"""Exception raised when a model provider request times out."""

	def __init__(
		self,
		message: str,
		status_code: int = 408,
		model: str | None = None,
	):
		super().__init__(message, status_code, model)


class ModelAuthenticationError(ModelProviderError):
	"""Exception raised when authentication with a model provider fails."""

	def __init__(
		self,
		message: str,
		status_code: int = 401,
		model: str | None = None,
	):
		super().__init__(message, status_code, model)


class ModelContextLengthError(ModelProviderError):
	"""Exception raised when the input exceeds the model's context length."""

	def __init__(
		self,
		message: str,
		status_code: int = 400,
		model: str | None = None,
	):
		super().__init__(message, status_code, model)
