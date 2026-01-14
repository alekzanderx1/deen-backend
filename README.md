# 🕌 Deen - Backend

This is the backend service for the Deen AI platform. It is built using **FastAPI** and provides API endpoints for semantic search and AI-powered answers based on Islamic sources.

---

## 🛠️ Setup Instructions

### 1. Create a Virtual Environment (if not already created)

```bash
python3 -m venv venv
```

### 2. Activate the Virtual Environment

```bash
source venv/bin/activate  # On macOS/Linux
venv\Scripts\activate      # On Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 🚀 Running the Server (Development Mode)

Make sure your virtual environment is activated, then run:

```bash
uvicorn main:app --reload
```

The server will start at:  
📍 `http://127.0.0.1:8000`

You can test the API and view docs at:  
📘 `http://127.0.0.1:8000/docs` (Swagger UI)

---

## 📦 Notes

- Make sure you have a valid `.env` file for any API keys (e.g., OpenAI, Pinecone).

---

### Useful commands to manage EC2 deployment

cd ~/deen-backend
git pull

#### Stop and remove everything

docker compose down

#### Optional but recommended on small instances

docker system prune -af

##### Rebuild with NO CACHE so pip doesn’t reuse anything

docker compose build --no-cache

##### Start up

docker compose up -d

#### logs checks:

docker logs --tail=200 deen-caddy
docker logs --tail=200 deen-backend
