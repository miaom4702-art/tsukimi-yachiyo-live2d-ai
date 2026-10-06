import json
import pytest
from ..memory import Memory


@pytest.fixture
def memory_file(tmp_path):
    return str(tmp_path / "memory.json")


class TestMemory:
    def test_add_and_get_all(self, memory_file):
        m = Memory()
        m.path = memory_file
        m.memories = []
        m.add("用户喜欢火锅")
        assert m.get_all() == ["用户喜欢火锅"]

    def test_add_duplicate(self, memory_file):
        m = Memory()
        m.path = memory_file
        m.memories = []
        m.add("用户喜欢火锅")
        m.add("用户喜欢火锅")
        assert m.get_all() == ["用户喜欢火锅"]

    def test_exists(self, memory_file):
        m = Memory()
        m.path = memory_file
        m.memories = []
        m.add("用户喜欢火锅")
        assert m.exists("用户喜欢火锅") is True
        assert m.exists("用户喜欢烤肉") is False

    def test_get_all_empty(self, memory_file):
        m = Memory()
        m.path = memory_file
        m.memories = []
        assert m.get_all() == []

    def test_persistence(self, memory_file):
        m1 = Memory()
        m1.path = memory_file
        m1.memories = []
        m1.add("记住这个")
        m2 = Memory()
        m2.path = memory_file
        m2.memories = json.loads(open(memory_file, encoding="utf-8").read())
        assert m2.get_all() == ["记住这个"]
