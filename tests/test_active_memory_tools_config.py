"""Smoke tests for active_memory_tools config section."""

from astrbot_plugin_livingmemory.core.base.config_manager import ConfigManager
from astrbot_plugin_livingmemory.core.base.config_validator import (
    ActiveMemoryToolsConfig,
    LivingMemoryConfig,
)


def test_default_disables_save_tool():
    cm = ConfigManager()
    assert cm.active_memory_tools.get("enable_save_tool") is False
    assert cm.get("active_memory_tools.enable_save_tool") is False


def test_user_can_enable_save_tool():
    cm = ConfigManager({"active_memory_tools": {"enable_save_tool": True}})
    assert cm.active_memory_tools.get("enable_save_tool") is True


def test_model_default_matches_schema_default():
    assert ActiveMemoryToolsConfig().enable_save_tool is False
    assert LivingMemoryConfig().active_memory_tools.enable_save_tool is False


def test_unknown_field_rejected():
    cfg = LivingMemoryConfig(
        active_memory_tools={"enable_save_tool": True, "extra": "ignored"}
    )
    assert cfg.active_memory_tools.enable_save_tool is True
