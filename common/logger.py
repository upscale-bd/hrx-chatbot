# logging service
from logging import getLogger, StreamHandler, Formatter, DEBUG


## a logger service that initialises with a specific name
class LoggerService:
    def __init__(self, name: str):
        self.logger = getLogger(name)
        self.logger.setLevel(DEBUG)

        # Only add handler if logger doesn't already have handlers
        if not self.logger.handlers:
            # Create console handler
            handler = StreamHandler()
            handler.setLevel(DEBUG)

            # Create formatter and set it for the handler
            formatter = Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)

            # Add the handler to the logger
            self.logger.addHandler(handler)

    def get_logger(self):
        return self.logger

    def log(self, message: str, level: int = DEBUG):
        """
        Logs a message with the specified logging level.
        :param message: The message to log.
        :param level: The logging level (default is DEBUG).
        """
        if level == DEBUG:
            self.logger.debug(message)
        else:
            self.logger.info(message)

    def error(self, message: str):
        """
        Logs an error message.
        :param message: The error message to log.
        """
        self.logger.error(message)

    def warning(self, message: str):
        """
        Logs a warning message.
        :param message: The warning message to log.
        """
        self.logger.warning(message)

    def info(self, message: str):
        """
        Logs an info message.
        :param message: The info message to log.
        """
        self.logger.info(message)

    def debug(self, message: str):
        """
        Logs a debug message.
        :param message: The debug message to log.
        """
        self.logger.debug(message)
def get_logger(name: str) -> LoggerService:
    """
    Get a logger instance with the specified name.
    Returns a LoggerService instance that can be used directly.
    """
    return LoggerService(name)
