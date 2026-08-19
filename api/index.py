import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from .cards import router as cards_router
from .cron_notify import router as cron_router

app = FastAPI(title="SIM Card Tracker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://web.telegram.org",
        "https://telegram.org",
        "http://localhost:5173",
        "http://localhost:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cards_router)
app.include_router(cron_router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Vercel использует Mangum для запуска FastAPI как Lambda
handler = Mangum(app, lifespan="off")