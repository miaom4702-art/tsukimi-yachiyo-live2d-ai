import asyncio
import edge_tts
from edge_tts.exceptions import NoAudioReceived
import pygame
import tempfile
import os
import threading


class Speaker:
    def __init__(self):
        self.voice = "zh-CN-XiaoyiNeural"
        self._stop_event = threading.Event()
        self._channel = None
        pygame.mixer.init()

    async def _generate(self, text, path, voice=None):
        communicate = edge_tts.Communicate(
            text=text,
            voice=voice or self.voice
        )
        await communicate.save(path)

    def stop(self):
        self._stop_event.set()
        if self._channel is not None:
            self._channel.stop()

    def speak(self, text, on_play=None, voice=None):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            path = f.name
        try:
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(self._generate(text, path, voice))
            except NoAudioReceived:
                print(f"[TTS] 未收到音频，请检查网络或语音名称: {voice or self.voice}")
                return
            except Exception as e:
                print(f"[TTS] 语音合成失败: {e}")
                return
            finally:
                loop.close()
            self._stop_event.clear()
            sound = pygame.mixer.Sound(path)
            duration = sound.get_length()
            channel = sound.play()
            self._channel = channel
            if on_play:
                on_play(duration)
            while channel is not None and channel.get_busy():
                if self._stop_event.is_set():
                    channel.stop()
                    break
                pygame.time.Clock().tick(10)
            self._channel = None
        finally:
            try:
                os.remove(path)
            except PermissionError:
                pass
# 本地测试入口
if __name__ == "__main__":
    spk = Speaker()
    spk.speak("测试语音播报，edge tts原生中文女声，无需本地TTS服务")