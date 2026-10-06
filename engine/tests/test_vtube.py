import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from ..vtube import VTubeStudio, _make_msg, _load_token, _save_token
from ..mood import MoodAnalyzer, MoodResult, Mood


class TestVTubeMessages:

    def test_make_msg_format(self):
        msg = _make_msg("Test", {"key": "value"})
        data = json.loads(msg)
        assert data["apiName"] == "VTubeStudioPublicAPI"
        assert data["apiVersion"] == "1.0"
        assert data["messageType"] == "Test"
        assert data["data"]["key"] == "value"
        assert "requestID" in data


class TestVTubeStudio:

    @pytest.fixture
    def vtube(self):
        return VTubeStudio()

    def test_init_not_authenticated(self, vtube):
        assert vtube.authenticated is False
        assert vtube.current_expression is None

    def test_make_msg_contains_request_id(self):
        msg = _make_msg("Test", {})
        data = json.loads(msg)
        assert len(data["requestID"]) == 12

    @pytest.mark.asyncio
    async def test_connect_success(self):
        with (
            patch("engine.vtube.websockets") as mock_ws_mod,
            patch("engine.vtube._load_token", return_value=None),
            patch("engine.vtube._save_token"),
        ):
            mock_ws = AsyncMock()
            mock_ws_mod.connect = AsyncMock(return_value=mock_ws)

            auth_resp_data = {
                "messageType": "AuthenticationResponse",
                "data": {
                    "authenticated": True,
                    "authenticationToken": "test_token_123",
                }
            }
            mock_ws.recv.return_value = json.dumps(auth_resp_data)

            vtube = VTubeStudio()
            await vtube.connect()

            assert vtube.authenticated is True
            assert vtube.token == "test_token_123"

    @pytest.mark.asyncio
    async def test_set_expression(self):
        mock_ws = AsyncMock()

        vtube = VTubeStudio()
        vtube.authenticated = True
        vtube.ws = mock_ws

        resp_data = {"messageType": "ExpressionActivation", "data": {}}
        mock_ws.recv.return_value = json.dumps(resp_data)

        await vtube.set_expression("笑咪咪.exp3.json")
        assert vtube.current_expression == "笑咪咪.exp3.json"

        send_data = mock_ws.send.call_args[0][0]
        assert "ExpressionActivation" in send_data
        assert "笑咪咪.exp3.json" in send_data

    @pytest.mark.asyncio
    async def test_clear_expression(self):
        mock_ws = AsyncMock()
        resp_data = {"messageType": "ExpressionActivation", "data": {}}
        mock_ws.recv.return_value = json.dumps(resp_data)

        vtube = VTubeStudio()
        vtube.authenticated = True
        vtube.ws = mock_ws
        vtube.current_expression = "笑咪咪.exp3.json"

        await vtube.clear_expression()
        assert vtube.current_expression is None

    def test_apply_mood_no_expression(self, vtube):
        result = MoodResult(mood=Mood.NEUTRAL)
        vtube.apply_mood(result)
        assert True

    def test_apply_mood_not_authenticated(self, vtube):
        result = MoodResult(mood=Mood.HAPPY, expression_file="笑咪咪.exp3.json")
        vtube.apply_mood(result)
        assert True


class TestMoodWithVTube:

    def test_mood_expression_mapping(self):
        analyzer = MoodAnalyzer()
        happy = analyzer.analyze("太开心了，真棒！")
        assert happy.expression_file is not None
        assert "笑咪咪" in happy.expression_file

        sad = analyzer.analyze("好难过，呜呜呜")
        assert sad.expression_file is not None
        assert "眼泪" in sad.expression_file

        playful = analyzer.analyze("嘿嘿，猜猜看")
        assert playful.expression_file is not None
        assert "眯眯眼" in playful.expression_file
