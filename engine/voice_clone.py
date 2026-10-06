import asyncio
import base64
import json
import os
import tempfile
import threading
import time
import traceback
from pathlib import Path
from typing import Optional

import httpx
import pygame

from .storage import load_json, save_json

# ── 配置 ────────────────────────────────────────────

CUSTOMIZATION_URL = "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/customization"
QWEN_TTS_API_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
VOICE_PROFILES_PATH = Path("data/voice_profiles.json")

# qwen3-tts-flash 官方系统音色
PRESET_VOICES = {
    "Cherry":    "芊悦 - 阳光元气小姐姐（女）",
    "Serena":    "苏瑶 - 温柔小姐姐（女）",
    "Chelsie":   "千雪 - 二次元虚拟女友（女）",
    "Momo":      "茉兔 - 撒娇搞怪（女）",
    "Vivian":    "十三 - 可爱小暴躁（女）",
    "Katerina":  "卡捷琳娜 - 御姐音（女）",
    "Seren":     "小婉 - 温和舒缓（女）",
    "Ethan":     "晨煦 - 阳光温暖（男）",
    "Kai":       "凯 - 磁性温柔（男）",
    "Moon":      "月白 - 率性帅气（男）",
}

_QWEN_TTS_MODEL = "qwen3-tts-vc-2026-01-22"
_QWEN_TTS_FLASH_MODEL = "qwen3-tts-flash"


class CosyVoiceTTS:

    def __init__(self, api_key: str, voice: str = "Cherry"):
        self.api_key = api_key
        self.voice = voice
        self._profiles: dict = load_json(str(VOICE_PROFILES_PATH), {})
        self._stop_event = threading.Event()
        self._channel = None

    # ── 音色管理 ────────────────────────────────────

    @property
    def available_voices(self) -> list[str]:
        return list(PRESET_VOICES.keys()) + list(self._profiles.keys())

    def set_voice(self, voice: str):
        self.voice = voice

    def get_voice_label(self, voice_id: str) -> str:
        if voice_id in PRESET_VOICES:
            return PRESET_VOICES[voice_id]
        profile = self._profiles.get(voice_id, {})
        return profile.get("name", voice_id)

    def is_cloned_voice(self, voice_id: str) -> bool:
        return voice_id in self._profiles

    # ── 声音克隆 ────────────────────────────────────

    def clone_voice(self, name: str, audio_path: str):
        profile = _clone_voice_qwen(self.api_key, name, audio_path)
        if profile:
            self._profiles[name] = profile
            save_json(str(VOICE_PROFILES_PATH), self._profiles)
        return profile

    def delete_voice(self, name: str):
        self._profiles.pop(name, None)
        save_json(str(VOICE_PROFILES_PATH), self._profiles)

    # ── 语音合成 ────────────────────────────────────

    def synthesize(self, text: str, voice: Optional[str] = None) -> Optional[bytes]:
        voice_id = voice or self.voice
        profile = self._profiles.get(voice_id)
        if profile:
            if profile.get("model") != _QWEN_TTS_MODEL:
                print(f"[TTS] 音色「{voice_id}」是旧版 {profile.get('model')} 复刻，接口已下线，请用 /clone 重新克隆")
                return None
            return _synthesize_qwen(self.api_key, text, profile.get("voice_id", voice_id))
        return _synthesize_qwen_flash(self.api_key, text, voice_id)

    def stop(self):
        self._stop_event.set()
        if self._channel is not None:
            self._channel.stop()

    def speak(self, text: str, voice: Optional[str] = None, on_play=None):
        voice_id = voice or self.voice
        audio = self.synthesize(text, voice_id)
        if audio is None:
            return False

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            path = f.name
        try:
            with open(path, "wb") as f:
                f.write(audio)

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
            return True
        except Exception as e:
            print(f"[TTS] 播放失败: {e}")
            return False
        finally:
            try:
                os.remove(path)
            except PermissionError:
                pass


# ── 克隆：Qwen-TTS（支持 base64 本地文件）────────────

MAX_CLONE_BYTES = 6_291_456  # 6 MB


