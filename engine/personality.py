from .storage import load_json


class Personality:

    def __init__(self):
        self.data = load_json("data/personality.json", {})

    @property
    def name(self):
        return self.data.get("name", "AI")

    @property
    def short_name(self):
        return self.data.get("short_name", self.name)

    def get_system_prompt(self):
        name = self.name
        short = self.short_name
        title = self.data.get("title", "")
        background = self.data.get("background", "")
        personality = self.data.get("personality", "")
        style = self.data.get("speaking_style", "")
        values = self.data.get("core_values", [])
        taboos = self.data.get("taboos", [])

        lines = [f"你是{name}。"]
        if title:
            lines.append(f"\n身份：{title}")
        if background:
            lines.append(f"\n【背景】\n{background}")
        if personality:
            lines.append(f"\n【性格核心】\n{personality}")
        if style:
            lines.append(f"\n【说话方式】\n{style}")
        if values:
            lines.append(f"\n【核心信念】\n" + "\n".join(f"- {v}" for v in values))
        if taboos:
            lines.append(f"\n【行为准则】\n" + "\n".join(f"- 禁止：{t}" for t in taboos))

        lines.append(f"\n请始终保持「{short}」的人格与用户交流。用第一人称「我」来回应。")

        return "\n".join(lines)
