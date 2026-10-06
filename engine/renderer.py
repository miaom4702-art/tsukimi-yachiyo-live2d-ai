import math
import os
import random
import threading
import time
from ctypes import windll
from pathlib import Path
from pypinyin import pinyin, Style

from OpenGL import GL as gl
import live2d.v3 as live2d

MODEL_DIR = Path(__file__).parent.parent / "live2d"
MODEL_PATH = MODEL_DIR / "八千代辉夜姬.model3.json"
WIDTH, HEIGHT = 600, 700

OPEN_VOWELS = {"a", "e", "o", "ai", "ei", "ao", "ou", "an", "en", "ang", "eng", "er"}
ROUNDED_VOWELS = {"u", "ü", "ong", "iong", "ua", "uo", "uai", "ui", "uan", "un", "uang"}
SPREAD_VOWELS = {"i", "ia", "ie", "iao", "iu", "ian", "iang", "in", "ing", "ya", "ye", "yo", "you", "yan", "yang", "yong"}


def _pinyin_mouth(py: str) -> tuple:
    if not py or py in ("？", "。", "！", "，", "、", "；", "：", "…", "—"):
        return 0.0, 0.0

    has_rounded = any(v in py for v in ROUNDED_VOWELS if v in py)
    has_spread = any(v in py for v in SPREAD_VOWELS if v in py)

    for v in OPEN_VOWELS:
        if v in py:
            open_y = 0.8
            break
    else:
        for v in SPREAD_VOWELS:
            if v in py:
                open_y = 0.5
                break
        else:
            for v in ROUNDED_VOWELS:
                if v in py:
                    open_y = 0.4
                    break
            else:
                open_y = 0.15

    if has_rounded:
        mouth_form = -0.5
    elif has_spread:
        mouth_form = 0.4
    else:
        mouth_form = 0.0

    return open_y, mouth_form


def _text_to_mouth_frames(text: str) -> list:
    raw = pinyin(text, style=Style.NORMAL, neutral_tone_with_five=True)
    return [_pinyin_mouth(r[0]) for r in raw]


EXPRESSION_FILES = {
    "笑咪咪.exp3.json": "happy",
    "眼泪.exp3.json": "sad",
    "泪珠.exp3.json": "touched",
    "眯眯眼.exp3.json": "playful",
}


