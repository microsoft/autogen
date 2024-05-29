import json
import logging

class StructuredMessage:
    def __init__(self, message, /, **kwargs):
        self.message = message
        self.kwargs = kwargs

    def __str__(self):
        return '%s >>> %s' % (self.message, json.dumps(self.kwargs))

_ = StructuredMessage   # optional, to improve readability

class StructuredLoggingHandler(logging.Handler):
    def emit(self, record):
        try:
            # Use the StructuredMessage if the message is an instance of it
            if isinstance(record.msg, StructuredMessage):
                print("got it")
                message = str(record.msg)
            else:
                message = self.format(record)
            print(message)  # You can replace this with any other output method (e.g., writing to a file)
        except Exception:
            self.handleError(record)

# Set up the logging configuration to use the custom handler
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger()
logger.handlers = []  # Remove default handlers
structured_handler = StructuredLoggingHandler()
logger.addHandler(structured_handler)

# Example usage
logging.info(_('message 1', foo='bar', bar='baz', num=123, fnum=123.456))