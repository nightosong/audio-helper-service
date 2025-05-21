# Audio Helper Server

该项目是一个音频处理服务，提供语音识别（ASR）和文本转语音（TTS）功能。以下是项目的详细介绍：

## 项目结构
```
audio-helper-server/
  .cache/       # asr模型缓存目录
  .env
  checkpoints/  # tts模型权重
  logs/         # 日志目录
  services/     # 服务模块
    api_asr.py  # ASR 服务
    api_tts.py  # TTS 服务
  main.py       # 主应用入口
```

## 功能模块
### 语音识别（ASR）
在 `services/api_asr.py` 中实现，提供 `/api/transcribe/` 接口，支持流式和非流式的语音识别。

### 文本转语音（TTS）
在 `services/api_tts.py` 中实现，提供 `/api/tts/generate` 接口，用于将文本转换为语音，可以选择流式输出。

## 启动服务
在 `main.py` 中定义了 FastAPI 应用，整合了 ASR 和 TTS 的路由。使用以下命令启动服务：
```bash
virtualenv .venv
source .venv/bin/activat3
pip3 install -r requirements.txt
# uvicorn 启动服务
uvicorn main:app --host 0.0.0.0 --port 7500 --reload
# gunicorn 启动服务
gunicorn main:app -k uvicorn.workers.UvicornWorker --workers 4 --bind 0.0.0.0:7500
```
或者使用 Docker 启动：
```bash
docker compose up -d --build
```

## API 文档
### 语音识别接口
- **URL**: `/api/asr/transcribe`
- **方法**: `POST`
- **参数**: 
  - `audio_file`: 上传的音频文件
  - `streaming`: 是否使用流式识别，默认为 `False`
  - `lang`: 语言类型，默认为 `auto`
  ```
    def test_asr():
        asr_url = "http://localhost:7500/api/asr/transcribe"
        with open(audio_file, "rb") as f:
            files = {"audio_file": f}
        response = requests.post(asr_url, files=files, timeout=600)
        response.raise_for_status()
        print(f"text: {response.json().get('text')}")

  ```

### 文本转语音接口
- **URL**: `/api/tts/generate`
- **方法**: `POST`
- **参数**: 
  - `input`: 输入的文本
  - `role`: 语音角色(目前支持："男"、"女")
  - `response_format`: 输出的音频格式（mp3, wav...）
  - `stream`: 是否使用流式输出（默认为true，需设置为false，目前不支持流式）
  ```
    def test_tts():
        tts_url = "http://localhost:7500/api/tts/generate"
        json_body = {
            "input": "你好，我是一个测试文本。",
            "role": "女",
            "stream": False,
            "response_format": "wav",
        }
        response = requests.post(
            tts_url,
            json=json_body,
            timeout=300,
        )
        response.raise_for_status()
        with open("output.wav", "wb") as f:
            f.write(response.content)
  ```