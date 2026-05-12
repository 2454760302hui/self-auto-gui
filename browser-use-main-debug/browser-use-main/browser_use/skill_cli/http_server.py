"""HTTP service wrapper for browser-use skill CLI."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import signal
import socket
import sys
import time
from typing import Any
from urllib.parse import urlparse, urlunparse

import httpx
from aiohttp import web

from browser_use import Agent, BrowserProfile, BrowserSession
from browser_use.llm.anthropic.chat import ChatAnthropic
from browser_use.llm.messages import UserMessage
from browser_use.llm.openai.chat import ChatOpenAI
from browser_use.skill_cli.daemon import Daemon
from browser_use.skill_cli.utils import discover_chrome_cdp_url


class HttpService:
	"""Small HTTP wrapper that reuses Daemon.dispatch()."""

	def __init__(
		self,
		host: str,
		port: int,
		headed: bool,
		profile: str | None,
		cdp_url: str | None = None,
		use_cloud: bool = False,
		cloud_timeout: int | None = None,
		cloud_proxy_country_code: str | None = None,
		cloud_profile_id: str | None = None,
		session: str = 'default',
	) -> None:
		self.host = host
		self.port = port
		self._session_name = session
		self._use_cloud = use_cloud
		self._cloud_timeout = cloud_timeout
		self._cloud_proxy_country_code = cloud_proxy_country_code
		self._cloud_profile_id = cloud_profile_id
		self.daemon = self._build_daemon(
			headed=headed,
			profile=profile,
			cdp_url=cdp_url,
			use_cloud=use_cloud,
		)
		self._runner: web.AppRunner | None = None
		self._site: web.TCPSite | None = None
		self._shutdown_event = asyncio.Event()
		self._task_lock = asyncio.Lock()
		self._llm_config_raw = ''
		self._llm_config_status = 'empty'
		self._llm_config_error = ''
		self._llm_config_summary: dict[str, Any] = {}
		self._configured_llm: ChatAnthropic | None = None
		# CDP URL for connecting to local Chrome (configurable via CHROME_CDP_URL env var)
		self._chrome_cdp_url = os.environ.get('CHROME_CDP_URL', 'http://127.0.0.1:9222')
		# Codegen state
		self._codegen_proc: asyncio.subprocess.Process | None = None
		self._codegen_output_file: str | None = None

		# Auto-initialize LLM from environment variables
		self._auto_init_llm_from_env()

	def _auto_init_llm_from_env(self) -> None:
		"""Auto-configure LLM from environment variables on startup using the full profile system."""
		try:
			from browser_use.config import FlatEnvConfig, _build_legacy_llm_profiles, _choose_default_profile_name, _collect_prefixed_profiles, _merge_profile_dicts

			env_config = FlatEnvConfig()
			legacy_profiles = _build_legacy_llm_profiles(env_config)
			env_profiles = _collect_prefixed_profiles('BROWSER_USE_LLM_', os.environ)
			llm_profiles = _merge_profile_dicts(legacy_profiles, env_profiles)

			if not llm_profiles:
				return

			default_name = _choose_default_profile_name(env_config, llm_profiles)
			if not default_name:
				default_name = next(iter(llm_profiles))

			profile = llm_profiles[default_name]
			llm = self._build_llm_from_profile(profile)
			if llm is None:
				return

			self._configured_llm = llm  # type: ignore[assignment]
			self._llm_config_status = 'ready'
			provider = profile.get('provider', 'anthropic')
			model = profile.get('model', '')
			base_url = profile.get('base_url', '')
			api_key = profile.get('auth_token') or profile.get('api_key') or ''
			self._llm_config_summary = {
				'provider': provider,
				'model': model,
				'base_url': base_url,
				'profile': default_name,
				'token_preview': self._mask_secret(api_key),
			}
			# Build synthetic raw_config for UI display
			if provider == 'openai':
				self._llm_config_raw = json.dumps({'env': {
					'OPENAI_API_KEY': api_key,
					'OPENAI_BASE_URL': base_url,
					'OPENAI_MODEL': model,
				}})
			else:
				self._llm_config_raw = json.dumps({'env': {
					'ANTHROPIC_AUTH_TOKEN': api_key,
					'ANTHROPIC_BASE_URL': base_url,
					'ANTHROPIC_MODEL': model,
				}})
		except Exception as exc:
			self._llm_config_status = 'error'
			self._llm_config_error = f'环境变量 LLM 初始化失败：{exc}'

	def _build_llm_from_profile(self, profile: dict[str, Any]) -> 'ChatAnthropic | None':
		"""Build an LLM instance from a profile dict.

		Uses default_headers instead of custom httpx client to avoid resource leaks.
		- provider=openai or messages_path=/v1/chat/completions → ChatOpenAI
		- Otherwise → ChatAnthropic with use_tool_calling=False
		"""
		provider = (profile.get('provider') or profile.get('model_provider') or 'anthropic').lower()
		model = profile.get('model', '')
		auth_token = profile.get('auth_token') or profile.get('api_key')
		base_url = (profile.get('base_url') or '').rstrip('/')
		messages_path = profile.get('messages_path') or '/v1/messages'
		auth_scheme = (profile.get('auth_scheme') or 'bearer').lower()
		auth_header_name = profile.get('auth_header_name') or 'Authorization'
		version_header_name = profile.get('version_header_name')
		version_header_value = profile.get('version_header_value')

		if not model or not auth_token:
			return None

		# Build auth headers
		headers: dict[str, str] = {}
		if auth_scheme == 'x-api-key':
			headers[auth_header_name] = auth_token
		else:
			headers[auth_header_name] = f'Bearer {auth_token}' if auth_scheme == 'bearer' else auth_token
		if version_header_name and version_header_value:
			headers[version_header_name] = version_header_value

		# ── OpenAI-compatible path ────────────────────────────────────────────
		use_openai_compat = (
			provider == 'openai'
			or messages_path in ('/v1/chat/completions', 'v1/chat/completions')
		)
		if use_openai_compat:
			from browser_use.llm.openai.chat import ChatOpenAI
			openai_base = base_url
			if openai_base.endswith('/v1'):
				openai_base = openai_base[:-3]
			return ChatOpenAI(  # type: ignore[return-value]
				model=model,
				api_key=auth_token,
				base_url=openai_base or None,
				default_headers=headers if headers else None,
				max_completion_tokens=4096,
				# Use add_schema_to_system_prompt for models that don't support response_format=json_schema
				add_schema_to_system_prompt=True,
				dont_force_structured_output=True,
			)

		# ── Anthropic path ────────────────────────────────────────────────────
		# Compute sdk_base_url so that sdk_base_url + /v1/messages == actual endpoint
		sdk_base_url = base_url or None
		if messages_path and messages_path not in ('/v1/messages', 'v1/messages'):
			actual = base_url.rstrip('/') + '/' + messages_path.lstrip('/')
			if actual.endswith('/v1/messages'):
				sdk_base_url = actual[:-len('/v1/messages')]

		return ChatAnthropic(
			model=model,
			auth_token=auth_token if auth_scheme != 'x-api-key' else None,
			api_key=auth_token if auth_scheme == 'x-api-key' else None,
			base_url=sdk_base_url,
			default_headers=headers if headers else None,
			max_tokens=4096,
			use_tool_calling=False,
		)

	def _llm_status_text(self) -> str:
		if self._llm_config_status == 'ready':
			model = self._llm_config_summary.get('model')
			base_url = self._llm_config_summary.get('base_url')
			return f'已测试通过，可直接执行自动化任务。模型：{model or "-"}；地址：{base_url or "-"}'
		if self._llm_config_status == 'error':
			return self._llm_config_error or '模型配置测试失败。'
		if self._llm_config_raw.strip():
			return '已粘贴配置，等待测试。'
		return '当前未配置模型。'

	def _mask_secret(self, value: str | None) -> str:
		if not value:
			return ''
		if len(value) <= 10:
			return '*' * len(value)
		return f'{value[:6]}***{value[-4:]}'

	def _llm_status_payload(self) -> dict[str, Any]:
		payload: dict[str, Any] = {
			'status': self._llm_config_status,
			'configured': self._configured_llm is not None,
			'error': self._llm_config_error or None,
			'raw_config': self._llm_config_raw,
			'status_text': self._llm_status_text(),
		}
		if self._llm_config_summary:
			payload['summary'] = self._llm_config_summary
		return payload

	def _build_llm_from_payload(self, body: dict[str, Any]) -> tuple[ChatAnthropic, dict[str, Any], str]:
		raw_config = body.get('config')
		if not isinstance(raw_config, str) or not raw_config.strip():
			raise RuntimeError('请先粘贴模型配置 JSON。')
		try:
			config = json.loads(raw_config)
		except json.JSONDecodeError as exc:
			raise RuntimeError('模型配置 JSON 解析失败，请检查格式。') from exc
		if not isinstance(config, dict):
			raise RuntimeError('模型配置必须是 JSON 对象。')
		env = config.get('env')
		if not isinstance(env, dict):
			raise RuntimeError('模型配置缺少 env 对象。')

		# Support both OpenAI and Anthropic formats
		openai_key = env.get('OPENAI_API_KEY')
		openai_base = env.get('OPENAI_BASE_URL') or env.get('OPENAI_API_BASE')
		openai_model = env.get('OPENAI_MODEL') or env.get('OPENAI_API_MODEL')
		auth_token = env.get('ANTHROPIC_AUTH_TOKEN') or env.get('ANTHROPIC_API_KEY')
		base_url = env.get('ANTHROPIC_BASE_URL')
		model = env.get('ANTHROPIC_MODEL') or env.get('ANTHROPIC_DEFAULT_SONNET_MODEL') or env.get('ANTHROPIC_DEFAULT_OPUS_MODEL') or env.get('ANTHROPIC_DEFAULT_HAIKU_MODEL')

		if openai_key and openai_base and openai_model:
			# OpenAI-compatible format
			profile = {
				'provider': 'openai',
				'model': openai_model.strip(),
				'api_key': openai_key.strip(),
				'base_url': openai_base.strip().rstrip('/'),
				'messages_path': '/v1/chat/completions',
			}
			api_key_for_summary = openai_key.strip()
			base_for_summary = openai_base.strip().rstrip('/')
			model_for_summary = openai_model.strip()
		elif auth_token and base_url and model:
			# Anthropic-compatible format
			profile = {
				'provider': 'anthropic',
				'model': model.strip(),
				'auth_token': auth_token.strip(),
				'base_url': base_url.strip().rstrip('/'),
				'auth_scheme': 'bearer',
				'auth_header_name': 'Authorization',
				'messages_path': '/v1/messages',
				'version_header_name': 'anthropic-version',
				'version_header_value': '2023-06-01',
			}
			api_key_for_summary = auth_token.strip()
			base_for_summary = base_url.strip().rstrip('/')
			model_for_summary = model.strip()
		else:
			raise RuntimeError('配置缺少必要字段。支持格式：\n'
				'OpenAI: OPENAI_API_KEY + OPENAI_BASE_URL + OPENAI_MODEL\n'
				'Anthropic: ANTHROPIC_AUTH_TOKEN + ANTHROPIC_BASE_URL + ANTHROPIC_MODEL')

		llm = self._build_llm_from_profile(profile)
		if llm is None:
			raise RuntimeError('模型配置构建失败。')
		summary = {
			'provider': profile['provider'],
			'model': model_for_summary,
			'base_url': base_for_summary,
			'token_preview': self._mask_secret(api_key_for_summary),
		}
		return llm, summary, raw_config

	async def _test_llm(self, llm: ChatAnthropic) -> None:
		try:
			await llm.ainvoke([UserMessage(content='Reply with OK only.')])
		except Exception as exc:
			raise RuntimeError(f'模型测试失败：{exc}') from exc

	def _build_response(self, status: int, payload: dict[str, Any]) -> web.Response:
		self._add_browser_target(payload)
		return web.json_response(payload, status=status)

	def _browser_target(self) -> dict[str, Any]:
		if self.daemon.use_cloud:
			return {'mode': 'cloud', 'visible': True, 'label': 'Cloud browser live preview'}
		if self.daemon.cdp_url:
			return {'mode': 'cdp', 'visible': True, 'label': 'Visible Chrome via CDP'}
		if self.daemon.profile:
			return {'mode': 'profile', 'visible': True, 'label': 'Visible Chrome profile'}
		return {'mode': 'virtual', 'visible': False, 'label': 'Headless browser'}

	def _connect_error(self, message: str) -> web.Response:
		return self._build_response(400, {'success': False, 'error': message, 'data': {}})

	def _build_daemon(self, *, headed: bool, profile: str | None, cdp_url: str | None, use_cloud: bool | None = None) -> Daemon:
		return Daemon(
			headed=headed,
			profile=profile,
			cdp_url=cdp_url,
			use_cloud=self._use_cloud if use_cloud is None else use_cloud,
			cloud_timeout=self._cloud_timeout,
			cloud_proxy_country_code=self._cloud_proxy_country_code,
			cloud_profile_id=self._cloud_profile_id,
			session=self._session_name,
		)

	def _requested_target(self, body: dict[str, Any]) -> tuple[str, str | None, str | None]:
		mode = body.get('mode') or 'current'
		manual_cdp_url = body.get('cdp_url') if isinstance(body.get('cdp_url'), str) else None
		profile = body.get('profile') if isinstance(body.get('profile'), str) else None
		return mode, manual_cdp_url, profile

	def _validate_manual_cdp_input(self, manual_cdp_url: str | None) -> None:
		if isinstance(manual_cdp_url, str) and manual_cdp_url.strip():
			parsed_url = urlparse(manual_cdp_url.strip())
			if parsed_url.scheme in ('ws', 'wss'):
				raise RuntimeError('CDP 地址应填写 http://127.0.0.1:9222 这样的 HTTP 地址，不要填写 ws:// 开头的 websocket 地址。')

	def _is_same_target(self, mode: str, manual_cdp_url: str | None, profile: str | None) -> bool:
		if mode == 'current':
			return True
		if mode == 'cdp':
			requested_cdp = manual_cdp_url.strip() if manual_cdp_url and manual_cdp_url.strip() else self.daemon.cdp_url
			return bool(self.daemon.cdp_url and requested_cdp == self.daemon.cdp_url)
		if mode == 'profile':
			requested_profile = profile.strip() if profile and profile.strip() else 'Default'
			return self.daemon.profile == requested_profile and not self.daemon.cdp_url and not self.daemon.use_cloud
		if mode == 'virtual':
			return not self.daemon.profile and not self.daemon.cdp_url and not self.daemon.use_cloud
		return False

	async def _get_tabs(self) -> list[dict[str, Any]]:
		session = self.daemon._session
		if session is None:
			return []
		state = await session.browser_session.get_browser_state_summary(include_screenshot=False)
		focused_target = session.browser_session.get_focused_target()
		return [
			{
				'index': idx,
				'tab_id': tab.target_id[-4:],
				'title': tab.title,
				'url': tab.url,
				'is_focused': bool(focused_target and tab.target_id == focused_target.target_id),
			}
			for idx, tab in enumerate(state.tabs)
		]

	async def _enrich_state_payload(self, payload: dict[str, Any]) -> None:
		if payload.get('success') and isinstance(payload.get('data'), dict):
			try:
				payload['data']['tabs'] = await self._get_tabs()
			except Exception:
				pass

	def _display_cdp_url(self, cdp_url: str | None) -> str | None:
		if not cdp_url:
			return None
		parsed_url = urlparse(cdp_url)
		if parsed_url.scheme in ('ws', 'wss'):
			http_scheme = 'https' if parsed_url.scheme == 'wss' else 'http'
			return urlunparse((http_scheme, parsed_url.netloc, '', '', '', ''))
		return urlunparse((parsed_url.scheme, parsed_url.netloc, '', '', '', '')) if parsed_url.netloc else cdp_url

	def _normalize_user_error(self, message: str) -> str:
		if 'BROWSER_USE_API_KEY' in message:
			return 'Natural-language automation requires BROWSER_USE_API_KEY. Please configure the API key first.'
		if 'non-JSON content' in message and 'ws://' in message:
			return 'CDP 地址应填写 http://127.0.0.1:9222 这样的 HTTP 地址，不要填写 ws:// 开头的 websocket 地址。'
		if 'did not return webSocketDebuggerUrl' in message and 'ws://' in message:
			return 'CDP 地址应填写 http://127.0.0.1:9222 这样的 HTTP 地址，不要填写 ws:// 开头的 websocket 地址。'
		if 'not reachable' in message:
			return '无法连接到 Chrome 调试地址。请先启动带 --remote-debugging-port=9222 的 Chrome，再填写 http://127.0.0.1:9222。'
		if 'timed out' in message:
			return '连接 Chrome 调试地址超时。请确认 Chrome 正常运行，并填写 http://127.0.0.1:9222。'
		return message

	def _normalize_cdp_url(self, cdp_url: str) -> str:
		parsed_url = urlparse(cdp_url)
		path = parsed_url.path.rstrip('/')
		if not path.endswith('/json/version'):
			path = path + '/json/version'
		return urlunparse((parsed_url.scheme, parsed_url.netloc, path, parsed_url.params, parsed_url.query, parsed_url.fragment))

	async def _probe_cdp_endpoint(self, cdp_url: str) -> dict[str, Any]:
		version_url = self._normalize_cdp_url(cdp_url)
		parsed_url = urlparse(version_url)
		is_localhost = parsed_url.hostname in ('localhost', '127.0.0.1', '::1')
		try:
			async with httpx.AsyncClient(timeout=httpx.Timeout(5.0), trust_env=not is_localhost) as client:
				response = await client.get(version_url)
		except httpx.ConnectError as exc:
			raise RuntimeError(
				f'Chrome CDP endpoint is not reachable at {version_url}. Start Chrome with --remote-debugging-port=9222 and confirm the URL returns DevTools JSON.'
			) from exc
		except httpx.TimeoutException as exc:
			raise RuntimeError(f'Chrome CDP endpoint timed out at {version_url}. Check whether Chrome remote debugging is healthy.') from exc
		except httpx.HTTPError as exc:
			raise RuntimeError(f'Chrome CDP endpoint request failed at {version_url}: {exc}') from exc

		if response.status_code != 200:
			raise RuntimeError(
				f'Chrome CDP endpoint returned HTTP {response.status_code} at {version_url}. Expected a DevTools /json/version response with webSocketDebuggerUrl.'
			)
		try:
			data = response.json()
		except ValueError as exc:
			raise RuntimeError(f'Chrome CDP endpoint returned non-JSON content at {version_url}.') from exc
		if not isinstance(data, dict) or not isinstance(data.get('webSocketDebuggerUrl'), str):
			raise RuntimeError(f'Chrome CDP endpoint at {version_url} did not return webSocketDebuggerUrl.')
		return {'version_url': version_url, 'web_socket_debugger_url': data['webSocketDebuggerUrl'], 'browser': data.get('Browser')}

	async def _resolve_cdp_url(self, manual_cdp_url: str | None) -> str:
		if isinstance(manual_cdp_url, str) and manual_cdp_url.strip():
			cdp_url = manual_cdp_url.strip()
			parsed_url = urlparse(cdp_url)
			if parsed_url.scheme in ('ws', 'wss'):
				raise RuntimeError('CDP 地址应填写 http://127.0.0.1:9222 这样的 HTTP 地址，不要填写 ws:// 开头的 websocket 地址。')
		else:
			try:
				cdp_url = discover_chrome_cdp_url()
			except RuntimeError as exc:
				raise RuntimeError(
					'Could not discover a visible Chrome CDP target. Start Chrome with --remote-debugging-port=9222 or provide a CDP URL such as http://127.0.0.1:9222.'
				) from exc
		await self._probe_cdp_endpoint(cdp_url)
		return cdp_url


	def _auto_launch_chrome(self, cdp_url: str) -> bool:
		"""Try to auto-launch Chrome with remote debugging if not already running."""
		import subprocess, sys, time as _time
		from urllib.parse import urlparse
		parsed = urlparse(cdp_url)
		port = parsed.port or 9222

		# Check if already running
		try:
			import urllib.request
			urllib.request.urlopen(f'http://127.0.0.1:{port}/json/version', timeout=2)
			return True  # already running
		except Exception:
			pass

		# Find Chrome executable
		import platform
		candidates = []
		if platform.system() == 'Windows':
			candidates = [
				r'C:\Program Files\Google\Chrome\Application\chrome.exe',
				r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
				os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe'),
			]
		elif platform.system() == 'Darwin':
			candidates = ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome']
		else:
			candidates = ['/usr/bin/google-chrome', '/usr/bin/chromium-browser', '/usr/bin/chromium']

		chrome_path = next((p for p in candidates if os.path.exists(p)), None)
		if not chrome_path:
			return False

		import tempfile
		user_data_dir = os.path.join(tempfile.gettempdir(), 'browser-use-chrome-profile')
		os.makedirs(user_data_dir, exist_ok=True)

		try:
			subprocess.Popen([
				chrome_path,
				f'--remote-debugging-port={port}',
				f'--user-data-dir={user_data_dir}',
				'--no-first-run',
				'--no-default-browser-check',
			], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
			# Wait for Chrome to start
			for _ in range(15):
				_time.sleep(0.5)
				try:
					urllib.request.urlopen(f'http://127.0.0.1:{port}/json/version', timeout=1)
					return True
				except Exception:
					pass
		except Exception:
			pass
		return False

	async def _ensure_connected_target(
		self,
		mode: str,
		manual_cdp_url: str | None = None,
		profile: str | None = None,
	) -> dict[str, Any]:
		resolved_manual_cdp_url = manual_cdp_url
		if mode == 'cdp':
			# Auto-launch Chrome if not running
			cdp_target = manual_cdp_url or self._chrome_cdp_url
			self._auto_launch_chrome(cdp_target)
			resolved_manual_cdp_url = await self._resolve_cdp_url(manual_cdp_url)
		should_rebuild = not self._is_same_target(mode, resolved_manual_cdp_url, profile)
		if should_rebuild:
			if self.daemon._session is not None:
				close_status, close_payload = await self._dispatch('shutdown')
				if not close_payload.get('success'):
					raise RuntimeError(close_payload.get('error') or f'Failed to shutdown current browser target ({close_status})')
			await self.daemon.shutdown()
			self.daemon = self._create_daemon(mode, manual_cdp_url=resolved_manual_cdp_url, profile=profile)

		status, payload = await self._dispatch('connect')
		if not payload.get('success'):
			raise RuntimeError(payload.get('error') or f'Failed to connect browser target ({status})')
		await self._enrich_state_payload(payload)
		if mode == 'cdp' and isinstance(payload.get('data'), dict):
			payload['data']['cdp_diagnostics'] = await self._probe_cdp_endpoint(resolved_manual_cdp_url or self.daemon.cdp_url or '')
		return payload

	async def _run_task_payload(
		self,
		task: str,
		max_steps: int = 25,
		mode: str | None = None,
		manual_cdp_url: str | None = None,
		profile: str | None = None,
		task_id: str | None = None,
	) -> dict[str, Any]:
		resolved_mode = mode or 'cdp'  # default to CDP (local Chrome) when no mode specified
		if resolved_mode == 'current':
			resolved_mode = self._browser_target()['mode']
		resolved_cdp_url = manual_cdp_url if resolved_mode == 'cdp' else None
		resolved_profile = profile if resolved_mode == 'profile' else None
		if self._configured_llm is None:
			raise RuntimeError('请先配置模型：在页面粘贴中转 API 的 JSON 配置并测试通过，或在 .env 文件中设置 ANTHROPIC_AUTH_TOKEN / ANTHROPIC_BASE_URL / ANTHROPIC_MODEL 环境变量后重启服务。')
		# Log actual LLM config being used for this task
		import logging as _logging
		_logger = _logging.getLogger('browser_use.skill_cli.http_server')
		_s = self._llm_config_summary
		_logger.info(f'[Task] LLM: provider={_s.get("provider")} model={_s.get("model")} base_url={_s.get("base_url")} token={_s.get("token_preview")}')
		connect_payload = await self._ensure_connected_target(
			resolved_mode,
			manual_cdp_url=resolved_cdp_url,
			profile=resolved_profile,
		)
		session = self.daemon._session
		if session is None:
			raise RuntimeError('Browser session was not created after connect')

		browser_session = session.browser_session
		browser_session.browser_profile.keep_alive = True
		is_headless = resolved_mode == 'virtual'

		# ── Task-id based tracing ────────────────────────────────────────────
		import time as _time, json as _json
		from pathlib import Path as _Path
		task_id = task_id or _time.strftime('%Y%m%d_%H%M%S')
		trace_dir = _Path('./traces') / task_id
		trace_dir.mkdir(parents=True, exist_ok=True)
		gif_path = str(trace_dir / 'recording.gif')
		conv_path = str(trace_dir / 'conversation.json')

		try:
			agent = Agent(
				task=task,
				llm=self._configured_llm,
				browser_session=browser_session,
				browser_profile=BrowserProfile(keep_alive=True, cdp_url=browser_session.cdp_url, headless=is_headless),
				enable_signal_handler=False,
				use_thinking=False,
				generate_gif=gif_path,
				save_conversation_path=conv_path,
			)
		except ValueError as exc:
			raise RuntimeError(str(exc)) from exc
		history = await agent.run(max_steps=max_steps)

		# Save structured trace
		# GLM models sometimes don't call done() explicitly — infer success from is_done + no errors
		raw_success = history.is_successful()
		if raw_success is None and history.is_done():
			errors = [e for e in (history.errors() or []) if e]
			raw_success = len(errors) == 0
		elif raw_success is None:
			# Not done: treat as failure (task didn't complete)
			raw_success = False
		trace = {
			'task_id': task_id,
			'task': task,
			'success': raw_success,
			'steps': history.number_of_steps(),
			'final_result': history.final_result(),
			'urls': history.urls(),
			'errors': history.errors(),
			'gif': gif_path,
			'conversation': conv_path,
		}
		with open(trace_dir / 'trace.json', 'w', encoding='utf-8') as f:
			_json.dump(trace, f, ensure_ascii=False, indent=2)

		payload: dict[str, Any] = {
			'success': raw_success,
			'is_done': bool(history.is_done()),
			'final_result': history.final_result() or '',
			'errors': [e for e in (history.errors() or []) if e],
			'urls': history.urls() or [],
			'steps': history.number_of_steps(),
			'task_id': task_id,
			'connected': connect_payload.get('data', {}),
		}
		state_status, state_payload = await self._dispatch('state')
		if state_payload.get('success'):
			await self._enrich_state_payload(state_payload)
			payload['state'] = state_payload.get('data', {})
		else:
			payload['state_error'] = state_payload.get('error') or f'Failed to read state ({state_status})'
		return payload

	def _add_browser_target(self, payload: dict[str, Any]) -> dict[str, Any]:
		if isinstance(payload.get('error'), str):
			payload['error'] = self._normalize_user_error(payload['error'])
		data = payload.get('data')
		if isinstance(data, dict):
			data['browser_target'] = self._browser_target()
			if isinstance(data.get('cdp_url'), str):
				data['cdp_url'] = self._display_cdp_url(data['cdp_url'])
			if isinstance(data.get('cdp_diagnostics'), dict):
				diagnostics = data['cdp_diagnostics']
				if isinstance(diagnostics.get('version_url'), str):
					diagnostics['version_url'] = self._display_cdp_url(diagnostics['version_url'])
				if isinstance(diagnostics.get('web_socket_debugger_url'), str):
					diagnostics['web_socket_debugger_url'] = self._display_cdp_url(diagnostics['web_socket_debugger_url'])
		return payload

	async def _dispatch(self, action: str, params: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
		response = await self.daemon.dispatch(
			{
				'id': f'http-{int(time.time() * 1000)}',
				'action': action,
				'params': params or {},
			}
		)
		status = 200 if response.get('success') else 400
		return status, response

	def _public_base_url(self) -> str:
		# When bound to 0.0.0.0, show localhost for display purposes
		display_host = '127.0.0.1' if self.host in ('0.0.0.0', '::') else self.host
		return f'http://{display_host}:{self.port}'

	async def index(self, request: web.Request) -> web.Response:
		base_url = self._public_base_url()
		cdp_url = self._chrome_cdp_url
		html = f"""<!doctype html>