def _clone_voice_qwen(api_key: str, name: str, audio_path: str) -> Optional[dict]:
    if not os.path.isfile(audio_path):
        print(f"[声音克隆] 文件不存在: {audio_path}")
        return None

    size = os.path.getsize(audio_path)
    if size > MAX_CLONE_BYTES:
        print(f"[声音克隆] 文件过大 ({size / 1024 / 1024:.1f} MB)，限制最大 6 MB")
        print(f"建议：用 ffmpeg 压缩：")
        print(f"  ffmpeg -i \"{audio_path}\" -b:a 64k \"压缩版_{os.path.basename(audio_path)}\"")
        return None

    with open(audio_path, "rb") as f:
        audio_b64 = base64.b64encode(f.read()).decode("ascii")

    ext = os.path.splitext(audio_path)[1].lower()
    mime = {"wav": "audio/wav", "mp3": "audio/mpeg", "ogg": "audio/ogg"}.get(ext, "audio/wav")

    payload = {
        "model": "qwen-voice-enrollment",
        "input": {
            "action": "create",
            "target_model": _QWEN_TTS_MODEL,
            "preferred_name": name,
            "audio": {"data": f"data:{mime};base64,{audio_b64}"},
        },
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        resp = httpx.post(CUSTOMIZATION_URL, headers=headers, json=payload, timeout=300)
        if resp.status_code == 200:
            data = resp.json()
            voice_id = data.get("output", {}).get("voice")
            if voice_id:
                print(f"[声音克隆] 成功: {name} (voice_id: {voice_id})")
                return {"name": name, "voice_id": voice_id, "model": _QWEN_TTS_MODEL}
            print(f"[声音克隆] 返回格式异常: {resp.text[:200]}")
            return None
        print(f"[声音克隆] 失败 {resp.status_code}: {resp.text[:300]}")
        return None
    except Exception as e:
        print(f"[声音克隆] 请求异常: {e}")
        return None


# ── 合成：Qwen3-TTS-Flash（系统预设音色）────────────

def _synthesize_qwen_flash(api_key: str, text: str, voice: str) -> Optional[bytes]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": _QWEN_TTS_FLASH_MODEL,
        "input": {"text": text},
        "parameters": {"voice": voice},
    }

    try:
        resp = httpx.post(QWEN_TTS_API_URL, headers=headers, json=payload, timeout=120)
        if resp.status_code == 200:
            data = resp.json()
            audio_url = data.get("output", {}).get("audio", {}).get("url")
            if audio_url:
                r = httpx.get(audio_url, timeout=60)
                if r.status_code == 200:
                    return r.content
            raw_audio = data.get("output", {}).get("audio", {}).get("data", "")
            if raw_audio:
                return base64.b64decode(raw_audio)
            return resp.content
        print(f"[Qwen3-TTS-Flash] 失败 {resp.status_code}: {resp.text[:300]}")
        return None
    except Exception as e:
        print(f"[Qwen3-TTS-Flash] 合成异常: {e}")
        return None


# ── 合成：Qwen-TTS（克隆音色）────────────────────

QWEN_TTS_API_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"


def _synthesize_qwen(api_key: str, text: str, voice: str) -> Optional[bytes]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": _QWEN_TTS_MODEL,
        "input": {
            "text": text,
        },
        "parameters": {
            "voice": voice,
        },
    }

    try:
        resp = httpx.post(QWEN_TTS_API_URL, headers=headers, json=payload, timeout=120)
        if resp.status_code == 200:
            data = resp.json()
            audio_url = data.get("output", {}).get("audio", {}).get("url")
            if audio_url:
                r = httpx.get(audio_url, timeout=60)
                if r.status_code == 200:
                    return r.content
            raw_audio = data.get("output", {}).get("audio", {}).get("data", "")
            if raw_audio:
                return base64.b64decode(raw_audio)
            return resp.content
        print(f"[Qwen-TTS] 失败 {resp.status_code}: {resp.text[:300]}")
        return None
    except Exception as e:
        print(f"[Qwen-TTS] 合成异常: {e}")
        return None


# ── 命令行测试 ──
if __name__ == "__main__":
    cfg = load_json("data/config.json", {})
    key = cfg.get("api_key", "")
    if not key:
        print("请在 config.json 中配置 api_key")
        exit(1)

    tts = CosyVoiceTTS(key, voice="Cherry")
    print("可用音色:", ", ".join(tts.available_voices))
    print("合成中...")
    tts.speak("你好，我是你的桌面AI助手，很高兴认识你")
