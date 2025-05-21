# Audio Helper Server

该项目是一个音频处理服务，提供语音识别（ASR）和文本转语音（TTS）功能。以下是项目的详细介绍：

## 项目结构
```
audio-helper-server/
  .cache/
  .dockerignore
  .env
  .gitignore
  .store/
  .venv/
  Dockerfile
  README.md
  __pycache__/
  docker-compose.yml
  logs/
  main.py
  requirements.txt
  services/
    api_asr.py
    api_tts.py
```

## 功能模块
### 语音识别（ASR）
在 `services/api_asr.py` 中实现，提供 `/api/transcribe/` 接口，支持流式和非流式的语音识别。支持的模型类型包括 `sensevoice`、`paraformer` 和 `streaming`。

### 文本转语音（TTS）
在 `services/api_tts.py` 中实现，提供 `/g2p` 和 `/tts` 接口。`/g2p` 用于将文本转换为音素和声调，`/tts` 用于将文本转换为语音，可以选择流式输出。

## 启动服务
在 `main.py` 中定义了 FastAPI 应用，整合了 ASR 和 TTS 的路由。使用以下命令启动服务：
```bash
gunicorn main:app -k uvicorn.workers.UvicornWorker --workers 4 --bind 0.0.0.0:7500
```
或者使用 Docker 启动：
```bash
docker compose up -d --build
```

## API 文档
### 语音识别接口
- **URL**: `/api/transcribe/`
- **方法**: `POST`
- **参数**: 
  - `audio_file`: 上传的音频文件
  - `streaming`: 是否使用流式识别，默认为 `False`
  - `lang`: 语言类型，默认为 `auto`

### 文本转音素接口
- **URL**: `/g2p`
- **方法**: `POST`
- **参数**: 
  - `text`: 输入的文本
  - `role`: 可选的语音角色

### 文本转语音接口
- **URL**: `/tts`
- **方法**: `POST`
- **参数**: 
  - `input`: 输入的文本
  - `role`: 语音角色(目前支持："男"、"女")
  - `response_format`: 输出的音频格式（mp3, wav...）
  - `stream`: 是否使用流式输出（默认为true,目前必须使用false）