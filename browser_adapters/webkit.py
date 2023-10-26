from common import FuzzedBrowser

import os
import random
import logging
import signal
import psutil
import copy

from typing import List, Tuple, Optional

from selenium.webdriver.webkitgtk import webdriver, options
from selenium.common.exceptions import WebDriverException
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import UnexpectedAlertPresentException
from selenium.common.exceptions import NoAlertPresentException
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.utils import free_port
import subprocess


class WebKitSeleniumBrowser(FuzzedBrowser):
    def __init__(self, thread_id, timeout, port="gtk"):
        self.thread_id = thread_id
        self.timeout_sec = int(timeout) / 1000
        self.port = port
        self.browser = None
        self.tmp_dir = "/tmp/webkittmpdir" + str(self.thread_id) + "pid" + str(
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

        # configure for launching browser
        self.caps = DesiredCapabilities.WEBKITGTK.copy()
        self.caps["pageLoadStrategy"] = "normal"
        self.option = options.Options()
        self.option.add_argument("--automation")
        self.option.add_argument("-f")
        self.termination_log = None
        if "WEBKIT_WEBDRIVER_PATH" in os.environ:
            self.webkit_driver_path = os.environ["WEBKIT_WEBDRIVER_PATH"]
        else:
            logging.error(f"[{thread_id}]: didn't set WEBKIT_WEBDRIVER_PATH env var")
            exit(1)
        if "WEBKIT_BINARY_PATH" in os.environ:
            self.option.binary_location = os.environ["WEBKIT_BINARY_PATH"]
        else:
            logging.error(f"[{thread_id}]: didn't set WEBKIT_BINARY_PATH env var")
            exit(1)
        os.environ["FUZZER_TMP_PATH"] = self.msg_path
        self.launch_browser()

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
        try:
            if self.xvfb:
                # it's very very dangerous, but I can't find a better way
                # because selenium didn't export an API for setting env var
                os.environ["DISPLAY"] = f":{self.display_port}"
            self.browser = webdriver.WebDriver(
                executable_path=self.webkit_driver_path,
                options=self.option,
                # desired_capabilities=self.caps,
                service_log_path=self.msg_path)
            self.browser.set_page_load_timeout(self.timeout_sec)
            self.browser.command_executor.set_timeout(20)
            logging.info(f"[{self.thread_id}]: end launching")
            webdriver_pid = self.browser.service.process.pid
            logging.info(f"[{self.thread_id}]: webkit pid: {webdriver_pid}")
        except KeyboardInterrupt as e:
            logging.info(f"interrupted by user: {e}")
        except BaseException as e:
            logging.error(f"[{self.thread_id}]: cannot launch webkit browser. {repr(e)}")
            # raise
            logging.error(f"[{self.thread_id}]: try again")
            # exit(1)
            self.close_browser()
            self.launch_browser()

    def close_browser(self):
        if self.browser is None:
            return
        webdriver_pid = self.browser.service.process.pid
        process = psutil.Process(webdriver_pid)
        child_procs = process.children(recursive=True)
        try:
            self.browser.quit()
            logging.debug(f"[{self.thread_id}]: successfully quit")
        except BaseException as e:
            logging.debug(f"[{self.thread_id}]: cannot normally quit. cause: {repr(e)}")
        logging.debug(f"[{self.thread_id}]: try to kill webdriver pid: {webdriver_pid}")
        try:
            os.kill(webdriver_pid, signal.SIGKILL)
            logging.debug(f"[{self.thread_id}]: successfully kill webdriver pid: {webdriver_pid}")
        except ProcessLookupError as e:
            pass
        except BaseException as e:
            logging.error(
                f"[{self.thread_id}]: cannot kill webdriver pid :{webdriver_pid}; cause: {repr(e)}")
        for pid in child_procs:
            logging.debug(f"[{self.thread_id}]: try to kill pid: {pid.pid}")
            try:
                os.kill(pid.pid, signal.SIGKILL)
                logging.debug(f"[{self.thread_id}]: successfully kill pid {pid.pid}")
            except ProcessLookupError as e:
                pass
            except BaseException as e:
                logging.error(f"[{self.thread_id}]: cannot kill {pid.pid}; cause: {repr(e)}")
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
            # handles = self.browser.window_handles
            # for handle in handles:
            #     if self.main_window != handle:
            #         self.browser.switch_to.window(handle)
            #         self.browser.close()
            # self.browser.switch_to.window(self.main_window)
            # self.browser.execute_script("window.open('','_blank');")
            self.close_all_tabs()
            self.browser.switch_to.window(self.browser.window_handles[0])
            self.browser.execute_script("window.open('','_blank');")
            self.browser.switch_to.window(self.browser.window_handles[1])
        except UnexpectedAlertPresentException as e:
            self.browser.switch_to.alert.accept()
            self.new_page()
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

    # Note: return true if the page does not crash
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

    def get_webdriver(self):
        return self.browser

    def get_statement_valid_feedback(self) -> Optional[str]:
        try:
            feedback = self.browser.execute_script("return JSON.stringify(myFeedback)")
            return feedback
        except BaseException as e:
            return None
