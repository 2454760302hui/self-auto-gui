"""Accessibility module for UI hierarchy extraction."""

from .ui_dump import (
    build_screen_description,
    dump_ui_hierarchy,
    find_clickable_elements,
    find_element_by_text,
)

__all__ = [
    "build_screen_description",
    "dump_ui_hierarchy",
    "find_element_by_text",
    "find_clickable_elements",
]
