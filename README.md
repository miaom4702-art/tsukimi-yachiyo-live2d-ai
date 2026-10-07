# DesktopAI · 月见八千代

**Live2D 桌面 AI 伴侣 · Desktop Live2D AI Companion**

> 一款运行于 Windows 桌面的 Live2D 虚拟角色 AI 伴侣，内置角色「月见八千代」（英文：Tsukimi Yachiyo）。本项目将大语言模型、语音识别、语音合成、长期记忆与情感表达深度整合，让可交互的 Live2D 角色常驻桌面右下角，与用户实时对话。

## 1. 项目解决什么问题

- **让 AI 有“形象”**：普通对话式 AI 只有文字，本项目在桌面上显示一个实时渲染的 Live2D 角色，会根据 AI 回复的情绪切换表情、做呼吸/眨眼/待机动作，并在说话时做口型同步。
- **让 AI 有“记忆”**：对话历史与用户长期记忆会持久化保存在本地，重启后仍能记得你，还能在回复中自然引用。
- **让 AI 能“听和说”**：支持离线中文语音识别（Vosk）进行语音输入，并支持 edge-tts 与阿里云 DashScope 语音合成（含声音克隆）进行语音输出。
- **提供多种交互方式**：既可以在终端里以命令行方式聊天，也可以启动本地 Web 界面在浏览器中聊天。

> 注意：Live2D 桌面悬浮窗依赖 Windows API（`ctypes.windll`、`msvcrt`），当前仅支持 **Windows**。

## 2. 主要功能

- **Live2D 桌面角色**
  - 无边框、背景透明、鼠标穿透的悬浮窗口，自动停靠屏幕右下角（600×700）。
  - 内置眨眼、呼吸、待机点头等动作。
  - 播放语音时根据拼音（`pypinyin`）驱动 `ParamMouthOpenY` / `ParamMouthForm` 做口型同步。
  - 按 `ESC` 可关闭渲染窗口。
- **大语言模型对话**
  - 通过 OpenAI 兼容接口调用阿里云 DashScope（默认模型 `qwen-plus`，模型可配置）。
  - 人格设定由 `data/personality.json` 提供（姓名、身份、背景、性格、说话方式、核心信念、行为准则），当前内置角色为“月见八千代”。
- **长期记忆**
  - 命中关键词（如“我叫”“我喜欢”“我住在”等）时自动记录记忆。
  - 支持 `/memory`、`/remember`、`/forget` 命令查看、添加、删除记忆，并实时刷新系统提示词。
- **对话历史**
  - 每次对话持久化到 `data/history.json`，仅保留最近 20 轮（40 条消息），超出自动裁剪。
- **情感/表情系统**
  - 对 AI 回复做关键词情感分析，映射到 8 种情绪：`neutral / happy / sad / touched / playful / angry / surprised / loving`。
  - 每种情绪对应 Live2D 表情文件与参数（如 `笑咪咪.exp3.json`、`眼泪.exp3.json` 等），同时可同步到 VTube Studio。
- **语音合成（TTS）**
  - 默认使用 **edge-tts**（中文女声 `zh-CN-XiaoyiNeural`）。
  - 可切换到 **DashScope CosyVoice / Qwen3-TTS**：既支持官方预设音色（Cherry、Serena、Chelsie、Momo 等），也支持 **声音克隆**。
  - `/t` 切换引擎，`/s` 列出音色，`/voice <id>` 选择音色，`/clone <名称> <音频路径>` 克隆声音（单文件最大 6 MB）。
- **日语朗读模式**
  - 开启后，控制台仍显示中文，但会先调用 LLM 把回复翻译成口语日语，再用日语 edge-tts 音色（`nanami` / `keita`）朗读。
  - `/jptts` 开关，`/jpv` 查看列表，`/jpv <id>` 切换音色。
- **语音输入**
  - 基于 **Vosk** 离线中文模型（`vosk-model-small-cn-0.22`）+ `sounddevice`。
  - 连续监听，静音约 1.5 秒自动断句识别；说“退出 / 结束 / 停止 / bye”可关闭语音模式。
  - 检测到用户说话时自动打断当前正在播放的语音（语音活动打断）。
- **打断控制**
  - 任意时刻按 `ESC` 可立即停止当前语音播放。
- **Web UI（可选）**
  - `python main.py --web` 启动本地 Flask 服务并自动打开浏览器（`http://127.0.0.1:5000`）。
  - 提供聊天气泡界面、日语开关、语音开关、清空历史等按钮。
- **VTube Studio 联动（可选）**
  - 通过 WebSocket（`ws://127.0.0.1:8001`）连接 VTube Studio，把情绪表情与参数注入到 VTube Studio 的模型中，令牌缓存在 `data/vtube_token.json`。
  - 连接失败时不影响其它功能。

## 3. 安装方法

### 环境要求

- Windows 10/11
- Python 3.10+（开发环境使用 Python 3.14）
- 可用麦克风与扬声器（语音输入/输出需要）
- 阿里云 DashScope API Key（对话与 CosyVoice 语音克隆需要）

### 步骤

1. 克隆仓库：

   ```bash
   git clone https://github.com/<your-name>/DesktopAI.git
   cd DesktopAI
   ```

2. 安装 Python 依赖：

   ```bash
   pip install -r requirements.txt
   ```

3. 下载 Vosk 中文语音识别模型（语音输入需要），解压到项目根目录的 `models/` 下，目录结构为：

   ```
   models/vosk-model-small-cn-0.22/
   ```

   模型下载地址：https://alphacephei.com/vosk/models

