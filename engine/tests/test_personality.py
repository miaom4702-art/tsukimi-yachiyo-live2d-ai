import json
import pytest
from unittest.mock import patch
from ..personality import Personality


@pytest.fixture
def personality_data():
    return {
        "name": "测试AI",
        "personality": "友善",
        "background": "测试助手"
    }


class TestPersonality:
    def test_name_default(self):
        with patch("engine.personality.load_json", return_value={}):
            p = Personality()
            assert p.name == "AI"

    def test_name_custom(self, personality_data):
        with patch("engine.personality.load_json", return_value=personality_data):
            p = Personality()
            assert p.name == "测试AI"

    def test_system_prompt_contains_name(self, personality_data):
        with patch("engine.personality.load_json", return_value=personality_data):
            p = Personality()
            prompt = p.get_system_prompt()
            assert "测试AI" in prompt

    def test_system_prompt_contains_background(self, personality_data):
        with patch("engine.personality.load_json", return_value=personality_data):
            p = Personality()
            prompt = p.get_system_prompt()
            assert "测试助手" in prompt

    def test_system_prompt_contains_personality(self, personality_data):
        with patch("engine.personality.load_json", return_value=personality_data):
            p = Personality()
            prompt = p.get_system_prompt()
            assert "友善" in prompt
