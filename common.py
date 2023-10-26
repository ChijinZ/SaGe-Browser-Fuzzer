import config
import os
import logging
import signal
from typing import Optional


def create_output_directory(path):
    # path = os.environ.get("OUTPUT_PATH")
    # if path is None:
    #     logging.error(f"doesn't have OUTPUT_PATH env var")
    #     exit()
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


class Timeout:
    def __init__(self, seconds=1, error_message='Timeout'):
        self.seconds = seconds
        self.error_message = error_message

    def handle_timeout(self, signum, frame):
        raise TimeoutError(self.error_message)

    def __enter__(self):
        signal.signal(signal.SIGALRM, self.handle_timeout)
        signal.alarm(self.seconds)

    def __exit__(self, type, value, traceback):
        signal.alarm(0)


class FuzzedBrowser(object):
    def ready(self):
        pass

    def clone(self):
        pass

    def fuzz(self, path: str) -> bool:
        pass

    def message(self) -> str:
        pass

    def get_statement_valid_feedback(self) -> Optional[str]:
        pass
