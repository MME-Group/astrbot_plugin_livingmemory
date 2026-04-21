"""Tests for plugin LLM tool registration."""

from unittest.mock import Mock

from astrbot_plugin_livingmemory.core.base.config_manager import ConfigManager
from astrbot_plugin_livingmemory.core.tools import MemorySaveTool, MemorySearchTool
from astrbot_plugin_livingmemory.main import LivingMemoryPlugin


def test_register_llm_tools_is_idempotent():
    plugin = LivingMemoryPlugin.__new__(LivingMemoryPlugin)
    plugin.context = Mock()
    plugin.config_manager = ConfigManager()
    plugin.initializer = Mock()
    plugin.initializer.memory_engine = Mock()
    plugin._llm_tools_registered = False

    plugin._register_llm_tools_if_needed()
    plugin._register_llm_tools_if_needed()

    plugin.context.add_llm_tools.assert_called_once()
    tool = plugin.context.add_llm_tools.call_args.args[0]
    assert isinstance(tool, MemorySearchTool)
    assert tool.name == "recall_long_term_memory"
    assert plugin._llm_tools_registered is True


def test_register_llm_tools_no_memory_engine():
    plugin = LivingMemoryPlugin.__new__(LivingMemoryPlugin)
    plugin.context = Mock()
    plugin.config_manager = ConfigManager()
    plugin.initializer = Mock()
    plugin.initializer.memory_engine = None
    plugin._llm_tools_registered = False

    plugin._register_llm_tools_if_needed()

    plugin.context.add_llm_tools.assert_not_called()
    assert plugin._llm_tools_registered is False


def test_register_llm_tools_save_tool_enabled():
    plugin = LivingMemoryPlugin.__new__(LivingMemoryPlugin)
    plugin.context = Mock()
    plugin.config_manager = ConfigManager(
        {"active_memory_tools": {"enable_save_tool": True}}
    )
    plugin.initializer = Mock()
    plugin.initializer.memory_engine = Mock()
    plugin._llm_tools_registered = False

    plugin._register_llm_tools_if_needed()

    plugin.context.add_llm_tools.assert_called_once()
    tools = plugin.context.add_llm_tools.call_args.args
    assert len(tools) == 2

    tool_by_name = {tool.name: tool for tool in tools}
    assert "recall_long_term_memory" in tool_by_name
    assert "save_long_term_memory" in tool_by_name
    assert isinstance(tool_by_name["recall_long_term_memory"], MemorySearchTool)
    assert isinstance(tool_by_name["save_long_term_memory"], MemorySaveTool)
    assert plugin._llm_tools_registered is True
