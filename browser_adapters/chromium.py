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
from selenium.common.exceptions import UnexpectedAlertPresentException

from typing import List, Tuple, Optional
import subprocess


class ChromiumSeleniumBrowser(FuzzedBrowser):
    def __init__(self, thread_id, timeout):
        self.thread_id = thread_id
        self.timeout_sec = int(timeout) / 1000
        self.browser = None  # actually it is a driver
        self.tmp_dir = "/tmp/chromiumtmpdir" + str(self.thread_id) + "pid" + str(
            os.getpid()) + "rand" + str(random.random())
        os.makedirs(self.tmp_dir, exist_ok=True)
        self.msg_path = self.tmp_dir + "/tmp_log"
        self.use_xvfb = True
        if "NO_XVFB" in os.environ:
            logging.info(f"[{self.thread_id}]: no xvfb")
            self.use_xvfb = False

        if self.use_xvfb:
            self.display_port = free_port()
            logging.info(f"[{self.thread_id}]: display port: {self.display_port}")
            self.xvfb = subprocess.Popen(
                ["Xvfb", f":{self.display_port}", "-ac", "-maxclients", "2048"])
        else:
            self.display_port = None
            self.xvfb = None

        # close the browser with this probability
        self.close_browser_prob = 0.01
        if "CLOSE_BROWSER_PROB" in os.environ:
            self.close_browser_prob = float(os.environ["CLOSE_BROWSER_PROB"])

        if "CHROMIUM_PATH" in os.environ:
            self.chromium_path = os.environ["CHROMIUM_PATH"]
        else:
            logging.error(f"[{thread_id}]: didn't set CHROMIUM_PATH env var")
            exit(1)
        if "CHROMEDRIVER_PATH" in os.environ:
            self.chrome_driver_path = os.environ["CHROMEDRIVER_PATH"]
        else:
            logging.error(f"[{thread_id}]: didn't set CHROMEDRIVER_PATH env var")
            exit(1)
        os.environ["LD_LIBRARY_PATH"] = "/".join(self.chromium_path.split("/")[:-1])
        logging.info(f"[{self.thread_id}]: LD_LIBRARY_PATH: {os.environ['LD_LIBRARY_PATH']}")
        self.termination_log = None

    def __del__(self):
        try:
            self.xvfb.kill()
        except:
            pass
        try:
            self.close_browser()
        except:
            pass

    def launch_browser(self):
        logging.info(f"[{self.thread_id}]: start launching")
        if self.use_xvfb and self.xvfb.poll() is not None:
            logging.info(f"[{self.thread_id}]: xvfb has been kill. port: {self.display_port}")
            self.xvfb.kill()
            self.xvfb = subprocess.Popen(
                ["Xvfb", f":{self.display_port}", "-ac", "-maxclients", "2048"])

        # file_output = open(self.msg_path, 'w')
        # logging.info(f"[{self.thread_id}]: free port {port}")
        # self.chromium = subprocess.Popen(
        #     [self.chromium_path, "--no-zygote", "--no-sandbox",
        #      "--remote-debugging-port=" + port],
        #     stdout=file_output, stderr=file_output)
        #
        ops = ChromeOptions()
        ops.binary_location = self.chromium_path
        # port = str(free_port())
        # ops.debugger_address = "127.0.0.1:" + port
        ops.add_argument("--no-sandbox")
        ops.add_argument("--disable-setuid-sandbox")
        ops.add_argument("--no-zygote")
        ops.add_argument("--disable-dev-shm-usage" ) # https://stackoverflow.com/questions/50642308/webdriverexception-unknown-error-devtoolsactiveport-file-doesnt-exist-while-t
        try:
            if self.use_xvfb:
                # it's very very dangerous, but I can't find a better way
                # because selenium didn't export an API for setting env var
                os.environ["DISPLAY"] = f":{self.display_port}"
            self.browser = Chrome(self.chrome_driver_path, options=ops
                                  , service_args=["--verbose", f"--log-path={self.msg_path}"])
            self.browser.set_page_load_timeout(self.timeout_sec)
            self.browser.command_executor.set_timeout(self.timeout_sec * 10)
            logging.info(f"[{self.thread_id}]: end launching")
            chromium_pid = self.browser.service.process.pid
            logging.info(f"[{self.thread_id}]: browser pid: {chromium_pid}")
        except UnexpectedAlertPresentException as e:
            self.browser.switch_to.alert.accept()
            self.new_page()
        except BaseException as e:
            logging.error(f"[{self.thread_id}]: cannot launch browser. {repr(e)}")
            # raise
            logging.error(f"[{self.thread_id}]: try again")
            self.launch_browser()

    def close_browser(self):
        driver_pid = self.browser.service.process.pid
        process = psutil.Process(driver_pid)
        child_procs = process.children(recursive=True)
        try:
            self.browser.quit()
            logging.info(f"[{self.thread_id}]: successfully quit")
        except BaseException as e:
            logging.info(f"[{self.thread_id}]: cannot normally quit. cause: {repr(e)}")
            os.kill(driver_pid, signal.SIGKILL)
        for pid in child_procs:
            logging.info(f"[{self.thread_id}]: try to kill pid: {pid.pid}")
            try:
                os.kill(pid.pid, signal.SIGKILL)
                logging.info(f"[{self.thread_id}]: successfully kill pid {pid.pid}")
            except ProcessLookupError as e:
                pass
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
            self.close_all_tabs()
            self.browser.switch_to.window(self.browser.window_handles[0])
            self.browser.execute_script("window.open('','_blank');")
            self.browser.switch_to.window(self.browser.window_handles[1])
        except BaseException as e:
            logging.error(
                f"[{self.thread_id}]: cannot create a new page, try to restart the browser. reason: {repr(e)}")
            # logging.error(
            #     f"[{self.thread_id}]: {self.message()}"
            # )
            self.close_browser()
            self.launch_browser()
            self.new_page()

    def ready(self):
        if self.browser is None:
            self.launch_browser()
            self.new_page()
        else:
            try:
                self.browser.switch_to.alert.accept()
            except BaseException as e:
                pass
            try:
                r = random.random()
                if r < self.close_browser_prob:
                    logging.info(
                        f"restart browser because the random pick: {r} {self.close_browser_prob}")
                    self.close_browser()
                    self.launch_browser()
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
        except UnexpectedAlertPresentException as e:
            logging.info(f"[{self.thread_id}]: {repr(e)}!")
            self.browser.switch_to.alert.accept()
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
            except BaseException as e:
                logging.info(f"[{self.thread_id}]: cannot close: {repr(e)}")
                self.close_browser()
                self.launch_browser()
                return True

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
        except UnicodeDecodeError as e:
            return "fail to decode current file"
        except IOError as e:
            return f"[{self.thread_id}]: fail to open msg_path. {repr(e)}"

    def get_statement_valid_feedback(self) -> Optional[str]:
        try:
            feedback = self.browser.execute_script("return JSON.stringify(myFeedback)")
            return feedback
        except BaseException as e:
            return None
