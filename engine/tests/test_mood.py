import pytest
from ..mood import MoodAnalyzer, Mood


class TestMoodAnalyzer:

    @pytest.fixture
    def analyzer(self):
        return MoodAnalyzer()

    def test_neutral_empty(self, analyzer):
        result = analyzer.analyze("")
        assert result.mood == Mood.NEUTRAL

    def test_happy(self, analyzer):
        result = analyzer.analyze("哈哈，今天真开心！")
        assert result.mood == Mood.HAPPY

    def test_sad(self, analyzer):
        result = analyzer.analyze("好难过，呜呜")
        assert result.mood == Mood.SAD

    def test_touched(self, analyzer):
        result = analyzer.analyze("太感动了，谢谢你")
        assert result.mood == Mood.TOUCHED

    def test_playful(self, analyzer):
        result = analyzer.analyze("嘿嘿，逗你玩的")
        assert result.mood == Mood.PLAYFUL

    def test_angry(self, analyzer):
        result = analyzer.analyze("真可恶，太生气了")
        assert result.mood == Mood.ANGRY

    def test_surprised(self, analyzer):
        result = analyzer.analyze("哇，真的吗？太厉害了！")
        assert result.mood == Mood.SURPRISED

    def test_loving(self, analyzer):
        result = analyzer.analyze("最喜欢你了，爱你哦")
        assert result.mood == Mood.LOVING

    def test_intensity_happy(self, analyzer):
        result = analyzer.analyze("哈哈，今天真开心！真棒！")
        assert result.mood == Mood.HAPPY
        assert 0 < result.intensity <= 1.0

    def test_expression_file_mapping(self, analyzer):
        result = analyzer.analyze("哈哈真开心")
        assert result.expression_file is not None
        assert result.expression_file.endswith(".exp3.json")

    def test_neutral_has_no_expression(self, analyzer):
        result = analyzer.analyze("今天天气晴朗")
        assert result.expression_file is None

    def test_sentiment_score_positive(self, analyzer):
        score = analyzer.analyze_sentiment_score("开心美好幸福")
        assert score > 0

    def test_sentiment_score_negative(self, analyzer):
        score = analyzer.analyze_sentiment_score("难过伤心痛苦")
        assert score < 0

    def test_sentiment_score_neutral(self, analyzer):
        score = analyzer.analyze_sentiment_score("桌子椅子")
        assert score == 0.0
