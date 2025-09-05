from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import chat
from api import reference

# RUN USING: uvicorn main:app --reload

app = FastAPI()

# 🔹 CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow requests from any origin (change for production)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

# API routers
app.include_router(reference.ref_router)
app.include_router(chat.chat_router)


@app.get("/")
def home():
    return {"message": "Welcome to the Shia Islam Chat API"}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}

