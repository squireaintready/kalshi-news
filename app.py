"""
Prediction Pulse - A Kalshi News Article Platform
Main Flask application
"""
import logging
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from markupsafe import Markup

import config
from cache import get_cache
from scheduler import init_scheduler, manual_refresh
from auth import get_user_manager, User

# Initialize Sentry for error monitoring (optional)
if config.SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
        sentry_sdk.init(
            dsn=config.SENTRY_DSN,
            integrations=[FlaskIntegration()],
            traces_sample_rate=0.1,
            send_default_pii=False
        )
    except ImportError:
        pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = config.FLASK_SECRET_KEY

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)


@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login"""
    return get_user_manager().get_user_by_id(user_id)


def admin_required(f):
    """Decorator for admin-only routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


# Template filters
@app.template_filter('format_date')
def format_date_filter(iso_string):
    """Format ISO date string for display"""
    if not iso_string:
        return "Unknown"
    try:
        dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y at %I:%M %p")
    except (ValueError, TypeError):
        return iso_string


@app.template_filter('format_close_time')
def format_close_time_filter(iso_string):
    """Format close time for display"""
    if not iso_string:
        return "Unknown"
    try:
        dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y")
    except (ValueError, TypeError):
        return iso_string


@app.template_filter('format_number')
def format_number_filter(value):
    """Format large numbers with commas"""
    if value is None:
        return "0"
    try:
        return "{:,}".format(int(value))
    except (ValueError, TypeError):
        return str(value)


@app.template_filter('estimate_read_time')
def estimate_read_time_filter(word_count):
    """Estimate reading time in minutes"""
    if not word_count:
        return 2
    # Average reading speed ~200-250 words per minute
    minutes = max(1, round(word_count / 225))
    return minutes


@app.template_filter('nl2br')
def nl2br_filter(text):
    """Convert newlines to <br> tags and wrap paragraphs"""
    if not text:
        return ""
    # Split by double newlines to get paragraphs
    paragraphs = text.split('\n\n')
    # Wrap each paragraph in <p> tags
    html_paragraphs = [f'<p>{p.strip()}</p>' for p in paragraphs if p.strip()]
    return Markup('\n'.join(html_paragraphs))


# Context processor for templates
@app.context_processor
def inject_globals():
    """Make common variables available in all templates"""
    return {
        'now': datetime.utcnow(),
        'current_user': current_user
    }


# Auth Routes
@app.route('/signup', methods=['GET', 'POST'])
@limiter.limit("10 per hour")
def signup():
    """User registration"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Validation
        if not email or not password:
            flash('Email and password are required.', 'error')
            return render_template('signup.html')

        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'error')
            return render_template('signup.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('signup.html')

        # Check if user exists
        user_manager = get_user_manager()
        existing_user = user_manager.get_user_by_email(email)
        if existing_user:
            flash('An account with this email already exists.', 'error')
            return render_template('signup.html')

        # Create user
        user = user_manager.create_user(email, password)
        if user:
            login_user(user)
            user_manager.update_last_login(user.id)
            flash('Account created successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Failed to create account. Please try again.', 'error')

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("20 per hour")
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user_manager = get_user_manager()
        user = user_manager.get_user_by_email(email)

        if user and user.check_password(password):
            login_user(user, remember=True)
            user_manager.update_last_login(user.id)
            flash('Logged in successfully!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'error')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard with personalized articles"""
    cache = get_cache()
    user_manager = get_user_manager()

    # Get user's bets
    user_bets = user_manager.get_user_bets(current_user.id)
    bet_tickers = [bet['market_ticker'] for bet in user_bets]

    # Get all articles
    all_articles = cache.get_all_articles()

    # Filter articles related to user's bets
    my_articles = [
        a for a in all_articles
        if a.get('market_ticker') in bet_tickers
    ]

    return render_template('dashboard.html',
                           user_bets=user_bets,
                           my_articles=my_articles,
                           all_articles=all_articles[:10])


