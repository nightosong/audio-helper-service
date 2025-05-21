import argparse
import multiprocessing as mp
from contextlib import asynccontextmanager, AsyncExitStack
from dotenv import load_dotenv

load_dotenv()
import uvicorn
from fastapi import FastAPI
from services.api_asr import router as asr_router, lifespan as asr_lifespan
from services.api_tts import router as tts_router, lifespan as tts_lifespan


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncExitStack() as stack:
        await stack.enter_async_context(asr_lifespan(app))
        await stack.enter_async_context(tts_lifespan(app))
        yield


app = FastAPI(lifespan=lifespan)
app.include_router(asr_router)
app.include_router(tts_router)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the FastAPI application.")
    parser.add_argument(
        "--host", default="0.0.0.0", help="Host to run the application on."
    )
    parser.add_argument(
        "--port", type=int, default=7500, help="Port to run the application on."
    )
    args = parser.parse_args()
    mp.set_start_method("spawn", force=True)
    uvicorn.run(app, host=args.host, port=args.port)
