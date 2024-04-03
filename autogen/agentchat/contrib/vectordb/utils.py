import logging
from termcolor import colored


class ColoredLogger(logging.Logger):
    def __init__(self, name, level=logging.NOTSET):
        super().__init__(name, level)

    def debug(self, msg, *args, color=None, **kwargs):
        super().debug(colored(msg, color), *args, **kwargs)

    def info(self, msg, *args, color=None, **kwargs):
        super().info(colored(msg, color), *args, **kwargs)

    def warning(self, msg, *args, color="yellow", **kwargs):
        super().warning(colored(msg, color), *args, **kwargs)

    def error(self, msg, *args, color="light_red", **kwargs):
        super().error(colored(msg, color), *args, **kwargs)

    def critical(self, msg, *args, color="red", **kwargs):
        super().critical(colored(msg, color), *args, **kwargs)


def get_logger(name: str, level: int = logging.INFO) -> ColoredLogger:
    logger = ColoredLogger(name, level)
    console_handler = logging.StreamHandler()
    logger.addHandler(console_handler)
    formatter = logging.Formatter("%(asctime)s - %(filename)s:%(lineno)5d - %(levelname)s - %(message)s")
    logger.handlers[0].setFormatter(formatter)
    return logger

logger = get_logger(__name__)
