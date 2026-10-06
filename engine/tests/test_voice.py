import pytest
from unittest.mock import patch, MagicMock
from ..voice_input import Listener


class TestListener:
    def test_listen_returns_text(self):
        mock_model = MagicMock()
        mock_recognizer = MagicMock()

        # Simulate: first call returns no text, second call returns recognized text
        mock_recognizer.AcceptWaveform.side_effect = [False, True]
        mock_recognizer.Result.return_value = '{"text": "你好世界"}'

        with (
            patch("engine.voice_input.Model", return_value=mock_model),
            patch("engine.voice_input.KaldiRecognizer", return_value=mock_recognizer),
            patch("engine.voice_input.sd.RawInputStream") as mock_stream,
        ):
            mock_ctx = MagicMock()
            mock_ctx.__enter__.return_value = None
            mock_stream.return_value = mock_ctx

            listener = Listener()
            listener.model = mock_model
            # Override the listen method to avoid infinite loop in test
            # Actually let's just test via the mock properly
            # We need to handle the queue loop

            # Patch queue to simulate data
            with patch("engine.voice_input.queue.Queue") as mock_q_cls:
                mock_q = MagicMock()
                mock_q_cls.return_value = mock_q
                mock_q.get.side_effect = [b"data1", b"data2"]

                result = listener.listen()
                assert result == "你好世界"
