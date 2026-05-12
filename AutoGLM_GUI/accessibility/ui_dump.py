"""UI Automator dump for extracting screen element hierarchy.

Provides a text-based representation of the screen that can be used
by non-vision models to understand and interact with the device.
"""

import re
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from AutoGLM_GUI.logger import logger
from AutoGLM_GUI.platform_utils import build_adb_command


@dataclass
class UIElement:
    """A UI element extracted from accessibility dump."""

    text: str
    content_desc: str
    resource_id: str
    class_name: str
    clickable: bool
    bounds: tuple[int, int, int, int]  # left, top, right, bottom
    package: str

    @property
    def center(self) -> tuple[int, int]:
        return (
            (self.bounds[0] + self.bounds[2]) // 2,
            (self.bounds[1] + self.bounds[3]) // 2,
        )

    def to_description(self, screen_width: int, screen_height: int) -> str:
        """Human-readable description with relative coordinates (0-1000 scale)."""
        cx, cy = self.center
        rx = int(cx / screen_width * 1000) if screen_width else 0
        ry = int(cy / screen_height * 1000) if screen_height else 0

        parts = []
        if self.text:
            parts.append(f'text="{self.text}"')
        if self.content_desc:
            parts.append(f'desc="{self.content_desc}"')
        if self.resource_id:
            # Shorten resource-id: keep only the id part
            short_id = self.resource_id.split("/")[-1] if "/" in self.resource_id else self.resource_id
            parts.append(f'id="{short_id}"')
        parts.append(f'pos=[{rx},{ry}]')
        if self.clickable:
            parts.append("clickable")

        return f"  <element {' '.join(parts)} />"


def dump_ui_hierarchy(device_id: str | None = None) -> list[UIElement]:
    """Dump the current UI hierarchy via uiautomator.

    Returns a flat list of UIElement with useful attributes.
    """
    adb_prefix = build_adb_command(device_id)
    try:
        subprocess.run(
            adb_prefix + ["shell", "uiautomator", "dump", "/sdcard/ui_dump.xml"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        result = subprocess.run(
            adb_prefix + ["shell", "cat", "/sdcard/ui_dump.xml"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except subprocess.TimeoutExpired:
        logger.warning("UI dump timed out")
        return []
    except Exception as e:
        logger.warning(f"UI dump failed: {e}")
        return []

    if result.returncode != 0 or not result.stdout:
        logger.warning(f"UI dump returned no data: {result.stderr}")
        return []

    return _parse_ui_xml(result.stdout)


def _parse_ui_xml(xml_content: str) -> list[UIElement]:
    """Parse UI hierarchy XML into a list of UIElement."""
    elements: list[UIElement] = []
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        logger.warning(f"Failed to parse UI XML: {e}")
        return []

    for node in root.iter("node"):
        text = node.attrib.get("text", "")
        content_desc = node.attrib.get("content-desc", "")
        resource_id = node.attrib.get("resource-id", "")
        class_name = node.attrib.get("class", "")
        clickable = node.attrib.get("clickable", "false") == "true"
        package = node.attrib.get("package", "")
        bounds_str = node.attrib.get("bounds", "")

        bounds = _parse_bounds(bounds_str)

        # Only include elements with useful info (text, content-desc, or clickable)
        if text or content_desc or (clickable and resource_id):
            elements.append(UIElement(
                text=text,
                content_desc=content_desc,
                resource_id=resource_id,
                class_name=class_name,
                clickable=clickable,
                bounds=bounds,
                package=package,
            ))

    return elements


def _parse_bounds(bounds_str: str) -> tuple[int, int, int, int]:
    """Parse bounds string like '[0,100][200,300]' into tuple."""
    match = re.findall(r"\d+", bounds_str)
    if len(match) == 4:
        return int(match[0]), int(match[1]), int(match[2]), int(match[3])
    return 0, 0, 0, 0


def find_element_by_text(
    elements: list[UIElement], search_text: str
) -> UIElement | None:
    """Find the best matching element by text or content-desc."""
    search_lower = search_text.lower()
    # Exact match first
    for el in elements:
        if el.text.lower() == search_lower or el.content_desc.lower() == search_lower:
            return el
    # Partial match
    for el in elements:
        if search_lower in el.text.lower() or search_lower in el.content_desc.lower():
            return el
    return None


def find_clickable_elements(elements: list[UIElement]) -> list[UIElement]:
    """Return only clickable elements."""
    return [el for el in elements if el.clickable]


def build_screen_description(
    elements: list[UIElement],
    screen_width: int,
    screen_height: int,
    current_app: str = "",
) -> str:
    """Build a text description of the screen for non-vision models."""
    lines = ["<screen_elements>"]
    if current_app:
        lines.append(f'  <current_app name="{current_app}" />')
    for el in elements:
        lines.append(el.to_description(screen_width, screen_height))
    lines.append("</screen_elements>")
    return "\n".join(lines)
