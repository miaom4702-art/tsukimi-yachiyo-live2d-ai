import json
import pytest
from ..storage import load_json, save_json


class TestLoadJson:
    def test_load_existing_file(self, tmp_path):
        data = {"key": "value"}
        f = tmp_path / "test.json"
        f.write_text(json.dumps(data), encoding="utf-8")
        assert load_json(str(f)) == data

    def test_load_nonexistent_file(self, tmp_path):
        f = tmp_path / "nonexistent.json"
        assert load_json(str(f), default=None) is None

    def test_load_nonexistent_file_custom_default(self, tmp_path):
        f = tmp_path / "nonexistent.json"
        assert load_json(str(f), default=[]) == []


class TestSaveJson:
    def test_save_and_reload(self, tmp_path):
        data = {"name": "四百冬", "age": 18}
        f = tmp_path / "output.json"
        save_json(str(f), data)
        assert json.loads(f.read_text(encoding="utf-8")) == data

    def test_save_list(self, tmp_path):
        data = ["a", "b", "c"]
        f = tmp_path / "list.json"
        save_json(str(f), data)
        assert json.loads(f.read_text(encoding="utf-8")) == data

    def test_save_ensure_unicode(self, tmp_path):
        data = {"msg": "你好"}
        f = tmp_path / "unicode.json"
        save_json(str(f), data)
        content = f.read_text(encoding="utf-8")
        assert "你好" in content
