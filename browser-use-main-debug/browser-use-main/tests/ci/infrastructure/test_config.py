"""Tests for lazy loading configuration system."""

import os

from browser_use.config import CONFIG, load_browser_use_config


class TestLazyConfig:
	"""Test lazy loading of environment variables through CONFIG object."""

	def test_config_reads_env_vars_lazily(self):
		"""Test that CONFIG reads environment variables each time they're accessed."""
		# Set an env var
		original_value = os.environ.get('BROWSER_USE_LOGGING_LEVEL', '')
		try:
			os.environ['BROWSER_USE_LOGGING_LEVEL'] = 'debug'
			assert CONFIG.BROWSER_USE_LOGGING_LEVEL == 'debug'

			# Change the env var
			os.environ['BROWSER_USE_LOGGING_LEVEL'] = 'info'
			assert CONFIG.BROWSER_USE_LOGGING_LEVEL == 'info'

			# Delete the env var to test default
			del os.environ['BROWSER_USE_LOGGING_LEVEL']
			assert CONFIG.BROWSER_USE_LOGGING_LEVEL == 'info'  # default value
		finally:
			# Restore original value
			if original_value:
				os.environ['BROWSER_USE_LOGGING_LEVEL'] = original_value
			else:
				os.environ.pop('BROWSER_USE_LOGGING_LEVEL', None)

	def test_boolean_env_vars(self):
		"""Test boolean environment variables are parsed correctly."""
		original_value = os.environ.get('ANONYMIZED_TELEMETRY', '')
		try:
			# Test true values
			for true_val in ['true', 'True', 'TRUE', 'yes', 'Yes', '1']:
				os.environ['ANONYMIZED_TELEMETRY'] = true_val
				assert CONFIG.ANONYMIZED_TELEMETRY is True, f'Failed for value: {true_val}'

			# Test false values
			for false_val in ['false', 'False', 'FALSE', 'no', 'No', '0']:
				os.environ['ANONYMIZED_TELEMETRY'] = false_val
				assert CONFIG.ANONYMIZED_TELEMETRY is False, f'Failed for value: {false_val}'
		finally:
			if original_value:
				os.environ['ANONYMIZED_TELEMETRY'] = original_value
			else:
				os.environ.pop('ANONYMIZED_TELEMETRY', None)

	def test_api_keys_lazy_loading(self):
		"""Test API keys are loaded lazily."""
		original_value = os.environ.get('OPENAI_API_KEY', '')
		try:
			# Test empty default
			os.environ.pop('OPENAI_API_KEY', None)
			assert CONFIG.OPENAI_API_KEY == ''

			# Set a value
			os.environ['OPENAI_API_KEY'] = 'test-key-123'
			assert CONFIG.OPENAI_API_KEY == 'test-key-123'

			# Change the value
			os.environ['OPENAI_API_KEY'] = 'new-key-456'
			assert CONFIG.OPENAI_API_KEY == 'new-key-456'
		finally:
			if original_value:
				os.environ['OPENAI_API_KEY'] = original_value
			else:
				os.environ.pop('OPENAI_API_KEY', None)

	def test_path_configuration(self):
		"""Test path configuration variables."""
		original_value = os.environ.get('XDG_CACHE_HOME', '')
		try:
			# Test custom path
			test_path = '/tmp/test-cache'
			os.environ['XDG_CACHE_HOME'] = test_path
			# Use Path().resolve() to handle symlinks (e.g., /tmp -> /private/tmp on macOS)
			from pathlib import Path

			assert CONFIG.XDG_CACHE_HOME == Path(test_path).resolve()

			# Test default path expansion
			os.environ.pop('XDG_CACHE_HOME', None)
			from pathlib import Path

			assert CONFIG.XDG_CACHE_HOME.name == '.cache'
			assert CONFIG.XDG_CACHE_HOME == Path('~/.cache').expanduser().resolve()
		finally:
			if original_value:
				os.environ['XDG_CACHE_HOME'] = original_value
			else:
				os.environ.pop('XDG_CACHE_HOME', None)


	def test_load_config_supports_named_llm_profiles(self):
		original_env = os.environ.copy()
		try:
			os.environ.pop('ANTHROPIC_AUTH_TOKEN', None)
			os.environ.pop('ANTHROPIC_BASE_URL', None)
			os.environ.pop('ANTHROPIC_MODEL', None)
			os.environ['BROWSER_USE_DEFAULT_LLM_PROFILE'] = 'glm'
			os.environ['BROWSER_USE_LLM_MINIMAX_PROVIDER'] = 'anthropic'
			os.environ['BROWSER_USE_LLM_MINIMAX_AUTH_TOKEN'] = 'token-minimax'
			os.environ['BROWSER_USE_LLM_MINIMAX_BASE_URL'] = 'https://relay-1.example.com'
			os.environ['BROWSER_USE_LLM_MINIMAX_MODEL'] = 'MiniMax-M2.7-highspeed'
			os.environ['BROWSER_USE_LLM_MINIMAX_AUTH_SCHEME'] = 'x-api-key'
			os.environ['BROWSER_USE_LLM_MINIMAX_AUTH_HEADER_NAME'] = 'x-api-key'
			os.environ['BROWSER_USE_LLM_MINIMAX_API_PATH'] = '/v1/messages'
			os.environ['BROWSER_USE_LLM_GLM_PROVIDER'] = 'anthropic'
			os.environ['BROWSER_USE_LLM_GLM_AUTH_TOKEN'] = 'token-glm'
			os.environ['BROWSER_USE_LLM_GLM_BASE_URL'] = 'https://relay-2.example.com'
			os.environ['BROWSER_USE_LLM_GLM_MODEL'] = 'glm-5'
			os.environ['BROWSER_USE_LLM_GLM_AUTH_SCHEME'] = 'bearer'
			os.environ['BROWSER_USE_LLM_GLM_AUTH_HEADER_NAME'] = 'Authorization'
			os.environ['BROWSER_USE_LLM_GLM_MESSAGES_PATH'] = '/messages'
			os.environ['BROWSER_USE_LLM_GLM_VERSION_HEADER_NAME'] = 'anthropic-version'
			os.environ['BROWSER_USE_LLM_GLM_VERSION_HEADER_VALUE'] = '2023-06-01'
			os.environ['BROWSER_USE_LLM_GLM_EXTRA_HEADERS'] = '{"x-relay":"glm"}'
			os.environ['BROWSER_USE_LLM_GLM_QUERY_PARAMS'] = '{"api-version":"2023-06-01"}'

			config = load_browser_use_config()

			assert config['default_llm_profile'] == 'glm'
			assert config['llm']['provider'] == 'anthropic'
			assert config['llm']['model'] == 'glm-5'
			assert config['llm']['auth_token'] == 'token-glm'
			assert config['llm']['auth_scheme'] == 'bearer'
			assert config['llm']['messages_path'] == '/messages'
			assert config['llm']['version_header_name'] == 'anthropic-version'
			assert config['llm']['extra_headers'] == '{"x-relay":"glm"}'
			assert config['llm_profiles']['minimax']['base_url'] == 'https://relay-1.example.com'
			assert config['llm_profiles']['minimax']['auth_scheme'] == 'x-api-key'
			assert config['llm_profiles']['minimax']['api_path'] == '/v1/messages'
		finally:
			os.environ.clear()
			os.environ.update(original_env)

	def test_load_config_uses_legacy_anthropic_env(self):
		original_env = os.environ.copy()
		try:
			os.environ.pop('BROWSER_USE_DEFAULT_LLM_PROFILE', None)
			for key in list(os.environ):
				if key.startswith('BROWSER_USE_LLM_'):
					os.environ.pop(key, None)
			os.environ['ANTHROPIC_AUTH_TOKEN'] = 'legacy-token'
			os.environ['ANTHROPIC_BASE_URL'] = 'https://legacy-relay.example.com'
			os.environ['ANTHROPIC_MODEL'] = 'glm-5'

			config = load_browser_use_config()

			assert config['llm']['provider'] == 'anthropic'
			assert config['llm']['auth_token'] == 'legacy-token'
			assert config['llm']['base_url'] == 'https://legacy-relay.example.com'
			assert config['llm']['model'] == 'glm-5'
		finally:
			os.environ.clear()
			os.environ.update(original_env)

	def test_load_config_infers_legacy_minimax_relay_settings(self):
		original_env = os.environ.copy()
		try:
			os.environ.clear()
			os.environ['HOME'] = original_env.get('HOME') or str(__import__('pathlib').Path.home())
			os.environ['USERPROFILE'] = original_env.get('USERPROFILE') or str(__import__('pathlib').Path.home())
			os.environ['ANTHROPIC_AUTH_TOKEN'] = 'legacy-token'
			os.environ['ANTHROPIC_BASE_URL'] = 'https://v2.aicodee.com'
			os.environ['ANTHROPIC_MODEL'] = 'MiniMax-M2.7-highspeed'

			config = load_browser_use_config()

			assert config['llm']['messages_path'] == '/v1/messages'
			assert config['llm']['auth_scheme'] == 'bearer'
			assert config['llm']['auth_header_name'] == 'Authorization'
			assert config['llm']['version_header_name'] == 'anthropic-version'
			assert config['llm']['version_header_value'] == '2023-06-01'
		finally:
			os.environ.clear()
			os.environ.update(original_env)

	def test_load_config_infers_legacy_glm_relay_settings(self):
		original_env = os.environ.copy()
		try:
			os.environ.clear()
			os.environ['HOME'] = original_env.get('HOME') or str(__import__('pathlib').Path.home())
			os.environ['USERPROFILE'] = original_env.get('USERPROFILE') or str(__import__('pathlib').Path.home())
			os.environ['ANTHROPIC_AUTH_TOKEN'] = 'legacy-token'
			os.environ['ANTHROPIC_BASE_URL'] = 'https://aicoding.bwits.cn:90/anthropic'
			os.environ['ANTHROPIC_MODEL'] = 'glm-5'

			config = load_browser_use_config()

			assert config['llm']['messages_path'] == '/v1/messages'
			assert config['llm']['version_header_name'] == 'anthropic-version'
			assert config['llm']['version_header_value'] == '2023-06-01'
		finally:
			os.environ.clear()
			os.environ.update(original_env)
