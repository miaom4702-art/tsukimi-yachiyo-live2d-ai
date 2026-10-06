import pytest
from unittest.mock import patch, MagicMock
from ..conversation import Conversation


@pytest.fixture
def mock_components():
    with (
        patch("engine.conversation.LLM") as mock_llm_cls,
        patch("engine.conversation.Personality") as mock_personality_cls,
        patch("engine.conversation.Memory") as mock_memory_cls,
        patch("engine.conversation.load_json") as mock_load_json,
        patch("engine.conversation.save_json") as mock_save_json,
    ):
        mock_llm = MagicMock()
        mock_llm.chat.return_value = "这是一个测试回复"
        mock_llm_cls.return_value = mock_llm

        mock_personality = MagicMock()
        mock_personality.get_system_prompt.return_value = "你是测试AI。\n\n背景：\n测试背景\n\n性格：\n友善\n\n请始终保持该人格与用户交流。\n"
        mock_personality_cls.return_value = mock_personality

        mock_memory = MagicMock()
        mock_memory.get_all.return_value = []
        mock_memory.exists.return_value = False
        mock_memory.remove.return_value = 0
        mock_memory.path = "data/memory.json"
        mock_memory_cls.return_value = mock_memory

        mock_load_json.return_value = []

        yield mock_llm, mock_personality, mock_memory


class TestConversation:
    def test_chat_normal(self, mock_components):
        mock_llm, _, _ = mock_components
        ai = Conversation()
        reply = ai.chat("你好")
        assert reply == "这是一个测试回复"
        mock_llm.chat.assert_called_once()

    def test_chat_saves_history(self, mock_components):
        mock_llm, _, _ = mock_components
        ai = Conversation()
        ai.chat("你好")
        assert len(ai.messages) == 3  # system + user + assistant

    def test_chat_multiple_turns(self, mock_components):
        mock_llm, _, _ = mock_components
        ai = Conversation()
        ai.chat("第一轮")
        ai.chat("第二轮")
        assert len(ai.messages) == 5  # system + 2 user + 2 assistant

    def test_memory_command(self, mock_components):
        _, _, mock_memory = mock_components
        mock_memory.get_all.return_value = ["记忆1", "记忆2"]
        ai = Conversation()
        reply = ai.chat("/memory")
        assert "记忆1" in reply
        assert "记忆2" in reply

    def test_memory_command_empty(self, mock_components):
        _, _, mock_memory = mock_components
        mock_memory.get_all.return_value = []
        ai = Conversation()
        reply = ai.chat("/memory")
        assert reply == "暂无记忆"

    def test_remember_command(self, mock_components):
        _, _, mock_memory = mock_components
        ai = Conversation()
        reply = ai.chat("/remember 用户喜欢编程")
        assert "已记录" in reply
        mock_memory.add.assert_called_once_with("用户喜欢编程")

    def test_remember_command_empty(self, mock_components):
        _, _, mock_memory = mock_components
        ai = Conversation()
        reply = ai.chat("/remember   ")
        assert "不能为空" in reply

    def test_try_remember_keyword(self, mock_components):
        _, _, mock_memory = mock_components
        mock_memory.exists.return_value = False
        ai = Conversation()
        ai.try_remember("我叫小明")
        mock_memory.add.assert_called_once()

    def test_try_remember_no_keyword(self, mock_components):
        _, _, mock_memory = mock_components
        ai = Conversation()
        ai.try_remember("今天天气真好")
        mock_memory.add.assert_not_called()

    def test_try_remember_duplicate(self, mock_components):
        _, _, mock_memory = mock_components
        mock_memory.exists.return_value = True
        ai = Conversation()
        ai.try_remember("我叫小明")
        mock_memory.add.assert_not_called()

    # ===== /forget =====

    def test_forget_command(self, mock_components):
        _, _, mock_memory = mock_components
        mock_memory.get_all.return_value = ["用户：我喜欢火锅", "用户：我喜欢编程"]
        mock_memory.remove.return_value = 1
        ai = Conversation()
        reply = ai.chat("/forget 火锅")
        assert "已删除" in reply
        assert "火锅" in reply

    def test_forget_not_found(self, mock_components):
        _, _, mock_memory = mock_components
        mock_memory.get_all.return_value = ["用户：我喜欢火锅"]
        ai = Conversation()
        reply = ai.chat("/forget 不存在的内容")
        assert "未找到" in reply

    def test_forget_empty_keyword(self, mock_components):
        _, _, mock_memory = mock_components
        ai = Conversation()
        reply = ai.chat("/forget   ")
        assert "关键词" in reply

    # ===== /clear =====

    def test_clear_history(self, mock_components):
        ai = Conversation()
        reply = ai.chat("/clear")
        assert "已清除" in reply

    def test_history_trim(self, mock_components):
        mock_llm, _, _ = mock_components
        ai = Conversation()
        # mock MAX_EXCHANGES to a small number for testing
        ai.max_exchanges = 1
        ai.chat("第一轮")
        ai.chat("第二轮")
        ai.chat("第三轮")
        # system + MAX_EXCHANGES exchanges should remain
        non_system = [m for m in ai.messages if m["role"] != "system"]
        assert len(non_system) <= 4  # 2 messages per exchange * 1 exchange + 2 extras
