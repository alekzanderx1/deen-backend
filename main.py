from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from api import chat
from api import reference
from api import hikmah
from models.JWTBearer import JWTBearer
from core.auth import jwks
import os

# RUN USING: uvicorn main:app --reload

app = FastAPI()

auth = JWTBearer(jwks)

# Comma-separated list from env, e.g.:
# CORS_ALLOW_ORIGINS="https://deen-frontend.vercel.app,https://staging.example.com"
raw = os.getenv("CORS_ALLOW_ORIGINS", "https://deen-frontend.vercel.app")
allow_origins = [o.strip() for o in raw.split(",") if o.strip()]

# 🔹 CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,  # Allow requests from any origin (change for production)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

# API routers
app.include_router(reference.ref_router,dependencies=[Depends(auth)])
app.include_router(chat.chat_router,dependencies=[Depends(auth)])
app.include_router(hikmah.hikmah_router,dependencies=[Depends(auth)])


@app.get("/",dependencies=[Depends(auth)])
def home():
    return {"message": "Welcome to the Shia Islam Chat API"}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}

