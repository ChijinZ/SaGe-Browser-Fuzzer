import logging
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError
import os
import random

from common import FuzzedBrowser


def get_browser(threadId, browser_name, playwright, timeout) -> FuzzedBrowser:
    browser = None
    if browser_name == "webkitgtk":
        browser = WebKitPlaywrightBrowser(threadId, playwright, timeout, "gtk")
    elif browser_name == "webkitwpe":
        browser = WebKitPlaywrightBrowser(threadId, playwright, timeout, "wpe")
    else:
        logging.error(f"invalid browser: {browser_name}")
        exit()
    assert browser is not None
    return browser


class PlayWrightBrowser(FuzzedBrowser):
    pass


class WebKitPlaywrightBrowser(FuzzedBrowser):
    def __init__(self, thread_id, playwright, timeout, port="gtk", random_close=0.1):
        self.thread_id = thread_id
        self.port = port
        self.playwright = playwright
        self.timeout = int(timeout)
        self.random_close = random_close
        self.browser = None
        self.current_page = None
        self.tmp_dir = "/tmp/webkittmpdir" + str(self.thread_id) + "pid" + str(
            os.getpid()) + "rand" + str(random.random())
        os.makedirs(self.tmp_dir, exist_ok=True)
        self.msg_path = self.tmp_dir + "/tmp_log"
        self.launch_browser()

    def launch_browser(self):
        env = os.environ
        env["FUZZER_TMP_PATH"] = self.msg_path
        logging.info("start launching")
        webkit_path = None
        if "WEBKIT_PATH" in os.environ:
            webkit_path = os.environ["WEBKIT_PATH"]
        self.browser = self.playwright.webkit.launch(headless=False if self.port == "gtk" else True,
                                                     env=env, executable_path=webkit_path)
        logging.info("end launching")
        self.current_page = None

    def ready(self):
        if self.browser is None:
            logging.error("error: self.browser is None")
            exit()
        try:
            self.current_page = self.browser.new_page()
        except PlaywrightError as e:
            logging.error(f"fail to create new page {e}")
            self.browser.close()
            self.launch_browser()
            self.current_page = self.browser.new_page()

    def fuzz(self, path: str) -> bool:
        path = "file://" + path
        try:
            self.current_page.goto(path, timeout=self.timeout)
            self.current_page.close()
            return True
        except PlaywrightTimeoutError as e:
            logging.info(f"timeout: {e}")
            if not self.current_page.is_closed():
                self.current_page.close()
            return True
        except PlaywrightError as e:
            logging.info(f"playwright error: {e}")
            if random.random() < self.random_close:
                logging.info("start closing")
                self.browser.close()
                logging.info("end closing")
                # if not self.current_page.is_closed():
                #     self.current_page.close()
                self.launch_browser()
            return False

    def message(self) -> str:
        try:
            with open(self.msg_path, "r") as f:
                return f.read()
        except IOError:
            return "fail to open msg_path"

    def close(self):
        self.browser.close()