<html lang="zh">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Self</title>
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg width='32' height='32' viewBox='0 0 52 64' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath fill-rule='evenodd' clip-rule='evenodd' d='M0.411091 50.172C-0.214959 49.4087 -0.078008 48.2852 0.691787 47.6671L7.98408 41.8121C8.62017 41.3013 9.55015 41.4167 10.0688 42.0463C15.022 48.0597 20.278 50.8436 26.0957 50.8436C31.8732 50.8436 36.9859 48.0991 41.7222 42.1525C42.2305 41.5142 43.1582 41.3822 43.8035 41.8816L51.1954 47.6021C51.976 48.2062 52.1332 49.3269 51.5203 50.1005C44.5175 58.9399 35.9435 63.5972 26.0957 63.5972C16.2766 63.5972 7.62609 58.969 0.411091 50.172Z' fill='%236647F0'/%3E%3Cpath fill-rule='evenodd' clip-rule='evenodd' d='M26.4487 17.1675C26.1739 16.9241 25.7606 16.924 25.4855 17.1672L9.62895 31.1882C9.02279 31.7242 8.09562 31.662 7.56651 31.0498L1.38195 23.8944C0.860213 23.2907 0.922623 22.3793 1.52177 21.8525L25.0072 1.19963C25.5562 0.716868 26.3783 0.716976 26.9271 1.19988L50.4178 21.8683C51.0173 22.3958 51.079 23.3081 50.556 23.9115L44.3565 31.0634C43.8267 31.6745 42.9001 31.7357 42.2946 31.1995L26.4487 17.1675Z' fill='%23FF02F0'/%3E%3C/svg%3E"/>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f5f5f5;color:#1a1a1a;min-height:100vh}}
.topbar{{background:#fff;border-bottom:1px solid #e5e7eb;padding:0 20px;height:52px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:10}}
.logo{{font-weight:700;font-size:16px;color:#111}}.logo span{{color:#7c3aed}}
.status-dot{{width:8px;height:8px;border-radius:50%;display:inline-block;margin-right:6px}}
.dot-ok{{background:#22c55e}}.dot-err{{background:#ef4444}}.dot-warn{{background:#f59e0b}}
.main{{max-width:860px;margin:0 auto;padding:20px 16px}}
.card{{background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:20px;margin-bottom:16px}}
.card-title{{font-size:14px;font-weight:600;color:#374151;margin-bottom:12px;display:flex;align-items:center;gap:6px}}
textarea,input[type=text],input[type=number]{{width:100%;border:1px solid #d1d5db;border-radius:8px;padding:10px 12px;font-size:14px;font-family:inherit;resize:vertical;outline:none;transition:border .15s}}
textarea:focus,input:focus{{border-color:#7c3aed;box-shadow:0 0 0 3px rgba(124,58,237,.1)}}
textarea{{min-height:80px}}
.row{{display:flex;gap:10px;margin-top:10px;flex-wrap:wrap;align-items:center}}
.btn{{border:none;border-radius:8px;padding:10px 18px;font-size:14px;font-weight:600;cursor:pointer;transition:all .15s;white-space:nowrap}}
.btn-primary{{background:#7c3aed;color:#fff}}.btn-primary:hover{{background:#6d28d9}}
.btn-primary:disabled{{background:#c4b5fd;cursor:not-allowed}}
.btn-secondary{{background:#f3f4f6;color:#374151}}.btn-secondary:hover{{background:#e5e7eb}}
.btn-sm{{padding:6px 12px;font-size:12px}}
.btn-danger{{background:#fee2e2;color:#b91c1c}}.btn-danger:hover{{background:#fecaca}}
.hint{{font-size:12px;color:#9ca3af;margin-top:6px;line-height:1.5}}
.result-area{{background:#111827;color:#e5eefc;border-radius:8px;padding:14px;font-size:12px;font-family:'Courier New',monospace;white-space:pre-wrap;word-break:break-word;max-height:300px;overflow:auto;margin-top:12px;display:none}}
.result-area.show{{display:block}}
.tag{{display:inline-flex;align-items:center;gap:4px;padding:4px 10px;border-radius:999px;font-size:12px;font-weight:700}}
.tag-pass{{background:#dcfce7;color:#166534;border:1px solid #86efac}}
.tag-fail{{background:#fee2e2;color:#991b1b;border:1px solid #fca5a5}}
.tag-run{{background:#ede9fe;color:#5b21b6}}
.progress{{display:none;align-items:center;gap:8px;margin-top:10px;font-size:13px;color:#7c3aed}}
.progress.show{{display:flex}}
.spinner{{width:16px;height:16px;border:2px solid #e9d5ff;border-top-color:#7c3aed;border-radius:50%;animation:spin .7s linear infinite}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
.history-list{{display:flex;flex-direction:column;gap:8px;max-height:360px;overflow:auto}}
.history-item{{border:1px solid #e5e7eb;border-radius:8px;padding:12px;cursor:pointer;transition:border .15s;display:flex;align-items:flex-start;gap:10px}}
.history-item:hover{{border-color:#7c3aed;background:#faf5ff}}
.history-item .task-text{{font-size:13px;font-weight:500;color:#111;flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.history-item .meta{{font-size:11px;color:#9ca3af;display:flex;gap:8px;align-items:center;margin-top:3px;flex-wrap:wrap}}
.llm-badge{{display:inline-flex;align-items:center;gap:4px;padding:4px 10px;background:#ede9fe;border-radius:6px;font-size:12px;color:#5b21b6;font-weight:500}}
.section-label{{font-size:11px;font-weight:600;color:#9ca3af;text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px;margin-top:12px}}
.section-label:first-child{{margin-top:0}}
.empty-state{{text-align:center;padding:32px;color:#9ca3af;font-size:13px}}
.trace-links{{display:flex;gap:12px;margin-top:10px;flex-wrap:wrap;align-items:center}}
.trace-links a{{font-size:12px;color:#7c3aed;text-decoration:none;font-weight:500}}
.trace-links a:hover{{text-decoration:underline}}
.tid{{font-size:11px;color:#6b7280;background:#f3f4f6;padding:2px 8px;border-radius:4px;font-family:monospace}}
/* Toast */
#toast{{position:fixed;bottom:24px;left:50%;transform:translateX(-50%) translateY(80px);background:#1f2937;color:#fff;padding:10px 20px;border-radius:8px;font-size:13px;font-weight:500;opacity:0;transition:all .3s;z-index:999;pointer-events:none}}
#toast.show{{opacity:1;transform:translateX(-50%) translateY(0)}}
#toast.toast-err{{background:#991b1b}}
#toast.toast-ok{{background:#166534}}
/* Replay panel */
.replay-panel{{margin-top:12px;padding:12px;background:#f9fafb;border-radius:8px;border:1px solid #e5e7eb}}
.replay-panel img{{width:100%;border-radius:6px;border:1px solid #e5e7eb}}
.step-list{{margin-top:8px;max-height:200px;overflow:auto;font-size:12px}}
.step-item{{padding:4px 8px;border-bottom:1px solid #f3f4f6;color:#374151}}
.step-item:last-child{{border-bottom:none}}
/* Collapse/expand animation */
.collapsible{{overflow:hidden;max-height:0;transition:max-height .3s ease,opacity .25s ease;opacity:0}}
.collapsible.expanded{{max-height:2000px;opacity:1}}
</style>
</head>
<body>
<div id="toast"></div>

<div class="topbar">
  <div class="logo">
    <svg width="100" height="28" viewBox="0 0 120 32" fill="none" xmlns="http://www.w3.org/2000/svg">
      <g transform="scale(0.5)">
        <path fill-rule="evenodd" clip-rule="evenodd" d="M0.411091 50.172C-0.214959 49.4087 -0.078008 48.2852 0.691787 47.6671L7.98408 41.8121C8.62017 41.3013 9.55015 41.4167 10.0688 42.0463C15.022 48.0597 20.278 50.8436 26.0957 50.8436C31.8732 50.8436 36.9859 48.0991 41.7222 42.1525C42.2305 41.5142 43.1582 41.3822 43.8035 41.8816L51.1954 47.6021C51.976 48.2062 52.1332 49.3269 51.5203 50.1005C44.5175 58.9399 35.9435 63.5972 26.0957 63.5972C16.2766 63.5972 7.62609 58.969 0.411091 50.172Z" fill="url(#sp0)"/>
        <path fill-rule="evenodd" clip-rule="evenodd" d="M26.4487 17.1675C26.1739 16.9241 25.7606 16.924 25.4855 17.1672L9.62895 31.1882C9.02279 31.7242 8.09562 31.662 7.56651 31.0498L1.38195 23.8944C0.860213 23.2907 0.922623 22.3793 1.52177 21.8525L25.0072 1.19963C25.5562 0.716868 26.3783 0.716976 26.9271 1.19988L50.4178 21.8683C51.0173 22.3958 51.079 23.3081 50.556 23.9115L44.3565 31.0634C43.8267 31.6745 42.9001 31.7357 42.2946 31.1995L26.4487 17.1675Z" fill="url(#sp1)"/>
      </g>
      <text x="34" y="22" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif" font-size="17" font-weight="700" fill="#111">Self</text>
      <defs>
        <linearGradient id="sp0" x1="-0.692871" y1="32.1384" x2="52.5993" y2="32.1384" gradientUnits="userSpaceOnUse"><stop offset="0.225962" stop-color="#6647F0"/><stop offset="0.793269" stop-color="#0091FF"/></linearGradient>
        <linearGradient id="sp1" x1="-0.692871" y1="31.621" x2="52.5993" y2="31.621" gradientUnits="userSpaceOnUse"><stop stop-color="#FF02F0"/><stop offset="0.778846" stop-color="#F76808"/><stop offset="1" stop-color="#F76808"/></linearGradient>
      </defs>
    </svg>
  </div>
  <div style="display:flex;align-items:center;gap:16px">
    <span id="llmBadge" class="llm-badge">⚙ 检查模型...</span>
  </div>
</div>

<div class="main">

  <!-- Task -->
  <div class="card">
    <div class="card-title"><span>🤖</span>自动化任务</div>
    <!-- Mode switcher -->
    <div style="display:flex;gap:0;margin-bottom:0;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden">
      <button id="modeLlmBtn" class="btn btn-sm" style="flex:1;border-radius:0;background:#7c3aed;color:#fff;padding:10px;font-size:13px" onclick="switchMode('llm')">🧠 LLM</button>
      <button id="modeDslBtn" class="btn btn-sm" style="flex:1;border-radius:0;background:#f3f4f6;color:#374151;padding:10px;font-size:13px" onclick="switchMode('dsl')">📝 NLP</button>
    </div>

    <!-- LLM mode -->
    <div id="llmModePanel" style="margin-top:14px">
      <!-- Usage hint -->
      <div style="margin-bottom:10px;padding:10px 12px;background:#f5f3ff;border-radius:8px;border-left:3px solid #7c3aed;font-size:12px;color:#5b21b6;line-height:1.7">
        <strong>使用说明：</strong>用自然语言描述任务，AI 自动控制浏览器逐步执行。<br/>
        <strong>适合：</strong>复杂动态场景、需要判断的任务。<strong>速度：</strong>每步 10-30s（需调用 LLM）。<br/>
        <strong>Demo：</strong><code style="background:#ede9fe;padding:1px 5px;border-radius:3px;cursor:pointer" onclick="document.getElementById('taskInput').value=this.textContent">打开必应，搜索耳机，查看前3个结果</code>
        &nbsp;<code style="background:#ede9fe;padding:1px 5px;border-radius:3px;cursor:pointer" onclick="document.getElementById('taskInput').value=this.textContent">打开 github.com，搜索 playwright</code>
      </div>
      <textarea id="taskInput" placeholder="描述任务，例如：打开必应，搜索耳机，查看前3个结果">打开必应，搜索耳机，查看前3个结果</textarea>
    </div>

    <!-- DSL mode -->
    <div id="dslModePanel" style="display:none;margin-top:14px">
      <!-- Usage hint -->
      <div style="margin-bottom:10px;padding:10px 12px;background:#eff6ff;border-radius:8px;border-left:3px solid #3b82f6;font-size:12px;color:#1e40af;line-height:1.7">
        <strong>使用说明：</strong>每行一条自然语言指令，直接映射为 Playwright 操作，无需 LLM，执行速度快（1-5s）。<br/>
        <strong>支持：</strong>打开/点击/输入/按键/等待/截图/滚动/悬停/获取文本/断言/iframe/多标签页 等全部 Playwright API。<br/>
        <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-top:6px">
          <strong>Demo：</strong>
          <code style="background:#dbeafe;padding:2px 8px;border-radius:4px;cursor:pointer" onclick="fillDslDemo('nav')">导航</code>
          <code style="background:#dbeafe;padding:2px 8px;border-radius:4px;cursor:pointer" onclick="fillDslDemo('click')">点击</code>
          <code style="background:#dbeafe;padding:2px 8px;border-radius:4px;cursor:pointer" onclick="fillDslDemo('input')">输入</code>
          <code style="background:#dbeafe;padding:2px 8px;border-radius:4px;cursor:pointer" onclick="fillDslDemo('form')">表单</code>
          <code style="background:#dbeafe;padding:2px 8px;border-radius:4px;cursor:pointer" onclick="fillDslDemo('select')">选择</code>
          <code style="background:#dbeafe;padding:2px 8px;border-radius:4px;cursor:pointer" onclick="fillDslDemo('scroll')">滚动</code>
          <code style="background:#dbeafe;padding:2px 8px;border-radius:4px;cursor:pointer" onclick="fillDslDemo('tabs')">标签页</code>
          <code style="background:#dbeafe;padding:2px 8px;border-radius:4px;cursor:pointer" onclick="fillDslDemo('wait')">等待</code>
          <code style="background:#dbeafe;padding:2px 8px;border-radius:4px;cursor:pointer" onclick="fillDslDemo('assert')">断言</code>
          <code style="background:#dbeafe;padding:2px 8px;border-radius:4px;cursor:pointer" onclick="fillDslDemo('popup')">弹窗</code>
          <code style="background:#dbeafe;padding:2px 8px;border-radius:4px;cursor:pointer" onclick="fillDslDemo('iframe')">iframe</code>
          <code style="background:#dbeafe;padding:2px 8px;border-radius:4px;cursor:pointer" onclick="fillDslDemo('drag')">拖拽</code>
          <code style="background:#dbeafe;padding:2px 8px;border-radius:4px;cursor:pointer" onclick="fillDslDemo('hover')">悬停</code>
          <code style="background:#dbeafe;padding:2px 8px;border-radius:4px;cursor:pointer" onclick="fillDslDemo('upload')">上传</code>
          <code style="background:#dbeafe;padding:2px 8px;border-radius:4px;cursor:pointer" onclick="fillDslDemo('js_exec')">JS执行</code>
          <span style="color:#d1d5db">|</span>
          <code style="background:#fef3c7;padding:2px 8px;border-radius:4px;cursor:pointer;font-weight:600" onclick="fillDslDemo('combo')">组合搜索</code>
          <code style="background:#fef3c7;padding:2px 8px;border-radius:4px;cursor:pointer;font-weight:600" onclick="fillDslDemo('combo_multi')">组合多页</code>
          <code style="background:#fef3c7;padding:2px 8px;border-radius:4px;cursor:pointer;font-weight:600" onclick="fillDslDemo('combo_form')">组合表单</code>
          <button onclick="showDslDocs()" style="border:none;background:#3b82f6;color:#fff;border-radius:4px;padding:2px 10px;font-size:11px;font-weight:600;cursor:pointer;margin-left:4px">📖 查看文档</button>
        </div>
      </div>
      <!-- Codegen recorder -->
      <div style="margin-bottom:12px;padding:12px;background:#f0fdf4;border:1px solid #86efac;border-radius:8px">
        <div style="font-size:12px;font-weight:600;color:#166534;margin-bottom:8px">🎬 录制生成 DSL（可选）</div>
        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
          <input type="text" id="dslCodegenUrl" placeholder="录制起始 URL（如 https://bing.com）" style="flex:1;min-width:180px;font-size:13px"/>
          <button id="dslCodegenBtn" class="btn btn-sm" style="background:#16a34a;color:#fff;white-space:nowrap" onclick="toggleDslCodegen()">● 开始录制</button>
        </div>
        <div id="dslCodegenStatus" style="margin-top:8px;font-size:12px;color:#6b7280;display:none"></div>
      </div>
      <!-- Parameterization -->
      <div id="paramPanel" style="display:none;margin-bottom:10px;padding:12px;background:#fff7ed;border-radius:8px;border:1px solid #fed7aa">
        <div style="font-size:12px;font-weight:600;color:#9a3412;margin-bottom:6px">📊 参数化 - 用同一套指令测试多组数据</div>
        <div style="font-size:11px;color:#9a3412;margin-bottom:8px;line-height:1.6">
          <strong>步骤 1：</strong>在指令中使用 <code style="background:#fef3c7;padding:1px 4px;border-radius:3px">${{变量名}}</code> 作为占位符<br/>
          <strong>步骤 2：</strong>在下方表格填写变量名和数据，系统会自动替换并依次执行<br/>
          <strong>示例：</strong>指令中写 <code style="background:#fef3c7;padding:1px 4px;border-radius:3px">输入 #q ${{keyword}}</code>，下方填入 keyword 的值即可
        </div>
        <div style="display:flex;gap:4px;margin-bottom:6px;align-items:center">
          <span style="font-size:11px;color:#6b7280;white-space:nowrap">变量名（逗号分隔）：</span>
          <input type="text" id="paramHeaders" placeholder="keyword, url" style="flex:1;font-size:12px;padding:4px 8px;border:1px solid #fed7aa;border-radius:4px"/>
        </div>
        <div style="font-size:11px;color:#6b7280;margin-bottom:4px">每组数据占一行（逗号分隔，顺序和变量名对应）：</div>
        <textarea id="paramData" placeholder="耳机, https://cn.bing.com&#10;手机, https://cn.bing.com&#10;电脑, https://cn.bing.com" style="min-height:80px;font-family:monospace;font-size:12px;width:100%;border:1px solid #fed7aa;border-radius:6px;padding:8px"></textarea>
        <div style="margin-top:6px;display:flex;gap:6px">
          <button onclick="fillParamExample()" style="border:none;background:#fdba74;color:#7c2d12;border-radius:4px;padding:3px 10px;font-size:11px;cursor:pointer">填入示例</button>
        </div>
      </div>
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
        <span style="font-size:11px;font-weight:600;color:#9ca3af;text-transform:uppercase;letter-spacing:.05em">NLP 指令（每行一条）</span>
        <div style="display:flex;gap:6px">
          <button onclick="toggleParamPanel()" id="paramBtn" style="border:none;background:#fff7ed;color:#9a3412;border-radius:6px;padding:3px 8px;font-size:11px;font-weight:600;cursor:pointer">📊 参数化</button>
          <button onclick="convertDslFromPw()" style="border:none;background:#ede9fe;color:#5b21b6;border-radius:6px;padding:3px 8px;font-size:11px;font-weight:600;cursor:pointer">↩ 从PW转换</button>
        </div>
      </div>
      <textarea id="dslScript" placeholder="打开 https://bing.com&#10;等待加载完成&#10;点击 文本=搜索&#10;输入 #sb_form_q 耳机&#10;按键 Enter&#10;等待加载完成&#10;截图" style="min-height:160px;font-family:monospace;font-size:13px;line-height:1.8"></textarea>
      <!-- DSL reference -->
      <div style="margin-top:8px;padding:10px;background:#f8faff;border-radius:6px;border:1px solid #c7d2fe;font-size:11px;color:#3730a3;line-height:2">
        <strong style="font-size:12px">📖 指令速查：</strong><br/>
        <code>打开 https://bing.com</code> &nbsp;·&nbsp; <code>等待加载完成</code> &nbsp;·&nbsp; <code>截图</code><br/>
        <code>点击 文本=登录</code> &nbsp;·&nbsp; <code>点击 role=button[name=提交]</code> &nbsp;·&nbsp; <code>点击 #id</code><br/>
        <code>输入 #id 内容</code> &nbsp;·&nbsp; <code>按键 Enter</code> &nbsp;·&nbsp; <code>滚动 下</code> &nbsp;·&nbsp; <code>断言可见 #el</code>
      </div>
    </div>

    <div class="row" style="margin-top:12px">
      <button class="btn btn-primary" id="runBtn" onclick="runTask()">▶ 执行指令</button>
      <button class="btn btn-secondary btn-sm" id="advBtn" onclick="toggleAdvanced()">⚙ 高级选项</button>
      <div id="nlpExportBtns" style="display:none;gap:6px;display:flex">
        <button class="btn btn-secondary btn-sm" onclick="exportYaml()">📄 导出 YAML</button>
        <button class="btn btn-secondary btn-sm" onclick="exportPytest()">🧪 导出 pytest</button>
      </div>
    </div>
    <div id="advancedPanel" style="display:none;margin-top:14px;padding-top:14px;border-top:1px solid #f3f4f6">
      <div class="section-label">浏览器模式</div>
      <div style="display:flex;gap:0;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;margin-bottom:10px">
        <button id="headlessBtn" class="btn btn-sm" style="flex:1;border-radius:0;background:#7c3aed;color:#fff;padding:8px" onclick="setBrowserMode('headless')">🔇 无头模式（后台）</button>
        <button id="headedBtn" class="btn btn-sm" style="flex:1;border-radius:0;background:#f3f4f6;color:#374151;padding:8px" onclick="setBrowserMode('headed')">👁 有头模式（可见）</button>
      </div>
      <div id="browserModeHint" style="font-size:11px;color:#6b7280;margin-bottom:10px">当前：无头模式，浏览器在后台运行，不显示窗口</div>
      <!-- Multi-browser -->
      <div style="margin-bottom:10px">
        <div style="display:flex;gap:8px;align-items:center">
          <label style="font-size:12px;color:#374151;cursor:pointer;display:flex;align-items:center;gap:6px">
            <input type="checkbox" id="multiBrowserCheck" onchange="toggleMultiBrowser()" style="margin-right:0"/>
            主从浏览器并行执行
          </label>
          <button id="scanBrowserBtn" onclick="scanBrowsers()" style="border:none;background:#ede9fe;color:#5b21b6;border-radius:6px;padding:3px 10px;font-size:11px;font-weight:600;cursor:pointer">🔍 自动发现</button>
        </div>
      </div>
      <div id="multiBrowserPanel" style="display:none;margin-bottom:10px;padding:12px;background:#f5f3ff;border-radius:8px;border:1px solid #ddd6fe">
        <div style="font-size:12px;font-weight:600;color:#5b21b6;margin-bottom:8px">已发现的浏览器实例</div>
        <div id="browserList" style="min-height:30px">
          <div style="font-size:11px;color:#9ca3af">点击「自动发现」扫描本地浏览器...</div>
        </div>
        <div style="margin-top:8px;font-size:11px;color:#6b7280">
          <span>或手动添加：</span>
          <div style="display:flex;gap:6px;margin-top:4px">
            <input type="text" id="manualCdpUrl" placeholder="http://127.0.0.1:9222" style="flex:1;font-size:12px;padding:4px 8px;border:1px solid #d1d5db;border-radius:4px"/>
            <button onclick="addManualBrowser()" style="border:none;background:#7c3aed;color:#fff;border-radius:4px;padding:4px 10px;font-size:11px;cursor:pointer">+ 添加</button>
          </div>
        </div>
      </div>
      <!-- Network capture -->
      <div style="margin-bottom:10px">
        <label style="font-size:12px;color:#374151;cursor:pointer">
          <input type="checkbox" id="captureNetworkCheck" style="margin-right:6px" checked/>
          捕获接口请求（过滤 JS/CSS/图片）
        </label>
      </div>
      <div class="section-label">Task ID</div>
      <div style="display:flex;gap:8px;align-items:center">
        <input type="text" id="taskIdInput" placeholder="自动生成（如 001、002...）" style="flex:1"/>
      </div>
      <div id="llmAdvanced">
        <div class="section-label">最大步骤数</div>
        <input type="number" id="maxStepsInput" value="25" min="1" max="100"/>
      </div>
    </div>
    <div class="progress" id="progress">
      <div class="spinner"></div>
      <span id="progressText">正在执行...</span>
    </div>
    <div id="logArea" style="display:none;margin-top:12px;padding:10px;background:#f9fafb;border-radius:8px;border:1px solid #e5e7eb;max-height:300px;overflow:auto;font-size:12px;color:#374151"></div>
  </div>

  <!-- Export Modal -->
  <div id="exportModal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:100;overflow:auto;padding:20px">
    <div style="background:#fff;border-radius:12px;max-width:700px;margin:0 auto;padding:24px;position:relative">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
        <h2 id="exportModalTitle" style="font-size:16px;font-weight:700;color:#111">导出</h2>
        <button onclick="document.getElementById('exportModal').style.display='none'" style="border:none;background:#f3f4f6;border-radius:6px;padding:6px 12px;cursor:pointer">✕ 关闭</button>
      </div>
      <textarea id="exportContent" style="width:100%;min-height:350px;font-family:monospace;font-size:12px;border:1px solid #d1d5db;border-radius:8px;padding:12px" readonly></textarea>
      <div id="exportRunResult" style="display:none;margin-top:10px;padding:10px;background:#f0fdf4;border:1px solid #86efac;border-radius:8px;max-height:200px;overflow:auto;font-size:12px"></div>
      <div style="margin-top:10px;display:flex;gap:8px">
        <button class="btn btn-primary btn-sm" onclick="copyExport()">📋 复制</button>
        <button class="btn btn-secondary btn-sm" onclick="downloadExport()">⬇ 下载</button>
        <button class="btn btn-sm" id="exportRunBtn" style="background:#059669;color:#fff" onclick="runExportedDsl()">▶ 执行并查看结果</button>
      </div>
    </div>
  </div>

  <!-- Result -->
  <div class="card" id="resultCard" style="display:none">
    <div class="card-title" style="justify-content:space-between">
      <span><span>📋</span>执行结果</span>
      <span id="resultTag" class="tag"></span>
    </div>
    <div id="taskIdDisplay" style="margin-bottom:8px"></div>
    <div id="resultText" style="font-size:13px;line-height:1.7;color:#374151;white-space:pre-wrap"></div>
    <div class="trace-links" id="traceLinks"></div>
    <!-- Replay panel (shown in advanced mode) -->
    <div id="replayPanel" class="replay-panel" style="display:none">
      <div style="font-size:12px;font-weight:600;color:#374151;margin-bottom:8px">🎬 GIF 回放</div>
      <img id="replayGif" src="" alt="GIF 回放"/>
      <div id="stepList" class="step-list"></div>
    </div>
    <div class="result-area" id="resultRaw"></div>
    <div class="row" style="margin-top:8px">
      <button class="btn btn-secondary btn-sm" onclick="toggleRaw()">原始数据</button>
    </div>
  </div>

  <!-- LLM Config — only shown in LLM mode -->
  <div class="card" id="llmCard" style="display:none">
    <div class="card-title" style="justify-content:space-between;cursor:pointer" onclick="toggleLlmCard()">
      <span><span>🔑</span>模型配置</span>
      <span id="llmCollapseIcon" style="font-size:16px;color:#9ca3af">▼</span>
    </div>
    <div id="llmStatus" class="hint" style="margin-bottom:12px">检查中...</div>
    <div id="llmManualArea" class="collapsible">
      <!-- Tab switcher -->
      <div style="display:flex;gap:0;margin-bottom:12px;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden">
        <button id="tabSimple" class="btn btn-sm" style="flex:1;border-radius:0;background:#7c3aed;color:#fff" onclick="switchTab('simple')">简单配置</button>
        <button id="tabJson" class="btn btn-sm" style="flex:1;border-radius:0;background:#f3f4f6;color:#374151" onclick="switchTab('json')">JSON 配置</button>
      </div>
      <!-- Simple fields -->
      <div id="simplePanel">
        <div class="section-label">API 地址（Base URL）</div>
        <input type="text" id="cfgUrl" placeholder="https://api.openai.com 或中转地址" style="margin-bottom:8px"/>
        <div class="section-label">API Key</div>
        <div style="display:flex;gap:8px;margin-bottom:8px">
          <input type="text" id="cfgKey" placeholder="sk-..." style="flex:1"/>
          <button id="keyToggleBtn" class="btn btn-secondary btn-sm" onclick="toggleApiKeyVisibility()" style="padding:8px 12px">👁 显示</button>
        </div>
        <div class="section-label">模型名称</div>
        <input type="text" id="cfgModel" placeholder="gpt-4o / glm-5.1 / claude-3-5-sonnet-20241022" style="margin-bottom:4px"/>
        <div class="hint">官方 OpenAI：https://api.openai.com &nbsp;|&nbsp; 官方 Anthropic：https://api.anthropic.com</div>
      </div>
      <!-- JSON panel -->
      <div id="jsonPanel" style="display:none">
        <div class="hint" style="margin-bottom:8px">支持 OpenAI 格式（OPENAI_API_KEY）和 Anthropic 格式（ANTHROPIC_AUTH_TOKEN）</div>
        <textarea id="llmJson" placeholder='{{"env":{{"OPENAI_API_KEY":"sk-...","OPENAI_BASE_URL":"https://...","OPENAI_MODEL":"gpt-4o"}}}}' style="min-height:100px;font-family:monospace;font-size:12px"></textarea>
      </div>
      <div class="row" style="margin-top:10px">
        <button id="testLlmBtn" class="btn btn-primary btn-sm" onclick="testLlm(this)">保存并测试</button>
      </div>
    </div>
  </div>

  <!-- History — only shown in LLM mode -->
  <div class="card" id="historyCard" style="display:none">
    <div class="card-title" style="justify-content:space-between">
      <span><span>📜</span>历史记录</span>
      <div style="display:flex;gap:8px">
        <button class="btn btn-secondary btn-sm" onclick="loadHistory()">刷新</button>
        <button class="btn btn-danger btn-sm" onclick="clearHistory()">清空</button>
      </div>
    </div>
    <div class="history-list" id="historyList">
      <div class="empty-state">暂无历史记录</div>
    </div>
  </div>

</div>

<!-- DSL Docs Modal -->
<div id="dslDocsModal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:100;overflow:auto;padding:20px">
  <div style="background:#fff;border-radius:12px;max-width:780px;margin:0 auto;padding:24px;position:relative">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
      <h2 style="font-size:16px;font-weight:700;color:#111">📖 自然语言指令完整文档</h2>
      <button onclick="document.getElementById('dslDocsModal').style.display='none'" style="border:none;background:#f3f4f6;border-radius:6px;padding:6px 12px;cursor:pointer;font-size:13px">✕ 关闭</button>
    </div>
    <div style="font-size:12px;color:#6b7280;margin-bottom:16px;padding:8px 12px;background:#f9fafb;border-radius:6px">
      每行一条指令，直接映射为 Playwright API 调用，无需 LLM，执行速度与原生 Playwright 脚本一致（1-5s）。
    </div>
    <div id="dslDocsContent" style="font-size:13px;line-height:1.8;color:#374151"></div>
  </div>
</div>

<script>
const BASE = '{base_url}';
const CDP_URL = '{cdp_url}';
let rawVisible = false;
let advancedOpen = false;
let taskCounter = 0;  // auto-increment task id

// ── Toast ─────────────────────────────────────────────────────────────────
function toast(msg, type='', duration=2000) {{
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = 'show' + (type ? ' toast-'+type : '');
  clearTimeout(el._t);
  el._t = setTimeout(() => {{ el.className = ''; }}, duration);
}}

// ── Init ──────────────────────────────────────────────────────────────────
let currentMode = 'llm';

const MODE_DESC = {{
  llm: '',
  dsl: '',
  playwright: ''
}};

function switchMode(mode) {{
  currentMode = mode;
  document.getElementById('llmModePanel').style.display = mode === 'llm' ? 'block' : 'none';
  document.getElementById('dslModePanel').style.display = mode === 'dsl' ? 'block' : 'none';
  document.getElementById('llmAdvanced').style.display = mode === 'llm' ? 'block' : 'none';
  // LLM-only cards
  const llmOnly = mode === 'llm';
  document.getElementById('llmCard').style.display = llmOnly ? 'block' : 'none';
  document.getElementById('historyCard').style.display = llmOnly ? 'block' : 'none';
  // Button styles
  const btns = {{ llm: 'modeLlmBtn', dsl: 'modeDslBtn' }};
  Object.entries(btns).forEach(([m, id]) => {{
    const el = document.getElementById(id);
    if (!el) return;
    el.style.background = m === mode ? '#7c3aed' : '#f3f4f6';
    el.style.color = m === mode ? '#fff' : '#374151';
  }});
  // Update run button label
  const runBtn = document.getElementById('runBtn');
  if (runBtn) {{
    runBtn.textContent = mode === 'dsl' ? '▶ 执行指令' : '▶ 开始执行';
  }}
  _updateExportBtns();
}}

const DSL_DEMOS = {{
  nav: '# 导航全覆盖：打开/返回/前进/刷新/等待\\n打开 https://cn.bing.com\\n等待加载完成\\n获取标题\\n获取URL\\n打开 https://github.com\\n等待加载完成\\n获取标题\\n返回\\n等待加载完成\\n获取标题\\n前进\\n等待加载完成\\n获取标题\\n刷新\\n等待加载完成\\n截图',
  click: '# 点击全覆盖：文本/CSS/悬停/双击/右键\\n打开 https://cn.bing.com\\n等待加载完成\\n悬停 #sb_form_q\\n点击 #sb_form_q\\n输入 #sb_form_q 耳机\\n按键 Enter\\n等待加载完成\\n断言URL包含 search\\n截图\\n滚动到 #b_results\\n截图',
  input: '# 输入全覆盖：CSS/文本/placeholder/清空/快捷键/输入文字\\n打开 https://cn.bing.com\\n等待加载完成\\n点击 #sb_form_q\\n输入 #sb_form_q 测试内容\\n截图\\n清空 #sb_form_q\\n截图\\n输入 #sb_form_q playwright\\n快捷键 Control+A\\n输入文字 browser automation\\n按键 Enter\\n等待加载完成\\n截图',
  form: '# 表单全覆盖：文本/tel/email/radio/checkbox/select/time/textarea/文件上传\\n打开 https://httpbin.org/forms/post\\n等待加载完成\\n# 文本输入\\n输入 文本=Customer name 张三\\n输入 文本=Telephone 13800138000\\n输入 文本=E-mail address test@example.com\\n截图\\n# 单选按钮（radio）\\n点击 文本=Medium\\n截图\\n# 复选框（checkbox）\\n勾选 文本=Bacon\\n勾选 文本=Extra Cheese\\n勾选 文本=Onion\\n勾选 文本=Mushroom\\n截图\\n# 取消勾选\\n取消勾选 文本=Extra Cheese\\n截图\\n# 时间选择器\\n输入 [type=time] 12:30\\n截图\\n# 文本域\\n输入 文本=Delivery instructions 请在12点前送达，谢谢！\\n截图\\n# 断言并提交\\n断言可见 文本=Submit order\\n点击 文本=Submit order\\n等待加载完成\\n断言URL包含 post\\n截图',
  assert: '# 断言+获取+JS全覆盖\\n打开 https://cn.bing.com\\n等待加载完成\\n断言标题包含 必应\\n断言URL包含 bing\\n获取标题\\n获取URL\\n执行JS document.title\\n执行JS window.location.href\\n执行JS document.querySelectorAll("a").length\\n输入 #sb_form_q playwright\\n按键 Enter\\n等待加载完成\\n等待 #b_results\\n断言可见 #b_results\\n获取文本 #b_tween\\n截图',
  scroll: '# 滚动全覆盖：上/下/顶/底/到元素\\n打开 https://cn.bing.com\\n等待加载完成\\n截图\\n滚动 下\\n截图\\n滚动 下\\n截图\\n滚动到底部\\n截图\\n滚动到顶部\\n截图\\n输入 #sb_form_q 滚动测试\\n按键 Enter\\n等待加载完成\\n滚动到 #b_results\\n截图\\n滚动 上\\n截图',
  tabs: '# 多标签页全覆盖：新建/切换/关闭\\n打开 https://cn.bing.com\\n等待加载完成\\n获取标题\\n截图\\n新标签页 https://github.com\\n等待加载完成\\n获取标题\\n截图\\n新标签页 https://httpbin.org\\n等待加载完成\\n获取标题\\n截图\\n切换标签页 1\\n获取标题\\n截图\\n关闭标签页\\n切换标签页 0\\n获取标题\\n截图',
  wait: '# 等待全覆盖：加载/元素/消失/网络\\n打开 https://cn.bing.com\\n等待加载完成\\n等待 #sb_form_q\\n输入 #sb_form_q 等待测试\\n按键 Enter\\n等待网络空闲\\n等待 #b_results\\n断言可见 #b_results\\n截图\\n等待 2000\\n截图',
  popup: '# 弹窗处理：alert/confirm/prompt\\n打开 https://the-internet.herokuapp.com/javascript_alerts\\n等待加载完成\\n截图\\n# 点击触发 alert\\n点击 文本=Click for JS Alert\\n接受弹窗\\n等待 1000\\n断言可见 #result\\n截图\\n# 点击触发 confirm\\n点击 文本=Click for JS Confirm\\n取消弹窗\\n等待 1000\\n获取文本 #result\\n截图\\n# 点击触发 prompt\\n点击 文本=Click for JS Prompt\\n接受弹窗\\n等待 1000\\n获取文本 #result\\n截图',
  iframe: '# iframe 操作：进入/退出/内部交互\\n打开 https://the-internet.herokuapp.com/iframe\\n等待加载完成\\n截图\\n进入iframe #mce_0_ifr\\n获取文本 #tinymce\\n清空 #tinymce\\n输入 #tinymce Hello from iframe!\\n退出iframe\\n截图',
  drag: '# 拖拽操作：drag and drop\\n打开 https://the-internet.herokuapp.com/drag_and_drop\\n等待加载完成\\n截图\\n拖拽 #column-a 到 #column-b\\n等待 1000\\n截图\\n拖拽 #column-b 到 #column-a\\n等待 1000\\n截图',
  combo: '# 组合场景：导航+搜索+滚动+断言+截图+获取\\n打开 https://cn.bing.com\\n等待加载完成\\n获取标题\\n输入 #sb_form_q playwright automation\\n点击 文本=搜索\\n等待网络空闲\\n断言URL包含 search\\n获取文本 #b_tween\\n滚动 下\\n滚动 下\\n滚动到底部\\n截图\\n滚动到顶部\\n截图\\n获取URL\\n执行JS document.querySelectorAll(".b_algo").length\\n返回\\n等待加载完成\\n断言标题包含 必应\\n截图',
  combo_multi: '# 多标签页组合：搜索+多页面+切换+关闭\\n打开 https://cn.bing.com\\n等待加载完成\\n输入 #sb_form_q browser automation\\n按键 Enter\\n等待加载完成\\n截图\\n新标签页 https://github.com/microsoft/playwright\\n等待加载完成\\n获取标题\\n截图\\n新标签页 https://httpbin.org/forms/post\\n等待加载完成\\n输入 文本=Customer name Test\\n截图\\n切换标签页 1\\n获取标题\\n截图\\n切换标签页 0\\n获取标题\\n截图',
  combo_form: '# 表单+断言+JS 组合场景\\n打开 https://httpbin.org/forms/post\\n等待加载完成\\n执行JS document.querySelectorAll("input").length\\n输入 文本=Customer name 李四\\n输入 文本=Telephone 13900139000\\n输入 文本=E-mail address lisi@test.com\\n点击 文本=Large\\n勾选 文本=Bacon\\n勾选 文本=Mushroom\\n输入 文本=Delivery instructions 加辣\\n断言可见 文本=Submit order\\n截图\\n点击 文本=Submit order\\n等待加载完成\\n断言URL包含 post\\n执行JS document.body.innerText\\n截图',
  select: '# 下拉选择操作\\n打开 https://the-internet.herokuapp.com/dropdown\\n等待加载完成\\n截图\\n选择 #dropdown 1\\n截图\\n获取属性 #dropdown value\\n选择 #dropdown 2\\n截图\\n获取属性 #dropdown value',
  upload: '# 文件上传操作\\n打开 https://the-internet.herokuapp.com/upload\\n等待加载完成\\n截图\\n上传文件 #file-upload C:\\\\Users\\\\test\\\\sample.txt\\n点击 文本=Upload\\n等待加载完成\\n断言可见 文本=File Uploaded\\n截图',
  hover: '# 悬停操作：hover menu\\n打开 https://the-internet.herokuapp.com/hovers\\n等待加载完成\\n截图\\n悬停 文本=Hover\\n等待 500\\n截图\\n点击 文本=View profile\\n等待加载完成\\n获取URL\\n截图',
  js_exec: '# JS执行：自定义操作\\n打开 https://cn.bing.com\\n等待加载完成\\n执行JS document.title\\n执行JS window.innerWidth + "x" + window.innerHeight\\n执行JS navigator.userAgent\\n执行JS document.cookie\\n执行JS localStorage.setItem("test","value")\\n执行JS localStorage.getItem("test")\\n执行JS window.scrollTo(0, 500)\\n执行JS document.querySelector("#sb_form_q").value = "注入内容"\\n截图'
}};

function fillDslDemo(name) {{
  const script = DSL_DEMOS[name];
  if (script) {{
    document.getElementById('dslScript').value = script.replace(/\\\\n/g, '\\n');
    toast('Demo 已填入，点击「执行指令」运行', 'ok', 2500);
  }}
}}

function showDslDocs() {{
  document.getElementById('dslDocsContent').innerHTML = getDslDocsHtml();
  document.getElementById('dslDocsModal').style.display = 'block';
}}

function getDslDocsHtml() {{
  const sections = [
    {{
      title: '🌐 导航',
      rows: [
        ['打开 <url>', 'page.goto(url)', '打开 https://bing.com'],
        ['返回', 'page.go_back()', '返回'],
        ['前进', 'page.go_forward()', '前进'],
        ['刷新', 'page.reload()', '刷新'],
        ['等待加载完成', 'wait_for_load_state("networkidle")', '等待加载完成'],
        ['等待 <ms>', '等待 N 毫秒后继续（转为状态等待）', '等待 2000'],
      ]
    }},
    {{
      title: '🖱️ 点击 / 交互',
      rows: [
        ['点击 <selector>', 'locator.click()', '点击 #login-btn'],
        ['点击 文本=<text>', 'get_by_text(text).click()', '点击 文本=登录'],
        ['点击 role=<role>[name=<n>]', 'get_by_role(role,name=n).click()', '点击 role=button[name=提交]'],
        ['点击 placeholder=<p>', 'get_by_placeholder(p).click()', '点击 placeholder=搜索'],
        ['点击 label=<l>', 'get_by_label(l).click()', '点击 label=用户名'],
        ['点击 testid=<id>', 'get_by_test_id(id).click()', '点击 testid=submit'],
        ['点击 xpath=<expr>', 'locator("xpath=...").click()', '点击 xpath=//button[@type="submit"]'],
        ['双击 <selector>', 'locator.dbl_click()', '双击 #item'],
        ['右键 <selector>', 'locator.click(button="right")', '右键 文本=文件'],
        ['悬停 <selector>', 'locator.hover()', '悬停 文本=菜单'],
        ['拖拽 <src> 到 <dst>', 'drag_and_drop(src, dst)', '拖拽 #item1 到 #target'],
      ]
    }},
    {{
      title: '⌨️ 输入 / 键盘',
      rows: [
        ['输入 <selector> <value>', 'locator.fill(value)', '输入 #username 张三'],
        ['输入 文本=<t> <value>', 'get_by_text(t).fill(value)', '输入 文本=搜索框 耳机'],
        ['输入 placeholder=<p> <v>', 'get_by_placeholder(p).fill(v)', '输入 placeholder=邮箱 test@test.com'],
        ['清空 <selector>', 'locator.clear()', '清空 #search'],
        ['按键 <key>', 'keyboard.press(key)', '按键 Enter'],
        ['按键 <key>', '支持所有按键', '按键 Tab / Escape / ArrowDown / F5'],
        ['输入文字 <text>', 'keyboard.type(text)', '输入文字 Hello World'],
        ['快捷键 <combo>', 'keyboard.press(combo)', '快捷键 Control+A'],
      ]
    }},
    {{
      title: '⏳ 等待',
      rows: [
        ['等待加载完成', 'wait_for_load_state("networkidle")', '等待加载完成'],
        ['等待 <selector>', 'locator.wait_for(state="visible")', '等待 #result'],
        ['等待 文本=<t>', 'get_by_text(t).wait_for()', '等待 文本=加载完成'],
        ['等待消失 <selector>', 'locator.wait_for(state="hidden")', '等待消失 .loading'],
        ['等待 <ms>', '转为状态等待（不阻塞）', '等待 3000'],
        ['等待网络空闲', 'wait_for_load_state("networkidle")', '等待网络空闲'],
      ]
    }},
    {{
      title: '📜 滚动',
      rows: [
        ['滚动 下', 'evaluate("window.scrollBy(0,600)")', '滚动 下'],
        ['滚动 上', 'evaluate("window.scrollBy(0,-600)")', '滚动 上'],
        ['滚动到底部', 'evaluate("window.scrollTo(0,document.body.scrollHeight)")', '滚动到底部'],
        ['滚动到顶部', 'evaluate("window.scrollTo(0,0)")', '滚动到顶部'],
        ['滚动到 <selector>', 'locator.scroll_into_view_if_needed()', '滚动到 #footer'],
      ]
    }},
    {{
      title: '📋 表单',
      rows: [
        ['选择 <selector> <value>', 'locator.select_option(value)', '选择 #country 中国'],
        ['勾选 <selector>', 'locator.check()', '勾选 #agree'],
        ['取消勾选 <selector>', 'locator.uncheck()', '取消勾选 #newsletter'],
        ['上传文件 <selector> <path>', 'locator.set_input_files(path)', '上传文件 #file /tmp/test.pdf'],
      ]
    }},
    {{
      title: '📸 截图 / 内容',
      rows: [
        ['截图', 'page.screenshot()', '截图'],
        ['截图 <selector>', 'locator.screenshot()', '截图 #chart'],
        ['获取文本 <selector>', 'locator.inner_text()', '获取文本 #result'],
        ['获取属性 <selector> <attr>', 'locator.get_attribute(attr)', '获取属性 #link href'],
        ['获取标题', 'page.title()', '获取标题'],
        ['获取URL', 'page.url', '获取URL'],
      ]
    }},
    {{
      title: '✅ 断言',
      rows: [
        ['断言可见 <selector>', 'expect(locator).to_be_visible()', '断言可见 #success'],
        ['断言文本 <selector> <text>', 'expect(locator).to_have_text(text)', '断言文本 #msg 成功'],
        ['断言URL包含 <text>', 'expect(page).to_have_url(re.compile(text))', '断言URL包含 success'],
        ['断言标题包含 <text>', 'expect(page).to_have_title(re.compile(text))', '断言标题包含 必应'],
      ]
    }},
    {{
      title: '🪟 多标签页 / 弹窗',
      rows: [
        ['新标签页 <url>', '新建标签页并导航', '新标签页 https://bing.com'],
        ['切换标签页 <index>', '切换到第 N 个标签页（从0开始）', '切换标签页 1'],
        ['关闭标签页', '关闭当前标签页', '关闭标签页'],
        ['接受弹窗', '自动接受 alert/confirm', '接受弹窗'],
        ['取消弹窗', '自动取消 confirm', '取消弹窗'],
      ]
    }},
    {{
      title: '🖼️ iframe',
      rows: [
        ['进入iframe <selector>', '切换到 iframe 上下文', '进入iframe #payment-frame'],
        ['退出iframe', '返回主页面上下文', '退出iframe'],
      ]
    }},
    {{
      title: '⚙️ 执行脚本',
      rows: [
        ['执行JS <code>', 'page.evaluate(code)', '执行JS document.title'],
        ['执行JS <code>', '可用于复杂操作', '执行JS window.scrollTo(0,0)'],
      ]
    }},
  ];

  let html = '';
  sections.forEach(sec => {{
    html += '<div style="margin-bottom:20px">';
    html += '<div style="font-size:13px;font-weight:700;color:#111;margin-bottom:8px;padding-bottom:4px;border-bottom:2px solid #e5e7eb">' + sec.title + '</div>';
    html += '<table style="width:100%;border-collapse:collapse;font-size:12px">';
    html += '<tr style="background:#f9fafb"><th style="text-align:left;padding:6px 8px;color:#6b7280;font-weight:600;width:35%">指令语法</th><th style="text-align:left;padding:6px 8px;color:#6b7280;font-weight:600;width:30%">对应 Playwright API</th><th style="text-align:left;padding:6px 8px;color:#6b7280;font-weight:600">示例</th></tr>';
    sec.rows.forEach((row, i) => {{
      const bg = i % 2 === 0 ? '#fff' : '#f9fafb';
      html += '<tr style="background:' + bg + '">';
      html += '<td style="padding:6px 8px;font-family:monospace;color:#5b21b6">' + row[0] + '</td>';
      html += '<td style="padding:6px 8px;color:#6b7280;font-size:11px">' + row[1] + '</td>';
      html += '<td style="padding:6px 8px;font-family:monospace;color:#166534;cursor:pointer" onclick="useDslExample(this.textContent)">' + row[2] + '</td>';
      html += '</tr>';
    }});
    html += '</table></div>';
  }});
  html += '<div style="margin-top:12px;padding:10px;background:#f0fdf4;border-radius:6px;font-size:12px;color:#166534">💡 点击示例列中的代码可直接追加到指令框中</div>';
  return html;
}}

function useDslExample(text) {{
  // Switch to DSL mode first so the textarea is visible
  if (currentMode !== 'dsl') switchMode('dsl');
  const ta = document.getElementById('dslScript');
  if (!ta) {{ toast('请先切换到自然语言模式', 'err'); return; }}
  const cur = ta.value;
  ta.value = cur ? cur + '\\n' + text.trim() : text.trim();
  document.getElementById('dslDocsModal').style.display = 'none';
  // Scroll to textarea
  ta.scrollIntoView({{behavior: 'smooth', block: 'center'}});
  ta.focus();
  toast('✅ 已追加指令', 'ok', 1500);
}}

window.addEventListener('DOMContentLoaded', () => {{
  checkLlm();
  loadHistory();
  initTaskCounter();
  switchMode('llm');  // init mode description
  // Sync browser mode from server
  fetch(BASE + '/health').then(x => x.json()).then(r => {{
    const headed = (r.data || r).headed === true;
    browserHeaded = headed;
    if (headed) setBrowserMode('headed');
  }}).catch(() => {{}});
}});

async function initTaskCounter() {{
  try {{
    const r = await fetch(BASE + '/traces').then(x => x.json());
    taskCounter = (r.runs || []).length;
    updateTaskIdPlaceholder();
  }} catch(e) {{}}
}}

function updateTaskIdPlaceholder() {{
  const next = String(taskCounter + 1).padStart(3, '0');
  const el = document.getElementById('taskIdInput');
  if (el) el.placeholder = next;
}}

function getNextTaskId() {{
  taskCounter++;
  const id = String(taskCounter).padStart(3, '0');
  updateTaskIdPlaceholder();
  return id;
}}

// ── LLM ──────────────────────────────────────────────────────────────────
async function checkLlm() {{
  try {{
    const r = await fetch(BASE + '/llm-status').then(x => x.json());
    const d = r.data || r;
    const badge = document.getElementById('llmBadge');
    const status = document.getElementById('llmStatus');
    if (d.configured) {{
      const s = d.summary || {{}};
      badge.textContent = '✓ ' + (s.model || 'LLM') + ' 已就绪';
      badge.style.background = '#dcfce7'; badge.style.color = '#166534';
      status.innerHTML = '<span style="color:#166534">✅ ' + (d.status_text || '模型已配置') + '</span>';
      // Auto-collapse when already configured
      collapseLlmCard();
    }} else {{
      badge.textContent = '⚠ 未配置模型';
      badge.style.background = '#fee2e2'; badge.style.color = '#991b1b';
      status.innerHTML = '<span style="color:#991b1b">⚠ 未配置模型，请填写配置并点击「保存并测试」</span>';
      // Expand when not configured
      expandLlmCard();
    }}
  }} catch(e) {{ console.error(e); }}
}}

function switchTab(tab) {{
  const isSimple = tab === 'simple';
  document.getElementById('simplePanel').style.display = isSimple ? 'block' : 'none';
  document.getElementById('jsonPanel').style.display = isSimple ? 'none' : 'block';
  document.getElementById('tabSimple').style.background = isSimple ? '#7c3aed' : '#f3f4f6';
  document.getElementById('tabSimple').style.color = isSimple ? '#fff' : '#374151';
  document.getElementById('tabJson').style.background = isSimple ? '#f3f4f6' : '#7c3aed';
  document.getElementById('tabJson').style.color = isSimple ? '#374151' : '#fff';
}}

function buildConfigFromUI() {{
  // JSON tab: use textarea directly (real token, not masked)
  const jsonPanel = document.getElementById('jsonPanel');
  if (jsonPanel && jsonPanel.style.display !== 'none') {{
    return document.getElementById('llmJson').value.trim();
  }}
  // Simple tab: build JSON from fields
  const url = document.getElementById('cfgUrl').value.trim();
  const key = document.getElementById('cfgKey').value.trim();
  const model = document.getElementById('cfgModel').value.trim();
  if (!url || !key || !model) return null;
  // Detect provider: OpenAI only for official openai.com; everything else uses Anthropic-compat
  const isOpenAI = url.includes('api.openai.com') || url.toLowerCase().includes('openai');
  if (isOpenAI) {{
    return JSON.stringify({{env:{{OPENAI_API_KEY:key,OPENAI_BASE_URL:url,OPENAI_MODEL:model}}}});
  }} else {{
    return JSON.stringify({{env:{{ANTHROPIC_AUTH_TOKEN:key,ANTHROPIC_BASE_URL:url,ANTHROPIC_MODEL:model}}}});
  }}
}}

async function testLlm(btn) {{
  const config = buildConfigFromUI();
  if (!config) {{
    toast('请填写完整配置（地址、Key、模型名）', 'err');
    return;
  }}
  if (!btn) btn = document.getElementById('testLlmBtn');
  const orig = btn.textContent;
  const t0 = Date.now();
  btn.disabled = true; btn.textContent = '测试中...';
  document.getElementById('llmStatus').innerHTML = '<span style="color:#6b7280">⏳ 正在连接模型...</span>';
  try {{
    const r = await fetch(BASE + '/test-llm', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{config}})
    }}).then(x => x.json());
    const elapsed = Date.now() - t0;
    if (r.success) {{
      document.getElementById('llmStatus').innerHTML = '<span style="color:#166534">✅ 测试通过，耗时 ' + elapsed + ' ms。模型可用。</span>';
      toast('✅ 测试通过 ' + elapsed + 'ms', 'ok');
      // Show masked config in JSON tab AFTER successful test
      try {{
        const cfg = JSON.parse(config);
        if (cfg.env) {{
          const masked = JSON.parse(JSON.stringify(cfg));
          ['ANTHROPIC_AUTH_TOKEN','ANTHROPIC_API_KEY','OPENAI_API_KEY'].forEach(k => {{
            if (masked.env[k]) masked.env[k] = maskKey(masked.env[k]);
          }});
          document.getElementById('llmJson').value = JSON.stringify(masked, null, 2);
        }}
      }} catch(e) {{}}
      checkLlm();
      // Collapse LLM card after success
      collapseLlmCard();
    }} else {{
      const msg = r.error || '未知错误';
      document.getElementById('llmStatus').innerHTML = '<span style="color:#991b1b">❌ 测试失败（' + elapsed + 'ms）：' + msg + '</span>';
      toast('模型不可用：' + msg.substring(0,60), 'err');
    }}
  }} catch(e) {{
    document.getElementById('llmStatus').innerHTML = '<span style="color:#991b1b">❌ 请求失败</span>';
    toast('模型不可用：连接失败', 'err');
  }} finally {{
    btn.disabled = false; btn.textContent = orig;
  }}
}}

// ── Task ──────────────────────────────────────────────────────────────────
async function runTask() {{
  if (currentMode === 'dsl') {{ return runDsl(); }}
  const task = document.getElementById('taskInput').value.trim();
  if (!task) {{ toast('请输入任务描述', 'err'); return; }}

  const llmCheck = await fetch(BASE + '/llm-status').then(x => x.json());
  const llmData = llmCheck.data || llmCheck;
  if (!llmData.configured) {{
    toast('模型未配置，请先测试配置', 'err');
    document.getElementById('llmCard').scrollIntoView({{behavior:'smooth'}});
    return;
  }}

  // Task ID: use input value or auto-increment
  const inputId = document.getElementById('taskIdInput')?.value.trim();
  const taskId = inputId || getNextTaskId();
  const maxSteps = parseInt(document.getElementById('maxStepsInput')?.value || '25') || 25;

  const payload = {{ task, mode: 'cdp', cdp_url: CDP_URL, max_steps: maxSteps, task_id: taskId }};

  setRunning(true);
  document.getElementById('resultCard').style.display = 'none';
  document.getElementById('replayPanel').style.display = 'none';

  // Start log polling
  const logArea = document.getElementById('logArea');
  logArea.style.display = 'block';
  logArea.innerHTML = '<div style="color:#9ca3af">等待任务启动...</div>';
  let logTimer = setInterval(async () => {{
    try {{
      const s = await fetch(BASE + '/state').then(x => x.json());
      if (s.success && s.data && s.data._raw_text) {{
        const lines = s.data._raw_text.split('\\n').slice(0,8);
        logArea.innerHTML = lines.map(l => '<div>'+escHtml(l)+'</div>').join('');
      }}
    }} catch(e) {{}}
  }}, 2000);

  try {{
    const resp = await fetch(BASE + '/run-task', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify(payload)
    }});
    clearInterval(logTimer);
    let r;
    try {{
      r = await resp.json();
    }} catch(jsonErr) {{
      showError('服务响应异常（HTTP ' + resp.status + '），请检查服务日志');
      return;
    }}
    showResult(r);
    loadHistory();
  }} catch(e) {{
    clearInterval(logTimer);
    showError('网络错误：' + String(e));
  }} finally {{
    setRunning(false);
    // Clear task id input after run
    if (!inputId) document.getElementById('taskIdInput').value = '';
  }}
}}

function setRunning(on) {{
  document.getElementById('runBtn').disabled = on;
  document.getElementById('progress').classList.toggle('show', on);
  if (on) {{
    let dots = 0;
    window._pt = setInterval(() => {{
      dots = (dots+1)%4;
      document.getElementById('progressText').textContent = '正在执行' + '.'.repeat(dots);
    }}, 500);
  }} else {{
    clearInterval(window._pt);
  }}
}}

function showResult(r) {{
  const card = document.getElementById('resultCard');
  card.style.display = 'block';
  const d = r.data || {{}};
  const passed = r.success && d.success === true;
  const failed = !r.success || d.success === false;
  const tag = document.getElementById('resultTag');
  if (passed) {{
    tag.textContent = '✓ PASS'; tag.className = 'tag tag-pass';
  }} else if (failed) {{
    tag.textContent = '✗ FAIL'; tag.className = 'tag tag-fail';
  }} else {{
    tag.textContent = '⚠ 完成'; tag.className = 'tag tag-run';
  }}

  const tid = d.task_id || '';
  document.getElementById('taskIdDisplay').innerHTML = tid
    ? '<span class="tid">task-id: ' + tid + '</span>' : '';

  const txt = document.getElementById('resultText');
  if (!r.success) {{
    txt.textContent = r.error || '执行失败';
  }} else {{
    txt.textContent = d.final_result || (d.is_done ? '任务完成' : '任务未完成');
    const errs = (d.errors || []).filter(Boolean);
    if (errs.length) txt.textContent += '\\n\\n⚠ 错误：' + errs[errs.length-1].substring(0,120);
    if (d.steps) txt.textContent += '\\n\\n共 ' + d.steps + ' 步';
  }}

  const links = document.getElementById('traceLinks');
  if (tid) {{
    links.innerHTML =
      '<a href="/traces/'+tid+'/recording.gif" target="_blank">🎬 GIF 回放</a>' +
      '<a href="/traces/'+tid+'/conversation.json" target="_blank">📄 对话日志</a>' +
      '<a href="/traces" target="_blank">📂 所有记录</a>';
    // Show replay in advanced panel if open
    if (advancedOpen) showReplay(tid, passed);
  }} else {{ links.innerHTML = ''; }}

  document.getElementById('resultRaw').textContent = JSON.stringify(r, null, 2);
}}

function showError(msg) {{
  const card = document.getElementById('resultCard');
  card.style.display = 'block';
  document.getElementById('resultTag').textContent = '✗ FAIL';
  document.getElementById('resultTag').className = 'tag tag-fail';
  document.getElementById('resultText').textContent = msg;
  document.getElementById('traceLinks').innerHTML = '';
}}

function showReplay(tid, passed) {{
  const panel = document.getElementById('replayPanel');
  panel.style.display = 'block';
  panel.style.borderColor = passed ? '#86efac' : '#fca5a5';
  const img = document.getElementById('replayGif');
  img.src = BASE + '/traces/' + tid + '/recording.gif?' + Date.now();
  // Load steps from trace.json
  fetch(BASE + '/traces/' + tid + '/trace.json')
    .then(x => x.json())
    .then(t => {{
      const urls = (t.urls || []).filter((u,i,a) => a.indexOf(u)===i).slice(0,10);
      const stepEl = document.getElementById('stepList');
      stepEl.innerHTML = urls.map((u,i) => '<div class="step-item">'+
        (i+1)+'. '+u.substring(0,80)+'</div>').join('');
    }}).catch(() => {{}});
}}

function toggleRaw() {{
  rawVisible = !rawVisible;
  document.getElementById('resultRaw').classList.toggle('show', rawVisible);
}}

function toggleAdvanced() {{
  advancedOpen = !advancedOpen;
  document.getElementById('advancedPanel').style.display = advancedOpen ? 'block' : 'none';
  document.getElementById('advBtn').textContent = advancedOpen ? '⚙ 收起' : '⚙ 高级选项';
  // If result exists and advanced just opened, show replay
  const tid = document.getElementById('taskIdDisplay').querySelector('.tid');
  if (advancedOpen && tid) {{
    const taskId = tid.textContent.replace('task-id: ','').trim();
    const passed = document.getElementById('resultTag').classList.contains('tag-pass');
    showReplay(taskId, passed);
  }}
}}

// ── History ───────────────────────────────────────────────────────────────
async function loadHistory() {{
  try {{
    const r = await fetch(BASE + '/traces').then(x => x.json());
    const list = document.getElementById('historyList');
    const runs = r.runs || [];
    if (!runs.length) {{
      list.innerHTML = '<div class="empty-state">暂无历史记录</div>';
      return;
    }}
    list.innerHTML = runs.slice(0,30).map(run => {{
      const passed = run.success === true;
      const failed = run.success === false;
      const tagCls = passed ? 'tag-pass' : (failed ? 'tag-fail' : 'tag-run');
      const tagTxt = passed ? 'PASS' : (failed ? 'FAIL' : '?');
      const tid = escHtml(run.task_id);
      const taskTxt = escHtml(run.task);
      return '<div class="history-item" data-tid="'+tid+'" data-task="'+taskTxt+'" onclick="historyClick(this)">' +
        '<div style="flex:1;min-width:0">' +
        '<div class="task-text">'+taskTxt+'</div>' +
        '<div class="meta">' +
        '<span class="tid">'+tid+'</span>' +
        '<span class="tag '+tagCls+'" style="font-size:10px;padding:2px 6px">'+tagTxt+'</span>' +
        '<span>'+run.steps+' 步</span>' +
        '<a href="/traces/'+tid+'/recording.gif" target="_blank" onclick="event.stopPropagation()" style="color:#7c3aed;font-size:11px">GIF</a>' +
        '</div></div></div>';
    }}).join('');
  }} catch(e) {{ console.error(e); }}
}}

async function clearHistory() {{
  if (!confirm('确认清空所有历史记录？此操作不可恢复。')) return;
  try {{
    const r = await fetch(BASE + '/traces/clear', {{method:'POST'}}).then(x=>x.json());
    if (r.success) {{
      toast('历史记录已清空', 'ok');
      loadHistory();
    }} else {{
      toast('清空失败：' + (r.error||''), 'err');
    }}
  }} catch(e) {{ toast('清空失败', 'err'); }}
}}

function historyClick(el) {{
  const taskId = el.dataset.tid;
  const task = el.dataset.task;
  replayTask(taskId, task);
}}

function replayTask(taskId, task) {{
  document.getElementById('taskInput').value = task;
  if (!advancedOpen) toggleAdvanced();
  document.getElementById('taskIdInput').value = taskId + '_r';
  showReplay(taskId, false);
  window.scrollTo({{top:0,behavior:'smooth'}});
}}

let apiKeyVisible = false;

// ── Codegen recorder ──────────────────────────────────────────────────────
let codegenRunning = false;

async function toggleCodegen() {{
  if (codegenRunning) {{
    await stopCodegen();
  }} else {{
    await startCodegen();
  }}
}}

async function startCodegen() {{
  const url = document.getElementById('codegenUrl').value.trim() || 'about:blank';
  const btn = document.getElementById('codegenBtn');
  const statusEl = document.getElementById('codegenStatus');
  btn.disabled = true;
  btn.textContent = '启动中...';
  try {{
    const r = await fetch(BASE + '/codegen/start', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{ url }})
    }}).then(x => x.json());
    if (r.success) {{
      codegenRunning = true;
      btn.textContent = '⏹ 停止录制';
      btn.style.background = '#dc2626';
      statusEl.style.display = 'block';
      statusEl.innerHTML = '<span style="color:#16a34a">🔴 录制中... 在弹出的浏览器窗口中操作，完成后点击「停止录制」</span>';
      toast('录制已启动，请在弹出窗口中操作', 'ok', 3000);
    }} else {{
      toast('启动失败：' + (r.error || ''), 'err');
    }}
  }} catch(e) {{
    toast('启动失败：' + String(e), 'err');
  }} finally {{
    btn.disabled = false;
  }}
}}

async function stopCodegen() {{
  const btn = document.getElementById('codegenBtn');
  const statusEl = document.getElementById('codegenStatus');
  btn.disabled = true;
  btn.textContent = '停止中...';
  statusEl.innerHTML = '<span style="color:#6b7280">⏳ 正在获取录制脚本...</span>';
  try {{
    const r = await fetch(BASE + '/codegen/stop', {{ method: 'POST' }}).then(x => x.json());
    codegenRunning = false;
    btn.textContent = '● 开始录制';
    btn.style.background = '#16a34a';
    if (r.success && r.script) {{
      // Auto-optimize and fill into textarea
      const opt = await fetch(BASE + '/optimize-script', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{ script: r.script }})
      }}).then(x => x.json()).catch(() => ({{ optimized: r.script }}));
      const finalScript = opt.optimized || r.script;
      document.getElementById('pwScript').value = finalScript;
      statusEl.innerHTML = '<span style="color:#16a34a">✅ 录制完成，脚本已自动优化填入</span>';
      toast('录制完成，脚本已优化', 'ok', 3000);
    }} else {{
      statusEl.innerHTML = '<span style="color:#991b1b">⚠ ' + (r.error || '未获取到脚本，请手动粘贴') + '</span>';
      toast(r.error || '未获取到脚本', 'err');
    }}
  }} catch(e) {{
    codegenRunning = false;
    btn.textContent = '● 开始录制';
    btn.style.background = '#16a34a';
    statusEl.innerHTML = '<span style="color:#991b1b">❌ 停止失败：' + String(e) + '</span>';
    toast('停止失败', 'err');
  }} finally {{
    btn.disabled = false;
  }}
}}

async function optimizeScript() {{
  const script = document.getElementById('pwScript').value.trim();
  if (!script) {{ toast('请先填入脚本', 'err'); return; }}
  try {{
    const r = await fetch(BASE + '/optimize-script', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{ script }})
    }}).then(x => x.json());
    if (r.optimized) {{
      document.getElementById('pwScript').value = r.optimized;
      toast('✅ 脚本已优化', 'ok');
    }} else {{
      toast(r.error || '优化失败', 'err');
    }}
  }} catch(e) {{
    toast('优化失败：' + String(e), 'err');
  }}
}}

// ── Export (YAML / pytest) ────────────────────────────────────────────────
let _exportFilename = 'test';
let _exportExt = 'yaml';

function toggleParamPanel() {{
  const p = document.getElementById('paramPanel');
  const btn = document.getElementById('paramBtn');
  const visible = p.style.display !== 'none';
  p.style.display = visible ? 'none' : 'block';
  btn.style.background = visible ? '#fff7ed' : '#fed7aa';
}}

function _getDslLines() {{
  return document.getElementById('dslScript').value.trim();
}}

function _getParamRows() {{
  const headersInput = document.getElementById('paramHeaders');
  const raw = document.getElementById('paramData').value.trim();
  if (!raw) return null;
  let headers;
  if (headersInput && headersInput.value.trim()) {{
    headers = headersInput.value.split(',').map(h => h.trim());
  }} else {{
    const lines = raw.split('\n').filter(l => l.trim());
    if (lines.length < 2) return null;
    headers = lines[0].split(',').map(h => h.trim());
  }}
  const dataRaw = (headersInput && headersInput.value.trim()) ? raw : raw.split('\n').slice(1).join('\n');
  const rows = dataRaw.split('\n').filter(l => l.trim()).map(l => {{
    const vals = l.split(',').map(v => v.trim());
    const obj = {{}};
    headers.forEach((h, i) => {{ obj[h] = vals[i] || ''; }});
    return obj;
  }});
  return rows.length > 0 ? {{ headers, rows }} : null;
}}

function exportYaml() {{
  const dsl = _getDslLines();
  if (!dsl) {{ toast('请先填入 NLP 指令', 'err'); return; }}
  const params = _getParamRows();
  let yaml = '# NLP 自动化测试 - 生成于 ' + new Date().toLocaleString() + '\\n';
  yaml += 'version: "1.0"\\n\\n';
  if (params) {{
    yaml += 'parameters:\\n';
    params.headers.forEach(h => {{ yaml += '  - ' + h + '\\n'; }});
    yaml += '\\ntest_data:\\n';
    params.rows.forEach((row, i) => {{
      yaml += '  - id: case_' + (i+1) + '\\n';
      Object.entries(row).forEach(([k,v]) => {{ yaml += '    ' + k + ': "' + v + '"\\n'; }});
    }});
    yaml += '\\n';
  }}
  yaml += 'steps:\\n';
  dsl.split('\\n').forEach(line => {{
    const l = line.trim();
    if (!l || l.startsWith('#')) return;
    yaml += '  - ' + JSON.stringify(l) + '\\n';
  }});
  _showExport('NLP → YAML', yaml, 'test_nlp.yaml');
}}

function exportPytest() {{
  const dsl = _getDslLines();
  if (!dsl) {{ toast('请先填入 NLP 指令', 'err'); return; }}
  const params = _getParamRows();
  const base = window.location.origin;
  const q3 = '"'.repeat(3);
  let code = q3 + 'Auto-generated pytest from NLP instructions' + q3 + '\\n';
  code += 'import pytest, requests, json\\n\\n';
  code += 'BASE = "' + base + '"\\n\\n';
  if (params) {{
    const paramStr = params.rows.map(r => '(' + Object.values(r).map(v => JSON.stringify(v)).join(', ') + ')').join(',\\n    ');
    const argStr = params.headers.join(', ');
    code += '@pytest.mark.parametrize("' + argStr + '", [\\n    ' + paramStr + '\\n])\\n';
    code += 'def test_nlp_parametrized(' + argStr + '):\\n';
  }} else {{
    code += 'def test_nlp():\\n';
  }}
  code += '    ' + q3 + 'Execute NLP instructions via Self API' + q3 + '\\n';
  code += '    dsl = ' + q3 + '\\n';
  dsl.split('\\n').forEach(line => {{ code += '    ' + line + '\\n'; }});
  code += '    ' + q3 + '\\n';
  if (params) {{
    code += '    # Apply parameters\\n';
    params.headers.forEach(h => {{
      code += '    dsl = dsl.replace("${{{' + h + '}}}", ' + h + ')\\n';
    }});
  }}
  code += '    resp = requests.post(BASE + "/run-dsl", json={{"dsl": dsl.strip()}}, timeout=120)\\n';
  code += '    assert resp.status_code == 200\\n';
  code += '    data = resp.json()\\n';
  code += '    assert data.get("success"), "NLP execution failed: " + str(data.get("data", {{}}).get("error"))\\n';
  _showExport('NLP → pytest', code, 'test_nlp.py');
}}

function _showExport(title, content, filename) {{
  document.getElementById('exportModalTitle').textContent = title;
  document.getElementById('exportContent').value = content;
  _exportFilename = filename;
  document.getElementById('exportModal').style.display = 'block';
}}

function copyExport() {{
  const ta = document.getElementById('exportContent');
  ta.select();
  document.execCommand('copy');
  toast('✅ 已复制到剪贴板', 'ok', 1500);
}}

function downloadExport() {{
  const content = document.getElementById('exportContent').value;
  const blob = new Blob([content], {{type: 'text/plain'}});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = _exportFilename;
  a.click();
  toast('✅ 已下载', 'ok', 1500);
}}

// Show export buttons when in DSL mode
function _updateExportBtns() {{
  const btns = document.getElementById('nlpExportBtns');
  if (btns) btns.style.display = currentMode === 'dsl' ? 'flex' : 'none';
}}

// ── Multi-browser discovery ──────────────────────────────────────────────
let _selectedBrowsers = [];

function toggleMultiBrowser() {{
  const checked = document.getElementById('multiBrowserCheck').checked;
  document.getElementById('multiBrowserPanel').style.display = checked ? 'block' : 'none';
  if (checked && _selectedBrowsers.length === 0) scanBrowsers();
}}

async function scanBrowsers() {{
  const btn = document.getElementById('scanBrowserBtn');
  const list = document.getElementById('browserList');
  btn.disabled = true; btn.textContent = '扫描中...';
  list.innerHTML = '<div style="font-size:11px;color:#9ca3af">正在扫描...</div>';
  try {{
    const r = await fetch(BASE + '/scan-browsers').then(x => x.json()).catch(() => ({{browsers: []}}));
    const browsers = r.browsers || [];
    if (browsers.length === 0) {{
      list.innerHTML = '<div style="font-size:11px;color:#9ca3af">未发现本地浏览器实例。请确保 Chrome 已以远程调试模式启动（带 --remote-debugging-port=9222 参数），或手动添加。</div>';
    }} else {{
      let html = '';
      browsers.forEach((b, i) => {{
        const checked = _selectedBrowsers.includes(b.url) ? 'checked' : '';
        html += '<label style="display:flex;align-items:center;gap:6px;padding:4px 0;font-size:12px;cursor:pointer">';
        html += '<input type="checkbox" ' + checked + ' data-url="' + b.url + '" onchange="toggleBrowserSelect(this)"/>';
        html += '<span style="color:#5b21b6;font-family:monospace">' + escHtml(b.url) + '</span>';
        html += '<span style="color:#6b7280;font-size:11px">(' + escHtml(b.title || b.type || 'browser') + ')</span>';
        html += '</label>';
      }});
      list.innerHTML = html;
    }}
  }} catch(e) {{
    list.innerHTML = '<div style="font-size:11px;color:#991b1b">扫描失败: ' + escHtml(String(e)) + '</div>';
  }}
  btn.disabled = false; btn.textContent = '🔍 自动发现';
}}

function toggleBrowserSelect(checkbox) {{
  const url = checkbox.dataset.url || checkbox.getAttribute('data-url');
  if (checkbox.checked) {{
    if (!_selectedBrowsers.includes(url)) _selectedBrowsers.push(url);
  }} else {{
    _selectedBrowsers = _selectedBrowsers.filter(u => u !== url);
  }}
  _syncBrowserTextarea();
}}

function addManualBrowser() {{
  const input = document.getElementById('manualCdpUrl');
  const url = input.value.trim();
  if (!url) {{ toast('请输入 CDP URL', 'err'); return; }}
  if (!_selectedBrowsers.includes(url)) _selectedBrowsers.push(url);
  _syncBrowserTextarea();
  input.value = '';
  // Update the list UI
  const list = document.getElementById('browserList');
  const label = document.createElement('label');
  label.style.cssText = 'display:flex;align-items:center;gap:6px;padding:4px 0;font-size:12px;cursor:pointer';
  label.innerHTML = '<input type="checkbox" checked data-url="' + url + '" onchange="toggleBrowserSelect(this)"/><span style="color:#5b21b6;font-family:monospace">' + escHtml(url) + '</span><span style="color:#6b7280;font-size:11px">(手动添加)</span>';
  // Remove 'no browsers' message if present
  const hint = list.querySelector('div[style*="color:#9ca3af"]');
  if (hint) hint.remove();
  list.appendChild(label);
  toast('✅ 已添加浏览器', 'ok', 1500);
}}

function _syncBrowserTextarea() {{
  const ta = document.getElementById('multiBrowserUrls');
  if (ta) ta.value = _selectedBrowsers.join('\n');
}}

// ── Export + Run ─────────────────────────────────────────────────────────
async function runExportedDsl() {{
  const dsl = _getDslLines();
  if (!dsl) {{ toast('没有可执行的指令', 'err'); return; }}
  const resultDiv = document.getElementById('exportRunResult');
  const btn = document.getElementById('exportRunBtn');
  btn.disabled = true; btn.textContent = '执行中...';
  resultDiv.style.display = 'block';
  resultDiv.innerHTML = '<div style="color:#6b7280">⏳ 正在执行导出的指令...</div>';
  try {{
    const resp = await fetch(BASE + '/run-dsl', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{ dsl }})
    }});
    const r = await resp.json();
    const d = r.data || {{}};
    const elapsed = d.elapsed_ms ? d.elapsed_ms + 'ms' : '';
    if (r.success) {{
      let html = '<div style="color:#166534;font-weight:600">✅ 执行成功 (' + elapsed + ')</div>';
      if (d.log) html += '<pre style="margin-top:6px;font-size:11px;white-space:pre-wrap;color:#374151">' + escHtml(d.log.slice(-800)) + '</pre>';
      resultDiv.innerHTML = html;
    }} else {{
      let html = '<div style="color:#991b1b;font-weight:600">❌ 执行失败 (' + elapsed + ')</div>';
      if (d.error) html += '<pre style="margin-top:6px;font-size:11px;color:#991b1b">' + escHtml(d.error.slice(0,500)) + '</pre>';
      resultDiv.innerHTML = html;
    }}
  }} catch(e) {{
    resultDiv.innerHTML = '<div style="color:#991b1b">❌ 网络错误: ' + escHtml(String(e)) + '</div>';
  }}
  btn.disabled = false; btn.textContent = '▶ 执行并查看结果';
}}

// ── Parameterization helpers ──────────────────────────────────────────────
function fillParamExample() {{
  document.getElementById('paramHeaders').value = 'keyword, url';
  document.getElementById('paramData').value = '耳机, https://cn.bing.com
手机, https://cn.bing.com
电脑, https://cn.bing.com';
  // Also fill a demo DSL that uses the params
  const ta = document.getElementById('dslScript');
  if (!ta.value.trim()) {{
    ta.value = '# 参数化示例：每组数据都会替换 ${{keyword}} 和 ${{url}}
打开 ${{url}}
等待加载完成
输入 #sb_form_q ${{keyword}}
按键 Enter
等待加载完成
截图';
  }}
  toast('✅ 已填入参数化示例', 'ok', 2000);
}}

// ── Browser mode ──────────────────────────────────────────────────────────
let browserHeaded = false;

function setBrowserMode(mode) {{
  browserHeaded = mode === 'headed';
  const headlessBtn = document.getElementById('headlessBtn');
  const headedBtn = document.getElementById('headedBtn');
  const hint = document.getElementById('browserModeHint');
  if (browserHeaded) {{
    headlessBtn.style.background = '#f3f4f6'; headlessBtn.style.color = '#374151';
    headedBtn.style.background = '#7c3aed'; headedBtn.style.color = '#fff';
    hint.textContent = '当前：有头模式，浏览器窗口可见，可以看到操作过程';
    hint.style.color = '#166534';
  }} else {{
    headlessBtn.style.background = '#7c3aed'; headlessBtn.style.color = '#fff';
    headedBtn.style.background = '#f3f4f6'; headedBtn.style.color = '#374151';
    hint.textContent = '当前：无头模式，浏览器在后台运行，不显示窗口';
    hint.style.color = '#6b7280';
  }}
  fetch(BASE + '/set-browser-mode', {{
    method: 'POST',
    headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{ headed: browserHeaded }})
  }}).then(x => x.json()).then(r => {{
    if (r.success) toast(browserHeaded ? '✅ 已切换为有头模式' : '✅ 已切换为无头模式', 'ok', 2000);
    else toast('切换失败: ' + (r.error||''), 'err');
  }}).catch(() => toast('切换失败', 'err'));
}}

// ── DSL mode ──────────────────────────────────────────────────────────────
let dslCodegenRunning = false;

async function toggleDslCodegen() {{
  if (dslCodegenRunning) {{ await stopDslCodegen(); }} else {{ await startDslCodegen(); }}
}}

async function startDslCodegen() {{
  const url = document.getElementById('dslCodegenUrl').value.trim() || 'about:blank';
  const btn = document.getElementById('dslCodegenBtn');
  const statusEl = document.getElementById('dslCodegenStatus');
  btn.disabled = true; btn.textContent = '启动中...';
  try {{
    const r = await fetch(BASE + '/codegen/start', {{
      method: 'POST', headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{ url }})
    }}).then(x => x.json());
    if (r.success) {{
      dslCodegenRunning = true;
      btn.textContent = '⏹ 停止录制'; btn.style.background = '#dc2626';
      statusEl.style.display = 'block';
      statusEl.innerHTML = '<span style="color:#16a34a">🔴 录制中... 操作完成后点击「停止录制」</span>';
      toast('录制已启动', 'ok', 3000);
    }} else {{ toast('启动失败：' + (r.error||''), 'err'); }}
  }} catch(e) {{ toast('启动失败：' + String(e), 'err'); }}
  finally {{ btn.disabled = false; }}
}}

async function stopDslCodegen() {{
  const btn = document.getElementById('dslCodegenBtn');
  const statusEl = document.getElementById('dslCodegenStatus');
  btn.disabled = true; btn.textContent = '停止中...';
  statusEl.innerHTML = '<span style="color:#6b7280">⏳ 正在转换为 DSL 指令...</span>';
  try {{
    const r = await fetch(BASE + '/codegen/stop', {{ method: 'POST' }}).then(x => x.json());
    dslCodegenRunning = false;
    btn.textContent = '● 开始录制'; btn.style.background = '#16a34a';
    if (r.success && r.script) {{
      // Convert Playwright script → DSL
      const dr = await fetch(BASE + '/script-to-dsl', {{
        method: 'POST', headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{ script: r.script }})
      }}).then(x => x.json()).catch(() => ({{}}));
      if (dr.dsl) {{
        document.getElementById('dslScript').value = dr.dsl;
        statusEl.innerHTML = '<span style="color:#16a34a">✅ 录制完成，已转换为 DSL 指令</span>';
        toast('录制完成，DSL 已生成', 'ok', 3000);
      }} else {{
        statusEl.innerHTML = '<span style="color:#f59e0b">⚠ 转换失败，原始脚本已填入 Playwright 面板</span>';
        document.getElementById('pwScript').value = r.script;
        switchMode('playwright');
      }}
    }} else {{
      statusEl.innerHTML = '<span style="color:#991b1b">⚠ ' + (r.error||'未录制到操作') + '</span>';
      toast(r.error || '未录制到操作', 'err');
    }}
  }} catch(e) {{
    dslCodegenRunning = false;
    btn.textContent = '● 开始录制'; btn.style.background = '#16a34a';
    toast('停止失败', 'err');
  }} finally {{ btn.disabled = false; }}
}}

async function convertDslFromPw() {{
  // Convert whatever is in pwScript textarea → DSL
  const script = document.getElementById('pwScript').value.trim() ||
                 document.getElementById('dslScript').value.trim();
  if (!script) {{ toast('请先在 Playwright 面板填入脚本', 'err'); return; }}
  try {{
    const r = await fetch(BASE + '/script-to-dsl', {{
      method: 'POST', headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{ script }})
    }}).then(x => x.json());
    if (r.dsl) {{
      document.getElementById('dslScript').value = r.dsl;
      toast('✅ 已转换为 DSL', 'ok');
    }} else {{ toast(r.error || '转换失败', 'err'); }}
  }} catch(e) {{ toast('转换失败', 'err'); }}
}}

async function runDsl() {{
  const dslTemplate = document.getElementById('dslScript').value.trim();
  if (!dslTemplate) {{ toast('请输入 NLP 指令', 'err'); return; }}
  const inputId = document.getElementById('taskIdInput')?.value.trim();
  const captureNetwork = document.getElementById('captureNetworkCheck')?.checked !== false;
  const multiCheck = document.getElementById('multiBrowserCheck')?.checked;
  const multiBrowserUrls = multiCheck
    ? (document.getElementById('multiBrowserUrls')?.value.trim().split('\\n').filter(u=>u.trim()) || [])
    : [];

  // Expand parameterization
  const params = _getParamRows();
  const cases = params ? params.rows : [null];

  setRunning(true);
  document.getElementById('resultCard').style.display = 'none';
  document.getElementById('logArea').style.display = 'block';
  document.getElementById('logArea').innerHTML = '<div style="color:#9ca3af">正在执行 NLP 指令...</div>';

  const allResults = [];
  let anyFail = false;

  for (let ci = 0; ci < cases.length; ci++) {{
    const row = cases[ci];
    let dsl = dslTemplate;
    if (row) {{
      Object.entries(row).forEach(([k,v]) => {{
        dsl = dsl.split('${{{' + k + '}}}').join(v);
      }});
    }}
    const taskId = inputId || getNextTaskId();
    const caseLabel = row ? ' [参数组 ' + (ci+1) + ']' : '';

    // Multi-browser: run in parallel
    const browserUrls = multiBrowserUrls.length > 0 ? multiBrowserUrls : [null];
    const promises = browserUrls.map(async (cdpUrl, bi) => {{
      const bLabel = cdpUrl ? ' [浏览器' + (bi+1) + ':' + cdpUrl + ']' : '';
      try {{
        const payload = {{ dsl, task_id: taskId + (bi > 0 ? '_b'+bi : ''), capture_network: captureNetwork }};
        if (cdpUrl) payload.cdp_url = cdpUrl;
        const resp = await fetch(BASE + '/run-dsl', {{
          method: 'POST',
          headers: {{'Content-Type': 'application/json'}},
          body: JSON.stringify(payload)
        }});
        const r = await resp.json();
        return {{ r, label: caseLabel + bLabel, taskId: payload.task_id }};
      }} catch(e) {{
        return {{ r: {{success:false, error: String(e)}}, label: caseLabel + bLabel, taskId }};
      }}
    }});

    const results = await Promise.all(promises);
    allResults.push(...results);
    results.forEach(({{r, label, taskId: tid}}) => {{
      if (!r.success) anyFail = true;
      const d = r.data || {{}};
      const elapsed = d.elapsed_ms ? ' (' + d.elapsed_ms + 'ms)' : '';
      const icon = r.success ? '✅' : '❌';
      let html = '<div style="margin-bottom:8px;padding:8px;background:' + (r.success?'#f0fdf4':'#fef2f2') + ';border-radius:6px">';
      html += '<div style="font-weight:600;color:' + (r.success?'#166534':'#991b1b') + '">' + icon + label + elapsed + '</div>';
      if (d.log) html += '<pre style="margin-top:4px;font-size:11px;white-space:pre-wrap">' + escHtml(d.log.slice(-600)) + '</pre>';
      if (!r.success && d.error) html += '<pre style="margin-top:4px;font-size:11px;color:#991b1b">' + escHtml(d.error.slice(0,400)) + '</pre>';
      // GIF link
      if (tid) html += '<div style="margin-top:4px"><a href="/traces/'+tid+'/recording.gif" target="_blank" style="font-size:11px;color:#7c3aed">🎬 GIF</a> <a href="/traces/'+tid+'/trace.json" target="_blank" style="font-size:11px;color:#7c3aed;margin-left:8px">📄 Trace</a></div>';
      // Network requests
      if (d.network && d.network.length) {{
        html += '<details style="margin-top:4px"><summary style="font-size:11px;cursor:pointer;color:#6b7280">🌐 接口请求 (' + d.network.length + ')</summary>';
        html += '<div style="max-height:120px;overflow:auto">';
        d.network.forEach(req => {{
          html += '<div style="font-size:10px;padding:2px 0;border-bottom:1px solid #f3f4f6">';
          html += '<span style="color:' + (req.status>=400?'#dc2626':req.status>=300?'#d97706':'#16a34a') + '">' + (req.status||'?') + '</span> ';
          html += escHtml(req.method) + ' ' + escHtml(req.url.slice(0,80));
          html += '</div>';
        }});
        html += '</div></details>';
      }}
      // Exception screenshots
      if (d.exception_screenshots && d.exception_screenshots.length) {{
        html += '<div style="margin-top:4px;font-size:11px;color:#991b1b">⚠ 异常截图：</div>';
        d.exception_screenshots.forEach(s => {{
          html += '<img src="/traces/'+tid+'/'+s+'" style="max-width:200px;border-radius:4px;margin:2px" />';
        }});
      }}
      html += '</div>';
      document.getElementById('logArea').innerHTML += html;
    }});
  }}

  // Summary result card
  const card = document.getElementById('resultCard');
  card.style.display = 'block';
  const tag = document.getElementById('resultTag');
  const totalPass = allResults.filter(x => x.r.success).length;
  tag.textContent = anyFail ? '✗ FAIL ' + totalPass + '/' + allResults.length : '✓ PASS ' + totalPass + '/' + allResults.length;
  tag.className = 'tag ' + (anyFail ? 'tag-fail' : 'tag-pass');
  const lastResult = allResults[allResults.length-1];
  const lastTid = lastResult?.taskId;
  document.getElementById('taskIdDisplay').innerHTML = lastTid ? '<span class="tid">task-id: ' + lastTid + '</span>' : '';
  document.getElementById('resultText').textContent = anyFail
    ? '❌ 部分执行失败，共 ' + allResults.length + ' 组，通过 ' + totalPass + ' 组'
    : '✅ 全部执行成功，共 ' + allResults.length + ' 组';
  if (lastTid) {{
    document.getElementById('traceLinks').innerHTML =
      '<a href="/traces/'+lastTid+'/recording.gif" target="_blank">🎬 GIF 回放</a>' +
      '<a href="/traces" target="_blank">📂 所有记录</a>';
  }}
  document.getElementById('resultRaw').textContent = JSON.stringify(allResults.map(x=>x.r), null, 2);
  setRunning(false);
  if (!inputId) document.getElementById('taskIdInput').value = '';
  loadHistory();
}}

async function runPlaywright() {{
  const script = document.getElementById('pwScript').value.trim();
  if (!script) {{ toast('请粘贴 Playwright 脚本', 'err'); return; }}
  const inputId = document.getElementById('taskIdInput')?.value.trim();
  const taskId = inputId || getNextTaskId();
  setRunning(true);
  document.getElementById('resultCard').style.display = 'none';
  document.getElementById('logArea').style.display = 'block';
  document.getElementById('logArea').innerHTML = '<div style="color:#9ca3af">正在执行 Playwright 脚本...</div>';
  try {{
    const resp = await fetch(BASE + '/run-playwright', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{ script, task_id: taskId }})
    }});
    let r;
    try {{ r = await resp.json(); }} catch(e) {{
      showError('服务响应异常（HTTP ' + resp.status + '）');
      return;
    }}
    const d = r.data || {{}};
    const elapsed = d.elapsed_ms ? ' (' + d.elapsed_ms + 'ms)' : '';
    if (r.success) {{
      document.getElementById('logArea').innerHTML = '<div style="color:#166534">✅ 执行完成' + elapsed + '</div>' +
        (d.stdout ? '<pre style="margin-top:6px;font-size:11px">' + escHtml(d.stdout.slice(-500)) + '</pre>' : '');
    }} else {{
      document.getElementById('logArea').innerHTML = '<div style="color:#991b1b">❌ 执行失败' + elapsed + '</div>' +
        '<pre style="margin-top:6px;font-size:11px;color:#991b1b">' + escHtml((d.error||r.error||'').slice(0,500)) + '</pre>';
    }}
    // Show result card
    const card = document.getElementById('resultCard');
    card.style.display = 'block';
    const tag = document.getElementById('resultTag');
    tag.textContent = r.success ? '✓ PASS' : '✗ FAIL';
    tag.className = 'tag ' + (r.success ? 'tag-pass' : 'tag-fail');
    document.getElementById('taskIdDisplay').innerHTML = '<span class="tid">task-id: ' + (d.task_id||taskId) + '</span>';
    document.getElementById('resultText').textContent = r.success
      ? '✅ Playwright 脚本执行成功' + elapsed + '\\n\\n' + (d.stdout||'').slice(-300)
      : '❌ 执行失败\\n\\n' + (d.error||r.error||'');
    document.getElementById('traceLinks').innerHTML = '';
    document.getElementById('resultRaw').textContent = JSON.stringify(r, null, 2);
    loadHistory();
  }} catch(e) {{
    showError('网络错误：' + String(e));
  }} finally {{
    setRunning(false);
    if (!inputId) document.getElementById('taskIdInput').value = '';
  }}
}}

function collapseLlmCard() {{
  const area = document.getElementById('llmManualArea');
  area.classList.remove('expanded');
  const icon = document.getElementById('llmCollapseIcon');
  if (icon) icon.textContent = '▶';
}}

async function expandLlmCard() {{
  const area = document.getElementById('llmManualArea');
  area.classList.add('expanded');
  const icon = document.getElementById('llmCollapseIcon');
  if (icon) icon.textContent = '▼';
  // Populate fields with current config when expanding
  try {{
    const r = await fetch(BASE + '/llm-status').then(x => x.json());
    const d = r.data || r;
    if (d.configured && d.summary) {{
      const s = d.summary;
      document.getElementById('cfgUrl').value = s.base_url || '';
      document.getElementById('cfgModel').value = s.model || '';
      // API key: show masked by default, store real key in data attribute
      const keyInput = document.getElementById('cfgKey');
      if (d.raw_config) {{
        try {{
          const cfg = JSON.parse(d.raw_config);
          const realKey = cfg.env?.ANTHROPIC_AUTH_TOKEN || cfg.env?.OPENAI_API_KEY || '';
          keyInput.dataset.realKey = realKey;
          keyInput.value = maskKey(realKey);
          keyInput.type = 'text';
          apiKeyVisible = false;
        }} catch(e) {{}}
      }}
    }}
  }} catch(e) {{}}
}}

function toggleLlmCard() {{
  const area = document.getElementById('llmManualArea');
  const collapsed = !area.classList.contains('expanded');
  if (collapsed) expandLlmCard(); else collapseLlmCard();
}}

function toggleApiKeyVisibility() {{
  const input = document.getElementById('cfgKey');
  const realKey = input.dataset.realKey || '';
  apiKeyVisible = !apiKeyVisible;
  input.value = apiKeyVisible ? realKey : maskKey(realKey);
  const btn = document.getElementById('keyToggleBtn');
  if (btn) btn.textContent = apiKeyVisible ? '🙈 隐藏' : '👁 显示';
}}

function escHtml(s) {{
  return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}

function maskKey(key) {{
  if (!key || key.length <= 8) return '****';
  return key.substring(0, 6) + '****' + key.substring(key.length - 4);
}}
</script>
</body>
</html>"""
		return web.Response(text=html, content_type='text/html')

	async def llm_status(self, request: web.Request) -> web.Response:
		return self._build_response(200, {'success': True, 'data': self._llm_status_payload()})

	async def test_llm(self, request: web.Request) -> web.Response:
		body = await self._json_body(request)
		try:
			llm, summary, raw_config = self._build_llm_from_payload(body)
			await self._test_llm(llm)
			self._configured_llm = llm
			self._llm_config_raw = raw_config
			self._llm_config_status = 'ready'
			self._llm_config_error = ''
			self._llm_config_summary = summary
			return self._build_response(200, {'success': True, 'data': self._llm_status_payload()})
		except RuntimeError as exc:
			self._configured_llm = None
			self._llm_config_status = 'error'
			self._llm_config_error = str(exc)
			self._llm_config_summary = {}
			return self._build_response(400, {'success': False, 'error': str(exc), 'data': self._llm_status_payload()})

	async def health(self, request: web.Request) -> web.Response:
		session = self.daemon._session
		payload = {
			'success': True,
			'data': {
				'status': 'ok',
				'session': self.daemon.session,
				'browser_connected': bool(session),
				'headed': self.daemon.headed,
				'profile': self.daemon.profile,
				'cdp_url': self.daemon.cdp_url,
				'use_cloud': self.daemon.use_cloud,
				'llm': self._llm_status_payload(),
			},
		}
		if self.daemon.cdp_url:
			try:
				payload['data']['cdp_diagnostics'] = await self._probe_cdp_endpoint(self.daemon.cdp_url)
			except RuntimeError as exc:
				payload['data']['cdp_diagnostics'] = {'error': str(exc)}
		return self._build_response(200, payload)

	async def connect(self, request: web.Request) -> web.Response:
		body = await self._optional_json_body(request)
		mode, manual_cdp_url, profile = self._requested_target(body)
		if mode == 'cdp':
			try:
				self._validate_manual_cdp_input(manual_cdp_url)
			except RuntimeError as exc:
				return self._build_response(400, {'success': False, 'error': str(exc), 'data': {}})

		if not self._is_same_target(mode, manual_cdp_url, profile):
			close_status, close_payload = await self._dispatch('shutdown')
			if not close_payload.get('success'):
				return self._build_response(close_status, close_payload)
			await self.daemon.shutdown()
			try:
				self.daemon = self._create_daemon(mode, manual_cdp_url=manual_cdp_url, profile=profile)
			except RuntimeError as exc:
				return self._connect_error(str(exc))

		status, payload = await self._dispatch('connect')
		await self._enrich_state_payload(payload)
		return self._build_response(status, payload)

	def _create_daemon(self, mode: str, manual_cdp_url: str | None = None, profile: str | None = None) -> Daemon:
		if mode == 'cdp':
			cdp_url = manual_cdp_url.strip() if isinstance(manual_cdp_url, str) and manual_cdp_url.strip() else None
			if not cdp_url:
				raise RuntimeError(
					'Could not discover a visible Chrome CDP target. Start Chrome on the host with --remote-debugging-port=9222 and provide a container-reachable CDP URL such as http://127.0.0.1:9222.'
				)
			return self._build_daemon(headed=True, profile=None, cdp_url=cdp_url, use_cloud=False)
		if mode == 'profile':
			profile_name = profile.strip() if isinstance(profile, str) and profile.strip() else 'Default'
			return self._build_daemon(headed=True, profile=profile_name, cdp_url=None, use_cloud=False)
		if mode == 'virtual':
			# In Docker, always headless; on host respect the current headed setting
			headed = self.daemon.headed if not os.environ.get('IN_DOCKER') else False
			return self._build_daemon(headed=headed, profile=None, cdp_url=None, use_cloud=False)
		raise RuntimeError(f'Unknown browser mode: {mode}')

	async def open(self, request: web.Request) -> web.Response:
		if not self._browser_target()['visible']:
			return self._build_response(
				400,
				{
					'success': False,
					'error': 'Open URL requires a visible browser target. Connect with Visible Chrome via CDP or Visible Chrome profile first.',
				},
			)
		body = await self._json_body(request)
		status, payload = await self._dispatch('open', {
			'url': body['url'],
			'new_tab': body.get('new_tab', False),
		})
		await self._enrich_state_payload(payload)
		return self._build_response(status, payload)

	async def run_task(self, request: web.Request) -> web.Response:
		body = await self._json_body(request)
		task = body.get('task')
		if not isinstance(task, str) or not task.strip():
			return self._build_response(400, {'success': False, 'error': 'Task is required', 'data': {}})
		mode, manual_cdp_url, profile = self._requested_target(body)
		try:
			self._validate_manual_cdp_input(manual_cdp_url)
		except RuntimeError as exc:
			return self._build_response(400, {'success': False, 'error': str(exc), 'data': {}})
		max_steps = body.get('max_steps', 25)
		if not isinstance(max_steps, int) or max_steps <= 0:
			max_steps = 25
		task_id = body.get('task_id') if isinstance(body.get('task_id'), str) else None
		async with self._task_lock:
			try:
				if mode == 'current':
					mode = None  # let _run_task_payload default to cdp
				payload = await self._run_task_payload(
					task.strip(),
					max_steps=max_steps,
					mode=mode,
					manual_cdp_url=manual_cdp_url,
					profile=profile,
					task_id=task_id,
				)
				return self._build_response(200, {'success': True, 'data': payload})
			except RuntimeError as exc:
				return self._build_response(400, {'success': False, 'error': str(exc), 'data': {}})
			except Exception as exc:
				# Catch all other exceptions to prevent service crash
				import traceback as _tb
				_tb.print_exc()
				return self._build_response(500, {'success': False, 'error': f'Internal error: {exc}', 'data': {}})

	async def state(self, request: web.Request) -> web.Response:
		status, payload = await self._dispatch('state')
		await self._enrich_state_payload(payload)
		return self._build_response(status, payload)

	async def switch_tab(self, request: web.Request) -> web.Response:
		body = await self._json_body(request)
		status, payload = await self._dispatch('switch', {'tab': body['tab']})
		return self._build_response(status, payload)

	async def close_tab(self, request: web.Request) -> web.Response:
		body = await self._json_body(request)
		status, payload = await self._dispatch('close-tab', {'tab': body.get('tab')})
		return self._build_response(status, payload)

	async def click(self, request: web.Request) -> web.Response:
		body = await self._json_body(request)
		args = body.get('args')
		if args is None:
			if 'index' in body:
				args = [body['index']]
			elif 'x' in body and 'y' in body:
				args = [body['x'], body['y']]
			else:
				return self._build_response(400, {'success': False, 'error': 'Provide args, index, or x/y'})
		status, payload = await self._dispatch('click', {'args': args})
		return self._build_response(status, payload)

	async def type_text(self, request: web.Request) -> web.Response:
		body = await self._json_body(request)
		status, payload = await self._dispatch('type', {'text': body['text']})
		return self._build_response(status, payload)

	async def close(self, request: web.Request) -> web.Response:
		status, payload = await self._dispatch('shutdown')
		asyncio.create_task(self.shutdown())
		return self._build_response(status, payload)

	async def _json_body(self, request: web.Request) -> dict[str, Any]:
		try:
			body = await request.json()
		except json.JSONDecodeError:
			raise web.HTTPBadRequest(text=json.dumps({'success': False, 'error': 'Invalid JSON body'}), content_type='application/json')
		if not isinstance(body, dict):
			raise web.HTTPBadRequest(text=json.dumps({'success': False, 'error': 'JSON body must be an object'}), content_type='application/json')
		return body

	async def _optional_json_body(self, request: web.Request) -> dict[str, Any]:
		if request.can_read_body:
			return await self._json_body(request)
		return {}

	async def scan_browsers(self, request: web.Request) -> web.Response:
		"""Scan for local Chrome DevTools Protocol endpoints."""
		import socket
		browsers = []
		ports_to_scan = [9222, 9223, 9224, 9225, 9226, 9227, 9228, 9229, 9515, 9516]
		for port in ports_to_scan:
			try:
				s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				s.settimeout(0.5)
				result = s.connect_ex(('127.0.0.1', port))
				s.close()
				if result == 0:
					url = f'http://127.0.0.1:{port}'
					# Try to get browser info
					info = {'url': url, 'title': 'Chrome', 'type': 'Chromium', 'port': port}
					try:
						import urllib.request
						with urllib.request.urlopen(f'{url}/json/version', timeout=1) as resp:
							import json as _json
							data = _json.loads(resp.read())
							info['title'] = data.get('Browser', 'Chrome')
							info['type'] = data.get('Browser', 'Chromium').split('/')[0] if '/' in data.get('Browser', '') else 'Chromium'
					except Exception:
						pass
					browsers.append(info)
			except Exception:
				pass
		return self._build_response(200, {'success': True, 'browsers': browsers})

	def build_app(self) -> web.Application:
		app = web.Application()
		app.router.add_get('/', self.index)
		app.router.add_get('/health', self.health)
		app.router.add_get('/llm-status', self.llm_status)
		app.router.add_post('/test-llm', self.test_llm)
		app.router.add_post('/connect', self.connect)
		app.router.add_post('/run-task', self.run_task)
		app.router.add_post('/open', self.open)
		app.router.add_get('/state', self.state)
		app.router.add_post('/switch-tab', self.switch_tab)
		app.router.add_post('/close-tab', self.close_tab)
		app.router.add_post('/click', self.click)
		app.router.add_post('/type', self.type_text)
		app.router.add_post('/close', self.close)
		app.router.add_get('/recording', self.get_recording)
		app.router.add_get('/traces', self.get_traces)
		app.router.add_get('/traces/{run_id}/{filename}', self.get_trace_file)
		app.router.add_post('/traces/clear', self.clear_traces)
		app.router.add_post('/run-playwright', self.run_playwright)
		app.router.add_post('/set-browser-mode', self.set_browser_mode)
		app.router.add_post('/codegen/start', self.codegen_start)
		app.router.add_post('/codegen/stop', self.codegen_stop)
		app.router.add_get('/codegen/status', self.codegen_status)
		app.router.add_post('/optimize-script', self.optimize_script)
		app.router.add_post('/script-to-dsl', self.script_to_dsl)
		app.router.add_get('/scan-browsers', self.scan_browsers)
		app.router.add_post('/run-dsl', self.run_dsl)
		app.router.add_post('/export-yaml', self.export_yaml)
		app.router.add_post('/export-pytest', self.export_pytest)
		app.router.add_get('/scan-browsers', self.scan_browsers)
		return app

	async def get_recording(self, request: web.Request) -> web.Response:
		"""Serve the latest task recording GIF."""
		import os
		gif_path = '/data/task_recording.gif'
		if not os.path.exists(gif_path):
			return web.Response(status=404, text='No recording available yet. Run a task first.')
		return web.FileResponse(gif_path, headers={'Content-Type': 'image/gif', 'Cache-Control': 'no-cache'})

	async def get_traces(self, request: web.Request) -> web.Response:
		"""List all trace runs with links to GIF and conversation."""
		import json as _json
		from pathlib import Path as _Path
		# Use absolute path relative to this file
		traces_dir = _Path(__file__).parent.parent.parent / 'traces'
		if not traces_dir.exists():
			# Also try cwd
			traces_dir = _Path('traces')
		if not traces_dir.exists():
			return web.json_response({'runs': []})
		runs = []
		for run_dir in sorted(traces_dir.iterdir(), reverse=True):
			if not run_dir.is_dir():
				continue
			trace_file = run_dir / 'trace.json'
			if trace_file.exists():
				try:
					with open(trace_file, encoding='utf-8') as f:
						t = _json.load(f)
					tid = t.get('task_id') or t.get('run_id') or run_dir.name
					runs.append({
						'task_id': tid,
						'task': t.get('task', ''),
						'success': t.get('success'),
						'steps': t.get('steps', 0),
					})
				except Exception:
					pass
		return web.json_response({'runs': runs})

	async def get_trace_file(self, request: web.Request) -> web.Response:
		"""Serve a specific trace file (GIF or JSON)."""
		from pathlib import Path as _Path
		run_id = request.match_info.get('run_id', '')
		filename = request.match_info.get('filename', '')
		# Try multiple base paths
		for base in [_Path(__file__).parent.parent.parent / 'traces', _Path('traces')]:
			path = base / run_id / filename
			if path.exists() and path.is_file():
				ct = 'image/gif' if filename.endswith('.gif') else 'application/json'
				return web.FileResponse(path, headers={'Content-Type': ct, 'Cache-Control': 'no-cache'})
		return web.Response(status=404, text='File not found')

	async def clear_traces(self, request: web.Request) -> web.Response:
		"""Delete all trace directories."""
		import shutil as _shutil
		from pathlib import Path as _Path
		deleted = 0
		for base in [_Path(__file__).parent.parent.parent / 'traces', _Path('traces')]:
			if base.exists():
				for run_dir in base.iterdir():
					if run_dir.is_dir():
						try:
							_shutil.rmtree(run_dir)
							deleted += 1
						except Exception:
							pass
		return web.json_response({'success': True, 'deleted': deleted})

	# ── Codegen recorder ──────────────────────────────────────────────────────

	async def codegen_start(self, request: web.Request) -> web.Response:
		"""Start playwright codegen in a subprocess, recording to a temp file."""
		import asyncio as _asyncio, sys, os, tempfile
		from pathlib import Path as _Path

		body = await self._json_body(request)
		url = body.get('url', 'about:blank').strip() or 'about:blank'

		# Kill any existing codegen process
		await self._codegen_kill()

		# Temp file to capture the generated script
		tmp = tempfile.NamedTemporaryFile(suffix='.py', delete=False, mode='w', encoding='utf-8')
		tmp.close()
		self._codegen_output_file = tmp.name

		try:
			# playwright codegen --target python-async -o <file> <url>
			proc = await _asyncio.create_subprocess_exec(
				sys.executable, '-m', 'playwright', 'codegen',
				'--target', 'python-async',
				'-o', self._codegen_output_file,
				url,
				stdout=_asyncio.subprocess.PIPE,
				stderr=_asyncio.subprocess.PIPE,
				env=os.environ.copy(),
			)
			self._codegen_proc = proc
			return web.json_response({'success': True, 'pid': proc.pid})
		except Exception as exc:
			return web.json_response({'success': False, 'error': str(exc)}, status=500)

	async def codegen_stop(self, request: web.Request) -> web.Response:
		"""Stop codegen and return the recorded script."""
		import asyncio as _asyncio
		from pathlib import Path as _Path

		proc = getattr(self, '_codegen_proc', None)
		out_file = getattr(self, '_codegen_output_file', None)

		if proc is None:
			return web.json_response({'success': False, 'error': '没有正在运行的录制进程'}, status=400)

		# Gracefully terminate — codegen writes the file on exit
		try:
			proc.terminate()
			try:
				await _asyncio.wait_for(proc.wait(), timeout=8)
			except _asyncio.TimeoutError:
				proc.kill()
				await proc.wait()
		except Exception:
			pass
		finally:
			self._codegen_proc = None

		# Read the output file
		script = ''
		if out_file:
			try:
				p = _Path(out_file)
				if p.exists() and p.stat().st_size > 0:
					script = p.read_text(encoding='utf-8')
				p.unlink(missing_ok=True)
			except Exception:
				pass
		self._codegen_output_file = None

		if not script.strip():
			return web.json_response({'success': False, 'error': '未录制到任何操作，脚本为空'})

		return web.json_response({'success': True, 'script': script})

	async def codegen_status(self, request: web.Request) -> web.Response:
		"""Return whether codegen is currently running."""
		proc = getattr(self, '_codegen_proc', None)
		running = proc is not None and proc.returncode is None
		return web.json_response({'success': True, 'running': running})

	async def _codegen_kill(self) -> None:
		"""Kill any existing codegen subprocess."""
		proc = getattr(self, '_codegen_proc', None)
		if proc and proc.returncode is None:
			try:
				proc.kill()
				await proc.wait()
			except Exception:
				pass
		self._codegen_proc = None

	async def optimize_script(self, request: web.Request) -> web.Response:
		"""Optimize a raw codegen script: replace fixed waits with state-based waits."""
		body = await self._json_body(request)
		script = body.get('script', '').strip()
		if not script:
			return web.json_response({'success': False, 'error': 'script is required'}, status=400)
		try:
			optimized = self._wrap_playwright_script(script)
			return web.json_response({'success': True, 'optimized': optimized})
		except Exception as exc:
			return web.json_response({'success': False, 'error': str(exc)}, status=500)

	async def script_to_dsl(self, request: web.Request) -> web.Response:
		"""Convert a Playwright Python script to natural-language DSL instructions."""
		body = await self._json_body(request)
		script = body.get('script', '').strip()
		if not script:
			return web.json_response({'success': False, 'error': 'script is required'}, status=400)
		try:
			dsl = self._playwright_to_dsl(script)
			return web.json_response({'success': True, 'dsl': dsl})
		except Exception as exc:
			return web.json_response({'success': False, 'error': str(exc)}, status=500)

	def _playwright_to_dsl(self, script: str) -> str:
		"""Convert Playwright Python async script lines to DSL instructions.

		Handles the most common codegen output patterns:
		  page.goto(url)                          → 打开 <url>
		  page.get_by_text(t).click()             → 点击 文本=<t>
		  page.get_by_role(r, name=n).click()     → 点击 role=<r>[name=<n>]
		  page.locator(sel).click()               → 点击 <sel>
		  page.click(sel)                         → 点击 <sel>
		  page.fill(sel, val)                     → 输入 <sel> <val>
		  page.get_by_placeholder(p).fill(val)    → 输入 placeholder=<p> <val>
		  page.keyboard.press(key)                → 按键 <key>
		  page.wait_for_load_state(...)           → 等待加载完成
		  page.wait_for_timeout(n)                → 等待 <n>
		  page.wait_for_selector(sel)             → 等待 <sel>
		  page.hover / get_by_text().hover()      → 悬停 <target>
		  page.screenshot()                       → 截图
		  page.select_option(sel, val)            → 选择 <sel> <val>
		"""
		import re

		dsl_lines: list[str] = []

		def _unquote(s: str) -> str:
			"""Strip surrounding quotes from a string literal."""
			s = s.strip()
			if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
				return s[1:-1]
			return s

		def _resolve_locator(expr: str) -> str:
			"""Turn a locator expression into a DSL selector string."""
			expr = expr.strip()
			# get_by_text('xxx')
			m = re.match(r"get_by_text\s*\(\s*(['\"].+?['\"])\s*\)", expr)
			if m:
				return f'文本={_unquote(m.group(1))}'
			# get_by_role('btn', name='xxx') or get_by_role('btn')
			m = re.match(r"get_by_role\s*\(\s*(['\"].+?['\"])\s*(?:,\s*name\s*=\s*(['\"].+?['\"])\s*)?\)", expr)
			if m:
				role = _unquote(m.group(1))
				name = _unquote(m.group(2)) if m.group(2) else ''
				return f'role={role}[name={name}]' if name else f'role={role}'
			# get_by_placeholder('xxx')
			m = re.match(r"get_by_placeholder\s*\(\s*(['\"].+?['\"])\s*\)", expr)
			if m:
				return f'placeholder={_unquote(m.group(1))}'
			# get_by_label('xxx')
			m = re.match(r"get_by_label\s*\(\s*(['\"].+?['\"])\s*\)", expr)
			if m:
				return f'label={_unquote(m.group(1))}'
			# get_by_test_id('xxx')
			m = re.match(r"get_by_test_id\s*\(\s*(['\"].+?['\"])\s*\)", expr)
			if m:
				return f'testid={_unquote(m.group(1))}'
			# locator('sel')
			m = re.match(r"locator\s*\(\s*(['\"].+?['\"])\s*\)", expr)
			if m:
				return _unquote(m.group(1))
			return expr

		for raw_line in script.splitlines():
			line = raw_line.strip()
			# Skip boilerplate
			if not line or line.startswith('#') or line.startswith('import ') or \
			   line.startswith('from ') or line.startswith('async def ') or \
			   line.startswith('async with ') or line.startswith('asyncio.run') or \
			   'async_playwright' in line or 'chromium.launch' in line or \
			   'chromium.connect' in line or 'new_page()' in line or \
			   'browser.close' in line or 'context.close' in line or \
			   line.startswith('browser ') or line.startswith('context ') or \
			   line.startswith('page = ') or line == 'pass':
				continue

			# Strip leading 'await '
			stmt = re.sub(r'^await\s+', '', line)

			# ── goto ──────────────────────────────────────────────────────
			m = re.match(r"page\.goto\s*\(\s*(['\"].+?['\"])", stmt)
			if m:
				dsl_lines.append(f'打开 {_unquote(m.group(1))}')
				continue

			# ── screenshot ────────────────────────────────────────────────
			if re.match(r"page\.screenshot\s*\(", stmt):
				dsl_lines.append('截图')
				continue

			# ── wait_for_load_state ───────────────────────────────────────
			if re.match(r"page\.wait_for_load_state\s*\(", stmt):
				dsl_lines.append('等待加载完成')
				continue

			# ── wait_for_timeout ──────────────────────────────────────────
			m = re.match(r"page\.wait_for_timeout\s*\(\s*(\d+)\s*\)", stmt)
			if m:
				dsl_lines.append(f'等待 {m.group(1)}')
				continue

			# ── wait_for_selector ─────────────────────────────────────────
			m = re.match(r"page\.wait_for_selector\s*\(\s*(['\"].+?['\"])", stmt)
			if m:
				dsl_lines.append(f'等待 {_unquote(m.group(1))}')
				continue

			# ── keyboard.press ────────────────────────────────────────────
			m = re.match(r"page\.keyboard\.press\s*\(\s*(['\"].+?['\"])\s*\)", stmt)
			if m:
				dsl_lines.append(f'按键 {_unquote(m.group(1))}')
				continue

			# ── page.press(sel, key) ──────────────────────────────────────
			m = re.match(r"page\.press\s*\(\s*(['\"].+?['\"])\s*,\s*(['\"].+?['\"])\s*\)", stmt)
			if m:
				dsl_lines.append(f'按键 {_unquote(m.group(2))}')
				continue

			# ── page.fill(sel, val) ───────────────────────────────────────
			m = re.match(r"page\.fill\s*\(\s*(['\"].+?['\"])\s*,\s*(['\"].+?['\"])\s*\)", stmt)
			if m:
				dsl_lines.append(f'输入 {_unquote(m.group(1))} {_unquote(m.group(2))}')
				continue

			# ── page.type(sel, val) ───────────────────────────────────────
			m = re.match(r"page\.type\s*\(\s*(['\"].+?['\"])\s*,\s*(['\"].+?['\"])\s*\)", stmt)
			if m:
				dsl_lines.append(f'输入 {_unquote(m.group(1))} {_unquote(m.group(2))}')
				continue

			# ── page.click(sel) ───────────────────────────────────────────
			m = re.match(r"page\.click\s*\(\s*(['\"].+?['\"])\s*\)", stmt)
			if m:
				dsl_lines.append(f'点击 {_unquote(m.group(1))}')
				continue

			# ── page.hover(sel) ───────────────────────────────────────────
			m = re.match(r"page\.hover\s*\(\s*(['\"].+?['\"])\s*\)", stmt)
			if m:
				dsl_lines.append(f'悬停 {_unquote(m.group(1))}')
				continue

			# ── page.select_option(sel, val) ──────────────────────────────
			m = re.match(r"page\.select_option\s*\(\s*(['\"].+?['\"])\s*,\s*(['\"].+?['\"])\s*\)", stmt)
			if m:
				dsl_lines.append(f'选择 {_unquote(m.group(1))} {_unquote(m.group(2))}')
				continue

			# ── chained: page.<locator>.<action>(...) ─────────────────────
			# e.g. page.get_by_text('登录').click()
			#      page.locator('#id').fill('value')
			m = re.match(r"page\.(get_by_\w+|locator)\s*\(.+", stmt)
			if m:
				# Extract locator part and action part
				# Find the last .action() call
				chain_m = re.match(
					r"page\.((?:get_by_\w+|locator)\s*\([^)]*\))(?:\s*\.\s*\w+\([^)]*\))*\s*\.\s*(\w+)\s*\(([^)]*)\)\s*$",
					stmt
				)
				if chain_m:
					locator_expr = chain_m.group(1)
					action = chain_m.group(2)
					action_arg = chain_m.group(3).strip()
					sel = _resolve_locator(locator_expr)
					if action == 'click':
						dsl_lines.append(f'点击 {sel}')
					elif action in ('fill', 'type'):
						dsl_lines.append(f'输入 {sel} {_unquote(action_arg)}')
					elif action == 'hover':
						dsl_lines.append(f'悬停 {sel}')
					elif action == 'press':
						dsl_lines.append(f'按键 {_unquote(action_arg)}')
					elif action == 'select_option':
						dsl_lines.append(f'选择 {sel} {_unquote(action_arg)}')
					elif action in ('wait_for', 'scroll_into_view_if_needed'):
						dsl_lines.append(f'等待 {sel}')
					else:
						dsl_lines.append(f'# {line}')
					continue

			# ── scroll ────────────────────────────────────────────────────
			if 'scroll' in stmt.lower() and 'window.scrollBy' in stmt:
				m = re.search(r'scrollBy\s*\(\s*0\s*,\s*(-?\d+)', stmt)
				if m:
					dy = int(m.group(1))
					dsl_lines.append('滚动 下' if dy > 0 else '滚动 上')
					continue

			# ── evaluate / other — keep as comment ────────────────────────
			if stmt.startswith('page.'):
				dsl_lines.append(f'# {line}')

		return '\n'.join(dsl_lines) if dsl_lines else ''

	def _dsl_locator(self, page: Any, target: str) -> Any:
		"""Resolve a DSL selector string to a Playwright locator."""
		import re
		t = target.strip()
		if t.startswith('文本='):
			return page.get_by_text(t[3:].strip(), exact=False)
		if t.startswith('role='):
			rest = t[5:]
			name_m = re.search(r'\[name=(.+?)\]', rest)
			role = re.sub(r'\[.+\]', '', rest).strip()
			if name_m:
				return page.get_by_role(role, name=name_m.group(1))
			return page.get_by_role(role)
		if t.startswith('placeholder='):
			return page.get_by_placeholder(t[12:].strip())
		if t.startswith('label='):
			return page.get_by_label(t[6:].strip())
		if t.startswith('testid='):
			return page.get_by_test_id(t[7:].strip())
		return page.locator(t)

	async def set_browser_mode(self, request: web.Request) -> web.Response:
		"""Switch between headed and headless browser mode."""
		body = await self._json_body(request)
		headed = bool(body.get('headed', False))
		try:
			# Rebuild daemon with new headed setting if it differs
			if self.daemon.headed != headed:
				# Shutdown current session cleanly
				if self.daemon._session is not None:
					try:
						await self._dispatch('shutdown')
					except Exception:
						pass
				await self.daemon.shutdown()
				self.daemon = self._build_daemon(
					headed=headed,
					profile=self.daemon.profile,
					cdp_url=self.daemon.cdp_url,
					use_cloud=self.daemon.use_cloud,
				)
			return web.json_response({'success': True, 'headed': headed})
		except Exception as exc:
			return web.json_response({'success': False, 'error': str(exc)}, status=500)

	def _get_live_cdp_url(self) -> str:
		"""Get the actual CDP URL of the currently connected browser session.
		Falls back to _chrome_cdp_url, then tries to discover a local Chrome."""
		# 1. Try the daemon's active session
		try:
			session = self.daemon._session
			if session and hasattr(session, 'browser_session') and session.browser_session:
				bs = session.browser_session
				if hasattr(bs, 'cdp_url') and bs.cdp_url:
					cdp = bs.cdp_url
					# Convert ws:// to http:// for connect_over_cdp
					if cdp.startswith('ws://') or cdp.startswith('wss://'):
						from urllib.parse import urlparse
						p = urlparse(cdp)
						scheme = 'https' if cdp.startswith('wss://') else 'http'
						cdp = f'{scheme}://{p.netloc}'
					return cdp
		except Exception:
			pass

		# 2. Try to discover a local Chrome
		try:
			discovered = discover_chrome_cdp_url()
			if discovered:
				if discovered.startswith('ws://') or discovered.startswith('wss://'):
					from urllib.parse import urlparse
					p = urlparse(discovered)
					scheme = 'https' if discovered.startswith('wss://') else 'http'
					return f'{scheme}://{p.netloc}'
				return discovered
		except Exception:
			pass

		# 3. Try common local ports
		import urllib.request as _ur
		for port in [9222, 9223, 9224, 9225]:
			try:
				_ur.urlopen(f'http://127.0.0.1:{port}/json/version', timeout=1)
				return f'http://127.0.0.1:{port}'
			except Exception:
				pass

		# 4. Fall back to configured URL
		return self._chrome_cdp_url

	async def scan_browsers(self, request: web.Request) -> web.Response:
		"""Scan for locally running Chrome instances with remote debugging enabled."""
		import urllib.request as _ur
		import json as _json
		browsers = []
		for port in range(9222, 9232):
			try:
				with _ur.urlopen(f'http://127.0.0.1:{port}/json/version', timeout=1) as r:
					info = _json.loads(r.read())
					browsers.append({
						'url': f'http://127.0.0.1:{port}',
						'title': info.get('Browser', f'Chrome:{port}'),
						'type': 'local',
					})
			except Exception:
				pass
		# Also check host.docker.internal
		try:
			with _ur.urlopen('http://host.docker.internal:9222/json/version', timeout=1) as r:
				info = _json.loads(r.read())
				browsers.append({
					'url': 'http://host.docker.internal:9222',
					'title': info.get('Browser', 'Docker Chrome'),
					'type': 'docker',
				})
		except Exception:
			pass
		return web.json_response({'success': True, 'browsers': browsers})

	async def export_yaml(self, request: web.Request) -> web.Response:
		"""Generate YAML test file from DSL instructions."""
		import yaml as _yaml_mod
		body = await self._json_body(request)
		dsl = body.get('dsl', '').strip()
		params = body.get('params')  # {headers: [...], rows: [...]}
		if not dsl:
			return web.json_response({'success': False, 'error': 'dsl required'}, status=400)
		doc: dict = {
			'version': '1.0',
			'steps': [l.strip() for l in dsl.splitlines() if l.strip() and not l.strip().startswith('#')],
		}
		if params and params.get('headers'):
			doc['parameters'] = params['headers']
			doc['test_data'] = [
				{'id': f'case_{i+1}', **row}
				for i, row in enumerate(params.get('rows', []))
			]
		try:
			import yaml
			content = yaml.dump(doc, allow_unicode=True, default_flow_style=False, sort_keys=False)
		except ImportError:
			import json
			content = '# YAML (PyYAML not installed, showing JSON)\n' + json.dumps(doc, ensure_ascii=False, indent=2)
		return web.json_response({'success': True, 'content': content})

	async def export_pytest(self, request: web.Request) -> web.Response:
		"""Generate pytest file from DSL instructions."""
		body = await self._json_body(request)
		dsl = body.get('dsl', '').strip()
		params = body.get('params')
		base_url = body.get('base_url', 'http://127.0.0.1:9242')
		if not dsl:
			return web.json_response({'success': False, 'error': 'dsl required'}, status=400)

		lines = ['"""Auto-generated pytest from NLP instructions"""',
		         'import pytest, requests', '', f'BASE = {base_url!r}', '']

		if params and params.get('headers'):
			headers = params['headers']
			rows = params.get('rows', [])
			param_str = ', '.join(f'{json.dumps(list(r.values()))}' for r in rows)
			lines.append(f'@pytest.mark.parametrize("{", ".join(headers)}", [{param_str}])')
			lines.append(f'def test_nlp_parametrized({", ".join(headers)}):')
		else:
			lines.append('def test_nlp():')

		lines.append('    """Execute NLP instructions via Self API"""')
		lines.append('    dsl = """')
		for l in dsl.splitlines():
			lines.append(f'    {l}')
		lines.append('    """')

		if params and params.get('headers'):
			for h in params['headers']:
				lines.append(f'    dsl = dsl.replace("${{{{{h}}}}}", {h})')

		lines += [
			'    resp = requests.post(BASE + "/run-dsl", json={"dsl": dsl.strip()}, timeout=120)',
			'    assert resp.status_code == 200',
			'    data = resp.json()',
			'    assert data.get("success"), "NLP execution failed: " + str((data.get("data") or {}).get("error", ""))',
		]
		import json
		content = '\n'.join(lines)
		return web.json_response({'success': True, 'content': content})

	async def run_dsl(self, request: web.Request) -> web.Response:
		"""Execute natural-language DSL instructions in-process via the server's browser session."""
		import time as _time, json as _json, re as _re
		from pathlib import Path as _Path

		body = await self._json_body(request)
		dsl = body.get('dsl', '').strip()
		task_id = body.get('task_id') or _time.strftime('%Y%m%d_%H%M%S')
		capture_network = body.get('capture_network', True)
		custom_cdp_url = body.get('cdp_url', '').strip() or None

		if not dsl:
			return web.json_response({'success': False, 'error': 'dsl is required'}, status=400)

		trace_dir = _Path('traces') / task_id
		trace_dir.mkdir(parents=True, exist_ok=True)
		(trace_dir / 'dsl.txt').write_text(dsl, encoding='utf-8')

		start_ms = int(_time.time() * 1000)
		log_lines: list[str] = []
		network_requests: list[dict] = []
		exception_screenshots: list[str] = []
		screenshots: list[str] = []  # for GIF

		try:
			# Connect to browser — use custom CDP URL if provided (multi-browser support)
			if custom_cdp_url:
				# Build a temporary daemon for this specific browser
				tmp_daemon = self._build_daemon(headed=self.daemon.headed, profile=None, cdp_url=custom_cdp_url)
				await tmp_daemon.dispatch({'action': 'connect'})
				session = tmp_daemon._session
			else:
				current_mode = self._browser_target()['mode']
				await self._ensure_connected_target(current_mode)
				session = self.daemon._session

			if session is None or session.browser_session is None:
				return web.json_response({'success': False, 'error': '浏览器未连接'}, status=400)

			bs = session.browser_session

			# ── Network capture via CDP ────────────────────────────────────
			_SKIP_TYPES = {'stylesheet', 'image', 'font', 'media', 'websocket', 'other'}
			_SKIP_EXTS = {'.js', '.css', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.woff', '.woff2', '.ttf', '.ico'}

			if capture_network:
				try:
					cdp_session = await bs.get_or_create_cdp_session()
					await cdp_session.cdp_client.send.Network.enable(session_id=cdp_session.session_id)

					def _on_request(event):
						url = event.get('request', {}).get('url', '')
						resource_type = event.get('type', '').lower()
						if resource_type in _SKIP_TYPES:
							return
						ext = _Path(url.split('?')[0]).suffix.lower()
						if ext in _SKIP_EXTS:
							return
						network_requests.append({
							'url': url,
							'method': event.get('request', {}).get('method', 'GET'),
							'type': resource_type,
							'status': None,
						})

					def _on_response(event):
						url = event.get('response', {}).get('url', '')
						status = event.get('response', {}).get('status', 0)
						for req in reversed(network_requests):
							if req['url'] == url and req['status'] is None:
								req['status'] = status
								break

					cdp_session.cdp_client.register.Network.requestWillBeSent(_on_request)
					cdp_session.cdp_client.register.Network.responseReceived(_on_response)
				except Exception:
					pass  # Network capture is optional

			async def _get_page():
				return await bs.get_current_page()

			async def _find_element(sel: str):
				"""Find element by DSL selector using JS marker strategy for accuracy."""
				page = await _get_page()
				t = sel.strip()

				async def _js_mark_and_find(js_body: str):
					"""Run JS that sets data-dsl-target on the target, then return it."""
					cleanup = '() => document.querySelectorAll("[data-dsl-target]").forEach(e => e.removeAttribute("data-dsl-target"))'
					await page.evaluate(cleanup)
					await page.evaluate(js_body)
					elems = await page.get_elements_by_css_selector('[data-dsl-target]')
					await page.evaluate(cleanup)
					return elems[0] if elems else None

				if t.startswith('文本='):
					text = t[3:].strip()
					# Use JS to find the correct element — handles label-wrapped inputs
					js = f'''() => {{
						const text = {text!r}.toLowerCase().trim();
						function mark(el) {{ el.setAttribute('data-dsl-target','1'); }}
						// 1. label wrapping input: <label>Text <input></label>
						for (const label of document.querySelectorAll('label')) {{
							// Get only the label's own text (strip child input text)
							const clone = label.cloneNode(true);
							clone.querySelectorAll('input,textarea,select').forEach(e => e.remove());
							const labelText = clone.textContent.replace(/[:\\s]+$/,'').trim().toLowerCase();
							if (labelText === text || labelText.startsWith(text) || text.startsWith(labelText.replace(/[:\\s]+$/,''))) {{
								const inp = label.querySelector('input:not([type=hidden]),textarea,select');
								if (inp) {{ mark(inp); return; }}
							}}
						}}
						// 2. label[for] → input#id
						for (const label of document.querySelectorAll('label[for]')) {{
							const clone = label.cloneNode(true);
							clone.querySelectorAll('input,textarea,select').forEach(e => e.remove());
							const labelText = clone.textContent.replace(/[:\\s]+$/,'').trim().toLowerCase();
							if (labelText === text || labelText.startsWith(text) || text.startsWith(labelText)) {{
								const inp = document.getElementById(label.getAttribute('for'));
								if (inp) {{ mark(inp); return; }}
							}}
						}}
						// 3. placeholder
						for (const inp of document.querySelectorAll('input,textarea')) {{
							if ((inp.placeholder||'').toLowerCase().includes(text)) {{ mark(inp); return; }}
						}}
						// 4. aria-label / name
						for (const inp of document.querySelectorAll('input,textarea,select')) {{
							const al = (inp.getAttribute('aria-label')||inp.name||'').toLowerCase();
							if (al.includes(text)) {{ mark(inp); return; }}
						}}
						// 5. button/link/option by text
						for (const el of document.querySelectorAll('button,a,[role="button"],option')) {{
							if (el.textContent.trim().toLowerCase().includes(text)) {{ mark(el); return; }}
						}}
						// 6. any leaf element by text
						const all = document.querySelectorAll('span,div,p,li,td,th,h1,h2,h3,h4,h5,label,legend');
						for (const el of all) {{
							if (el.children.length === 0 && el.textContent.trim().toLowerCase().includes(text)) {{
								mark(el); return;
							}}
						}}
					}}'''
					return await _js_mark_and_find(js)

				if t.startswith('role='):
					rest = t[5:]
					name_m = _re.search(r'\[name=(.+?)\]', rest)
					role = _re.sub(r'\[.+\]', '', rest).strip()
					name = name_m.group(1) if name_m else None
					if not name:
						elems = await page.get_elements_by_css_selector(f'[role="{role}"], {role}')
						return elems[0] if elems else None
					js = f'''() => {{
						const name = {name!r}.toLowerCase();
						for (const el of document.querySelectorAll('[role="{role}"],{role}')) {{
							const txt = (el.textContent||el.getAttribute('aria-label')||'').trim().toLowerCase();
							if (txt.includes(name)) {{ el.setAttribute('data-dsl-target','1'); break; }}
						}}
					}}'''
					return await _js_mark_and_find(js)

				if t.startswith('placeholder='):
					ph = t[12:].strip()
					elems = await page.get_elements_by_css_selector(
						f'input[placeholder*="{ph}"], textarea[placeholder*="{ph}"]'
					)
					return elems[0] if elems else None

				if t.startswith('label='):
					label_text = t[6:].strip()
					js = f'''() => {{
						const text = {label_text!r}.toLowerCase();
						for (const label of document.querySelectorAll('label')) {{
							if (label.textContent.trim().toLowerCase().includes(text)) {{
								const inp = label.querySelector('input,textarea,select');
								if (inp) {{ inp.setAttribute('data-dsl-target','1'); return; }}
								const forId = label.getAttribute('for');
								if (forId) {{
									const el = document.getElementById(forId);
									if (el) {{ el.setAttribute('data-dsl-target','1'); return; }}
								}}
							}}
						}}
					}}'''
					return await _js_mark_and_find(js)

				if t.startswith('testid='):
					elems = await page.get_elements_by_css_selector(f'[data-testid="{t[7:].strip()}"]')
					return elems[0] if elems else None

				if t.startswith('xpath='):
					xpath = t[6:].strip()
					js = f'''() => {{
						const r = document.evaluate({xpath!r}, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
						if (r.singleNodeValue) r.singleNodeValue.setAttribute('data-dsl-target','1');
					}}'''
					return await _js_mark_and_find(js)

				# Default: CSS selector (or auto-detect text if not valid CSS)
				# If selector has no CSS special chars, treat as text search
				if not any(c in t for c in ('#', '.', '[', ':', '>', '+', '~', '*', '^', '$', '=')):
					# Looks like plain text — auto-convert to 文本= search
					return await _find_element(f'文本={t}')
				elems = await page.get_elements_by_css_selector(t)
				return elems[0] if elems else None

			screenshot_idx = 0

			def _split_selector_value(text: str):
				"""Split 'selector value' where selector may contain spaces (e.g. 文本=Customer name).
				Rules:
				- 文本=xxx  → selector ends at last space, value is last token(s)
				  BUT: 文本=Customer name 张三 → selector=文本=Customer name, value=张三
				  We detect: if starts with 文本= or role= or placeholder= or label=,
				  the value is the LAST space-separated segment that doesn't look like
				  part of the selector prefix.
				- For CSS selectors (#id, .class, xpath=, testid=) → first space splits.
				"""
				text = text.strip()
				# CSS-style selectors: no spaces in selector, split on first space
				for prefix in ('#', '.', 'xpath=', 'testid='):
					if text.startswith(prefix):
						parts = text.split(' ', 1)
						if len(parts) == 2:
							return parts[0], parts[1].strip()
						return text, None
				# Text/role/placeholder/label selectors: value is the last word
				# Strategy: find the last space and split there
				for prefix in ('文本=', 'role=', 'placeholder=', 'label='):
					if text.startswith(prefix):
						idx = text.rfind(' ')
						if idx > len(prefix):
							return text[:idx].strip(), text[idx+1:].strip()
						return text, None
				# Default: split on first space
				parts = text.split(' ', 1)
				if len(parts) == 2:
					return parts[0], parts[1].strip()
				return text, None

			for raw in dsl.splitlines():
				instr = raw.strip()
				if not instr or instr.startswith('#'):
					continue
				log_lines.append(f'▶ {instr}')

				try:
					# ── 导航 ──────────────────────────────────────────────
					if instr.startswith('打开 '):
						await bs.navigate_to(instr[3:].strip())
						continue
					if instr == '返回':
						page = await _get_page(); await page.go_back(); continue
					if instr == '前进':
						page = await _get_page(); await page.go_forward(); continue
					if instr == '刷新':
						page = await _get_page(); await page.reload(); continue
					if instr in ('等待加载完成', '等待网络空闲'):
						await asyncio.sleep(1); continue

					m = _re.match(r'^等待\s+(\d+)$', instr)
					if m:
						await asyncio.sleep(min(int(m.group(1)) / 1000, 10)); continue

					# ── 等待 <selector> / 等待消失 ──────────────────────────
					if instr.startswith('等待消失 '):
						sel_str = instr[5:].strip()
						el = await _find_element(sel_str)
						if el:
							# Poll until element is gone (max 10s)
							for _ in range(20):
								await asyncio.sleep(0.5)
								try:
									info = await el.get_basic_info()
									if info.get('error'):
										break
								except Exception:
									break
						continue

					if instr.startswith('等待 '):
						sel_str = instr[3:].strip()
						# Wait for element to appear (max 10s)
						for _ in range(20):
							el = await _find_element(sel_str)
							if el:
								break
							await asyncio.sleep(0.5)
						continue

					# ── 点击 ──────────────────────────────────────────────
					if instr.startswith('点击 ') or instr.startswith('点击'):
						sel_str = instr[3:].strip() if instr.startswith('点击 ') else instr[2:].strip()
						el = await _find_element(sel_str)
						if el:
							await el.click()
							await asyncio.sleep(0.5)
						else:
							raise RuntimeError(f'找不到元素: {sel_str}')
						continue

					# ── 双击 ──────────────────────────────────────────────
					if instr.startswith('双击 '):
						el = await _find_element(instr[3:].strip())
						if el: await el.click(click_count=2)
						continue

					# ── 右键 ──────────────────────────────────────────────
					if instr.startswith('右键 '):
						el = await _find_element(instr[3:].strip())
						if el: await el.click(button='right')
						continue

					# ── 悬停 ──────────────────────────────────────────────
					if instr.startswith('悬停 '):
						el = await _find_element(instr[3:].strip())
						if el: await el.hover()
						continue

					# ── 输入 ──────────────────────────────────────────────
					m = _re.match(r'^输入\s+(.+)$', instr)
					if m:
						sel, val = _split_selector_value(m.group(1))
						if sel and val is not None:
							el = await _find_element(sel)
							if el:
								await el.fill(val)
							else:
								raise RuntimeError(f'找不到输入框: {sel}')
						continue

					# ── 清空 ──────────────────────────────────────────────
					if instr.startswith('清空 '):
						el = await _find_element(instr[3:].strip())
						if el: await el.fill('')
						continue

					# ── 按键 ──────────────────────────────────────────────
					if instr.startswith('按键 ') or instr.startswith('快捷键 '):
						prefix_len = 3 if instr.startswith('按键 ') else 4
						key = instr[prefix_len:].strip()
						page = await _get_page()
						await page.press(key)
						await asyncio.sleep(0.5)
						continue

					# ── 输入文字 ──────────────────────────────────────────
					if instr.startswith('输入文字 '):
						page = await _get_page()
						await page.press(instr[5:].strip())
						continue

					# ── 选择 ──────────────────────────────────────────────
					m = _re.match(r'^选择\s+(.+)$', instr)
					if m:
						sel, val = _split_selector_value(m.group(1))
						if sel and val is not None:
							el = await _find_element(sel)
							if el: await el.select_option(val)
						continue

					# ── 勾选 / 取消勾选 ───────────────────────────────────
					if instr.startswith('勾选 '):
						el = await _find_element(instr[3:].strip())
						if el: await el.check()
						continue
					if instr.startswith('取消勾选 '):
						el = await _find_element(instr[5:].strip())
						if el: await el.check()  # toggle
						continue

					# ── 滚动 ──────────────────────────────────────────────
					if instr in ('滚动 下', '向下滚动'):
						page = await _get_page()
						await page.evaluate('() => window.scrollBy(0, 600)')
						continue
					if instr in ('滚动 上', '向上滚动'):
						page = await _get_page()
						await page.evaluate('() => window.scrollBy(0, -600)')
						continue
					if instr == '滚动到底部':
						page = await _get_page()
						await page.evaluate('() => window.scrollTo(0, document.body.scrollHeight)')
						continue
					if instr == '滚动到顶部':
						page = await _get_page()
						await page.evaluate('() => window.scrollTo(0, 0)')
						continue

					# ── 截图 ──────────────────────────────────────────────
					if instr == '截图' or instr.startswith('截图 '):
						screenshot_idx += 1
						p = str(trace_dir / f'screenshot_{screenshot_idx}.png')
						await bs.take_screenshot(path=p)
						screenshots.append(p)  # track for GIF
						log_lines.append(f'  📸 截图已保存: {p}')
						continue

					# ── 获取文本 ──────────────────────────────────────────
					if instr.startswith('获取文本 '):
						el = await _find_element(instr[5:].strip())
						if el:
							try:
								# Mark element, then get its innerText via JS
								page = await _get_page()
								await page.evaluate('() => document.querySelectorAll("[data-dsl-tmp]").forEach(e=>e.removeAttribute("data-dsl-tmp"))')
								node_id = await el._get_node_id()
								# Use DOM.setAttributeValue to mark, then query
								await el._client.send.DOM.setAttributeValue(
									{{'nodeId': node_id, 'name': 'data-dsl-tmp', 'value': '1'}},
									session_id=await el._ensure_session()
								)
								text = await page.evaluate('() => { const el = document.querySelector("[data-dsl-tmp]"); return el ? el.innerText.trim() : ""; }')
								await page.evaluate('() => document.querySelectorAll("[data-dsl-tmp]").forEach(e=>e.removeAttribute("data-dsl-tmp"))')
								log_lines.append(f'  📝 文本: {text}')
							except Exception as e:
								log_lines.append(f'  📝 获取文本失败: {e}')
						continue

					# ── 获取属性 ──────────────────────────────────────────
					m = _re.match(r'^获取属性\s+(\S+)\s+(\S+)$', instr)
					if m:
						el = await _find_element(m.group(1))
						if el:
							val = await el.get_attribute(m.group(2))
							log_lines.append(f'  📝 属性 {m.group(2)}: {val}')
						continue

					# ── 获取标题 / URL ────────────────────────────────────
					if instr == '获取标题':
						title = await bs.get_current_page_title()
						log_lines.append(f'  📝 标题: {title}')
						continue
					if instr == '获取URL':
						url = await bs.get_current_page_url()
						log_lines.append(f'  📝 URL: {url}')
						continue

					# ── 执行JS ────────────────────────────────────────────
					if instr.startswith('执行JS '):
						code = instr[4:].strip()
						page = await _get_page()
						# Actor page.evaluate needs arrow function format
						if not code.startswith('(') and not code.startswith('async'):
							code = f'() => {code}'
						result = await page.evaluate(code)
						if result:
							log_lines.append(f'  📝 JS结果: {result}')
						continue

					# ── 断言 ──────────────────────────────────────────────
					if instr.startswith('断言可见 '):
						el = await _find_element(instr[5:].strip())
						assert el is not None, f'断言失败: 元素不可见 [{instr[5:].strip()}]'
						continue
					if instr.startswith('断言URL包含 '):
						url = await bs.get_current_page_url()
						assert instr[8:].strip() in url, f'断言失败: URL不包含 [{instr[8:].strip()}]'
						continue
					if instr.startswith('断言标题包含 '):
						title = await bs.get_current_page_title()
						assert instr[8:].strip() in title, f'断言失败: 标题不包含 [{instr[8:].strip()}]'
						continue

					log_lines.append(f'  ⚠ 未识别指令: {instr}')

				except AssertionError:
					raise
				except Exception as step_err:
					raise RuntimeError(f'指令 [{instr}] 执行失败: {step_err}') from step_err

			elapsed_ms = int(_time.time() * 1000) - start_ms
			log_text = '\n'.join(log_lines)

			# Generate GIF from screenshots
			gif_path = None
			if screenshots:
				try:
					import importlib
					if importlib.util.find_spec('PIL'):
						from PIL import Image
						frames = []
						for sp in screenshots:
							try:
								frames.append(Image.open(sp).convert('RGBA'))
							except Exception:
								pass
						if frames:
							gif_path = str(trace_dir / 'recording.gif')
							frames[0].save(gif_path, save_all=True, append_images=frames[1:],
							               optimize=False, duration=800, loop=0)
							log_lines.append(f'  🎬 GIF 已生成: {gif_path}')
				except Exception:
					pass

			trace = {
				'task_id': task_id, 'mode': 'dsl', 'success': True,
				'elapsed_ms': elapsed_ms, 'dsl': dsl, 'log': log_text,
				'network': network_requests[-50:],
			}
			(trace_dir / 'trace.json').write_text(_json.dumps(trace, ensure_ascii=False, indent=2), encoding='utf-8')
			return web.json_response({
				'success': True,
				'data': {
					'task_id': task_id, 'elapsed_ms': elapsed_ms, 'mode': 'dsl',
					'log': log_text, 'network': network_requests[-50:],
					'exception_screenshots': exception_screenshots,
					'gif': gif_path,
				}
			})

		except Exception as exc:
			elapsed_ms = int(_time.time() * 1000) - start_ms
			err_msg = str(exc)
			log_text = '\n'.join(log_lines)

			# Take exception screenshot
			try:
				exc_shot = f'exception_{len(exception_screenshots)+1}.png'
				exc_path = str(trace_dir / exc_shot)
				await bs.take_screenshot(path=exc_path)
				exception_screenshots.append(exc_shot)
				log_lines.append(f'  📸 异常截图: {exc_path}')
				import traceback as _tb
				log_lines.append(f'  🔴 堆栈: {_tb.format_exc()[-500:]}')
			except Exception:
				pass

			log_text = '\n'.join(log_lines)
			trace = {
				'task_id': task_id, 'mode': 'dsl', 'success': False,
				'elapsed_ms': elapsed_ms, 'dsl': dsl, 'error': err_msg, 'log': log_text,
				'network': network_requests[-50:],
				'exception_screenshots': exception_screenshots,
			}
			(trace_dir / 'trace.json').write_text(_json.dumps(trace, ensure_ascii=False, indent=2), encoding='utf-8')
			return web.json_response({
				'success': False,
				'data': {
					'task_id': task_id, 'elapsed_ms': elapsed_ms, 'mode': 'dsl',
					'log': log_text, 'error': err_msg,
					'network': network_requests[-50:],
					'exception_screenshots': exception_screenshots,
				}
			})

	def _dsl_to_python(self, dsl: str, trace_dir: str = '.', cdp_url: str | None = None) -> str:
			"""Compile DSL instructions to a runnable Playwright Python script."""
			import re

			cdp_url = cdp_url or self._get_live_cdp_url()

			def _resolve_selector(target: str) -> str:
				t = target.strip()
				if t.startswith('文本='):
					return f'page.get_by_text({t[3:].strip()!r}, exact=False)'
				if t.startswith('role='):
					rest = t[5:]
					name_m = re.search(r'\[name=(.+?)\]', rest)
					role = re.sub(r'\[.+\]', '', rest).strip()
					if name_m:
						return f'page.get_by_role({role!r}, name={name_m.group(1)!r})'
					return f'page.get_by_role({role!r})'
				if t.startswith('placeholder='):
					return f'page.get_by_placeholder({t[12:].strip()!r})'
				if t.startswith('label='):
					return f'page.get_by_label({t[6:].strip()!r})'
				if t.startswith('testid='):
					return f'page.get_by_test_id({t[7:].strip()!r})'
				if t.startswith('xpath='):
					return f'page.locator({t!r})'
				return f'page.locator({t!r})'

			lines: list[str] = []
			screenshot_idx = [0]
			in_iframe = [False]

			def pg() -> str:
				return '_iframe_ctx' if in_iframe[0] else 'page'

			def loc(sel: str) -> str:
				return _resolve_selector(sel).replace('page.', pg() + '.')

			for raw in dsl.splitlines():
				instr = raw.strip()
				if not instr or instr.startswith('#'):
					continue

				p = pg()

				# ── 导航 ──────────────────────────────────────────────────────
				if instr.startswith('打开 '):
					lines.append(f'    await stable_goto({p}, {instr[3:].strip()!r})')
					continue
				if instr == '返回':
					lines.append(f'    await {p}.go_back()')
					lines.append(f'    await wait_for_navigation({p})')
					continue
				if instr == '前进':
					lines.append(f'    await {p}.go_forward()')
					lines.append(f'    await wait_for_navigation({p})')
					continue
				if instr == '刷新':
					lines.append(f'    await {p}.reload()')
					lines.append(f'    await wait_for_navigation({p})')
					continue
				if instr in ('等待加载完成', '等待网络空闲'):
					lines.append(f'    await wait_for_navigation({p})')
					continue

				# ── 等待 N ms ─────────────────────────────────────────────────
				m = re.match(r'^等待\s+(\d+)$', instr)
				if m:
					lines.append(f'    await wait_for_navigation({p})')
					continue

				# ── 等待消失 ──────────────────────────────────────────────────
				if instr.startswith('等待消失 '):
					lines.append(f'    await {loc(instr[5:].strip())}.wait_for(state="hidden", timeout=15000)')
					continue

				# ── 等待 <selector> ───────────────────────────────────────────
				if instr.startswith('等待 '):
					lines.append(f'    await {loc(instr[3:].strip())}.wait_for(state="visible", timeout=15000)')
					continue

				# ── 点击 ──────────────────────────────────────────────────────
				if instr.startswith('点击 '):
					l = loc(instr[3:].strip())
					lines.append(f'    await {l}.wait_for(state="visible", timeout=15000)')
					lines.append(f'    await {l}.click()')
					lines.append(f'    await wait_for_navigation({p})')
					continue

				# ── 双击 ──────────────────────────────────────────────────────
				if instr.startswith('双击 '):
					l = loc(instr[3:].strip())
					lines.append(f'    await {l}.wait_for(state="visible", timeout=15000)')
					lines.append(f'    await {l}.dbl_click()')
					continue

				# ── 右键 ──────────────────────────────────────────────────────
				if instr.startswith('右键 '):
					l = loc(instr[3:].strip())
					lines.append(f'    await {l}.wait_for(state="visible", timeout=15000)')
					lines.append(f'    await {l}.click(button="right")')
					continue

				# ── 悬停 ──────────────────────────────────────────────────────
				if instr.startswith('悬停 '):
					l = loc(instr[3:].strip())
					lines.append(f'    await {l}.wait_for(state="visible", timeout=15000)')
					lines.append(f'    await {l}.hover()')
					continue

				# ── 拖拽 <src> 到 <dst> ───────────────────────────────────────
				m = re.match(r'^拖拽\s+(\S+)\s+到\s+(\S+)$', instr)
				if m:
					lines.append(f'    await {p}.drag_and_drop({m.group(1)!r}, {m.group(2)!r})')
					continue

				# ── 输入 <selector> <value> ───────────────────────────────────
				m = re.match(r'^输入\s+(\S+)\s+(.+)$', instr)
				if m:
					l = loc(m.group(1))
					lines.append(f'    await {l}.wait_for(state="visible", timeout=15000)')
					lines.append(f'    await {l}.fill({m.group(2).strip()!r})')
					continue

				# ── 清空 ──────────────────────────────────────────────────────
				if instr.startswith('清空 '):
					lines.append(f'    await {loc(instr[3:].strip())}.clear()')
					continue

				# ── 输入文字 <text> (keyboard.type) ──────────────────────────
				if instr.startswith('输入文字 '):
					lines.append(f'    await {p}.keyboard.type({instr[5:].strip()!r})')
					continue

				# ── 按键 ──────────────────────────────────────────────────────
				if instr.startswith('按键 '):
					lines.append(f'    await {p}.keyboard.press({instr[3:].strip()!r})')
					lines.append(f'    await wait_for_navigation({p})')
					continue

				# ── 快捷键 ────────────────────────────────────────────────────
				if instr.startswith('快捷键 '):
					lines.append(f'    await {p}.keyboard.press({instr[4:].strip()!r})')
					continue

				# ── 选择 <selector> <value> ───────────────────────────────────
				m = re.match(r'^选择\s+(\S+)\s+(.+)$', instr)
				if m:
					lines.append(f'    await {loc(m.group(1))}.select_option({m.group(2).strip()!r})')
					continue

				# ── 勾选 / 取消勾选 ───────────────────────────────────────────
				if instr.startswith('勾选 '):
					lines.append(f'    await {loc(instr[3:].strip())}.check()')
					continue
				if instr.startswith('取消勾选 '):
					lines.append(f'    await {loc(instr[5:].strip())}.uncheck()')
					continue

				# ── 上传文件 <selector> <path> ────────────────────────────────
				m = re.match(r'^上传文件\s+(\S+)\s+(.+)$', instr)
				if m:
					lines.append(f'    await {loc(m.group(1))}.set_input_files({m.group(2).strip()!r})')
					continue

				# ── 滚动 ──────────────────────────────────────────────────────
				if instr in ('滚动 下', '向下滚动'):
					lines.append(f'    await {p}.evaluate("window.scrollBy(0, 600)")')
					continue
				if instr in ('滚动 上', '向上滚动'):
					lines.append(f'    await {p}.evaluate("window.scrollBy(0, -600)")')
					continue
				if instr == '滚动到底部':
					lines.append(f'    await {p}.evaluate("window.scrollTo(0, document.body.scrollHeight)")')
					continue
				if instr == '滚动到顶部':
					lines.append(f'    await {p}.evaluate("window.scrollTo(0, 0)")')
					continue
				if instr.startswith('滚动到 '):
					lines.append(f'    await {loc(instr[4:].strip())}.scroll_into_view_if_needed()')
					continue

				# ── 截图 ──────────────────────────────────────────────────────
				if instr == '截图':
					screenshot_idx[0] += 1
					n = screenshot_idx[0]
					lines.append(f'    await {p}.screenshot(path=r"{trace_dir}/screenshot_{n}.png")')
					lines.append(f'    print("截图已保存: {trace_dir}/screenshot_{n}.png")')
					continue
				if instr.startswith('截图 '):
					screenshot_idx[0] += 1
					n = screenshot_idx[0]
					lines.append(f'    await {loc(instr[3:].strip())}.screenshot(path=r"{trace_dir}/screenshot_{n}.png")')
					lines.append(f'    print("截图已保存: {trace_dir}/screenshot_{n}.png")')
					continue

				# ── 获取文本 ──────────────────────────────────────────────────
				if instr.startswith('获取文本 '):
					lines.append(f'    _text = await {loc(instr[5:].strip())}.inner_text()')
					lines.append('    print(f"获取文本: {_text}")')
					continue

				# ── 获取属性 <selector> <attr> ────────────────────────────────
				m = re.match(r'^获取属性\s+(\S+)\s+(\S+)$', instr)
				if m:
					lines.append(f'    _attr = await {loc(m.group(1))}.get_attribute({m.group(2)!r})')
					lines.append('    print(f"获取属性: {_attr}")')
					continue

				# ── 获取标题 / 获取URL ────────────────────────────────────────
				if instr == '获取标题':
					lines.append(f'    _title = await {p}.title()')
					lines.append('    print(f"标题: {_title}")')
					continue
				if instr == '获取URL':
					lines.append(f'    print(f"URL: {{{p}.url}}")')
					continue

				# ── 断言 ──────────────────────────────────────────────────────
				if instr.startswith('断言可见 '):
					l = loc(instr[5:].strip())
					lines.append(f'    assert await {l}.is_visible(), "断言失败: 元素不可见"')
					continue
				m = re.match(r'^断言文本\s+(\S+)\s+(.+)$', instr)
				if m:
					l = loc(m.group(1))
					expected = m.group(2).strip()
					lines.append(f'    _t = await {l}.inner_text()')
					lines.append(f'    assert {expected!r} in _t, f"断言失败: 期望包含 {expected!r}, 实际: {{_t}}"')
					continue
				if instr.startswith('断言URL包含 '):
					text = instr[8:].strip()
					lines.append(f'    assert {text!r} in {p}.url, f"断言失败: URL不包含 {text!r}"')
					continue
				if instr.startswith('断言标题包含 '):
					text = instr[8:].strip()
					lines.append(f'    _title = await {p}.title()')
					lines.append(f'    assert {text!r} in _title, f"断言失败: 标题不包含 {text!r}"')
					continue

				# ── 多标签页 ──────────────────────────────────────────────────
				if instr.startswith('新标签页 '):
					url = instr[5:].strip()
					lines.append(f'    _new_page = await browser.contexts[0].new_page()')
					lines.append(f'    await stable_goto(_new_page, {url!r})')
					lines.append('    page = _new_page')
					continue
				m = re.match(r'^切换标签页\s+(\d+)$', instr)
				if m:
					lines.append(f'    page = browser.contexts[0].pages[{m.group(1)}]')
					continue
				if instr == '关闭标签页':
					lines.append('    await page.close()')
					lines.append('    page = browser.contexts[0].pages[-1] if browser.contexts[0].pages else page')
					continue

				# ── 弹窗处理 ──────────────────────────────────────────────────
				if instr == '接受弹窗':
					lines.append('    page.on("dialog", lambda d: asyncio.ensure_future(d.accept()))')
					continue
				if instr == '取消弹窗':
					lines.append('    page.on("dialog", lambda d: asyncio.ensure_future(d.dismiss()))')
					continue

				# ── iframe ────────────────────────────────────────────────────
				if instr.startswith('进入iframe '):
					sel_str = instr[7:].strip()
					lines.append(f'    _iframe_ctx = page.frame_locator({sel_str!r})')
					in_iframe[0] = True
					continue
				if instr == '退出iframe':
					in_iframe[0] = False
					lines.append('    # 退出 iframe，恢复主页面上下文')
					continue

				# ── 执行JS ────────────────────────────────────────────────────
				if instr.startswith('执行JS '):
					code = instr[4:].strip()
					lines.append(f'    _js_result = await {p}.evaluate({code!r})')
					lines.append('    if _js_result is not None: print(f"执行JS结果: {_js_result}")')
					continue

				# ── unknown ───────────────────────────────────────────────────
				lines.append(f'    # 未识别指令: {instr}')

			body_code = '\n'.join(lines) if lines else '    pass'
			# body_code lines use 4-space indent; re-indent to 8 spaces for async with block
			body_code_indented = '\n'.join(
				('    ' + l) if l.strip() else l
				for l in body_code.splitlines()
			)

			script_lines = [
				'import asyncio',
				'import sys',
				'import os',
				'from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError',
				'',
				'async def stable_goto(page, url, timeout=30000):',
				'    await page.goto(url, wait_until="domcontentloaded", timeout=timeout)',
				'    try:',
				'        await page.wait_for_load_state("networkidle", timeout=10000)',
				'    except PlaywrightTimeoutError:',
				'        pass',
				'',
				'async def wait_for_navigation(page, timeout=12000):',
				'    try:',
				'        await page.wait_for_load_state("networkidle", timeout=timeout)',
				'    except PlaywrightTimeoutError:',
				'        try:',
				'            await page.wait_for_load_state("domcontentloaded", timeout=5000)',
				'        except PlaywrightTimeoutError:',
				'            pass',
				'',
				'async def main():',
				'    async with async_playwright() as p:',
				f'        browser = await p.chromium.connect_over_cdp({cdp_url!r})',
				'        page = browser.contexts[0].pages[0] if browser.contexts and browser.contexts[0].pages else await browser.contexts[0].new_page()',
				body_code_indented,
				'        print("DSL 执行完成")',
				'',
				'asyncio.run(main())',
			]
			return '\n'.join(script_lines) + '\n'


	async def run_playwright(self, request: web.Request) -> web.Response:
		"""Execute a Playwright script with wait-for-state strategy (no hardcoded timeouts)."""
		import time as _time, json as _json, asyncio as _asyncio
		from pathlib import Path as _Path

		body = await self._json_body(request)
		script = body.get('script', '').strip()
		task_id = body.get('task_id') or _time.strftime('%Y%m%d_%H%M%S')

		if not script:
			return web.json_response({'success': False, 'error': 'script is required'}, status=400)

		# Rewrite connect_over_cdp URL to the live session URL
		import re as _re
		live_cdp = self._get_live_cdp_url()
		self._auto_launch_chrome(live_cdp)
		script = _re.sub(
			r'connect_over_cdp\s*\(\s*["\']http[^"\']*["\']\s*\)',
			f'connect_over_cdp({live_cdp!r})',
			script
		)

		# Wrap user script with stability helpers injected
		wrapped = self._wrap_playwright_script(script)

		trace_dir = _Path('traces') / task_id
		trace_dir.mkdir(parents=True, exist_ok=True)

		start_ms = int(_time.time() * 1000)
		try:
			# Write script to temp file and execute
			import subprocess, sys, os
			script_file = trace_dir / 'script.py'
			script_file.write_text(wrapped, encoding='utf-8')

			proc = await _asyncio.create_subprocess_exec(
				sys.executable, str(script_file),
				stdout=_asyncio.subprocess.PIPE,
				stderr=_asyncio.subprocess.PIPE,
				env=os.environ.copy(),  # inherit env so playwright/pip packages are found
			)
			try:
				stdout, stderr = await _asyncio.wait_for(proc.communicate(), timeout=90)
			except _asyncio.TimeoutError:
				proc.kill()
				await proc.communicate()  # drain pipes to avoid resource leak
				return web.json_response({'success': False, 'error': 'Script timed out after 90s', 'task_id': task_id}, status=400)

			elapsed_ms = int(_time.time() * 1000) - start_ms
			stdout_str = stdout.decode('utf-8', errors='replace')
			stderr_str = stderr.decode('utf-8', errors='replace')

			success = proc.returncode == 0
			# Save trace
			trace = {
				'task_id': task_id,
				'mode': 'playwright',
				'success': success,
				'elapsed_ms': elapsed_ms,
				'stdout': stdout_str[-2000:],
				'stderr': stderr_str[-2000:] if not success else '',
				'script': script,
			}
			(trace_dir / 'trace.json').write_text(_json.dumps(trace, ensure_ascii=False, indent=2), encoding='utf-8')

			return web.json_response({
				'success': success,
				'data': {
					'task_id': task_id,
					'elapsed_ms': elapsed_ms,
					'stdout': stdout_str[-1000:],
					'error': stderr_str[-500:] if not success else None,
					'mode': 'playwright',
				}
			})
		except Exception as exc:
			return web.json_response({'success': False, 'error': str(exc), 'task_id': task_id}, status=500)

	def _wrap_playwright_script(self, script: str) -> str:
		"""Wrap user Playwright script with stability helpers:
		- Replace waitForTimeout with waitForLoadState
		- Add auto-wait before interactions
		- Set sensible default timeouts
		"""
		import re

		# ── Step 1: strip conflicting imports from user script ─────────────────
		# Remove lines that re-import asyncio / playwright (we inject them in preamble)
		script = re.sub(r'^import asyncio\s*$', '# import asyncio  # moved to preamble', script, flags=re.MULTILINE)
		script = re.sub(r'^import sys\s*$', '# import sys  # moved to preamble', script, flags=re.MULTILINE)
		script = re.sub(r'^from playwright.*async_playwright.*$', '# playwright import moved to preamble', script, flags=re.MULTILINE)

		# ── Step 2: replace hardcoded waits with state-based waits ────────────
		# wait_for_timeout(N) / wait_for_timeout(variable)
		script = re.sub(
			r'await\s+page\.wait_for_timeout\s*\([^)]+\)',
			'await page.wait_for_load_state("networkidle")',
			script
		)
		script = re.sub(
			r'await\s+page\.waitForTimeout\s*\([^)]+\)',
			'await page.wait_for_load_state("networkidle")',
			script
		)
		# time.sleep(N) inside async scripts
		script = re.sub(
			r'time\.sleep\s*\([^)]+\)',
			'await page.wait_for_load_state("networkidle")',
			script
		)
		# asyncio.sleep(N) — replace with short yield
		script = re.sub(
			r'await\s+asyncio\.sleep\s*\([^)]+\)',
			'await page.wait_for_load_state("networkidle")',
			script
		)

		# ── Step 3: inject preamble (imports + helpers) ────────────────────────
		preamble = '''import asyncio
import sys
import os
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# ── Stability helpers ──────────────────────────────────────────────────────
async def stable_click(page, selector, timeout=15000):
    """Click after waiting for element to be visible and enabled."""
    await page.wait_for_selector(selector, state="visible", timeout=timeout)
    await page.locator(selector).wait_for(state="enabled", timeout=timeout)
    await page.click(selector)

async def stable_fill(page, selector, value, timeout=15000):
    """Fill after waiting for element to be editable."""
    await page.wait_for_selector(selector, state="visible", timeout=timeout)
    await page.fill(selector, value)

async def stable_goto(page, url, timeout=30000):
    """Navigate and wait for network idle with domcontentloaded fallback."""
    await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
    except PlaywrightTimeoutError:
        pass  # networkidle timeout is ok, page may have long-polling

async def wait_for_navigation(page, timeout=15000):
    """Wait for page to settle after an action."""
    try:
        await page.wait_for_load_state("networkidle", timeout=timeout)
    except PlaywrightTimeoutError:
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
        except PlaywrightTimeoutError:
            pass

# ── User script ────────────────────────────────────────────────────────────
'''
		return preamble + '\n' + script

	async def run(self) -> None:
		loop = asyncio.get_running_loop()

		def _signal_handler() -> None:
			asyncio.create_task(self.shutdown())

		for sig in (signal.SIGINT, signal.SIGTERM):
			with contextlib.suppress(NotImplementedError):
				loop.add_signal_handler(sig, _signal_handler)

		# Suppress InvalidStateError from websocket disconnects
		import asyncio as _asyncio
		_orig_exc_handler = loop.get_exception_handler()
		def _exc_handler(loop, ctx):
			exc = ctx.get('exception')
			if isinstance(exc, _asyncio.InvalidStateError):
				return  # suppress websocket disconnect noise
			if _orig_exc_handler:
				_orig_exc_handler(loop, ctx)
			else:
				loop.default_exception_handler(ctx)
		loop.set_exception_handler(_exc_handler)

		app = self.build_app()
		self._runner = web.AppRunner(app)
		await self._runner.setup()
		self._site = web.TCPSite(self._runner, self.host, self.port)
		await self._site.start()
		print(f'')
		print(f'  ✅ Self 服务已启动')
		print(f'  🌐 本机访问:    http://localhost:{self.port}')
		print(f'  🌐 本机访问:    http://127.0.0.1:{self.port}')
		if self.host in ('0.0.0.0', '::'):
			print(f'  🌐 局域网访问:  http://<本机IP>:{self.port}')
		print(f'')
		await self._shutdown_event.wait()

	async def shutdown(self) -> None:
		if self._shutdown_event.is_set():
			return
		self._shutdown_event.set()
		await self.daemon.shutdown()
		if self._runner is not None:
			await self._runner.cleanup()


async def serve(args: argparse.Namespace) -> int:
	service = HttpService(
		host=args.host,
		port=args.port,
		headed=args.headed,
		profile=args.profile,
		cdp_url=args.cdp_url,
		use_cloud=getattr(args, 'use_cloud', False),
		cloud_timeout=getattr(args, 'cloud_timeout', None),
		cloud_proxy_country_code=getattr(args, 'cloud_proxy_country', None),
		cloud_profile_id=getattr(args, 'cloud_profile_id', None),
		session=args.session or 'default',
	)
	await service.run()
	return 0


def main() -> int:
	# Load .env file before parsing args
	try:
		from dotenv import load_dotenv
		load_dotenv()
	except ImportError:
		pass  # python-dotenv not installed

	parser = argparse.ArgumentParser(description='browser-use HTTP server')
	parser.add_argument('--host', default='127.0.0.1')
	parser.add_argument('--port', type=int, default=9242)
	parser.add_argument('--session', default='default')
	parser.add_argument('--headed', action='store_true')
	parser.add_argument('--profile')
	parser.add_argument('--cdp-url')
	parser.add_argument('--use-cloud', action='store_true')
	parser.add_argument('--cloud-timeout', type=int)
	parser.add_argument('--cloud-proxy-country')
	parser.add_argument('--cloud-profile-id')
	args = parser.parse_args()
	return asyncio.run(serve(args))


if __name__ == '__main__':
	sys.exit(main())
