import os
import random
import logging
import signal
import psutil
import copy
from common import FuzzedBrowser
from selenium.webdriver.common.utils import free_port
from selenium.common.exceptions import WebDriverException
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import Chrome, ChromeOptions


class LibcefSeleniumBrowser(FuzzedBrowser):
    def __init__(self, thread_id, timeout):
        self.thread_id = thread_id
        self.timeout_sec = int(timeout) / 1000
        self.browser = None
        self.tmp_dir = "/tmp/libceftmpdir" + str(self.thread_id) + "pid" + str(
            os.getpid()) + "rand" + str(random.random())
        os.makedirs(self.tmp_dir, exist_ok=True)
        self.msg_path = self.tmp_dir + "/tmp_log"
        if "CEFCLIENT_PATH" in os.environ:
            self.cefclient_path = os.environ["CEFCLIENT_PATH"]
        else:
            logging.error(f"[{thread_id}]: didn't set CEFCLIENT_PATH env var")
            exit(1)
        if "CHROMEDRIVER_PATH" in os.environ:
            self.chrome_driver_path = os.environ["CHROMEDRIVER_PATH"]
        else:
            logging.error(f"[{thread_id}]: didn't set CHROMEDRIVER_PATH env var")
            exit(1)
        os.environ["LD_LIBRARY_PATH"] = "/".join(self.cefclient_path.split("/")[:-1])
        logging.info(f"[{self.thread_id}]: LD_LIBRARY_PATH: {os.environ['LD_LIBRARY_PATH']}")
        self.termination_log = None

    def launch_browser(self):
        logging.info(f"[{self.thread_id}]: start launching")
        port = free_port()
        logging.info(f"[{self.thread_id}]: free port {port}")
        ops = ChromeOptions()
        ops.add_argument("--no-sandbox")
        ops.add_argument("--remote-debugging-port=" + str(port))
        ops.add_argument("--url=https://www.baidu.com")
        ops.binary_location = self.cefclient_path
        try:
            self.browser = Chrome(self.chrome_driver_path, options=ops,
                                  service_log_path=self.msg_path)
            self.browser.set_page_load_timeout(self.timeout_sec)
            self.browser.command_executor.set_timeout(self.timeout_sec * 10)
            logging.info(f"[{self.thread_id}]: end launching")
            cef_pid = self.browser.service.process.pid
            logging.info(f"[{self.thread_id}]: webkit pid: {cef_pid}")
        except BaseException as e:
            logging.error(f"[{self.thread_id}]: cannot launch browser. {repr(e)}")
            # raise
            logging.error(f"[{self.thread_id}]: try again")
            self.launch_browser()

    def close_browser(self):
        webdriver_pid = self.browser.service.process.pid
        process = psutil.Process(webdriver_pid)
        child_procs = process.children(recursive=True)
        try:
            self.browser.quit()
            logging.info(f"[{self.thread_id}]: successfully quit")
        except BaseException as e:
            logging.info(f"[{self.thread_id}]: cannot normally quit. cause: {repr(e)}")
        logging.info(f"[{self.thread_id}]: try to kill webdriver pid: {webdriver_pid}")
        try:
            os.kill(webdriver_pid, signal.SIGKILL)
            logging.info(f"[{self.thread_id}]: successfully kill webdriver pid: {webdriver_pid}")
        except BaseException as e:
            logging.info(
                f"[{self.thread_id}]: cannot kill webdriver pid :{webdriver_pid}; cause: {repr(e)}")
        for pid in child_procs:
            logging.info(f"[{self.thread_id}]: try to kill pid: {pid.pid}")
            try:
                os.kill(pid.pid, signal.SIGKILL)
                logging.info(f"[{self.thread_id}]: successfully kill pid {pid.pid}")
            except BaseException as e:
                logging.info(f"[{self.thread_id}]: cannot kill {pid.pid}; cause: {repr(e)}")
        self.browser = None

    def close_all_tabs(self):
        try:
            handles = self.browser.window_handles
            if len(handles) == 1:
                return
            handle_0 = handles[0]
            for handle in handles:
                if handle_0 != handle:
                    self.browser.switch_to.window(handle)
                    self.browser.close()
            self.browser.switch_to.window(handle_0)
        except BaseException as e:
            raise

    def new_page(self):
        try:
            # self.close_all_tabs()
            self.browser.switch_to.window(self.browser.window_handles[0])
            self.browser.execute_script("window.open('','_blank');")
            self.browser.switch_to.window(self.browser.window_handles[1])
        except BaseException as e:
            logging.error(
                f"[{self.thread_id}]: cannot create a new page, try to restart the browser. reason: {repr(e)}")
            logging.error(
                f"[{self.thread_id}]: {self.message()}"
            )
            self.close_browser()
            self.launch_browser()
            self.new_page()

    def ready(self):
        if self.browser is None:
            self.launch_browser()
            self.new_page()
        else:
            try:
                self.new_page()
            except BaseException as e:
                logging.error(f"[{self.thread_id}]: cannot new a page. {repr(e)}")
                self.close_browser()
                self.launch_browser()
                self.new_page()

    def clone(self):
        cloned = copy.copy(self)
        cloned.browser = None
        return cloned

    def fuzz(self, path: str) -> bool:
        path = "file://" + path
        try:
            self.browser.get(path)
            return True
        except TimeoutException as e:
            logging.info(f"[{self.thread_id}]: timeout, {repr(e)}!")
            try:
                self.browser.close()
            except BaseException as e:
                logging.info(
                    f"[{self.thread_id}]: timeout, but cannot close current window. {repr(e)}")
                self.close_browser()
                self.launch_browser()
            return True
        except BaseException as e:
            try:
                logging.info(f"[{self.thread_id}]: not finish, because: {repr(e)}")
                self.browser.close()
                logging.info(f"[{self.thread_id}]: browser can be closed!")
                return True
            except WebDriverException as e:
                logging.info(f"[{self.thread_id}]: crash! WebDriverException: {repr(e)}")
                self.termination_log = self.get_log()
                self.close_browser()
                self.launch_browser()
                return False

    def message(self) -> str:
        if self.termination_log:
            tmp = self.termination_log
            self.termination_log = None
            return tmp
        else:
            return self.get_log()

    def get_log(self) -> str:
        try:
            with open(self.msg_path, "r") as f:
                return f.read()
        except IOError as e:
            return f"[{self.thread_id}]: fail to open msg_path. {repr(e)}"
