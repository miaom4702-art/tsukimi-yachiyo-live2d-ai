import os
import sys
import re
import time
import asyncio
import threading
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from engine.conversation import Conversation
from engine.speech import Speaker
from engine.renderer import Live2DRenderer
from engine.voice_input import Listener
from engine.voice_clone import CosyVoiceTTS
from engine.storage import load_json, save_json

try:
    from engine.vtube import VTubeStudio
    _HAS_VTUBE = True
except ImportError:
    _HAS_VTUBE = False

console = Console()

CONFIG_PATH = "data/config.json"
SETTINGS_PATH = "data/settings.json"


def load_settings():
    return load_json(SETTINGS_PATH, {
        "voice_mode": False,
        "tts_mode": "edge-tts",
        "clone_voice": "longwan",
        "jp_tts": False,
        "jp_voice": "nanami",
    })


def save_settings(s):
    save_json(SETTINGS_PATH, s)


JAPANESE_VOICES = {
    "nanami": "ja-JP-NanamiNeural - 标准女性",
    "keita": "ja-JP-KeitaNeural - 标准男性",
}


def _strip_tts(text):
    t = re.sub(r"（[^）]*）", "", text)
    t = re.sub(r"\*[^*]+\*", "", t)
    t = re.sub(r"\*\*(.*?)\*\*", r"\1", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


class DesktopAIApp:

    def __init__(self):
        self.settings = load_settings()
        self.config = load_json(CONFIG_PATH, {})

        self.ai = Conversation(config=self.config)
        self.renderer = Live2DRenderer()
        self.speaker = Speaker()
        self.listener = Listener()

        api_key = self.config.get("api_key", os.environ.get("DASHSCOPE_API_KEY", ""))
        clone_voice = self.settings.get("clone_voice", "longwan")
        self.clone_tts = CosyVoiceTTS(api_key, voice=clone_voice)

        self.voice_mode = self.settings.get("voice_mode", False)
        self.tts_mode = self.settings.get("tts_mode", "edge-tts")
        self.jp_tts = self.settings.get("jp_tts", False)
        self.jp_voice = self.settings.get("jp_voice", "nanami")
        self._interrupt_lock = threading.Lock()
        self._esc_running = True

        self._start_esc_listener()

        self.vtube = None
        self._vtube_loop = None
        if _HAS_VTUBE:
            try:
                self.vtube = VTubeStudio()
                self._vtube_loop = asyncio.new_event_loop()
                t = threading.Thread(target=self._vtube_loop.run_forever, daemon=True)
                t.start()
                future = asyncio.run_coroutine_threadsafe(
                    self.vtube.connect(), self._vtube_loop
                )
                future.result(timeout=5)
                console.print("[green]VTube Studio 已连接[/]")
            except Exception as e:
                self.vtube = None
                console.print(f"[dim]VTube Studio 未连接: {e}[/]")

        self.renderer.start()
        if self.voice_mode:
            self._start_voice_mode()

    def _panel(self, title, content, style):
        return Panel(
            Text(content, style=style),
            title=title,
            border_style=style,
            padding=(0, 1),
        )

    # ── 打断 ────────────────────────────────────────

    def interrupt(self):
        with self._interrupt_lock:
            self.speaker.stop()
            self.clone_tts.stop()
            self.renderer.set_speaking(False)

    def _start_esc_listener(self):
        try:
            import msvcrt
        except ImportError:
            return

        def loop():
            while self._esc_running:
                try:
                    if msvcrt.kbhit():
                        key = msvcrt.getwch()
                        if key == "\x1b":
                            self.interrupt()
                            console.print("[dim]⏹ 已打断[/]")
                        else:
                            msvcrt.ungetwch(key)
                except Exception:
                    pass
                time.sleep(0.05)

        threading.Thread(target=loop, daemon=True).start()

    # ── 聊天 ────────────────────────────────────────

    def chat(self, text):
        console.print(self._panel(f" 你 [{datetime.now().strftime('%H:%M')}]", text, "cyan"))
        reply = self.ai.chat(text)

        name = self.ai.personality.name
        console.print(self._panel(f" {name} [{datetime.now().strftime('%H:%M')}]", reply, "green"))

        mood = self.ai.last_mood
        self.renderer.set_mood(mood.expression_file, mood.params, mood.intensity)
        if self.vtube and self._vtube_loop:
            asyncio.run_coroutine_threadsafe(
                self.vtube._apply_mood_async(mood), self._vtube_loop
            )

        tts_text = _strip_tts(reply)
        if tts_text:
            self._speak(tts_text)

        return reply

    def _to_japanese(self, text):
        context = self.ai.messages[-4:] if len(self.ai.messages) > 1 else []
        msg = [{"role": "system", "content": "根据对话上下文将中文翻译成自然的口语日语，保留说话者的语气和风格。只输出翻译结果，不要多余内容。"}]
        for m in context:
            if m["role"] != "system":
                msg.append({"role": m["role"], "content": m["content"]})
        msg.append({"role": "user", "content": f"把上面最后一句中文翻译成日语，只输出翻译结果：\n{text}"})
        return self.ai.llm.chat(msg)

    def _speak(self, text):
        tts_text = self._to_japanese(text) if self.jp_tts else text
        if self.jp_tts:
            jp_voice = JAPANESE_VOICES.get(self.jp_voice)
            if jp_voice is None:
                jp_voice = JAPANESE_VOICES["nanami"]
            self.speaker.speak(
                tts_text,
                on_play=lambda d: self.renderer.set_speaking(True, text=tts_text, duration=d),
                voice=jp_voice.split(" - ")[0],
            )
        elif self.tts_mode == "cosyvoice":
            ok = self.clone_tts.speak(
                tts_text,
                on_play=lambda d: self.renderer.set_speaking(True, text=tts_text, duration=d),
            )
            if not ok:
                self.speaker.speak(
                    tts_text,
                    on_play=lambda d: self.renderer.set_speaking(True, text=tts_text, duration=d),
                )
        else:
            self.speaker.speak(
                tts_text,
                on_play=lambda d: self.renderer.set_speaking(True, text=tts_text, duration=d),
            )
        self.renderer.set_speaking(False)

    # ── 语音输入 ────────────────────────────────────

    def _on_voice_result(self, text):
        text = text.strip()
        if not text:
            return
        if text == "bye" or text == "退出" or text == "结束" or text == "停止":
            self._toggle_voice_mode()
            return
        console.print(f"\n[bold cyan]🎤 {text}[/]")
        self.chat(text)

    def _start_voice_mode(self):
        self.voice_mode = True
        console.print("[bold cyan]🎤 语音模式已开启，直接说话即可（说「退出」关闭）[/]")
        self.listener.start_continuous(
            self._on_voice_result,
            on_voice_activity=self.interrupt,
        )

    def _stop_voice_mode(self):
        self.voice_mode = False
        self.listener.stop_continuous()
        console.print("[dim]语音模式已关闭[/]")

    def _toggle_voice_mode(self):
        if self.voice_mode:
            self._stop_voice_mode()
        else:
            self._start_voice_mode()
        self.settings["voice_mode"] = self.voice_mode
        save_settings(self.settings)

    # ── TTS ─────────────────────────────────────────

    def _toggle_tts(self):
        if self.tts_mode == "edge-tts":
            self.tts_mode = "cosyvoice"
            label = self.clone_tts.get_voice_label(self.clone_tts.voice)
            console.print(f"[green]TTS → CosyVoice ({label})[/]")
        else:
            self.tts_mode = "edge-tts"
            console.print("[green]TTS → edge-tts 标准语音[/]")
        self.settings["tts_mode"] = self.tts_mode
        save_settings(self.settings)

    def _list_voices(self):
        console.print("\n[bold]可用 CosyVoice 音色:[/]")
        for vid in self.clone_tts.available_voices:
            label = self.clone_tts.get_voice_label(vid)
            marker = " ✓" if vid == self.clone_tts.voice else ""
            console.print(f"  {vid:20s} {label}{marker}")

    def _set_voice(self, voice_id):
        if voice_id in self.clone_tts.available_voices:
            self.clone_tts.set_voice(voice_id)
            self.settings["clone_voice"] = voice_id
            save_settings(self.settings)
            console.print(f"[green]音色 → {self.clone_tts.get_voice_label(voice_id)}[/]")
        else:
            console.print(f"[red]未知音色: {voice_id}[/]")

    def _reconnect_vtube(self):
        if not _HAS_VTUBE:
            console.print("[red]VTube Studio 库未安装[/]")
            return
        try:
            if self.vtube:
                future = asyncio.run_coroutine_threadsafe(
                    self.vtube.close(), self._vtube_loop
                )
                future.result(timeout=5)
            self.vtube = VTubeStudio()
            if not self._vtube_loop or not self._vtube_loop.is_running():
                self._vtube_loop = asyncio.new_event_loop()
                t = threading.Thread(target=self._vtube_loop.run_forever, daemon=True)
                t.start()
            future = asyncio.run_coroutine_threadsafe(
                self.vtube.connect(), self._vtube_loop
            )
            future.result(timeout=5)
            console.print("[green]VTube Studio 已重连[/]")
        except Exception as e:
            console.print(f"[red]VTube Studio 连接失败: {e}[/]")

    def _toggle_jptts(self):
        self.jp_tts = not self.jp_tts
        self.settings["jp_tts"] = self.jp_tts
        save_settings(self.settings)
        if self.jp_tts:
            voice_label = JAPANESE_VOICES.get(self.jp_voice, self.jp_voice)
            console.print(f"[green]日语朗读已开启 — 控制台显示中文，TTS 朗读日语（{voice_label}）[/]")
        else:
            console.print("[dim]日语朗读已关闭，TTS 朗读中文[/]")

    def _list_jp_voices(self):
        console.print("\n[bold]可用 Edge TTS 日语语音:[/]")
        for key, label in JAPANESE_VOICES.items():
            marker = " ✓" if key == self.jp_voice else ""
            console.print(f"  [cyan]{key:12s}[/] {label}{marker}")

    def _set_jp_voice(self, voice_key):
        if voice_key in JAPANESE_VOICES:
            self.jp_voice = voice_key
            self.settings["jp_voice"] = voice_key
            save_settings(self.settings)
            console.print(f"[green]日语语音 → {JAPANESE_VOICES[voice_key]}[/]")
        else:
            console.print(f"[red]未知日语语音: {voice_key}，可用: {', '.join(JAPANESE_VOICES)}[/]")

    def _clone_voice_cmd(self, name, path):
        console.print(f"[yellow]正在从 {path} 克隆声音「{name}」...[/]")
        profile = self.clone_tts.clone_voice(name, path)
        if profile:
            console.print(f"[green]✓ 声音克隆成功: {name}[/]")
            self._set_voice(name)
        else:
            console.print("[red]✗ 声音克隆失败，检查音频路径和网络[/]")

    # ── 帮助 ────────────────────────────────────────

    def _print_help(self):
        console.print(Panel.fit("""\
[bold]DesktopAI 命令[/]

[cyan]/v[/]         语音输入开关
[cyan]/t[/]         TTS 引擎切换 (edge-tts ↔ CosyVoice)
[cyan]/s[/]         列出 CosyVoice 音色
[cyan]/voice <id>[/]  切换音色，如 /voice shanshan
[cyan]/clone <name> <path>[/]  从音频文件克隆声音
[cyan]/memory[/]    查看长期记忆
[cyan]/remember <text>[/]  添加记忆
[cyan]/forget <kw>[/]  删除记忆
[cyan]/clear[/]     清空对话历史
[cyan]/help[/]      显示此帮助
[cyan]/jptts[/]    日语朗读开关（显示中文→说日语）
[cyan]/jpv[/]      列出日语语音列表
[cyan]/jpv <id>[/]  切换日语语音，如 /jpv keita
[cyan]/vtube[/]     重连 VTube Studio
[cyan]exit[/]       退出""", title="帮助"))

    # ── 主循环 ──────────────────────────────────────

    def run(self):
        console.clear()
        self._print_help()

        while True:
            try:
                raw = console.input(f"\n[bold cyan]你[/] [{datetime.now().strftime('%H:%M')}]: ")
            except (EOFError, KeyboardInterrupt):
                break

            cmd = raw.strip()
            if not cmd:
                continue
            if cmd.lower() == "exit":
                break

            if cmd == "/v":
                self._toggle_voice_mode()
            elif cmd == "/t":
                self._toggle_tts()
            elif cmd == "/s":
                self._list_voices()
            elif cmd.startswith("/voice "):
                self._set_voice(cmd[7:].strip())
            elif cmd.startswith("/clone "):
                parts = cmd[7:].strip().split(None, 1)
                if len(parts) < 2:
                    console.print("[red]用法: /clone <名称> <音频文件路径>[/]")
                else:
                    self._clone_voice_cmd(parts[0], parts[1])
            elif cmd == "/help":
                self._print_help()
            elif cmd == "/jptts":
                self._toggle_jptts()
            elif cmd == "/jpv":
                self._list_jp_voices()
            elif cmd.startswith("/jpv "):
                self._set_jp_voice(cmd[5:].strip())
            elif cmd == "/vtube" and _HAS_VTUBE:
                self._reconnect_vtube()
            else:
                self.chat(cmd)

        self.renderer.stop()
        self.listener.stop_continuous()
        self._esc_running = False
        if self.vtube and self._vtube_loop:
            self._vtube_loop.call_soon_threadsafe(self._vtube_loop.stop)


def main():
    if "--web" in sys.argv:
        import threading
        import webbrowser
        from engine.server import app as web_app, init as web_init

        desktop = DesktopAIApp()
        desktop.renderer.start()
        web_init(desktop)

        t = threading.Thread(
            target=lambda: web_app.run(host="127.0.0.1", port=5000, debug=False, threaded=True),
            daemon=True,
        )
        t.start()
        webbrowser.open("http://127.0.0.1:5000")
        console.print("[green]Web UI 已启动 → http://127.0.0.1:5000[/]")
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            desktop.renderer.stop()
    else:
        try:
            DesktopAIApp().run()
        except Exception:
            console.print_exception()
            sys.exit(1)


if __name__ == "__main__":
    main()
