import logging
import os
import sys
import configparser
from logging.handlers import RotatingFileHandler

# --- Determine base path --- START
if getattr(sys, 'frozen', False):
    # If the application is run as a bundle (frozen), use the executable directory
    base_path = os.path.dirname(sys.executable)
else:
    # If run from a normal Python environment, use the script's directory
    base_path = os.path.dirname(os.path.abspath(__file__))

# --- Read Configuration --- START
config_path = os.path.join(base_path, 'config.ini')
config = configparser.ConfigParser()
log_level_str = 'INFO' # Default log level
if config.read(config_path, encoding='utf-8'):
    log_level_str = config.get('dev', 'log_level', fallback='INFO').upper()
else:
    print(f"警告：无法找到或读取配置文件 {config_path}，将使用默认日志级别 INFO")

# Map string level to logging constant
log_levels = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}
log_level = log_levels.get(log_level_str, logging.INFO)
# --- Read Configuration --- END

# Construct paths relative to the base path
log_dir = os.path.join(base_path, 'logs')
log_file_path = os.path.join(log_dir, 'app.log')
# --- Determine base path --- END

def setup_logger(log_file=log_file_path, level=log_level):
    """配置日志记录器，使用从配置或默认值设置的级别"""
    # Ensure log directory exists
    os.makedirs(log_dir, exist_ok=True)

    # Slightly improved formatter
    log_formatter = logging.Formatter('%(asctime)s [%(levelname)-8s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    log_handler = RotatingFileHandler(
        log_file,
        maxBytes=5*1024*1024, # 5 MB
        backupCount=2,
        encoding='utf-8'
    )
    log_handler.setFormatter(log_formatter)

    # 控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)

    logger = logging.getLogger('szu_network_fixer')
    logger.setLevel(level)

    # 避免重复添加handler
    if not logger.handlers:
        logger.addHandler(log_handler)
        logger.addHandler(console_handler)

    return logger

# 初始化logger
# Removed: Log directory creation is now inside setup_logger
# if not os.path.exists('logs'):
#     os.makedirs('logs')

logger = setup_logger() 