import pytest
from unittest.mock import patch, MagicMock
from ..llm import LLM


class TestLLM:
    def test_chat_returns_reply(self):
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "你好！"

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        llm = LLM(api_key="sk-test")
        llm.client = mock_client

        reply = llm.chat([{"role": "user", "content": "hello"}])
        assert reply == "你好！"

    def test_chat_passes_messages(self):
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "ok"

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        llm = LLM(api_key="sk-test")
        llm.client = mock_client

        messages = [{"role": "user", "content": "test"}]
        llm.chat(messages)

        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["messages"] == messages
        assert call_kwargs["model"] == "qwen-plus"
