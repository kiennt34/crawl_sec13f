"""
Configuration management for SEC 13F crawler.
Uses environment variables with sensible defaults.
"""
import logging
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
load_dotenv()

class Config:
    """Configuration class for SEC 13F crawler."""
    
    # Database configuration
    DB_HOST: str = os.getenv("SEC13F_DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("SEC13F_DB_PORT", "3306"))
    DB_USER: str = os.getenv("SEC13F_DB_USER", "secuser")
    DB_PASSWORD: str = os.getenv("SEC13F_DB_PASSWORD", "")
    DB_NAME: str = os.getenv("SEC13F_DB_NAME", "sec13f")
    
    # Data directories
    BASE_DATA_DIR: Path = Path(os.getenv("SEC13F_DATA_DIR", "/mnt/Data/App/HybridFinancial/sec13f"))
    ZIPS_DIR: Path = BASE_DATA_DIR / "zips"
    STAGING_DIR: Path = BASE_DATA_DIR / "staging"
    EXTRACTED_DIR: Path = BASE_DATA_DIR / "extracted"
    
    # SEC configuration
    CRAWL_URL: str = os.getenv(
        "SEC13F_LINK",
        "https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets"
    )
    USER_AGENT: str = os.getenv(
        "SEC13F_USER_AGENT",
        "HybridFinancial 13F Loader (contact@example.com)"
    )
    # Print information
    print(f"SEC_INDEX_URL: {CRAWL_URL}")
    print(f"USER_AGENT: {USER_AGENT}")
    print(f"DB_HOST: {DB_HOST}")
    print(f"DB_PORT: {DB_PORT}")
    print(f"DB_USER: {DB_USER}")
    print(f"DB_PASSWORD Exists: {'Yes' if DB_PASSWORD else 'No'}")
    print(f"DB_NAME: {DB_NAME}")
    print(f"BASE_DATA_DIR: {BASE_DATA_DIR}")
    print(f"ZIPS_DIR: {ZIPS_DIR}")
    print(f"STAGING_DIR: {STAGING_DIR}")
    print(f"EXTRACTED_DIR: {EXTRACTED_DIR}")
    
    # Crawler settings
    REQUEST_TIMEOUT: int = 30
    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 1.0
    
    # Logging settings
    if os.getenv("LOG_LEVEL") is not None:
        if os.getenv("LOG_LEVEL").isdigit():
            LOG_LEVEL: int = int(os.getenv("LOG_LEVEL"))
        else:
            if os.getenv("LOG_LEVEL").upper() == "DEBUG":
                LOG_LEVEL: int = logging.DEBUG
            elif os.getenv("LOG_LEVEL").upper() == "INFO": 
                LOG_LEVEL: int = logging.INFO
    else:
        LOG_LEVEL: int = logging.INFO
    
    @classmethod
    def ensure_directories(cls) -> None:
        """Create necessary directories if they don't exist."""
        cls.ZIPS_DIR.mkdir(parents=True, exist_ok=True)
        cls.STAGING_DIR.mkdir(parents=True, exist_ok=True)
        cls.EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def get_db_connection_string(cls) -> dict:
        """Get database connection parameters as a dictionary."""
        return {
            "host": cls.DB_HOST,
            "port": cls.DB_PORT,
            "user": cls.DB_USER,
            "password": cls.DB_PASSWORD,
            "database": cls.DB_NAME,
            "local_infile": 1,      # important
            "charset": "utf8mb4",
            "autocommit": False,
            "connect_timeout": 60,      # 60 seconds to establish connection
            "read_timeout": 3600,       # 1 hour for large LOAD DATA operations
            "write_timeout": 3600       # 1 hour for large LOAD DATA operations
        }

    @classmethod
    def reinit_datadirs(cls, base_dir: Optional[Path] = None) -> None:
        """Reinitialize data directories, optionally with a new base directory."""
        if base_dir:
            cls.BASE_DATA_DIR = base_dir
            cls.ZIPS_DIR = cls.BASE_DATA_DIR / "zips"
            cls.STAGING_DIR = cls.BASE_DATA_DIR / "staging"
            cls.EXTRACTED_DIR = cls.BASE_DATA_DIR / "extracted"
        cls.ensure_directories()
        print(f"Reinitialized data directories with base: {cls.BASE_DATA_DIR}")