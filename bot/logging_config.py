import logging
import sys
from logging.handlers import RotatingFileHandler

def setup_logger(name: str = "trading_bot", log_file: str = "trading_bot.log") -> logging.Logger:
    """
    Sets up a logger that outputs to both a rotating file and standard output.
    """
    logger = logging.getLogger(name)
    
    # Avoid adding multiple handlers if setup is called multiple times
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Formatter for log messages
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # File Handler (Rotating log file max 5MB, keep 2 backups)
        file_handler = RotatingFileHandler(
            log_file, maxBytes=5 * 1024 * 1024, backupCount=2
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        
        # Stream Handler (Standard output)
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        stream_handler.setLevel(logging.WARNING) # Only log warnings/errors to console normally to keep it clean, CLI handles info
        
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)
        
    return logger

logger = setup_logger()
