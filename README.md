# Groq Recording & Replay Proxy

FastAPI proxy for recording Groq/OpenAI-compatible chat completion requests into SQLite and replaying them later without consuming Groq credits.

## Quick Start

```powershell
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env and set GROQ_API_KEY.
python app/main.py
```

Linux/macOS:

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env and set GROQ_API_KEY.
python app/main.py
```

You can also run:

```bash
uvicorn app.main:app --reload
```

Point your application at:

```text
http://127.0.0.1:8000/openai/v1
```

## Modes

`PROXY_MODE=record` forwards chat completion calls to Groq, saves the request/response pair, and returns Groq's response.

`PROXY_MODE=replay` hashes each incoming request, looks up a saved fixture, and returns it. Missing fixtures return HTTP 404 with:

```json
{"error": "fixture_not_found"}
```

`PROXY_MODE=regular` hashes each incoming request, returns a saved fixture when one exists, and otherwise forwards the request to Groq, saves the response, and returns it.

## Configuration

Create `.env` from `.env.example`, then adjust values as needed. The app loads `.env` automatically.

```text
PROXY_MODE=replay
GROQ_API_KEY=your_groq_api_key_here
GROQ_BASE_URL=https://api.groq.com/openai/v1
SQLITE_PATH=data/fixtures.db
CACHE_ENABLED=true
LOG_LEVEL=INFO
PROVIDER=groq
```

When `GROQ_API_KEY` is configured, the proxy uses it for forwarded Groq requests. Incoming `Authorization` headers are only used when `GROQ_API_KEY` is not set.

## API

Implemented proxy endpoints:

```http
POST /openai/v1/chat/completions
GET /openai/v1/models
```

Admin endpoints:

```http
GET /admin/stats
GET /admin/fixture/{request_hash}
GET /admin/fixtures?model=llama-test&date=2026-06-15&limit=50&offset=0
```

## Fixtures

Fixtures are stored in SQLite at `data/fixtures.db` using:

```sql
CREATE TABLE llm_fixtures (
    id INTEGER PRIMARY KEY,
    request_hash TEXT UNIQUE,
    provider TEXT,
    model TEXT,
    created_at TEXT,
    request_json TEXT,
    response_json TEXT
);
```

Export:

```bash
python export_fixtures.py
```

Import:

```bash
python import_fixtures.py
```

Clear all fixtures directly from SQLite:

```bash
python clear_fixtures.py
```

Clear all fixtures and the in-memory cache on a running proxy:

```bash
python clear_fixtures.py --proxy-url http://127.0.0.1:8000
```

Exported files are written to `fixtures/{request_hash}.json`.

## Architecture

The API layer accepts OpenAI-compatible requests and delegates to `FixtureService`. In record mode, the service forwards through the `LLMProvider` abstraction, stores the response through `FixtureRepository`, updates the in-memory hash cache, and returns the provider response. In replay mode, the service checks the startup-loaded hash cache for O(1) existence, loads the fixture from SQLite, and returns the saved response. In regular mode, the service tries replay first and falls back to record mode on a cache miss.

Provider support is isolated behind `LLMProvider`, so OpenAI, Anthropic, Gemini, or other providers can be added without changing the API routes.

## Testing

```bash
pytest --cov=app --cov=export_fixtures --cov=import_fixtures
```

The suite covers record mode, replay mode, regular mode, fixture misses, deterministic hashing, concurrency, SQLite persistence, export, import, and admin APIs.
