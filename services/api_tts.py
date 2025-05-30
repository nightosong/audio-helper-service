import os
import json
import numpy as np
from typing import Optional
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import Response, StreamingResponse
from flashtts import AsyncMega3Engine
from flashtts.server.protocol import OpenAISpeechRequest
from flashtts.server.utils.audio_writer import StreamingAudioWriter

router = APIRouter(prefix="/api/tts")
engine: AsyncMega3Engine = None


class TextRequest(BaseModel):
    text: str
    role: Optional[str] = None


class SpeechRequest(OpenAISpeechRequest):
    role: str = Field(..., description="Specifies the voice role")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # 检查模型缓存
    tts_model_path = os.getenv("TTS_MODEL_PATH", ".cache/checkpoints")
    if not os.path.exists(tts_model_path):
        os.makedirs(tts_model_path, exist_ok=True)
        from modelscope import snapshot_download

        snapshot_download("ByteDance/MegaTTS3", local_dir=tts_model_path)
    # 初始化引擎
    global engine
    engine = AsyncMega3Engine(
        model_path=os.getenv("TTS_MODEL_PATH", ".cache/checkpoints"),
        llm_device="cuda",
        llm_batch_size=int(os.getenv("TTS_LLM_BATCH_SIZE", 8)),
        llm_gpu_memory_utilization=float(os.getenv("TTS_GPU_MEMORY_UTILIZATION", 0.6)),
        batch_size=int(os.getenv("TTS_BATCH_SIZE", 1)),
        tokenizer_device="cuda",
        backend="vllm",
        torch_dtype=os.getenv("TTS_TORCH_DTYPE", "auto"),
    )
    # 加载角色
    if os.path.exists("data/mega-roles.json"):
        with open("data/mega-roles.json", "r", encoding="utf-8") as f:
            roles: list = json.load(f)
            for info in roles:
                await engine.add_speaker(
                    name=info["name"],
                    audio=tuple(info["audio"]),
                )
    yield
    if hasattr(engine, "generator"):
        engine.shutdown()


def generate_audio(audio: np.ndarray, writer: StreamingAudioWriter):
    try:
        output = writer.write_chunk(audio, finalize=False)
        final = writer.write_chunk(finalize=True)
        output = output + final
    except Exception as e:
        try:
            writer.close()
        except:
            pass
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while writing the audio: {str(e)}",
        )
    try:
        writer.close()
    except:
        pass
    return output


async def generate_audio_stream(generator, data, writer: StreamingAudioWriter):
    try:
        async for chunk in generator(**data):
            audio = writer.write_chunk(chunk, finalize=False)
            yield audio
        yield writer.write_chunk(finalize=True)
    except Exception as e:
        try:
            writer.close()
        except:
            pass
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred during the streaming audio generation: {str(e)}",
        )
    finally:
        try:
            writer.close()
        except:
            pass


@router.post("/g2p")
async def g2p_api(request: TextRequest):
    result = await engine._generate(
        request.text,
        temperature=0.9,
        top_k=50,
        top_p=0.95,
        repetition_penalty=1.0,
        max_tokens=4096,
    )
    return {
        "ph_pred": result["ph_pred"].squeeze().tolist(),
        "tone_pred": result["tone_pred"].squeeze().tolist(),
    }


@router.post("/generate")
async def api_tts_generate(request: SpeechRequest):
    content_type = {
        "mp3": "audio/mpeg",
        "opus": "audio/opus",
        "aac": "audio/aac",
        "flac": "audio/flac",
        "wav": "audio/wav",
        "pcm": "audio/pcm",
    }.get(request.response_format, f"audio/{request.response_format}")
    audio_writer = StreamingAudioWriter(
        format=request.response_format,
        sample_rate=engine.SAMPLE_RATE,
    )
    api_inputs = {
        "text": request.input,
        "name": request.role,
    }
    if request.stream:
        return StreamingResponse(
            generate_audio_stream(
                engine.speak_stream_async,
                api_inputs,
                audio_writer,
            ),
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename=speech.{request.response_format}",
                "X-Accel-Buffering": "no",
                "Cache-Control": "no-cache",
                "Transfer-Encoding": "chunked",
            },
        )
    else:
        headers = {
            "Content-Disposition": f"attachment; filename=speech.{request.response_format}",
            "Cache-Control": "no-cache",
        }
        try:
            audio_data = await engine.speak_async(**api_inputs)
            if isinstance(audio_data, tuple):
                audio_data = audio_data[0]
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

        output = generate_audio(audio_data, audio_writer)

        return Response(
            content=output,
            media_type=content_type,
            headers=headers,
        )