class Live2DRenderer:
    def __init__(self):
        self._model = None
        self._running = False
        self._mood_queue = []
        self._speaking = False
        self._speak_start = 0.0
        self._speak_frames = []
        self._speak_duration = 1.0
        self._lock = threading.Lock()
        self._anim_time = 0.0
        self._blink_timer = 0.0
        self._blinking = False
        self._blink_progress = 0.0
        self._idle_targets = {"ParamAngleX": 0, "ParamAngleY": 0}
        self._idle_phase = 0.0

    def set_mood(self, expression_file: str = None, params: dict = None, intensity: float = 1.0):
        with self._lock:
            self._mood_queue.append({
                "expression_file": expression_file,
                "params": params or {},
                "intensity": intensity,
            })

    def set_speaking(self, active: bool, text: str = "", duration: float = 1.0):
        with self._lock:
            self._speaking = active
            if active:
                self._speak_start = time.time()
                self._speak_frames = _text_to_mouth_frames(text)
                self._speak_duration = max(duration, 0.5)

    def start(self):
        self._running = True
        t = threading.Thread(target=self._render_loop, daemon=True)
        t.start()

    def stop(self):
        self._running = False

    def _render_loop(self):
        import pygame

        pygame.init()
        pygame.display.set_caption("DesktopAI")

        flags = pygame.DOUBLEBUF | pygame.OPENGL | pygame.NOFRAME
        screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)

        hwnd = pygame.display.get_wm_info()["window"]

        GWL_EXSTYLE = -20
        WS_EX_LAYERED = 0x80000
        WS_EX_TRANSPARENT = 0x20
        WS_EX_TOOLWINDOW = 0x80
        current = windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        windll.user32.SetWindowLongW(
            hwnd, GWL_EXSTYLE,
            current | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW,
        )

        COLOR_MAGENTA = 0x00FF00FF
        LWA_COLORKEY = 1
        windll.user32.SetLayeredWindowAttributes(hwnd, COLOR_MAGENTA, 0, LWA_COLORKEY)

        info = pygame.display.Info()
        sw, sh = info.current_w, info.current_h
        margin = 10
        x = sw - WIDTH - margin
        y = sh - HEIGHT - margin
        SWP_NOZORDER = 4
        SWP_SHOWWINDOW = 0x40
        SWP_NOSIZE = 1
        windll.user32.SetWindowPos(hwnd, 0, x, y, 0, 0, SWP_NOZORDER | SWP_NOSIZE | SWP_SHOWWINDOW)

        live2d.init()
        live2d.glInit()
        gl.glClearColor(1.0, 0.0, 1.0, 0.0)

        model = live2d.LAppModel()
        model.LoadModelJson(str(MODEL_PATH))
        model.Resize(WIDTH, HEIGHT)

        for expr_file, expr_id in EXPRESSION_FILES.items():
            path = MODEL_DIR / expr_file
            if path.exists():
                model.LoadExtraExpression(expr_id, str(path))

        model.ResetExpression()

        self._model = model

        clock = pygame.time.Clock()

        while self._running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self._running = False

            dt = clock.tick(60) / 1000.0
            self._anim_time += dt
            self._drain_mood_queue()
            self._update_blink(dt)
            self._update_breathing()
            self._update_idle_motion(dt)
            self._update_mouth()
            gl.glClearColor(1.0, 0.0, 1.0, 0.0)
            live2d.clearBuffer()
            model.Update()
            model.Draw()
            pygame.display.flip()

        live2d.dispose()
        pygame.quit()

    def _update_mouth(self):
        if self._model is None:
            return
        with self._lock:
            speaking = self._speaking
            start = self._speak_start
            frames = self._speak_frames[:]
            duration = self._speak_duration
        if speaking and frames:
            elapsed = time.time() - start
            progress = elapsed / duration
            if progress >= 1.0:
                open_y, mouth_form = frames[-1]
            else:
                idx = int(progress * len(frames))
                idx = min(idx, len(frames) - 1)
                open_y, mouth_form = frames[idx]
            self._model.SetParameterValue("ParamMouthOpenY", open_y, 0.5)
            self._model.SetParameterValue("ParamMouthForm", mouth_form, 0.5)
        else:
            self._model.SetParameterValue("ParamMouthOpenY", 0.0, 0.5)
            self._model.SetParameterValue("ParamMouthForm", 0.0, 0.5)

    def _drain_mood_queue(self):
        if not self._mood_queue or self._model is None:
            return

        with self._lock:
            queue = self._mood_queue[:]
            self._mood_queue.clear()

        for data in queue:
            self._apply_mood(data)

    def _apply_mood(self, data):
        expr_file = data.get("expression_file")
        params = data.get("params", {})
        intensity = data.get("intensity", 1.0)

        if expr_file:
            expr_id = EXPRESSION_FILES.get(expr_file)
            if expr_id:
                self._model.SetExpression(expr_id)
        else:
            self._model.ResetExpression()

        for param_id, value in params.items():
            self._model.SetParameterValue(param_id, value * intensity, 1.0)

    def _update_blink(self, dt):
        if self._model is None:
            return
        self._blink_timer -= dt
        if self._blink_timer <= 0 and not self._blinking:
            self._blinking = True
            self._blink_progress = 0.0
        if self._blinking:
            self._blink_progress += dt * 8
            if self._blink_progress < 0.5:
                v = 1.0 - self._blink_progress * 2
            elif self._blink_progress < 1.0:
                v = (self._blink_progress - 0.5) * 2
            else:
                v = 1.0
                self._blinking = False
                self._blink_timer = 2.0 + abs(random.gauss(0, 1)) * 2
            self._model.SetParameterValue("ParamEyeLOpen", v, 0.3)
            self._model.SetParameterValue("ParamEyeROpen", v, 0.3)

    def _update_breathing(self):
        if self._model is None:
            return
        breath = math.sin(self._anim_time * 2.5) * 0.04
        self._model.SetParameterValue("ParamAngle_BodyY", breath, 0.3)
        self._model.SetParameterValue("ParamAngle_BodyZ", breath * 0.5, 0.3)
        self._model.SetParameterValue("ParamAngle_ChestZ", breath * 0.3, 0.3)

    def _update_idle_motion(self, dt):
        if self._model is None:
            return
        self._idle_phase += dt * 0.3
        hx = math.sin(self._idle_phase) * 3
        hy = math.sin(self._idle_phase * 0.7 + 1.0) * 2
        self._model.SetParameterValue("ParamAngleX", hx, 0.5)
        self._model.SetParameterValue("ParamAngleY", hy, 0.5)
