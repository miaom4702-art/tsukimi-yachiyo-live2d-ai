import json
import asyncio
import uuid
from pathlib import Path
from typing import Optional
import websockets

from .storage import load_json, save_json

TOKEN_PATH = Path("data/vtube_token.json")
VTUBE_HOST = "ws://127.0.0.1:8001"
PLUGIN_NAME = "DesktopAI"
PLUGIN_DEV = "user"


def _req_id():
    return uuid.uuid4().hex[:12]


def _make_msg(msg_type: str, data: dict, req_id: str = None):
    return json.dumps({
        "apiName": "VTubeStudioPublicAPI",
        "apiVersion": "1.0",
        "requestID": req_id or _req_id(),
        "messageType": msg_type,
        "data": data,
    }, ensure_ascii=False)


def _load_token():
    data = load_json(str(TOKEN_PATH), {})
    return data.get("token")


def _save_token(token: str):
    save_json(str(TOKEN_PATH), {"token": token})


class VTubeStudio:

    def __init__(self, host: str = VTUBE_HOST):
        self.host = host
        self.ws = None
        self.authenticated = False
        self.token = _load_token()
        self.current_expression: Optional[str] = None

    async def connect(self):
        self.ws = await websockets.connect(self.host)
        await self._authenticate()

    async def close(self):
        if self.ws:
            await self.ws.close()
            self.ws = None
            self.authenticated = False

    async def _send(self, msg_type: str, data: dict) -> dict:
        msg = _make_msg(msg_type, data)
        await self.ws.send(msg)
        resp = await self.ws.recv()
        return json.loads(resp)

    async def _authenticate(self):
        req_data = {
            "pluginName": PLUGIN_NAME,
            "pluginDeveloper": PLUGIN_DEV,
        }
        if self.token:
            req_data["authenticationToken"] = self.token

        resp = await self._send("AuthenticationRequest", req_data)

        if resp.get("messageType") == "AuthenticationResponse":
            data = resp.get("data", {})
            if data.get("authenticated"):
                self.authenticated = True
                new_token = data.get("authenticationToken")
                if new_token:
                    self.token = new_token
                    _save_token(new_token)
                return

        if not self.authenticated:
            raise ConnectionError(
                "VTube Studio 认证失败。"
                "请确保 VTube Studio 已打开并启用了 WebSocket API（设置 → API → 启用）。"
            )

    async def set_expression(self, expression_file: str):
        if not self.authenticated:
            return

        if expression_file == self.current_expression:
            return

        if self.current_expression:
            await self._send("ExpressionActivation", {
                "expressionFile": self.current_expression,
                "active": False,
            })

        if expression_file:
            await self._send("ExpressionActivation", {
                "expressionFile": expression_file,
                "active": True,
            })

        self.current_expression = expression_file

    async def clear_expression(self):
        if self.current_expression:
            await self._send("ExpressionActivation", {
                "expressionFile": self.current_expression,
                "active": False,
            })
            self.current_expression = None

    async def set_parameters(self, params: dict, weight: float = 1.0):
        if not self.authenticated or not params:
            return

        face_found = False
        any_params = await self._get_available_params()
        if not any_params:
            return

        param_values = []
        for param_id, value in params.items():
            if param_id in any_params:
                param_values.append({
                    "id": param_id,
                    "value": value * weight,
                })

        if param_values:
            await self._send("InjectParameterData", {
                "parameterValues": param_values,
                "faceFound": True,
                "mode": "set",
            })

    async def _get_available_params(self) -> set:
        try:
            resp = await self._send("ParameterList", {
                "parameterCount": 0,
                "parameterList": [],
            })
            data = resp.get("data", {})
            params = data.get("parameterList", [])
            return set(p.get("id") for p in params)
        except Exception:
            return set()

    async def speak_mouth(self, open_value: float = 0.6):
        await self.set_parameters({"ParamMouthOpenY": open_value})

    def apply_mood(self, result, loop=None):
        if not self.authenticated:
            return
        coro = self._apply_mood_async(result)
        loop = loop or asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(coro)
        else:
            loop.run_until_complete(coro)

    async def _apply_mood_async(self, result):
        if result.expression_file:
            await self.set_expression(result.expression_file)
        else:
            await self.clear_expression()
        if result.params:
            await self.set_parameters(result.params, result.intensity)
