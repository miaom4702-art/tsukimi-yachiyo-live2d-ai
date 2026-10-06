# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 规范，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [0.1.0] - 2026-10-06

首个公开版本。

### 新增

- **Live2D 桌面角色**：无边框、透明、鼠标穿透的悬浮窗，停靠屏幕右下角，内含眨眼、呼吸、待机动作与基于拼音的口型同步。
- **大语言模型对话**：通过 OpenAI 兼容接口接入阿里云 DashScope，默认模型 `qwen-plus`。
- **人格系统**：由 `data/personality.json` 定义角色（默认「月见八千代」）。
- **长期记忆**：关键词自动记忆，支持 `/memory`、`/remember`、`/forget` 命令。
- **对话历史**：本地持久化并自动裁剪至最近 20 轮。
- **情感/表情系统**：关键词情感分析映射到 8 种情绪及 Live2D 表情与参数。
- **语音合成**：edge-tts 默认语音，可切换 DashScope CosyVoice / Qwen3-TTS，支持预设音色与声音克隆（`/clone`）。
- **日语朗读模式**：中文显示、日语朗读（`/jptts`、`/jpv`）。
- **语音输入**：基于 Vosk 离线中文模型的连续语音识别，支持静音断句与语音活动打断。
- **打断控制**：按 `ESC` 立即停止语音播放。
- **Web UI**：`python main.py --web` 启动本地 Flask 聊天界面。
- **VTube Studio 联动**：通过 WebSocket 同步情绪表情与参数。
- **测试**：`pytest` 单元测试覆盖核心模块。

[0.1.0]: https://github.com/miaom4702-art/DesktopAI/releases/tag/v0.1.0
