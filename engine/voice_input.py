import json
import queue
import threading
import time
import traceback

import sounddevice as sd

from vosk import Model, KaldiRecognizer


class Listener:

    def __init__(self, model_path="models/vosk-model-small-cn-0.22"):
        self.model = Model(model_path)
        self._running = False
        self._thread: threading.Thread | None = None
        self._result_queue: queue.Queue = queue.Queue()
        self._on_voice_activity = None

    # ── 阻塞式单次识别 ──────────────────────────────

    def listen(self, timeout: float | None = None) -> str:
        q: queue.Queue = queue.Queue()

        def callback(indata, frames, time_info, status):
            q.put(bytes(indata))

        rec = KaldiRecognizer(self.model, 16000)

        with sd.RawInputStream(
            samplerate=16000, blocksize=8000, dtype="int16",
            channels=1, callback=callback,
        ):
            start = time.time()
            while True:
                data = q.get()
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text = result.get("text", "")
                    if text:
                        return text
                if timeout and (time.time() - start) > timeout:
                    return ""

    # ── 按键触发式（按住录音，松手识别）───────────────

    def start_recording(self):
        self._running = True
        self._frames: list[bytes] = []
        self._result_queue = queue.Queue()

        def callback(indata, frames, time_info, status):
            if self._running:
                self._frames.append(bytes(indata))

        self._stream = sd.RawInputStream(
            samplerate=16000, blocksize=8000,
            dtype="int16", channels=1, callback=callback,
        )
        self._stream.start()

    def stop_recording(self) -> str:
        self._running = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        audio_data = b"".join(self._frames)
        if not audio_data:
            return ""

        rec = KaldiRecognizer(self.model, 16000)
        frames_count = len(audio_data) // 320
        for i in range(0, len(audio_data), 320):
            chunk = audio_data[i : i + 320]
            if len(chunk) < 320:
                chunk = chunk.ljust(320, b"\x00")
            rec.AcceptWaveform(chunk)

        result = json.loads(rec.FinalResult())
        return result.get("text", "")

    # ── 连续非阻塞监听（后台线程 + 静音断句）─────────

    def start_continuous(self, callback, silence_sec=1.5, on_voice_activity=None):
        self._running = True
        self._on_voice_activity = on_voice_activity
        self._thread = threading.Thread(
            target=self._continuous_loop,
            args=(callback, silence_sec),
            daemon=True,
        )
        self._thread.start()

    def stop_continuous(self):
        self._running = False
        self._on_voice_activity = None
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

    @staticmethod
    def _calc_rms(data: bytes) -> float:
        if len(data) < 2:
            return 0.0
        samples = len(data) // 2
        total = 0
        for i in range(samples):
            s = int.from_bytes(data[i*2:(i+1)*2], "little", signed=True)
            total += s * s
        return (total / samples) ** 0.5 if samples else 0.0

    def _continuous_loop(self, callback, silence_sec):
        q: queue.Queue = queue.Queue()

        def cb(indata, frames, time_info, status):
            q.put(bytes(indata))

        rec = KaldiRecognizer(self.model, 16000)
        rec.SetWords(False)

        with sd.RawInputStream(
            samplerate=16000, blocksize=8000,
            dtype="int16", channels=1, callback=cb,
        ):
            speaking = False
            silence_start = 0.0
            partial_buf = b""

            while self._running:
                try:
                    data = q.get(timeout=0.1)
                except queue.Empty:
                    if speaking and (time.time() - silence_start) > silence_sec:
                        text = self._flush_recognizer(rec, partial_buf)
                        if text:
                            callback(text)
                        speaking = False
                        partial_buf = b""
                    continue

                # 音量检测
                try:
                    rms = self._calc_rms(data)
                except Exception:
                    rms = 0.0

                if rms > 500.0:
                    if not speaking:
                        speaking = True
                        if self._on_voice_activity:
                            try:
                                self._on_voice_activity()
                            except Exception as e:
                                print(f"[打断] 回调异常: {e}")
                    silence_start = time.time()
                    rec.AcceptWaveform(data)
                else:
                    partial_buf += data
                    if speaking and (time.time() - silence_start) > silence_sec:
                        text = self._flush_recognizer(rec, partial_buf)
                        if text:
                            callback(text)
                        speaking = False
                        partial_buf = b""

    def _flush_recognizer(self, rec, partial_buf):
        if partial_buf:
            for i in range(0, len(partial_buf), 320):
                chunk = partial_buf[i : i + 320]
                if len(chunk) < 320:
                    chunk = chunk.ljust(320, b"\x00")
                rec.AcceptWaveform(chunk)
        result = json.loads(rec.FinalResult())
        return result.get("text", "")


# ── 简易测试 ──
if __name__ == "__main__":
    v = Listener()
    print("按 Enter 开始录音，再按 Enter 结束")
    while True:
        input()
        v.start_recording()
        print("录音中...")
        input()
        text = v.stop_recording()
        print(f"识别结果: {text}")