4. 配置 API Key。在 `data/` 下创建 `config.json`：

   ```json
   {
       "api_key": "你的 DashScope API Key",
       "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
       "model": "qwen-plus"
   }
   ```

   > 也可以改用环境变量 `DASHSCOPE_API_KEY`（当 `config.json` 未配置 `api_key` 时生效）。

5. 准备 Live2D 模型资源，放在 `live2d/` 目录下（渲染器默认加载 `live2d/八千代辉夜姬.model3.json` 及其关联文件）。若使用其它模型，需同步修改 `engine/renderer.py` 中的 `MODEL_PATH`。

## 4. 使用方法

### 启动

终端模式（默认）：

```bash
python main.py
```

Web 界面模式：

```bash
python main.py --web
```

### 终端常用命令

| 命令 | 说明 |
| --- | --- |
| `/v` | 语音输入开关（连续监听） |
| `/t` | 切换 TTS 引擎（edge-tts ↔ CosyVoice/Qwen3-TTS） |
| `/s` | 列出可用的 CosyVoice 音色 |
| `/voice <id>` | 切换音色，例如 `/voice Cherry` |
| `/clone <名称> <音频路径>` | 从音频文件克隆声音 |
| `/memory` | 查看长期记忆 |
| `/remember <内容>` | 添加一条长期记忆 |
| `/forget <关键词>` | 删除包含关键词的记忆 |
| `/clear` | 清空对话历史 |
| `/jptts` | 日语朗读开关 |
| `/jpv` | 列出日语语音 |
| `/jpv <id>` | 切换日语语音，例如 `/jpv keita` |
| `/vtube` | 重连 VTube Studio |
| `/help` | 显示帮助 |
| `exit` | 退出程序 |

按 `ESC` 可随时打断正在播放的语音。

### Web 接口（`--web` 模式）

- `POST /api/chat`，请求体 `{"message": "你好"}`，返回 `{"reply": "..."}`
- `POST /api/command`，请求体 `{"command": "/jptts"}`
- `GET /api/settings`，返回 `jp_tts`、`tts_mode`、`voice_mode`、`ai_name`

## 5. 输入输出示例

### 示例一：终端文字对话

输入：

```
你 [14:30]: 你好，介绍一下你自己
```

输出（控制台显示 AI 角色名“月见八千代”，并按情绪切换 Live2D 表情、朗读语音）：

```
 月见八千代 [14:30]: 你好呀～我是月见八千代，这里是「月读」。
今天也愿意把时间留给八千代的直播吗？想聊点什么都可以哦～
```

### 示例二：语音输入

开启语音模式（`/v`）后直接说话，静音约 1.5 秒后：

```
🎤 今天天气怎么样
你 [14:32]: 今天天气怎么样
月见八千代 [14:32]: 今天是个适合出门看看的好天气呢，记得带上好心情哦～
```

### 示例三：长期记忆

输入：

```
你 [14:35]: /remember 用户喜欢在晚上写代码
```

输出：

```
已记录：用户喜欢在晚上写代码
```

之后询问相关内容时，AI 会在回复中参考该记忆。

### 示例四：切换语音音色

输入：

```
你 [14:40]: /s
你 [14:40]: /voice Cherry
```

输出：

```
可用 CosyVoice 音色:
  Cherry               芊悦 - 阳光元气小姐姐（女）
  Serena               苏瑶 - 温柔小姐姐（女）
  ...
音色 → 芊悦 - 阳光元气小姐姐（女）
```

### 示例五：Web 聊天接口

请求：

```bash
curl -X POST http://127.0.0.1:5000/api/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"晚上好\"}"
```

响应：

```json
{"reply": "晚上好呀～忙了一天辛苦啦，要不要听八千代唱首歌放松一下？"}
```

## 目录结构

```
DesktopAI/
├─ main.py                  # 程序入口（终端 / --web）
├─ requirements.txt
├─ data/                    # 人格、配置、记忆、历史、音色等数据
│  ├─ personality.json      # 角色人格设定
│  ├─ config.json           # API Key 等配置（本地创建，不提交）
│  ├─ history.json          # 对话历史（运行时生成）
│  ├─ memory.json           # 长期记忆（运行时生成）
│  └─ voice_profiles.json   # 克隆音色档案（运行时生成）
├─ engine/                  # 核心逻辑
│  ├─ conversation.py       # 对话编排：记忆、历史、命令
│  ├─ llm.py                # LLM（DashScope OpenAI 兼容接口）
│  ├─ mood.py               # 关键词情感分析与表情映射
│  ├─ personality.py        # 人格提示词构建
│  ├─ memory.py             # 长期记忆读写
│  ├─ renderer.py           # Live2D 桌面渲染与口型同步
│  ├─ speech.py             # edge-tts 语音合成与播放
│  ├─ voice_clone.py        # DashScope 语音克隆与合成
│  ├─ voice_input.py        # Vosk 语音识别
│  ├─ vtube.py              # VTube Studio WebSocket 联动
│  ├─ server.py             # Flask Web 服务
│  ├─ templates/chat.html   # Web 聊天界面
│  └─ tests/                # pytest 单元测试
├─ live2d/                  # Live2D 模型与表情文件
└─ models/                  # Vosk 语音模型（需自行下载）
```

## 运行测试

```bash
pytest
```

## License

本项目基于 [MIT License](LICENSE) 开源。
