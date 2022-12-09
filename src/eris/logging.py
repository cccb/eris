"""
Logging
"""

from datetime import datetime

def log(fmt, *args, **kwargs):
    """Print a log message"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S\t")
    print(timestamp + fmt.format(*args, **kwargs))
