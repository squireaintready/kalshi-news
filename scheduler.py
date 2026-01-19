"""
Scheduler for automatic article refresh using APScheduler
"""
import logging
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit

import config
from kalshi_client import get_client
from article_generator import get_generator
from cache import get_cache

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = BackgroundScheduler()


def generate_articles_job():
    """
    Job to fetch trending markets and generate articles
    Called on schedule by APScheduler
    """
    logger.info("Starting scheduled article generation...")

    try:
        kalshi = get_client()
        generator = get_generator()
        cache = get_cache()

        # Fetch trending markets
        trending_markets = kalshi.get_trending_markets(limit=config.MAX_MARKETS_TO_FETCH)
        logger.info(f"Found {len(trending_markets)} trending markets")

        if not trending_markets:
            logger.warning("No trending markets found, skipping article generation")
            return

        # Get existing article market tickers to avoid duplicates
        existing_articles = cache.get_all_articles()
        existing_analysis_tickers = {
            a.get("market_ticker") for a in existing_articles
            if a.get("article_type") == "analysis"
        }

        articles_generated = 0
        for market in trending_markets:
            if articles_generated >= config.MAX_ARTICLES_TO_GENERATE:
                break

            ticker = market.get("ticker")

            # Skip if we already have an analysis article for this market
            if ticker in existing_analysis_tickers:
                logger.debug(f"Skipping {ticker}, already have article")
                continue

            try:
                # Enrich market data
                enriched_market = kalshi.enrich_market_data(market)

                # Generate article
                article = generator.generate_article(enriched_market)

                if article:
                    # Save to cache
                    cache.add_article(article)
                    articles_generated += 1
                    logger.info(f"Generated article for {ticker}: {article['title'][:50]}...")

            except Exception as e:
                logger.error(f"Failed to generate article for {ticker}: {e}")
                continue

        logger.info(f"Article generation complete. Generated {articles_generated} new articles.")

    except Exception as e:
        logger.error(f"Article generation job failed: {e}")


def check_resolutions_job():
    """
    Job to check for resolved markets and generate results articles
    Also marks existing articles as expired
    """
    logger.info("Checking for resolved markets...")

    try:
        kalshi = get_client()
        generator = get_generator()
        cache = get_cache()

        articles = cache.get_all_articles()
        if not articles:
            return

        results_generated = 0
        articles_updated = False

        for article in articles:
            # Skip if already a results article or already marked resolved
            if article.get("article_type") == "results":
                continue
            if article.get("status") == "resolved":
                continue

            ticker = article.get("market_ticker")
            if not ticker:
                continue

            # Check if the market close time has passed
            close_time_str = article.get("close_time")
            if close_time_str:
                try:
                    close_time = datetime.fromisoformat(close_time_str.replace("Z", "+00:00"))
                    now = datetime.now(timezone.utc)

                    if now > close_time:
                        # Market has expired - mark the article
                        article["status"] = "resolved"
                        articles_updated = True
                        logger.info(f"Marked article as resolved: {ticker}")

                        # Try to fetch resolution data and generate results article
                        if results_generated < config.MAX_RESULTS_ARTICLES_TO_GENERATE:
                            try:
                                market_data = kalshi.get_market(ticker)
                                if market_data:
                                    # Check if market has actually resolved
                                    result = market_data.get("result")
                                    if result:
                                        market_data["close_time_readable"] = close_time.strftime("%B %d, %Y")
                                        results_article = generator.generate_results_article(
                                            market_data,
                                            original_article=article
                                        )
                                        if results_article:
                                            cache.add_article(results_article)
                                            article["results_article_id"] = results_article["id"]
                                            results_generated += 1
                                            logger.info(f"Generated results article for {ticker}")
                            except Exception as e:
                                logger.error(f"Failed to generate results for {ticker}: {e}")

                except (ValueError, TypeError) as e:
                    logger.debug(f"Could not parse close time for {ticker}: {e}")

        # Save updated articles if any were modified
        if articles_updated:
            cache.save_articles(articles)

        logger.info(f"Resolution check complete. Generated {results_generated} results articles.")

    except Exception as e:
        logger.error(f"Resolution check job failed: {e}")


def manual_refresh():
    """
    Manually trigger article generation
    Returns the number of articles generated
    """
    logger.info("Manual article refresh triggered")

    try:
        kalshi = get_client()
        generator = get_generator()
        cache = get_cache()

        trending_markets = kalshi.get_trending_markets(limit=config.MAX_MARKETS_TO_FETCH)

        if not trending_markets:
            logger.warning("No trending markets found")
            return 0

        articles_generated = 0
        for market in trending_markets[:config.MAX_ARTICLES_TO_GENERATE]:
            try:
                enriched_market = kalshi.enrich_market_data(market)
                article = generator.generate_article(enriched_market)

                if article:
                    cache.add_article(article)
                    articles_generated += 1
                    logger.info(f"Generated: {article['title'][:50]}...")

            except Exception as e:
                logger.error(f"Failed to generate article for {market.get('ticker')}: {e}")
                continue

        return articles_generated

    except Exception as e:
        logger.error(f"Manual refresh failed: {e}")
        return 0


def init_scheduler():
    """Initialize and start the background scheduler"""
    if scheduler.running:
        logger.info("Scheduler already running")
        return

    # Add the article generation job (runs every 20 min by default)
    scheduler.add_job(
        func=generate_articles_job,
        trigger=IntervalTrigger(minutes=config.ARTICLE_REFRESH_INTERVAL_MINUTES),
        id="generate_articles",
        name="Generate articles from trending markets",
        replace_existing=True
    )

    # Add the resolution check job (runs every 10 min by default)
    scheduler.add_job(
        func=check_resolutions_job,
        trigger=IntervalTrigger(minutes=config.RESOLUTION_CHECK_INTERVAL_MINUTES),
        id="check_resolutions",
        name="Check for resolved markets and generate results",
        replace_existing=True
    )

    # Start the scheduler
    scheduler.start()
    logger.info(
        f"Scheduler started. "
        f"New articles every {config.ARTICLE_REFRESH_INTERVAL_MINUTES} min, "
        f"resolution checks every {config.RESOLUTION_CHECK_INTERVAL_MINUTES} min."
    )

    # Ensure scheduler shuts down properly on exit
    atexit.register(lambda: scheduler.shutdown(wait=False))


def shutdown_scheduler():
    """Shutdown the scheduler gracefully"""
    if scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("Scheduler shutdown complete")
