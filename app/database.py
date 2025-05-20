from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Confirm DB URL
logger.info(f"Connecting to DB")

# Create SQLAlchemy engine
engine = create_engine(settings.DATABASE_URL, echo=False)

# Confirm DB connection and list tables
try:
    with engine.connect() as conn:
        logger.info("✅ Connected to the database engine.")
        result = conn.execute(text("SELECT 1"))
        logger.info("✅ Test query succeeded: SELECT 1 = %s", result.scalar())

        inspector = inspect(engine)
        table_names = inspector.get_table_names()

        if not table_names:
            logger.warning("⚠️ No tables found! Did you run migrations or load a dump?")
except Exception as e:
    logger.error("❌ Failed to connect or inspect the DB: %s", e)

# ORM setup
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """
    Yields a database session, closing it after use.
    """
    try:
        db = SessionLocal()
        logger.debug("🛠️ Created new DB session.")
        yield db
    finally:
        db.close()
        logger.debug("🔒 Closed DB session.")
