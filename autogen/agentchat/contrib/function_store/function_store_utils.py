import subprocess
import sys
import functools


def requires(*packages):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for package in packages:
                try:
                    __import__(package)
                except ImportError:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", package, "--quiet"])
            return func(*args, **kwargs)

        return wrapper

    return decorator
