from browser_use.llm.anthropic.chat import ChatAnthropic
from browser_use.llm.factory import create_llm_from_config
from browser_use.llm.openai.chat import ChatOpenAI


def test_create_llm_from_anthropic_profile():
	llm = create_llm_from_config(
		{
			'provider': 'anthropic',
			'model': 'glm-5',
			'auth_token': 'relay-token',
			'base_url': 'https://relay.example.com/anthropic',
			'temperature': 0.1,
		}
	)

	assert isinstance(llm, ChatAnthropic)
	assert llm.model == 'glm-5'
	assert llm.auth_token == 'relay-token'
	assert str(llm.base_url) == 'https://relay.example.com/anthropic'


def test_create_llm_from_anthropic_relay_profile_with_custom_headers():
	llm = create_llm_from_config(
		{
			'provider': 'anthropic',
			'model': 'glm-5',
			'auth_token': 'relay-token',
			'base_url': 'https://relay.example.com/anthropic',
			'auth_scheme': 'bearer',
			'auth_header_name': 'X-Relay-Auth',
			'version_header_name': 'anthropic-version',
			'version_header_value': '2023-06-01',
			'extra_headers': '{"x-relay":"glm"}',
			'query_params': '{"api-version":"2023-06-01"}',
			'messages_path': '/messages',
		}
	)

	assert isinstance(llm, ChatAnthropic)
	assert llm.auth_token is None
	assert llm.api_key is None
	assert llm.default_headers == {
		'X-Relay-Auth': 'Bearer relay-token',
		'anthropic-version': '2023-06-01',
		'x-relay': 'glm',
	}
	assert llm.default_query == {'api-version': '2023-06-01'}
	assert llm.messages_path == '/messages'


def test_create_llm_from_anthropic_relay_profile_with_x_api_key():
	llm = create_llm_from_config(
		{
			'provider': 'anthropic',
			'model': 'MiniMax-M2.7-highspeed',
			'auth_token': 'relay-token',
			'base_url': 'https://relay.example.com',
			'auth_scheme': 'x-api-key',
			'auth_header_name': 'x-api-key',
			'api_path': '/v1/messages',
		}
	)

	assert isinstance(llm, ChatAnthropic)
	assert llm.api_key == 'relay-token'
	assert llm.auth_token == 'relay-token'
	assert llm.api_path == '/v1/messages'
	assert llm._get_client_params()['base_url'] == 'https://relay.example.com/v1/messages'


def test_create_llm_from_openai_profile():
	llm = create_llm_from_config(
		{
			'provider': 'openai',
			'model': 'gpt-4o-mini',
			'api_key': 'relay-key',
			'base_url': 'https://relay.example.com/openai',
		}
	)



def test_chat_anthropic_raw_messages_url_for_custom_endpoint():
	llm = create_llm_from_config(
		{
			'provider': 'anthropic',
			'model': 'MiniMax-M2.7-highspeed',
			'auth_token': 'relay-token',
			'base_url': 'https://relay.example.com',
			'messages_path': '/v1/messages',
		}
	)

	assert isinstance(llm, ChatAnthropic)
	assert llm._get_raw_messages_url() == 'https://relay.example.com/v1/messages'
