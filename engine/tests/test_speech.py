import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from ..speech import Speaker


class TestSpeaker:
    def test_speak_calls_edge_tts(self):
        with (
            patch("engine.speech.edge_tts.Communicate") as mock_comm,
            patch("engine.speech.pygame.mixer") as mock_mixer,
            patch("engine.speech.pygame.mixer.Sound") as mock_sound_cls,
            patch("engine.speech.pygame.time.Clock") as mock_clock,
            patch("engine.speech.tempfile.NamedTemporaryFile") as mock_tmp,
            patch("engine.speech.os.remove") as mock_remove,
        ):
            mock_comm_instance = MagicMock()
            mock_comm_instance.save = AsyncMock(return_value=None)
            mock_comm.return_value = mock_comm_instance
            mock_tmp_file = MagicMock()
            mock_tmp_file.name = "C:\\tmp\\test.mp3"
            mock_tmp.return_value.__enter__.return_value = mock_tmp_file

            mock_sound = MagicMock()
            mock_sound.get_length.return_value = 1.0
            mock_sound_cls.return_value = mock_sound

            mock_channel = MagicMock()
            mock_channel.get_busy.side_effect = [True, False]
            mock_sound.play.return_value = mock_channel

            speaker = Speaker()
            speaker.speak("你好")

            mock_comm.assert_called_once_with(text="你好", voice="zh-CN-XiaoyiNeural")
            mock_comm_instance.save.assert_called_once()
            mock_sound_cls.assert_called_once_with("C:\\tmp\\test.mp3")
            mock_sound.play.assert_called_once()
