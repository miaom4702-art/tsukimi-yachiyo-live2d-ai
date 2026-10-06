import sys
from pathlib import Path

import flask

sys.path.insert(0, str(Path(__file__).parent.parent))

app = flask.Flask(
    __name__,
    template_folder=str(Path(__file__).parent / "templates"),
    static_folder=str(Path(__file__).parent / "static"),
)

_desktop_app = None


def init(app_instance):
    global _desktop_app
    _desktop_app = app_instance


@app.route("/")
def index():
    return flask.render_template("chat.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    if _desktop_app is None:
        return flask.jsonify({"error": "AI not initialized"}), 500
    data = flask.request.get_json(silent=True) or {}
    message = data.get("message", "").strip()
    if not message:
        return flask.jsonify({"error": "消息不能为空"}), 400
    reply = _desktop_app.chat(message)
    return flask.jsonify({"reply": reply})


@app.route("/api/command", methods=["POST"])
def command():
    if _desktop_app is None:
        return flask.jsonify({"error": "AI not initialized"}), 500
    data = flask.request.get_json(silent=True) or {}
    cmd = data.get("command", "").strip()
    app = _desktop_app

    if cmd == "/v":
        app._toggle_voice_mode()
        return flask.jsonify({"voice_mode": app.voice_mode})
    elif cmd == "/t":
        app._toggle_tts()
        return flask.jsonify({"tts_mode": app.tts_mode})
    elif cmd == "/jptts":
        app._toggle_jptts()
        return flask.jsonify({"jp_tts": app.jp_tts})
    elif cmd == "/clear":
        app.ai.chat("/clear")
        return flask.jsonify({"result": "ok"})
    elif cmd.startswith("/voice "):
        app._set_voice(cmd[7:].strip())
        return flask.jsonify({"result": "ok"})
    elif cmd == "/help":
        return flask.jsonify({"result": "ok"})
    return flask.jsonify({"error": f"未知命令: {cmd}"}), 400


@app.route("/api/settings")
def settings():
    if _desktop_app is None:
        return flask.jsonify({"error": "not initialized"}), 500
    app = _desktop_app
    return flask.jsonify({
        "jp_tts": app.jp_tts,
        "tts_mode": app.tts_mode,
        "voice_mode": app.voice_mode,
        "ai_name": app.ai.personality.name,
    })