@app.route('/watchlist', methods=['GET', 'POST'])
@login_required
@limiter.limit("30 per hour")
def watchlist():
    """Manage user's market watchlist"""
    user_manager = get_user_manager()
    cache = get_cache()

    if request.method == 'POST':
        action = request.form.get('action')
        ticker = request.form.get('ticker', '').strip().upper()

        if action == 'add' and ticker:
            # Verify ticker exists on Kalshi
            from kalshi_client import get_client
            client = get_client()
            market = client.get_market(ticker)

            if market:
                user_manager.add_user_ticker(current_user.id, ticker)
                flash(f'Added {ticker} to your watchlist!', 'success')

                # Generate article if it doesn't exist
                existing_tickers = {a.get('market_ticker') for a in cache.get_all_articles()}
                if ticker not in existing_tickers:
                    _generate_article_for_ticker(ticker)
            else:
                flash(f'Market ticker "{ticker}" not found on Kalshi.', 'error')

        elif action == 'remove' and ticker:
            user_manager.remove_user_ticker(current_user.id, ticker)
            flash(f'Removed {ticker} from your watchlist.', 'success')

        return redirect(url_for('watchlist'))

    # Get user's current watchlist
    user_bets = user_manager.get_user_bets(current_user.id)

    # Get all articles to show available tickers
    all_articles = cache.get_all_articles()
    available_tickers = list({a.get('market_ticker') for a in all_articles if a.get('market_ticker')})

    return render_template('watchlist.html',
                           user_bets=user_bets,
                           available_tickers=available_tickers)


def _generate_article_for_ticker(ticker: str):
    """Generate an article for a specific ticker"""
    try:
        from kalshi_client import get_client
        from article_generator import get_generator

        client = get_client()
        generator = get_generator()
        cache = get_cache()

        market = client.get_market(ticker)
        if market:
            enriched = client.enrich_market_data(market)
            article = generator.generate_article(enriched)
            if article:
                cache.add_article(article)
                logger.info(f"Generated article for ticker: {ticker}")
    except Exception as e:
        logger.error(f"Failed to generate article for {ticker}: {e}")




# Main Routes
@app.route('/')
def index():
    """Homepage showing latest articles"""
    cache = get_cache()
    articles = cache.get_all_articles()
    return render_template('index.html', articles=articles)


@app.route('/article/<article_id>')
def article_page(article_id):
    """Individual article page"""
    cache = get_cache()
    article = cache.get_article_by_id(article_id)

    if not article:
        flash('Article not found', 'error')
        return redirect(url_for('index'))

    return render_template('article.html', article=article)


@app.route('/about')
def about():
    """About page"""
    return render_template('about.html')


@app.route('/refresh')
@login_required
@admin_required
@limiter.limit("5 per hour")
def refresh_articles():
    """Manually trigger article generation (admin only)"""
    try:
        count = manual_refresh()
        if count > 0:
            flash(f'Successfully generated {count} new article(s)!', 'success')
        else:
            flash('No new articles generated. Check logs for details.', 'warning')
    except Exception as e:
        logger.error(f"Refresh failed: {e}")
        flash(f'Error generating articles: {str(e)}', 'error')

    return redirect(url_for('index'))


@app.route('/health')
@limiter.exempt
def health():
    """Health check endpoint"""
    return {'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}


# API endpoints for future mobile app
@app.route('/api/articles')
@limiter.limit("100 per hour")
def api_articles():
    """API: Get all articles"""
    cache = get_cache()
    articles = cache.get_all_articles()
    return jsonify({"articles": articles})


@app.route('/api/articles/<article_id>')
@limiter.limit("100 per hour")
def api_article(article_id):
    """API: Get single article"""
    cache = get_cache()
    article = cache.get_article_by_id(article_id)
    if article:
        return jsonify({"article": article})
    return jsonify({"error": "Article not found"}), 404


@app.route('/api/search-markets')
@login_required
@limiter.limit("30 per hour")
def api_search_markets():
    """API: Search Kalshi markets by keyword"""
    query = request.args.get('q', '').strip()
    if not query or len(query) < 2:
        return jsonify({"markets": [], "error": "Query too short"})

    from kalshi_client import get_client
    client = get_client()
    markets = client.search_markets(query, limit=15)

    # Simplify response
    results = []
    for m in markets:
        results.append({
            "ticker": m.get("ticker"),
            "title": m.get("title"),
            "event_title": m.get("_event_title", ""),
            "probability": m.get("yes_bid") or m.get("last_price", 50),
            "volume": m.get("volume", 0)
        })

    return jsonify({"markets": results})


# Error handlers
@app.errorhandler(404)
def not_found(e):
    """404 error handler"""
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(e):
    """500 error handler"""
    logger.error(f"Server error: {e}")
    return render_template('500.html'), 500


@app.errorhandler(429)
def ratelimit_handler(e):
    """Rate limit exceeded handler"""
    return jsonify({"error": "Rate limit exceeded. Please try again later."}), 429


# Application startup
def create_app():
    """Application factory"""
    # Initialize scheduler for automatic refresh
    init_scheduler()
    return app


# For gunicorn: `gunicorn app:application`
application = create_app()


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=config.FLASK_DEBUG
    )
