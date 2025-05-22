import os
import argparse
import multiprocessing as mp
from typing import Dict, Tuple, Callable
from contextlib import asynccontextmanager, AsyncExitStack
from dotenv import load_dotenv

load_dotenv()
import uvicorn
from fastapi import FastAPI
from modules.nacosdk import nacos_register
from services.api_asr import router as asr_router, lifespan as asr_lifespan
from services.api_tts import router as tts_router, lifespan as tts_lifespan

mp.set_start_method("spawn", force=True)

ModuleMap: Dict[str, Tuple[Callable, Callable]] = {
    "asr": (asr_router, asr_lifespan),
    "tts": (tts_router, tts_lifespan),
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    nacos_register()
    async with AsyncExitStack() as stack:
        for key in os.getenv("API_SUPPORT_LIST", "").split(","):
            if key in ModuleMap:
                router, lifespan = ModuleMap[key]
                app.include_router(router)
                await stack.enter_async_context(lifespan(app))
        yield


app = FastAPI(lifespan=lifespan)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the FastAPI application.")
    parser.add_argument(
        "--server", default="audio-helper-server", help="Service name to register."
    )
    parser.add_argument(
        "--host", default="0.0.0.0", help="Host to run the application on."
    )
    parser.add_argument(
        "--port", type=int, default=7500, help="Port to run the application on."
    )
    args = parser.parse_args()
    nacos_register(args.server, args.host, args.port)
    uvicorn.run(app, host=args.host, port=args.port)
