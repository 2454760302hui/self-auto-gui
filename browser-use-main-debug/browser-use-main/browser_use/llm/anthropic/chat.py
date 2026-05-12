import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, TypeVar, overload
from urllib.parse import urlsplit, urlunsplit

import httpx
from anthropic import (
	APIConnectionError,
	APIStatusError,
	AsyncAnthropic,
	NotGiven,
	RateLimitError,
	omit,
)
from anthropic.types import CacheControlEphemeralParam, Message, ToolParam
from anthropic.types.model_param import ModelParam
from anthropic.types.text_block import TextBlock
from anthropic.types.tool_choice_tool_param import ToolChoiceToolParam
from httpx import Timeout
from pydantic import BaseModel

from browser_use.llm.anthropic.serializer import AnthropicMessageSerializer
from browser_use.llm.base import BaseChatModel
from browser_use.llm.exceptions import ModelProviderError, ModelRateLimitError
from browser_use.llm.messages import BaseMessage
from browser_use.llm.schema import SchemaOptimizer
from browser_use.llm.views import ChatInvokeCompletion, ChatInvokeUsage

T = TypeVar('T', bound=BaseModel)


@dataclass
class ChatAnthropic(BaseChatModel):
	"""
	A wrapper around Anthropic's chat model.
	"""

	# Model configuration
	model: str | ModelParam
	max_tokens: int = 8192
	temperature: float | None = None
	top_p: float | None = None
	seed: int | None = None

	# Client initialization parameters
	api_key: str | None = None
	auth_token: str | None = None
	base_url: str | httpx.URL | None = None
	api_path: str | None = None
	messages_path: str | None = None
	timeout: float | Timeout | None | NotGiven = NotGiven()
	max_retries: int = 10
	default_headers: Mapping[str, str] | None = None
	default_query: Mapping[str, object] | None = None
	http_client: httpx.AsyncClient | None = None
	# Set to False for relays that don't support tool_choice=required (e.g. GLM-5 thinking mode)
	use_tool_calling: bool = True

	# Static
	@property
	def provider(self) -> str:
		return 'anthropic'

	def _normalize_base_url(self) -> str | httpx.URL | None:
		if self.base_url is None:
			return None
		if not self.api_path:
			return self.base_url

		base_url = str(self.base_url)
		target_path = self.api_path.strip('/')
		parts = urlsplit(base_url)
		base_path = parts.path.rstrip('/')
		normalized_path = '/'.join(part for part in [base_path, target_path] if part)
		if normalized_path and not normalized_path.startswith('/'):
			normalized_path = f'/{normalized_path}'
		return urlunsplit((parts.scheme, parts.netloc, normalized_path or parts.path, parts.query, parts.fragment))

	def _get_raw_messages_url(self) -> str | None:
		if self.base_url is None or self.messages_path is None:
			return None

		parts = urlsplit(str(self.base_url))
		base_path = parts.path.rstrip('/')
		target_path = self.messages_path.strip('/')
		normalized_path = '/'.join(part for part in [base_path, target_path] if part)
		if normalized_path and not normalized_path.startswith('/'):
			normalized_path = f'/{normalized_path}'
		return urlunsplit((parts.scheme, parts.netloc, normalized_path or '/', parts.query, parts.fragment))

	def _build_raw_headers(self) -> dict[str, str]:
		headers = {'content-type': 'application/json'}
		if self.default_headers:
			headers.update(dict(self.default_headers))
		if self.api_key and 'x-api-key' not in {k.lower() for k in headers}:
			headers['x-api-key'] = self.api_key
		if self.auth_token and 'authorization' not in {k.lower() for k in headers}:
			headers['Authorization'] = f'Bearer {self.auth_token}'
		return headers

	def _build_raw_payload(self, anthropic_messages: list[dict[str, Any]], system_prompt: str | None) -> dict[str, Any]:
		payload: dict[str, Any] = {
			'model': self.model,
			'messages': anthropic_messages,
		}
		if system_prompt:
			payload['system'] = system_prompt
		payload.update(self._get_client_params_for_invoke())
		return payload

	async def _ainvoke_via_raw_http(self, anthropic_messages: list[dict[str, Any]], system_prompt: str | None) -> ChatInvokeCompletion[str]:
		url = self._get_raw_messages_url()
		assert url is not None
		client_kwargs: dict[str, Any] = {'timeout': 60.0}
		if not isinstance(self.timeout, NotGiven):
			client_kwargs['timeout'] = self.timeout
		async with httpx.AsyncClient(**client_kwargs) as client:
			response = await client.post(
				url,
				headers=self._build_raw_headers(),
				params=self.default_query,
				json=self._build_raw_payload(anthropic_messages, system_prompt),
			)
			response.raise_for_status()
			data = response.json()

		content = data.get('content') or []
		text_parts = [block.get('text', '') for block in content if block.get('type') == 'text']
		usage = data.get('usage') or {}
		return ChatInvokeCompletion(
			completion=''.join(text_parts),
			usage=ChatInvokeUsage(
				prompt_tokens=usage.get('input_tokens', 0) + (usage.get('cache_read_input_tokens') or 0),
				completion_tokens=usage.get('output_tokens', 0),
				total_tokens=usage.get('input_tokens', 0) + usage.get('output_tokens', 0),
				prompt_cached_tokens=usage.get('cache_read_input_tokens'),
				prompt_cache_creation_tokens=usage.get('cache_creation_input_tokens'),
				prompt_image_tokens=None,
			),
			stop_reason=data.get('stop_reason'),
		)

	def _get_client_params(self) -> dict[str, Any]:
		"""Prepare client parameters dictionary."""
		# Define base client params
		base_params = {
			'api_key': self.api_key,
			'auth_token': self.auth_token,
			'base_url': self._normalize_base_url(),
			'timeout': self.timeout,
			'max_retries': self.max_retries,
			'default_headers': self.default_headers,
			'default_query': self.default_query,
			'http_client': self.http_client,
		}

		# Create client_params dict with non-None values and non-NotGiven values
		client_params = {}
		for k, v in base_params.items():
			if v is not None and v is not NotGiven():
				client_params[k] = v

		return client_params

	def _get_client_params_for_invoke(self):
		"""Prepare client parameters dictionary for invoke."""

		client_params = {}

		if self.temperature is not None:
			client_params['temperature'] = self.temperature

		if self.max_tokens is not None:
			client_params['max_tokens'] = self.max_tokens

		if self.top_p is not None:
			client_params['top_p'] = self.top_p

		if self.seed is not None:
			client_params['seed'] = self.seed

		return client_params

	def get_client(self) -> AsyncAnthropic:
		"""
		Returns an AsyncAnthropic client.

		Returns:
			AsyncAnthropic: An instance of the AsyncAnthropic client.
		"""
		client_params = self._get_client_params()
		return AsyncAnthropic(**client_params)

	@property
	def name(self) -> str:
		return str(self.model)

	def _get_usage(self, response: Message) -> ChatInvokeUsage | None:
		usage = ChatInvokeUsage(
			prompt_tokens=response.usage.input_tokens
			+ (
				response.usage.cache_read_input_tokens or 0
			),  # Total tokens in Anthropic are a bit fucked, you have to add cached tokens to the prompt tokens
			completion_tokens=response.usage.output_tokens,
			total_tokens=response.usage.input_tokens + response.usage.output_tokens,
			prompt_cached_tokens=response.usage.cache_read_input_tokens,
			prompt_cache_creation_tokens=response.usage.cache_creation_input_tokens,
			prompt_image_tokens=None,
		)
		return usage

	@overload
	async def ainvoke(
		self, messages: list[BaseMessage], output_format: None = None, **kwargs: Any
	) -> ChatInvokeCompletion[str]: ...

	@overload
	async def ainvoke(self, messages: list[BaseMessage], output_format: type[T], **kwargs: Any) -> ChatInvokeCompletion[T]: ...

	async def ainvoke(
		self, messages: list[BaseMessage], output_format: type[T] | None = None, **kwargs: Any
	) -> ChatInvokeCompletion[T] | ChatInvokeCompletion[str]:
		anthropic_messages, system_prompt = AnthropicMessageSerializer.serialize_messages(messages)

		try:
			if output_format is None:
				if self.messages_path:
					return await self._ainvoke_via_raw_http(anthropic_messages, system_prompt)
				# Normal completion without structured output
				response = await self.get_client().messages.create(
					model=self.model,
					messages=anthropic_messages,
					system=system_prompt or omit,
					**self._get_client_params_for_invoke(),
				)

				# Ensure we have a valid Message object before accessing attributes
				if not isinstance(response, Message):
					raise ModelProviderError(
						message=f'Unexpected response type from Anthropic API: {type(response).__name__}. Response: {str(response)[:200]}',
						status_code=502,
						model=self.name,
					)

				usage = self._get_usage(response)

				# Extract text from the first content block
				first_content = response.content[0]
				if isinstance(first_content, TextBlock):
					response_text = first_content.text
				else:
					# If it's not a text block, convert to string
					response_text = str(first_content)

				return ChatInvokeCompletion(
					completion=response_text,
					usage=usage,
					stop_reason=response.stop_reason,
				)

			else:
				# Use tool calling for structured output
				# Create a tool that represents the output format
				tool_name = output_format.__name__

				# If relay doesn't support tool_choice=required, use JSON text mode instead
				if not self.use_tool_calling:
					schema = SchemaOptimizer.create_optimized_json_schema(output_format)
					schema_str = json.dumps(schema, ensure_ascii=False)
					json_instruction = (
						f'\n\nYou MUST respond with a valid JSON object matching this schema (no markdown, no explanation):\n{schema_str}'
					)
					# Inject instruction into last user message
					import copy
					patched_messages = copy.deepcopy(anthropic_messages)
					for msg in reversed(patched_messages):
						if msg.get('role') == 'user':
							content = msg.get('content', '')
							if isinstance(content, str):
								msg['content'] = content + json_instruction
							elif isinstance(content, list):
								for part in reversed(content):
									if isinstance(part, dict) and part.get('type') == 'text':
										part['text'] = part['text'] + json_instruction
										break
							break
					response = await self.get_client().messages.create(
						model=self.model,
						messages=patched_messages,
						system=system_prompt or omit,
						**self._get_client_params_for_invoke(),
					)
					if not isinstance(response, Message):
						raise ModelProviderError(
							message=f'Unexpected response type: {type(response).__name__}',
							status_code=502,
							model=self.name,
						)
					usage = self._get_usage(response)
					raw_text = ''
					for block in response.content:
						if isinstance(block, TextBlock):
							raw_text = block.text.strip()
							break
					# Strip markdown fences
					if raw_text.startswith('```'):
						raw_text = raw_text.split('```')[1]
						if raw_text.startswith('json'):
							raw_text = raw_text[4:]
						raw_text = raw_text.strip()
					try:
						parsed_json = json.loads(raw_text)
						return ChatInvokeCompletion(
							completion=output_format.model_validate(parsed_json),
							usage=usage,
							stop_reason=response.stop_reason,
						)
					except Exception as exc:
						raise ModelProviderError(
							message=f'Failed to parse JSON response: {exc}\nRaw: {raw_text[:200]}',
							model=self.name,
						) from exc
				schema = SchemaOptimizer.create_optimized_json_schema(output_format)

				# Remove title from schema if present (Anthropic doesn't like it in parameters)
				if 'title' in schema:
					del schema['title']

				tool = ToolParam(
					name=tool_name,
					description=f'Extract information in the format of {tool_name}',
					input_schema=schema,
					cache_control=CacheControlEphemeralParam(type='ephemeral'),
				)

				# Use auto tool_choice for compatibility with non-standard relays (e.g. GLM)
				# that don't support tool_choice=required/object in thinking mode
				from anthropic.types import ToolChoiceAutoParam
				tool_choice = ToolChoiceAutoParam(type='auto')

				response = await self.get_client().messages.create(
					model=self.model,
					messages=anthropic_messages,
					tools=[tool],
					system=system_prompt or omit,
					tool_choice=tool_choice,
					**self._get_client_params_for_invoke(),
				)

				# Ensure we have a valid Message object before accessing attributes
				if not isinstance(response, Message):
					raise ModelProviderError(
						message=f'Unexpected response type from Anthropic API: {type(response).__name__}. Response: {str(response)[:200]}',
						status_code=502,
						model=self.name,
					)

				usage = self._get_usage(response)

				# Extract the tool use block
				for content_block in response.content:
					if hasattr(content_block, 'type') and content_block.type == 'tool_use':
						# Parse the tool input as the structured output
						try:
							return ChatInvokeCompletion(
								completion=output_format.model_validate(content_block.input),
								usage=usage,
								stop_reason=response.stop_reason,
							)
						except Exception as e:
							# If validation fails, try to fix common model output issues
							_input = content_block.input
							if isinstance(_input, str):
								_input = json.loads(_input)
							elif isinstance(_input, dict):
								# Model sometimes double-serializes fields
								for key, value in _input.items():
									if isinstance(value, str) and value.startswith(('[', '{')):
										try:
											_input[key] = json.loads(value)
										except json.JSONDecodeError:
											cleaned = value.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
											try:
												_input[key] = json.loads(cleaned)
											except json.JSONDecodeError:
												pass
							else:
								raise
							return ChatInvokeCompletion(
								completion=output_format.model_validate(_input),
								usage=usage,
								stop_reason=response.stop_reason,
							)

				# If no tool use block found, try to parse text response as JSON fallback
				# (some relays like GLM-5 with tool_choice=auto may return text instead of tool_use)
				for content_block in response.content:
					if hasattr(content_block, 'type') and content_block.type == 'text':
						text = content_block.text.strip()
						# Try to extract JSON from the text
						try:
							# Strip markdown code fences if present
							if text.startswith('```'):
								text = text.split('```')[1]
								if text.startswith('json'):
									text = text[4:]
								text = text.strip()
							parsed_json = json.loads(text)
							return ChatInvokeCompletion(
								completion=output_format.model_validate(parsed_json),
								usage=usage,
								stop_reason=response.stop_reason,
							)
						except Exception:
							pass
				raise ValueError('Expected tool use in response but none found')

		except APIConnectionError as e:
			raise ModelProviderError(message=e.message, model=self.name) from e
		except RateLimitError as e:
			raise ModelRateLimitError(message=e.message, model=self.name) from e
		except APIStatusError as e:
			raise ModelProviderError(message=e.message, status_code=e.status_code, model=self.name) from e
		except Exception as e:
			raise ModelProviderError(message=str(e), model=self.name) from e
