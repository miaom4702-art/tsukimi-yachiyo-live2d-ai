from pathlib import Path
from .llm import LLM
from .personality import Personality
from .memory import Memory
from .storage import load_json, save_json
from .mood import MoodAnalyzer, MoodResult

HISTORY_PATH = Path("data/history.json")
_DEFAULT_MAX_EXCHANGES = 20


class Conversation:

    def __init__(self, config=None, max_exchanges=_DEFAULT_MAX_EXCHANGES):
        config = config or {}

        self.llm = LLM(
            api_key=config.get("api_key"),
            base_url=config.get("base_url"),
            model=config.get("model", "qwen-plus"),
        )
        self.personality = Personality()
        self.memory = Memory()
        self.max_exchanges = max_exchanges
        self.mood_analyzer = MoodAnalyzer()
        self.last_mood: MoodResult = MoodResult()

        history = load_json(str(HISTORY_PATH), [])
        self.messages = [self._build_system_message()]
        self.messages.extend(history)

    def _build_system_message(self):

        return {
            "role": "system",
            "content": self.build_system_prompt()
        }

    def _save_history(self):

        history = [m for m in self.messages if m["role"] != "system"]
        save_json(str(HISTORY_PATH), history)

    def _trim_history(self):

        non_system = [m for m in self.messages if m["role"] != "system"]
        if len(non_system) > self.max_exchanges * 2:
            remove_count = len(non_system) - self.max_exchanges * 2
            removed = set(id(m) for m in non_system[:remove_count])
            self.messages = [
                m for m in self.messages if id(m) not in removed
            ]

    def build_memory_prompt(self):

        memories = self.memory.get_all()

        if not memories:
            return ""

        memory_text = "\n".join(memories)

        return f"""

用户长期记忆：

{memory_text}

以上内容是真实记录的长期信息。

如果用户询问相关内容，请优先参考这些记忆。
"""

    def build_system_prompt(self):

        parts = [self.personality.get_system_prompt()]
        mem = self.build_memory_prompt()
        if mem:
            parts.append(mem)
        return "\n".join(parts)

    def refresh_system_prompt(self):

        self.messages[0]["content"] = (
            self.build_system_prompt()
        )

    def try_remember(self, text):

        keywords = [
            "我叫", "我是",
            "我喜欢", "我讨厌",
            "我住在", "我来自", "我在",
            "我的专业", "我的工作", "我的学校",
            "我最喜欢", "我最讨厌",
            "我想学", "我正在学",
            "我今年", "我出生",
        ]

        for keyword in keywords:

            if keyword in text:

                memory_text = "用户：" + text

                if not self.memory.exists(memory_text):

                    self.memory.add(memory_text)

                    self.refresh_system_prompt()

                    print(
                        f"[自动记忆] {memory_text}"
                    )

                break

    def chat(self, text):

        self.try_remember(text)

        # ===== 查看记忆 =====

        if text == "/memory":

            memories = self.memory.get_all()

            if not memories:
                return "暂无记忆"

            return "\n".join(memories)

        # ===== 添加记忆 =====

        if text.startswith("/remember "):

            memory_text = text[10:].strip()

            if not memory_text:
                return "记忆内容不能为空"

            self.memory.add(memory_text)

            self.refresh_system_prompt()

            return f"已记录：{memory_text}"

        # ===== 删除记忆 =====

        if text.startswith("/forget "):

            keyword = text[8:].strip()

            if not keyword:
                return "请提供要删除的记忆关键词"

            removed = self.memory.remove(keyword)
            if removed == 0:
                return f"未找到包含「{keyword}」的记忆"
            self.refresh_system_prompt()

            return f"已删除 {removed} 条包含「{keyword}」的记忆"

        # ===== 清除全部历史 =====

        if text == "/clear":

            self.messages = [self._build_system_message()]
            save_json(str(HISTORY_PATH), [])
            return "对话历史已清除"

        # ===== 普通聊天 =====

        self.messages.append(
            {
                "role": "user",
                "content": text
            }
        )

        reply = self.llm.chat(
            self.messages
        )

        self.last_mood = self.mood_analyzer.analyze(reply)

        self.messages.append(
            {
                "role": "assistant",
                "content": reply
            }
        )

        self._trim_history()
        self._save_history()

        return reply