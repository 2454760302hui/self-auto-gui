"""Contract tests for media API endpoints."""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import AutoGLM_GUI.api.media as media_api
import AutoGLM_GUI.device_manager as device_manager_module
from AutoGLM_GUI.exceptions import DeviceNotAvailableError

pytestmark = [pytest.mark.contract, pytest.mark.release_gate]


@dataclass
class FakeScreenshot:
    base64_data: str
    width: int
    height: int
    is_sensitive: bool


class FakeDevice:
    """Fake DeviceProtocol for local devices."""

    def __init__(self, screenshot: FakeScreenshot) -> None:
        self._screenshot = screenshot

    def get_screenshot(self, timeout: int = 10) -> FakeScreenshot:
        return self._screenshot


class FakeRemoteDevice:
    """Fake DeviceProtocol for remote devices."""

    def __init__(self, screenshot: FakeScreenshot) -> None:
        self._screenshot = screenshot

    def get_screenshot(self, timeout: int = 10) -> FakeScreenshot:
        return self._screenshot


class FakeDeviceManager:
    def __init__(self) -> None:
        self._local_screenshot = FakeScreenshot(
            base64_data="LOCAL_IMG",
            width=1080,
            height=1920,
            is_sensitive=False,
        )
        self._remote_screenshot = FakeScreenshot(
            base64_data="REMOTE_IMG",
            width=800,
            height=1600,
            is_sensitive=True,
        )
        self._remote_instance = FakeRemoteDevice(self._remote_screenshot)

    def get_device_protocol(self, device_id: str) -> FakeDevice | FakeRemoteDevice:
        if device_id == "local-device":
            return FakeDevice(self._local_screenshot)
        if device_id == "remote-device":
            return self._remote_instance
        raise ValueError(f"Device {device_id} not found in DeviceManager")

    def get_remote_device_instance(self) -> None:
        pass


@pytest.fixture
def media_env(monkeypatch: pytest.MonkeyPatch) -> dict:
    fake_manager = FakeDeviceManager()
    reset_calls: list[str | None] = []

    class FakeDeviceManagerClass:
        @staticmethod
        def get_instance() -> FakeDeviceManager:
            return fake_manager

    def fake_stop_streamers(device_id: str | None = None) -> None:
        reset_calls.append(device_id)

    monkeypatch.setattr(device_manager_module, "DeviceManager", FakeDeviceManagerClass)
    monkeypatch.setattr(media_api, "stop_streamers", fake_stop_streamers)

    app = FastAPI()
    app.include_router(media_api.router)

    return {
        "client": TestClient(app),
        "manager": fake_manager,
        "reset_calls": reset_calls,
    }


def test_reset_video_stream_all(media_env: dict) -> None:
    response = media_env["client"].post("/api/video/reset")

    assert response.status_code == 200
    assert response.json() == {"success": True, "message": "All video streams reset"}
    assert media_env["reset_calls"] == [None]


def test_reset_video_stream_single_device(media_env: dict) -> None:
    response = media_env["client"].post("/api/video/reset", params={"device_id": "d1"})

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "message": "Video stream reset for device d1",
    }
    assert media_env["reset_calls"] == ["d1"]


def test_screenshot_requires_device_id(media_env: dict) -> None:
    response = media_env["client"].post("/api/screenshot", json={})

    assert response.status_code == 200
    assert response.json() == {
        "success": False,
        "image": "",
        "width": 0,
        "height": 0,
        "is_sensitive": False,
        "error": "device_id is required",
    }


def test_screenshot_device_not_found(media_env: dict) -> None:
    response = media_env["client"].post(
        "/api/screenshot",
        json={"device_id": "unknown-device"},
    )

    assert response.status_code == 200
    assert response.json()["success"] is False
    assert "not found" in response.json()["error"].lower()


def test_screenshot_local_device_success(media_env: dict) -> None:
    response = media_env["client"].post(
        "/api/screenshot",
        json={"device_id": "local-device"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "image": "LOCAL_IMG",
        "width": 1080,
        "height": 1920,
        "is_sensitive": False,
        "error": None,
    }


def test_screenshot_remote_device_success(media_env: dict) -> None:
    response = media_env["client"].post(
        "/api/screenshot",
        json={"device_id": "remote-device"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "image": "REMOTE_IMG",
        "width": 800,
        "height": 1600,
        "is_sensitive": True,
        "error": None,
    }


def test_screenshot_remote_device_missing_instance(media_env: dict) -> None:
    """Screenshot with a device that raises ValueError from get_device_protocol."""
    original = media_env["manager"].get_device_protocol

    def raising_protocol(device_id: str) -> None:
        raise ValueError(f"Remote device {device_id} not found")

    media_env["manager"].get_device_protocol = raising_protocol

    response = media_env["client"].post(
        "/api/screenshot",
        json={"device_id": "remote-device"},
    )

    assert response.status_code == 200
    assert response.json()["success"] is False
    assert "not found" in response.json()["error"].lower()

    media_env["manager"].get_device_protocol = original


def test_screenshot_handles_device_not_available_error(
    media_env: dict,
) -> None:
    """Screenshot propagates DeviceNotAvailableError from device protocol."""
    original = media_env["manager"].get_device_protocol

    class FailingDevice:
        def get_screenshot(self, timeout: int = 10) -> None:
            raise DeviceNotAvailableError("device temporarily offline")

    def failing_protocol(device_id: str) -> FailingDevice:
        return FailingDevice()

    media_env["manager"].get_device_protocol = failing_protocol

    response = media_env["client"].post(
        "/api/screenshot",
        json={"device_id": "local-device"},
    )

    assert response.status_code == 200
    assert response.json()["success"] is False
    assert response.json()["error"] == "device temporarily offline"

    media_env["manager"].get_device_protocol = original
