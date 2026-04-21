"""供 Agent 主动保存长期记忆的工具。"""

import asyncio
from dataclasses import field
import json
from typing import Any

from pydantic.dataclasses import dataclass

from astrbot.api import logger
from astrbot.core.agent.run_context import ContextWrapper
from astrbot.core.agent.tool import FunctionTool, ToolExecResult
from astrbot.core.astr_agent_context import AstrAgentContext

from ..base.config_manager import ConfigManager
from ..utils import get_persona_id


def _json_result(data: dict[str, Any]) -> str:
    """将工具结果稳定序列化为 JSON 文本。"""
    return json.dumps(data, ensure_ascii=False, default=str)


@dataclass
class MemorySaveTool(FunctionTool[AstrAgentContext]):
    """主动保存一条重要记忆"""

    __pydantic_config__ = {"arbitrary_types_allowed": True}

    context: Any = None
    config_manager: ConfigManager | None = None
    memory_engine: Any = None

    name: str = "save_long_term_memory"
    description: str = (
        "Save a single concise long-term memory when the conversation reveals "
        "information worth remembering long-term, such as the user's stable "
        "preferences, important events, commitments, key decisions, or durable "
        "facts about the user. Content must be a short, self-contained summary "
        "written in the third person (about the user), NOT a transcript of the "
        "conversation. Do NOT call this for transient chit-chat, jokes, or "
        "details the user explicitly asks you to forget. Prefer calling this at "
        "most once per turn; if multiple facts need saving, combine them into "
        "one concise summary."
    )
    parameters: dict[str, Any] = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": (
                        "The concise, self-contained summary to remember. "
                        "Example: 'The user prefers dark mode and is allergic "
                        "to peanuts.' Keep it short (ideally under 200 chars) "
                        "and avoid copying full user messages verbatim."
                    ),
                },
                "importance": {
                    "type": "number",
                    "description": (
                        "Importance score in [0.0, 1.0]. Use ~0.3 for minor "
                        "preferences, ~0.7 for general important facts "
                        "(default), and >=0.9 only for critical commitments "
                        "or identity-level facts."
                    ),
                    "default": 0.7,
                    "minimum": 0.0,
                    "maximum": 1.0,
                },
            },
            "required": ["content"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        content: str,
        importance: float = 0.7,
    ) -> ToolExecResult:
        """执行主动记忆保存。"""
        cleaned_content = (content or "").strip()
        if not cleaned_content:
            return _json_result(
                {
                    "saved": False,
                    "error": "content is empty",
                }
            )

        if (
            self.config_manager is None
            or self.memory_engine is None
            or self.context is None
        ):
            return _json_result(
                {
                    "saved": False,
                    "error": "memory save tool is not initialized",
                }
            )

        try:
            importance_value = float(importance)
        except (TypeError, ValueError):
            importance_value = 0.7
        if importance_value != importance_value:
            importance_value = 0.7
        importance_value = max(0.0, min(1.0, importance_value))

        try:
            event = context.context.event
            session_id = event.unified_msg_origin
            persona_id = await get_persona_id(self.context, event)

            metadata: dict[str, Any] = {
                "source": "llm_tool_save",
                "triggered_by": "save_long_term_memory",
            }

            doc_id = await self.memory_engine.add_memory(
                content=cleaned_content,
                session_id=session_id,
                persona_id=persona_id,
                importance=importance_value,
                metadata=metadata,
            )

            return _json_result(
                {
                    "saved": True,
                    "id": doc_id,
                    "importance": importance_value,
                    "session_id": session_id,
                    "persona_id": persona_id,
                }
            )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"主动记忆保存失败: {e}", exc_info=True)
            return _json_result(
                {
                    "saved": False,
                    "error": "internal_error",
                }
            )
