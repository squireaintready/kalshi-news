"""
Prediction Pulse - A Kalshi News Article Platform
Main Flask application
"""
import logging
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, flash, request
from markupsafe import Markup

import config
from cache import get_cache
from scheduler import init_scheduler, manual_refresh

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = config.FLASK_SECRET_KEY


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
def inject_now():
    """Make current datetime available in all templates"""
    return {'now': datetime.utcnow()}


# Routes
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
def refresh_articles():
    """Manually trigger article generation"""
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
def health():
    """Health check endpoint"""
    return {'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}


# Error handlers
@app.errorhandler(404)
def not_found(e):
    """404 error handler"""
    return render_template('base.html'), 404


@app.errorhandler(500)
def server_error(e):
    """500 error handler"""
    logger.error(f"Server error: {e}")
    return render_template('base.html'), 500


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
