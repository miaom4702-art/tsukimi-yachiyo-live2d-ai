import pytest
from unittest.mock import patch, MagicMock
from ..conversation import Conversation


class TestRefresh:
    def test_refresh_system_prompt_updates_messages(self):
        with (
            patch("engine.conversation.LLM"),
            patch("engine.conversation.Personality") as mock_personality_cls,
            patch("engine.conversation.Memory") as mock_memory_cls,
            patch("engine.conversation.load_json", return_value=[]),
            patch("engine.conversation.save_json"),
        ):
            mock_personality = MagicMock()
            mock_personality.get_system_prompt.return_value = "原始人格\n"
            mock_personality_cls.return_value = mock_personality

            mock_memory = MagicMock()
            mock_memory.get_all.return_value = []
            mock_memory_cls.return_value = mock_memory

            ai = Conversation()
            assert "原始人格" in ai.messages[0]["content"]

            mock_memory.get_all.return_value = ["新记忆"]
            ai.refresh_system_prompt()
            assert "新记忆" in ai.messages[0]["content"]
