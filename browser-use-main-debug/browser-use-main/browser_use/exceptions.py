"""Browser-use exceptions.

Note: LLM-specific exceptions have been consolidated into browser_use.llm.exceptions.
LLMException is kept here for backward compatibility only.
"""

import warnings

from browser_use.llm.exceptions import ModelError, ModelProviderError  # noqa: F401 - re-export for convenience


class LLMException(Exception):
	"""Deprecated: Use ModelProviderError from browser_use.llm.exceptions instead."""

	def __init__(self, status_code: int, message: str):
		warnings.warn(
			'LLMException is deprecated. Use ModelProviderError from browser_use.llm.exceptions instead.',
			DeprecationWarning,
			stacklevel=2,
		)
		self.status_code = status_code
		self.message = message
		super().__init__(f'Error {status_code}: {message}')


class BrowserUseError(Exception):
	"""Base exception for browser-use errors."""

	pass


class BrowserConnectionError(BrowserUseError):
	"""Raised when the browser connection fails."""

	pass


class BrowserNavigationError(BrowserUseError):
	"""Raised when a navigation action fails."""

	pass


class AgentError(BrowserUseError):
	"""Raised when the agent encounters an unrecoverable error."""

	pass


class ConfigurationError(BrowserUseError):
	"""Raised when there is a configuration problem."""

	pass
