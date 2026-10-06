from enum import Enum
from dataclasses import dataclass, field
from typing import Optional


class Mood(Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    TOUCHED = "touched"
    PLAYFUL = "playful"
    ANGRY = "angry"
    SURPRISED = "surprised"
    LOVING = "loving"


@dataclass
class MoodResult:
    mood: Mood = Mood.NEUTRAL
    intensity: float = 0.5
    expression_file: Optional[str] = None
    params: dict = field(default_factory=dict)


MOOD_KEYWORDS = [
    (Mood.HAPPY, [
        "开心", "高兴", "快乐", "哈哈", "嘻嘻", "太好", "真棒", "不错",
        "喜欢", "美好", "幸福", "耶", "好呀", "太好啦", "真可爱",
        "微笑", "笑容", "有趣", "有意思", "棒极了",
    ]),
    (Mood.SAD, [
        "难过", "伤心", "悲伤", "哭", "呜呜", "好难过", "不开心",
        "遗憾", "可惜", "失望", "心痛", "伤感", "悲哀", "悲伤",
        "泪", "哭哭", "唉", "叹气",
    ]),
    (Mood.TOUCHED, [
        "感动", "感谢", "谢谢", "感恩", "温馨", "温暖", "真好",
        "善良", "温柔", "好温柔", "泪目", "暖心",
    ]),
    (Mood.PLAYFUL, [
        "调皮", "捣蛋", "捉弄", "开玩笑", "逗你", "猜猜",
        "秘密", "告诉你", "其实", "偷偷", "嘻嘻",
    ]),
    (Mood.ANGRY, [
        "生气", "愤怒", "讨厌", "可恶", "气死", "烦人", "受不了",
        "不满", "怒", "烦", "恼火", "火大",
    ]),
    (Mood.SURPRISED, [
        "哇", "真的吗", "天哪", "不会吧", "震惊", "惊讶", "居然",
        "竟然", "没想到", "出乎意料", "太厉害了", "不敢相信",
    ]),
    (Mood.LOVING, [
        "爱你", "喜欢你", "好喜欢你", "最喜欢", "亲爱的", "宝贝",
        "想你了", "想你", "抱抱", "亲亲", "可爱",
    ]),
]


POSITIVE_WORDS = {
    "开心", "高兴", "快乐", "喜欢", "美好", "幸福", "好", "棒",
    "棒极了", "优秀", "赞", "厉害", "不错", "爱", "温柔", "温暖",
    "感动", "感谢", "谢谢", "可爱", "善良", "漂亮", "好看",
}

NEGATIVE_WORDS = {
    "难过", "伤心", "悲伤", "讨厌", "可恶", "生气", "愤怒", "烦",
    "无聊", "糟糕", "差", "烂", "坏", "恨", "痛苦", "难受",
    "失望", "悲哀", "遗憾", "可惜",
}


class MoodAnalyzer:

    def analyze(self, text: str) -> MoodResult:
        if not text:
            return MoodResult()

        text_lower = text.lower()
        matched_moods = {}

        for mood, keywords in MOOD_KEYWORDS:
            score = 0
            for kw in keywords:
                if kw in text_lower:
                    score += 1
            if score > 0:
                matched_moods[mood] = score

        if not matched_moods:
            return MoodResult(mood=Mood.NEUTRAL, intensity=0.3)

        best_mood = max(matched_moods, key=matched_moods.get)
        max_score = matched_moods[best_mood]

        total_score = sum(matched_moods.values())
        intensity = min(max_score / (total_score or 1), 1.0)

        result = MoodResult(mood=best_mood, intensity=intensity)
        self._apply_expression(result)
        return result

    def analyze_sentiment_score(self, text: str) -> float:
        pos = sum(1 for w in POSITIVE_WORDS if w in text)
        neg = sum(1 for w in NEGATIVE_WORDS if w in text)
        total = pos + neg
        if total == 0:
            return 0.0
        return (pos - neg) / total

    def _apply_expression(self, result: MoodResult):
        mapping = {
            Mood.HAPPY: ("笑咪咪.exp3.json", {
                "ParamMouthForm": 1.0,
                "ParamEyeSmile_Happy_L": 1.0,
                "ParamEyeSmile_Happy_R": 1.0,
            }),
            Mood.SAD: ("眼泪.exp3.json", {
                "ParamEyeLOpen": 0.3,
                "ParamEyeROpen": 0.3,
            }),
            Mood.TOUCHED: ("泪珠.exp3.json", {
                "ParamMouthForm": 0.3,
            }),
            Mood.PLAYFUL: ("眯眯眼.exp3.json", {
                "ParamEyeLSmile": 1.0,
                "ParamEyeRSmile": 1.0,
            }),
            Mood.ANGRY: (None, {
                "ParamBrowLY": -0.5,
                "ParamBrowRY": -0.5,
                "ParamMouthForm": -0.5,
                "ParamEyeSmile_Angry_L": 1.0,
                "ParamEyeSmile_Angry_R": 1.0,
            }),
            Mood.SURPRISED: (None, {
                "ParamMouthOpenY": 0.8,
                "ParamEyeLOpen": 1.5,
                "ParamEyeROpen": 1.5,
            }),
            Mood.LOVING: ("笑咪咪.exp3.json", {
                "ParamMouthForm": 1.0,
                "ParamEyeLSmile": 1.0,
                "ParamEyeRSmile": 1.0,
            }),
            Mood.NEUTRAL: (None, {}),
        }

        expr_file, params = mapping.get(result.mood, (None, {}))
        result.expression_file = expr_file
        result.params = params
