import time
import sys
import logging
import click
from flask.cli import with_appcontext
from flask import current_app
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from app.extensions import db
from app.services.chat_service import ChatService
from app.utils.capabilities import check_model_capabilities

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def wait_for_db(max_retries=30, interval=2):
    """Wait for the database to become available."""
    logger.info("Checking database connection...")
    
    for i in range(max_retries):
        try:
            db.session.execute(text('SELECT 1'))
            logger.info(" [OK] Database connection established.")
            return True
        except OperationalError:
            logger.info(f" [..] Waiting for database... ({i+1}/{max_retries})")
            time.sleep(interval)
        except Exception as e:
            logger.error(f" [!!] Unexpected error connecting to database: {e}")
            return False
                
    logger.error(" [!!] Database connection timed out.")
    return False

def init_database():
    """Initialize the database tables."""
    logger.info("Initializing database schema...")
    try:
        # Check if tables exist (simple check)
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        
        if not tables:
            logger.info(" [..] No tables found. Creating tables...")
            db.create_all()
            logger.info(" [OK] Database tables created successfully.")
        else:
            logger.info(f" [OK] Database already initialized. Found tables: {', '.join(tables)}")
            
    except Exception as e:
        logger.error(f" [!!] Failed to initialize database: {e}")
        sys.exit(1)

def check_model_api():
    """Check connection to the AI Model API."""
    logger.info("Checking AI Model API connection...")
    try:
        models = ChatService.get_models()
        if models:
            logger.info(f" [OK] Connected to AI API. Found {len(models)} models.")
        else:
            logger.warning(" [?!] Connected to API but no models returned.")
    except Exception as e:
        logger.warning(f" [!!] Failed to connect to AI Model API: {e}")
        logger.warning("      Application will start, but chat functionality may be impaired.")

@click.command('init-db')
@with_appcontext
def init_db_command():
    """Initialize the database and check connections."""
    print("\n" + "="*50)
    print(" ChatAI System Startup Checks")
    print("="*50 + "\n")
    
    # 1. Wait for DB
    if not wait_for_db():
        sys.exit(1)
        
    # 2. Initialize DB
    init_database()
    
    # 3. Check API
    check_model_api()
    
    print("\n" + "="*50)
    print(" System Ready")
    print("="*50 + "\n")

@click.command('check-capabilities')
@with_appcontext
def check_capabilities_command():
    """Check and print detailed model capabilities."""
    check_model_capabilities()
