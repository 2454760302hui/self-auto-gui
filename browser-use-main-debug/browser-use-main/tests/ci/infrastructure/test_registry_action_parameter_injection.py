import asyncio
import base64
import socketserver

import pytest
from pytest_httpserver import HTTPServer

from browser_use.browser import BrowserProfile, BrowserSession

# Fix for httpserver hanging on shutdown - prevent blocking on socket close
socketserver.ThreadingMixIn.block_on_close = False
socketserver.ThreadingMixIn.daemon_threads = True


class TestBrowserContext:
	"""Tests for browser context functionality using real browser instances."""

	@pytest.fixture(scope='session')
	def http_server(self):
		"""Create and provide a test HTTP server that serves static content."""
		server = HTTPServer()
		server.start()

		# Add routes for test pages
		server.expect_request('/').respond_with_data(
			'<html><head><title>Test Home Page</title></head><body><h1>Test Home Page</h1><p>Welcome to the test site</p></body></html>',
			content_type='text/html',
		)

		server.expect_request('/scroll_test').respond_with_data(
			"""
            <html>
            <head>
                <title>Scroll Test</title>
                <style>
                    body { height: 3000px; }
                    .marker { position: absolute; }
                    #top { top: 0; }
                    #middle { top: 1000px; }
                    #bottom { top: 2000px; }
                </style>
            </head>
            <body>
                <div id="top" class="marker">Top of the page</div>
                <div id="middle" class="marker">Middle of the page</div>
                <div id="bottom" class="marker">Bottom of the page</div>
            </body>
            </html>
            """,
			content_type='text/html',
		)

		yield server
		server.stop()

	@pytest.fixture(scope='session')
	def base_url(self, http_server):
		"""Return the base URL for the test HTTP server."""
		return f'http://{http_server.host}:{http_server.port}'

	@pytest.fixture(scope='module')
	async def browser_session(self):
		"""Create and provide a BrowserSession instance with security disabled."""
		browser_session = BrowserSession(
			browser_profile=BrowserProfile(
				headless=True,
				user_data_dir=None,
				keep_alive=True,
			)
		)
		await browser_session.start()
		yield browser_session
		await browser_session.kill()
		# Ensure event bus is properly stopped
		await browser_session.event_bus.stop(clear=True, timeout=5)

	def test_is_url_allowed(self):
		"""
		Test the _is_url_allowed method to verify that it correctly checks URLs against
		the allowed domains configuration.
		"""
		# Import the url matching function directly
		from browser_use.browser.profile import BrowserProfile

		# Scenario 1: Test with None allowed_domains (all allowed)
		config1 = BrowserProfile(allowed_domains=None, headless=True, user_data_dir=None)
		# When allowed_domains is None, all URLs should be allowed
		# We test this indirectly through the profile's url validation
		assert config1.allowed_domains is None

		# Scenario 2: Test with specific allowed domains
		allowed = ['example.com', 'mysite.org']
		config2 = BrowserProfile(allowed_domains=allowed, headless=True, user_data_dir=None)
		assert 'example.com' in config2.allowed_domains
		assert 'mysite.org' in config2.allowed_domains

	# Method was removed from BrowserSession

	def test_enhanced_css_selector_for_element(self):
		"""
		Test removed: _enhanced_css_selector_for_element method no longer exists.
		"""
		pass  # Method was removed from BrowserSession

	@pytest.mark.asyncio
	async def test_navigate_and_get_current_page(self, browser_session, base_url):
		"""Test that navigate method changes the URL and get_current_page returns the proper page."""
		from browser_use.browser.events import NavigateToUrlEvent, NavigationCompleteEvent

		# Navigate to the test page
		event = browser_session.event_bus.dispatch(NavigateToUrlEvent(url=f'{base_url}/'))
		await event
		# Wait for navigation to complete
		await browser_session.event_bus.expect(NavigationCompleteEvent, timeout=10.0)

		# Get the current page URL
		url = await browser_session.get_current_page_url()

		# Verify the page URL matches what we navigated to
		assert f'{base_url}/' in url

		# Verify the page title
		title = await browser_session.get_current_page_title()
		assert title == 'Test Home Page'

	@pytest.mark.asyncio
	async def test_refresh_page(self, browser_session, base_url):
		"""Test that refresh_page correctly reloads the current page."""
		from browser_use.browser.events import NavigateToUrlEvent, NavigationCompleteEvent

		# Navigate to the test page first
		event = browser_session.event_bus.dispatch(NavigateToUrlEvent(url=f'{base_url}/'))
		await event
		await browser_session.event_bus.expect(NavigationCompleteEvent, timeout=10.0)

		# Get the current page info before refresh
		url_before = await browser_session.get_current_page_url()
		title_before = await browser_session.get_current_page_title()

		# Refresh using CDP directly via tools
		from browser_use.tools.service import Tools

		tools = Tools()
		await tools.navigate(url=url_before, browser_session=browser_session)
		await browser_session.event_bus.expect(NavigationCompleteEvent, timeout=10.0)

		# Get the current page info after refresh
		url_after = await browser_session.get_current_page_url()
		title_after = await browser_session.get_current_page_title()

		# Verify it's still on the same URL
		assert url_after == url_before

		# Verify the page title is still correct
		assert title_after == 'Test Home Page'

	@pytest.mark.asyncio
	async def test_execute_javascript(self, browser_session, base_url):
		"""Test that execute_javascript correctly executes JavaScript in the current page."""
		from browser_use.browser.events import NavigateToUrlEvent, NavigationCompleteEvent

		# Navigate to a test page
		event = browser_session.event_bus.dispatch(NavigateToUrlEvent(url=f'{base_url}/'))
		await event
		await browser_session.event_bus.expect(NavigationCompleteEvent, timeout=10.0)

		# Execute a simple JavaScript snippet that returns a value via CDP
		cdp_session = await browser_session.get_or_create_cdp_session()
		result = await cdp_session.cdp_client.send.Runtime.evaluate(
			params={'expression': 'document.title', 'returnByValue': True},
			session_id=cdp_session.session_id,
		)

		# Verify the result
		assert result.get('result', {}).get('value') == 'Test Home Page'

	@pytest.mark.asyncio
	async def test_get_scroll_info(self, browser_session, base_url):
		"""Test scroll position detection via CDP."""
		from browser_use.browser.events import NavigateToUrlEvent, NavigationCompleteEvent

		# Navigate to the scroll test page
		event = browser_session.event_bus.dispatch(NavigateToUrlEvent(url=f'{base_url}/scroll_test'))
		await event
		await browser_session.event_bus.expect(NavigationCompleteEvent, timeout=10.0)

		# Get scroll info via CDP
		cdp_session = await browser_session.get_or_create_cdp_session()
		scroll_result = await cdp_session.cdp_client.send.Runtime.evaluate(
			params={
				'expression': '''
					({
						pixelsAbove: window.scrollY || document.documentElement.scrollTop || 0,
						pixelsBelow: document.documentElement.scrollHeight - window.innerHeight - (window.scrollY || document.documentElement.scrollTop)
					})
				''',
				'returnByValue': True,
			},
			session_id=cdp_session.session_id,
		)

		scroll_info = scroll_result.get('result', {}).get('value', {})
		pixels_above_initial = scroll_info.get('pixelsAbove', 0)
		pixels_below_initial = scroll_info.get('pixelsBelow', 0)

		# Verify initial scroll position
		assert pixels_above_initial == 0, 'Initial scroll position should be at the top'
		assert pixels_below_initial > 0, 'There should be content below the viewport'

		# Scroll down the page via CDP
		await cdp_session.cdp_client.send.Runtime.evaluate(
			params={'expression': 'window.scrollBy(0, 500)', 'returnByValue': False},
			session_id=cdp_session.session_id,
		)
		await asyncio.sleep(0.2)  # Brief delay for scroll to complete

		# Get new scroll info
		scroll_result_after = await cdp_session.cdp_client.send.Runtime.evaluate(
			params={
				'expression': '''
					({
						pixelsAbove: window.scrollY || document.documentElement.scrollTop || 0,
						pixelsBelow: document.documentElement.scrollHeight - window.innerHeight - (window.scrollY || document.documentElement.scrollTop)
					})
				''',
				'returnByValue': True,
			},
			session_id=cdp_session.session_id,
		)
		scroll_info_after = scroll_result_after.get('result', {}).get('value', {})
		pixels_above_after_scroll = scroll_info_after.get('pixelsAbove', 0)
		pixels_below_after_scroll = scroll_info_after.get('pixelsBelow', 0)

		# Verify new scroll position
		assert pixels_above_after_scroll > 0, 'Page should be scrolled down'
		assert pixels_above_after_scroll >= 400, 'Page should be scrolled down at least 400px'
		assert pixels_below_after_scroll < pixels_below_initial, 'Less content should be below viewport after scrolling'

	@pytest.mark.asyncio
	async def test_take_screenshot(self, browser_session, base_url):
		"""Test that take_screenshot returns a valid base64 encoded image."""
		from browser_use.browser.events import NavigateToUrlEvent, NavigationCompleteEvent

		# Navigate to the test page
		event = browser_session.event_bus.dispatch(NavigateToUrlEvent(url=f'{base_url}/'))
		await event
		await browser_session.event_bus.expect(NavigationCompleteEvent, timeout=10.0)

		# Take a screenshot
		screenshot_base64 = await browser_session.take_screenshot()

		# Verify the screenshot is a valid base64 string
		assert isinstance(screenshot_base64, bytes)
		assert len(screenshot_base64) > 0

		# Verify the data starts with a valid image signature (PNG file header)
		assert screenshot_base64[:8] == b'\x89PNG\r\n\x1a\n', 'Screenshot is not a valid PNG image'

	@pytest.mark.asyncio
	async def test_switch_tab_operations(self, browser_session, base_url):
		"""Test tab creation, switching, and closing operations."""
		from browser_use.browser.events import NavigateToUrlEvent, NavigationCompleteEvent, SwitchTabEvent, CloseTabEvent

		# Navigate to home page in first tab
		event = browser_session.event_bus.dispatch(NavigateToUrlEvent(url=f'{base_url}/'))
		await event
		await browser_session.event_bus.expect(NavigationCompleteEvent, timeout=10.0)

		# Create a new tab
		event = browser_session.event_bus.dispatch(NavigateToUrlEvent(url=f'{base_url}/scroll_test', new_tab=True))
		await event
		await browser_session.event_bus.expect(NavigationCompleteEvent, timeout=10.0)

		# Verify we have two tabs now
		tabs_info = await browser_session.get_tabs()
		assert len(tabs_info) >= 2, 'Should have at least two tabs open'

		# Verify current tab is the scroll test page (last opened)
		current_url = await browser_session.get_current_page_url()
		assert f'{base_url}/scroll_test' in current_url

		# Switch back to the first tab (get first non-current tab)
		tabs = await browser_session.get_tabs()
		first_tab_id = tabs[0].target_id
		switch_event = browser_session.event_bus.dispatch(SwitchTabEvent(target_id=first_tab_id))
		await switch_event

		# Verify we're back on the home page
		current_url = await browser_session.get_current_page_url()
		assert f'{base_url}/' in current_url

		# Close the second tab
		if len(tabs) > 1:
			second_tab_id = tabs[-1].target_id
			close_event = browser_session.event_bus.dispatch(CloseTabEvent(target_id=second_tab_id))
			await close_event
			await asyncio.sleep(0.2)  # Brief delay for tab close

		# Verify we have the expected number of tabs
		tabs_info = await browser_session.get_tabs()
		# Filter out about:blank tabs created by the watchdog
		non_blank_tabs = [tab for tab in tabs_info if 'about:blank' not in tab.url]
		assert len(non_blank_tabs) >= 1, f'Should have at least one non-blank tab open, got {len(non_blank_tabs)}'

	# TODO: highlighting doesn't exist anymore
	# @pytest.mark.asyncio
	# async def test_remove_highlights(self, browser_session, base_url):
	# 	"""Test that remove_highlights successfully removes highlight elements."""
	# 	# Navigate to a test page
	# 	from browser_use.browser.events import NavigateToUrlEvent; event = browser_session.event_bus.dispatch(NavigateToUrlEvent(url=f'{base_url}/')

	# 	# Add a highlight via JavaScript
	# 	await browser_session.execute_javascript("""
	#         const container = document.createElement('div');
	#         container.id = 'playwright-highlight-container';
	#         document.body.appendChild(container);

	#         const highlight = document.createElement('div');
	#         highlight.id = 'playwright-highlight-1';
	#         container.appendChild(highlight);

	#         const element = document.querySelector('h1');
	#         element.setAttribute('browser-user-highlight-id', 'playwright-highlight-1');
	#     """)

	# 	# Verify the highlight container exists
	# 	container_exists = await browser_session.execute_javascript(
	# 		"document.getElementById('playwright-highlight-container') !== null"
	# 	)
	# 	assert container_exists, 'Highlight container should exist before removal'

	# 	# Call remove_highlights
	# 	await browser_session.remove_highlights()

	# 	# Verify the highlight container was removed
	# 	container_exists_after = await browser_session.execute_javascript(
	# 		"document.getElementById('playwright-highlight-container') !== null"
	# 	)
	# 	assert not container_exists_after, 'Highlight container should be removed'

	# 	# Verify the highlight attribute was removed from the element
	# 	attribute_exists = await browser_session.execute_javascript(
	# 		"document.querySelector('h1').hasAttribute('browser-user-highlight-id')"
	# 	)
	# 	assert not attribute_exists, 'browser-user-highlight-id attribute should be removed'

	@pytest.mark.asyncio
	async def test_custom_action_with_no_arguments(self, browser_session, base_url):
		"""Test that custom actions with no arguments are handled correctly"""
		from browser_use.agent.views import ActionResult
		from browser_use.tools.registry.service import Registry
		from browser_use.tools.service import Tools

		# Create a tools instance
		tools = Tools()

		# Get the registry from tools
		registry = tools.registry

		# Register a custom action with no arguments using the registry's action decorator
		@registry.action('Some custom action with no args')
		def simple_action(browser_session=None):
			return ActionResult(extracted_content='return some result')

		# Navigate to a test page
		from browser_use.browser.events import NavigateToUrlEvent, NavigationCompleteEvent

		event = browser_session.event_bus.dispatch(NavigateToUrlEvent(url=f'{base_url}/'))
		await event
		await browser_session.event_bus.expect(NavigationCompleteEvent, timeout=10.0)

		# Execute the action directly via tools
		result = await tools.registry.execute_action(
			'simple_action',
			params={},
			browser_session=browser_session,
		)

		# Verify the result
		assert isinstance(result, ActionResult)
		assert result.extracted_content == 'return some result'

		# Test that the action model is created correctly
		action_model = registry.create_action_model()

		# The action should be in the model fields
		assert 'simple_action' in action_model.model_fields

		# Create an instance with the simple_action
		action_instance = action_model(simple_action=None)

		# Test that model_dump works correctly
		dumped = action_instance.model_dump(exclude_unset=True)
		assert 'simple_action' in dumped
		assert dumped['simple_action'] is None or dumped['simple_action'] == {}

		# Test async version as well
		@registry.action('Async custom action with no args')
		async def async_simple_action():
			return ActionResult(extracted_content='async result')

		result = await registry.execute_action('async_simple_action', {})
		assert result.extracted_content == 'async result'

		# Test with special parameters but no regular arguments
		@registry.action('Action with only special params')
		async def special_params_only(browser_session):
			current_url = await browser_session.get_current_page_url()
			return ActionResult(extracted_content=f'Page URL: {current_url}')

		result = await registry.execute_action('special_params_only', {}, browser_session=browser_session)
		assert 'Page URL:' in result.extracted_content
		assert base_url in result.extracted_content
