"""Tests for the active long-term memory save tool."""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from astrbot_plugin_livingmemory.core.base.config_manager import ConfigManager
from astrbot_plugin_livingmemory.core.tools.memory_save_tool import MemorySaveTool


@pytest.fixture
def memory_engine():
    engine = Mock()
    engine.add_memory = AsyncMock(return_value=123)
    return engine


@pytest.fixture
def astr_context():
    return Mock()


def _make_run_context():
    event = Mock()
    event.unified_msg_origin = "test:private:session-1"

    run_context = Mock()
    run_context.context = Mock()
    run_context.context.event = event
    return run_context


@pytest.mark.asyncio
async def test_save_tool_writes_memory_with_default_importance(
    memory_engine, astr_context
):
    tool = MemorySaveTool(
        context=astr_context,
        config_manager=ConfigManager(),
        memory_engine=memory_engine,
    )

    with patch(
        "astrbot_plugin_livingmemory.core.tools.memory_save_tool.get_persona_id",
        new_callable=AsyncMock,
    ) as get_persona:
        get_persona.return_value = "persona_a"
        raw_result = await tool.call(
            _make_run_context(), content="用户喜欢深色模式，并且对花生过敏。"
        )

    result = json.loads(raw_result)
    assert result["saved"] is True
    assert result["id"] == 123
    assert result["importance"] == 0.7
    assert result["session_id"] == "test:private:session-1"
    assert result["persona_id"] == "persona_a"

    memory_engine.add_memory.assert_awaited_once()
    kwargs = memory_engine.add_memory.await_args.kwargs
    assert kwargs["content"] == "用户喜欢深色模式，并且对花生过敏。"
    assert kwargs["session_id"] == "test:private:session-1"
    assert kwargs["persona_id"] == "persona_a"
    assert kwargs["importance"] == 0.7
    metadata = kwargs["metadata"]
    assert metadata["source"] == "llm_tool_save"
    assert metadata["triggered_by"] == "save_long_term_memory"


@pytest.mark.asyncio
async def test_save_tool_clamps_importance_high(memory_engine, astr_context):
    tool = MemorySaveTool(
        context=astr_context,
        config_manager=ConfigManager(),
        memory_engine=memory_engine,
    )

    with patch(
        "astrbot_plugin_livingmemory.core.tools.memory_save_tool.get_persona_id",
        new_callable=AsyncMock,
    ) as get_persona:
        get_persona.return_value = None
        raw_result = await tool.call(
            _make_run_context(), content="重要承诺", importance=5.0
        )

    result = json.loads(raw_result)
    assert result["saved"] is True
    assert result["importance"] == 1.0


@pytest.mark.asyncio
async def test_save_tool_clamps_importance_low(memory_engine, astr_context):
    tool = MemorySaveTool(
        context=astr_context,
        config_manager=ConfigManager(),
        memory_engine=memory_engine,
    )

    with patch(
        "astrbot_plugin_livingmemory.core.tools.memory_save_tool.get_persona_id",
        new_callable=AsyncMock,
    ) as get_persona:
        get_persona.return_value = None
        raw_result = await tool.call(
            _make_run_context(), content="轻量偏好", importance=-1.0
        )

    result = json.loads(raw_result)
    assert result["saved"] is True
    assert result["importance"] == 0.0


@pytest.mark.asyncio
async def test_save_tool_rejects_empty_content(memory_engine, astr_context):
    tool = MemorySaveTool(
        context=astr_context,
        config_manager=ConfigManager(),
        memory_engine=memory_engine,
    )

    raw_result = await tool.call(_make_run_context(), content="   ")
    result = json.loads(raw_result)
    assert result["saved"] is False
    assert result["error"] == "content is empty"
    memory_engine.add_memory.assert_not_awaited()


@pytest.mark.asyncio
async def test_save_tool_falls_back_to_default_for_invalid_importance(
    memory_engine, astr_context
):
    tool = MemorySaveTool(
        context=astr_context,
        config_manager=ConfigManager(),
        memory_engine=memory_engine,
    )

    with patch(
        "astrbot_plugin_livingmemory.core.tools.memory_save_tool.get_persona_id",
        new_callable=AsyncMock,
    ) as get_persona:
        get_persona.return_value = "persona_a"
        raw_result = await tool.call(
            _make_run_context(), content="非法重要度测试", importance="oops"
        )

    result = json.loads(raw_result)
    assert result["saved"] is True
    assert result["importance"] == 0.7


@pytest.mark.asyncio
async def test_save_tool_guards_uninitialized_components():
    tool = MemorySaveTool(
        context=None,
        config_manager=None,
        memory_engine=None,
    )
    raw_result = await tool.call(_make_run_context(), content="hi")
    result = json.loads(raw_result)
    assert result["saved"] is False
    assert result["error"] == "memory save tool is not initialized"


@pytest.mark.asyncio
async def test_save_tool_returns_internal_error_on_engine_exception(
    memory_engine, astr_context
):
    memory_engine.add_memory = AsyncMock(side_effect=RuntimeError("boom"))
    tool = MemorySaveTool(
        context=astr_context,
        config_manager=ConfigManager(),
        memory_engine=memory_engine,
    )

    with patch(
        "astrbot_plugin_livingmemory.core.tools.memory_save_tool.get_persona_id",
        new_callable=AsyncMock,
    ) as get_persona:
        get_persona.return_value = None
        raw_result = await tool.call(_make_run_context(), content="任意")

    result = json.loads(raw_result)
    assert result["saved"] is False
    assert result["error"] == "internal_error"
