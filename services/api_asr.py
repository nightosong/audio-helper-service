import os
import io
import soundfile
from contextlib import asynccontextmanager
from threading import Lock
from fastapi import FastAPI, APIRouter, Form, UploadFile, BackgroundTasks
from fastapi.responses import StreamingResponse
from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess

router = APIRouter(prefix="/api/asr")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # 检查模型缓存
    asr_model_path = os.getenv("MODELSCOPE_CACHE", ".cache/modelscope/hub")
    if not os.path.exists(asr_model_path):
        os.makedirs(asr_model_path, exist_ok=True)
        from modelscope import snapshot_download

        snapshot_download("iic/SenseVoiceSmall")
        snapshot_download("iic/speech_fsmn_vad_zh-cn-16k-common-pytorch")
    yield


class ASRModelManager:
    _models = {}
    _lock = Lock()

    @classmethod
    def get_model(cls, model_type: str):
        with cls._lock:
            if model_type not in cls._models:
                if model_type == "sensevoice":
                    cls._models[model_type] = AutoModel(
                        model="iic/SenseVoiceSmall",
                        vad_model="fsmn-vad",
                        vad_kwargs={"max_single_segment_time": 30000},
                        device="cuda:0",
                        disable_update=True,
                    )
                elif model_type == "paraformer":
                    cls._models[model_type] = AutoModel(
                        model="paraformer-zh",
                        vad_model="fsmn-vad",
                        punc_model="ct-punc",
                        device="cuda:1",
                        disable_update=True,
                    )
                elif model_type == "streaming":
                    cls._models[model_type] = AutoModel(
                        model="paraformer-zh-streaming",
                        device="cuda:1",
                        disable_update=True,
                    )
                else:
                    raise ValueError(f"Unknown model type: {model_type}")
            return cls._models[model_type]


async def non_streaming_transcribe(
    model: AutoModel, audio_path: str, lang: str = "auto"
):
    res = model.generate(
        input=audio_path,
        cache={},
        language=lang,
        use_itn=True,
        batch_size_s=60,
        merge_vad=True,
        merge_length_s=15,
    )
    return rich_transcription_postprocess(res[0]["text"])


async def streaming_transcribe(model: AutoModel, audio_path: str):
    speech, sample_rate = soundfile.read(audio_path)
    chunk_size = [0, 10, 5]
    chunk_stride = chunk_size[1] * 960
    encoder_chunk_look_back = 4
    decoder_chunk_look_back = 1

    total_chunk_num = int(len(speech) / chunk_stride) + 1
    cache = {}
    results = []
    for i in range(total_chunk_num):
        speech_chunk = speech[i * chunk_stride : (i + 1) * chunk_stride]
        is_final = i == total_chunk_num - 1
        res = model.generate(
            input=speech_chunk,
            cache=cache,
            is_final=is_final,
            chunk_size=chunk_size,
            encoder_chunk_look_back=encoder_chunk_look_back,
            decoder_chunk_look_back=decoder_chunk_look_back,
        )
        results.append(res)
    return "".join([r[0]["text"] for r in results])


@router.post("/transcribe/")
async def transcribe(
    audio_file: UploadFile,
    streaming: bool = Form(False),
    lang: str = "auto",
    background_tasks: BackgroundTasks = None,
):
    audio_data = await audio_file.read()
    audio_input = io.BytesIO(audio_data)

    model_type = "streaming" if streaming else "sensevoice"
    model = ASRModelManager.get_model(model_type)

    if streaming:

        async def stream_results():
            results = await streaming_transcribe(model, audio_input)
            for result in results:
                yield result

        return StreamingResponse(stream_results())
    else:
        result = await non_streaming_transcribe(model, audio_input, lang)
        return {"status": "completed", "text": result}
