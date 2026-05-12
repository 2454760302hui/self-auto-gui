from typing import Any

from browser_use.llm import ChatAWSBedrock, ChatAzureOpenAI, ChatBrowserUse, ChatGoogle, ChatOpenAI
from browser_use.llm.anthropic.chat import ChatAnthropic
from browser_use.llm.base import BaseChatModel


def _parse_mapping(value: Any) -> dict[str, Any]:
	if not value:
		return {}
	if isinstance(value, dict):
		return dict(value)
	if isinstance(value, str):
		return {str(k): v for k, v in __import__('json').loads(value).items()}
	return {}


def _normalize_header_value(auth_scheme: str, token: str) -> str:
	if auth_scheme == 'bearer':
		return f'Bearer {token}'
	return token


def _build_anthropic_kwargs(llm_config: dict[str, Any], model: str, temperature: float) -> dict[str, Any]:
	kwargs: dict[str, Any] = {
		'model': model,
		'temperature': temperature,
		'api_key': llm_config.get('api_key'),
		'auth_token': llm_config.get('auth_token'),
		'base_url': llm_config.get('base_url'),
		'api_path': llm_config.get('api_path'),
		'messages_path': llm_config.get('messages_path'),
	}

	auth_scheme = str(llm_config.get('auth_scheme') or '').strip().lower()
	auth_header_name = llm_config.get('auth_header_name')
	default_headers = _parse_mapping(llm_config.get('extra_headers'))
	default_query = _parse_mapping(llm_config.get('query_params'))

	version_header_name = llm_config.get('version_header_name')
	version_header_value = llm_config.get('version_header_value')
	if version_header_name and version_header_value:
		default_headers[str(version_header_name)] = str(version_header_value)

	if auth_scheme and auth_scheme != 'none' and auth_header_name:
		header_name = str(auth_header_name)
		token_value = llm_config.get('auth_token') or llm_config.get('api_key')
		if token_value:
			lower_header = header_name.lower()
			if auth_scheme == 'bearer' and lower_header == 'authorization':
				kwargs['auth_token'] = token_value
			elif auth_scheme == 'x-api-key' and lower_header == 'x-api-key':
				kwargs['api_key'] = token_value
			else:
				default_headers[header_name] = _normalize_header_value(auth_scheme, str(token_value))
				kwargs['api_key'] = None
				kwargs['auth_token'] = None

	if default_headers:
		kwargs['default_headers'] = {str(k): str(v) for k, v in default_headers.items()}
	if default_query:
		kwargs['default_query'] = {str(k): v for k, v in default_query.items()}

	return kwargs


def create_llm_from_config(llm_config: dict[str, Any], model_override: str | None = None, http_client: Any = None) -> BaseChatModel:
	provider = str(llm_config.get('provider') or llm_config.get('model_provider') or 'openai').lower()
	model = model_override or llm_config.get('model')
	temperature = llm_config.get('temperature', 0.7)

	if provider == 'anthropic':
		kwargs = _build_anthropic_kwargs(llm_config, model or 'claude-4-sonnet', temperature)
		if http_client:
			kwargs['http_client'] = http_client
		return ChatAnthropic(**kwargs)

	if provider == 'openai':
		return ChatOpenAI(
			model=model or 'gpt-4o',
			temperature=temperature,
			api_key=llm_config.get('api_key'),
			base_url=llm_config.get('base_url'),
			http_client=http_client,
		)

	if provider == 'google':
		return ChatGoogle(
			model=model or 'gemini-2.5-pro',
			temperature=temperature,
			api_key=llm_config.get('api_key'),
			http_client=http_client,
		)

	if provider == 'azure':
		return ChatAzureOpenAI(
			model=model or 'gpt-4.1-mini',
			api_key=llm_config.get('api_key'),
			azure_endpoint=llm_config.get('azure_endpoint') or llm_config.get('base_url'),
			http_client=http_client,
		)

	if provider == 'browser-use':
		return ChatBrowserUse(
			model=model or 'bu-latest',
			api_key=llm_config.get('api_key'),
			base_url=llm_config.get('base_url'),
			http_client=http_client,
		)

	if provider == 'bedrock':
		return ChatAWSBedrock(
			model=model or 'us.anthropic.claude-sonnet-4-20250514-v1:0',
			aws_region=llm_config.get('region') or 'us-east-1',
			aws_sso_auth=bool(llm_config.get('aws_sso_auth', False)),
		)

	raise ValueError(f'Unsupported LLM provider: {provider}')
