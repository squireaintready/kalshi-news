# Prediction Pulse

A news article platform that automatically generates engaging articles based on trending Kalshi prediction markets.

## Features

- **Automatic Market Tracking**: Fetches trending/active markets from Kalshi API
- **AI-Powered Article Generation**: Creates conversational, human-sounding articles using Claude or GPT-4
- **Unique Writing Style**: Articles written in a casual, curious tone with subtle Joe Rogan-esque energy
- **Web Interface**: Clean Flask-based UI to browse and read generated articles
- **Scheduled Refresh**: Automatically generates new articles on a configurable interval
- **Flexible Caching**: Supports both file-based and Redis caching

## Quick Start

### 1. Clone and Setup

```bash
cd kalshi-news
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the project root:

```bash
# Kalshi API (optional - public data available without auth)
KALSHI_EMAIL=your_email@example.com
KALSHI_PASSWORD=your_kalshi_password

# LLM Provider (choose one)
LLM_PROVIDER=anthropic  # or "openai"
ANTHROPIC_API_KEY=your_anthropic_api_key
# OPENAI_API_KEY=your_openai_api_key

# Flask
FLASK_SECRET_KEY=change-this-to-something-random
FLASK_DEBUG=false

# Cache (optional)
CACHE_TYPE=file  # or "redis"
# REDIS_URL=redis://localhost:6379/0

# Scheduler
ARTICLE_REFRESH_INTERVAL=60  # minutes
MAX_MARKETS_TO_FETCH=10
MAX_ARTICLES_TO_GENERATE=5
```

### 3. Run the Application

```bash
python app.py
```

Visit `http://localhost:5000` in your browser.

## Project Structure

```
kalshi-news/
├── app.py                 # Flask application
├── kalshi_client.py       # Kalshi API client
├── article_generator.py   # LLM-based article generation
├── cache.py               # Caching layer (file/Redis)
├── scheduler.py           # APScheduler for auto-refresh
├── config.py              # Configuration management
├── requirements.txt       # Python dependencies
├── templates/             # Jinja2 HTML templates
│   ├── base.html
│   ├── index.html
│   ├── article.html
│   └── about.html
├── static/
│   └── style.css
└── cache/                 # File-based cache storage
```

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `anthropic` | LLM to use (`anthropic` or `openai`) |
| `CACHE_TYPE` | `file` | Cache backend (`file` or `redis`) |
| `CACHE_TTL` | `3600` | Cache time-to-live in seconds |
| `ARTICLE_REFRESH_INTERVAL` | `60` | Minutes between auto-refresh |
| `MAX_MARKETS_TO_FETCH` | `10` | Markets to fetch per refresh |
| `MAX_ARTICLES_TO_GENERATE` | `5` | Max articles per refresh |

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Homepage with article list |
| `GET /article/<id>` | Individual article page |
| `GET /about` | About page |
| `GET /refresh` | Manually trigger article generation |
| `GET /health` | Health check endpoint |

## Production Deployment

For production, use Gunicorn:

```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:create_app()
```

With Redis caching:

```bash
CACHE_TYPE=redis REDIS_URL=redis://localhost:6379/0 gunicorn -w 4 app:create_app()
```

## How It Works

1. **Market Scoring**: The system fetches open markets from Kalshi and scores them by "interestingness" based on:
   - Trading volume (more activity = more interest)
   - Probability range (20-80% is more uncertain/interesting)
   - Open interest
   - Time until close

2. **Article Generation**: Top-scoring markets are sent to an LLM with a custom prompt that:
   - Creates clickbait-y but believable titles
   - Writes in a casual, conversational style
   - Analyzes whether odds seem right
   - Discusses potential catalysts and upcoming events
   - Keeps articles between 400-650 words

3. **Caching & Display**: Generated articles are cached and displayed on the web interface with a clean, modern dark theme.

## Customization

### Changing the Writing Style

Edit the prompts in `article_generator.py`:
- `ARTICLE_SYSTEM_PROMPT`: Controls the overall voice and style
- `ARTICLE_USER_PROMPT_TEMPLATE`: Structures what the article should cover

### Adjusting Market Selection

Modify `_calculate_market_score()` in `kalshi_client.py` to change how markets are ranked.

## Troubleshooting

**No articles appearing?**
- Check that your LLM API key is valid
- Click "Refresh Articles" to manually trigger generation
- Check the console logs for errors

**Kalshi API errors?**
- The public API works without authentication for basic data
- For full access, add your Kalshi credentials

**Redis connection issues?**
- Ensure Redis is running: `redis-server`
- Check `REDIS_URL` format: `redis://localhost:6379/0`

## License

MIT
