# Troubleshooting Guide

## CORS Error: "No 'Access-Control-Allow-Origin' header"

### Problem

Frontend getting CORS error when calling API:

```
Access to fetch at 'http://127.0.0.1:8080/user-progress' from origin 'http://localhost:5173'
has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present
```

### Root Causes

1. **CORS Configuration**: `main.py` only allowed `https://deen-frontend.vercel.app` by default
2. **Port Confusion**: Frontend calling port 8080, backend running on port 8000
3. **Caddy Not Running**: Caddy reverse proxy (port 8080) not active in development

### Solutions

#### ✅ Solution 1: Fixed CORS Configuration (IMPLEMENTED)

Updated `main.py` to automatically allow localhost origins in development:

```python
# In development, allow localhost origins
if os.getenv("ENV", "development") == "development":
    allow_origins.extend([
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ])
```

#### ✅ Solution 2: Restart Backend

**Restart your FastAPI server** for CORS changes to take effect:

```bash
# Stop current server (Ctrl+C)
# Then restart:
uvicorn main:app --reload
```

#### ✅ Solution 3: Update Frontend API Base URL

Your frontend should call port **8000** (FastAPI) directly in development, not 8080 (Caddy):

**Frontend `.env` or config:**

```javascript
// Development
const API_BASE_URL = "http://127.0.0.1:8000";

// Production
const API_BASE_URL = "https://deen-fastapi.duckdns.org";
```

Or use environment detection:

```javascript
const API_BASE_URL =
  process.env.NODE_ENV === "production"
    ? "https://deen-fastapi.duckdns.org"
    : "http://127.0.0.1:8000";
```

### Alternative: Run Caddy Locally (Optional)

If you want to use port 8080 in development:

1. **Update Caddyfile for local development:**

```caddyfile
# Add local config
:8080 {
    encode gzip
    reverse_proxy localhost:8000
}
```

2. **Run Caddy:**

```bash
cd caddy
caddy run --config Caddyfile
```

3. **Update main.py CORS to allow via Caddy:**

```python
allow_origins.extend([
    "http://localhost:8080",
    "http://127.0.0.1:8080",
])
```

## 500 Internal Server Error

### Check Server Logs

The 500 error usually shows in terminal. Look for:

```
===== SERVER EXCEPTION =====
[Full traceback here]
============================
```

### Common Causes

1. **Validation Error**: Pydantic rejecting payload

   - Check `user_id` is string, not int
   - Check all required fields present

2. **Database Connection**:

   ```bash
   # Test DB connection
   curl http://127.0.0.1:8000/_debug/db
   ```

3. **Missing Fields**: Check payload matches schema
   ```json
   {
     "user_id": "username_string", // ✅ string
     "lesson_id": 1 // ✅ required
   }
   ```

### Enable Detailed Error Responses

The exception middleware already prints full tracebacks to console. Check terminal where `uvicorn` is running.

## Quick Checklist

- [ ] Restart FastAPI server after CORS changes
- [ ] Frontend calling `http://127.0.0.1:8000` (not 8080)
- [ ] `user_id` sent as **string** in POST body
- [ ] Check terminal for exception traces
- [ ] Test with curl:
  ```bash
  curl -X POST http://127.0.0.1:8000/user-progress \
    -H "Content-Type: application/json" \
    -d '{"user_id": "test_user", "lesson_id": 1}'
  ```

## Environment Variables

Set in `.env` file:

```bash
ENV=development                           # Enables localhost CORS
CORS_ALLOW_ORIGINS=https://your-prod-frontend.com,http://localhost:5173
DB_HOST=your-db-host
DB_PORT=5432
# ... other DB vars
```

## Still Having Issues?

1. Check full server logs in terminal
2. Test API with curl/Postman to isolate frontend vs backend
3. Verify migration ran: `alembic current`
4. Check user_id type:
   ```sql
   \d user_progress
   ```
