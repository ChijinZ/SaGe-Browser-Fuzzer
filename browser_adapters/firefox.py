import os
import random
import logging
import signal
import psutil
import copy
from common import FuzzedBrowser
from selenium.webdriver.common.utils import free_port
from selenium.webdriver.firefox import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import Firefox, FirefoxOptions, FirefoxProfile
import subprocess
import errno
from selenium.common.exceptions import UnexpectedAlertPresentException, InvalidSessionIdException
from threading import Lock
from typing import List, Tuple, Optional


class FirefoxSeleniumBrowser(FuzzedBrowser):
    def __init__(self, thread_id, timeout):
        self.thread_id = thread_id
        self.timeout_sec = int(timeout) / 1000
        self.firefox = None
        self.seperate = False
        self.close_browser_prob = 1.0 / 50
        self.browser: Firefox = None  # actually it is a driver
        self.tmp_dir = "/tmp/firefoxtmpdir" + str(self.thread_id) + "pid" + str(
            os.getpid()) + "rand" + str(random.random())
        os.makedirs(self.tmp_dir, exist_ok=True)
        self.profile_dir = os.path.join(self.tmp_dir, 'profile')
        os.makedirs(self.profile_dir, exist_ok=True)
        self.firefox_error = os.path.join(self.tmp_dir, 'console.error')
        self.msg_path = self.tmp_dir + "/tmp_log"

        self.use_xvfb = True
        if "NO_XVFB" in os.environ:
            logging.info(f"[{self.thread_id}]: no xvfb")
            self.use_xvfb = False

        if self.use_xvfb:
            temp_lock = Lock()
            with temp_lock:
                self.display_port = free_port()
            logging.info(f"[{self.thread_id}]: display port: {self.display_port}")
            self.xvfb = subprocess.Popen(
                ["Xvfb", f":{self.display_port}", "-ac", "-maxclients", "2048"])
        else:
            self.display_port = None
            self.xvfb = None

        if "FIREFOX_PATH" in os.environ:
            self.firefox_path = os.environ["FIREFOX_PATH"]
        else:
            logging.error(f"[{thread_id}]: didn't set FIREFOX_PATH env var")
            exit(1)
        if "FIREFOXDRIVER_PATH" in os.environ:
            self.firefox_driver_path = os.environ["FIREFOXDRIVER_PATH"]
        else:
            logging.error(f"[{thread_id}]: didn't set FIREFOXDRIVER_PATH env var")
            exit(1)
        self.termination_log = None
        # self.launch_browser()

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
        if self.use_xvfb and self.xvfb.poll() is not None:
            logging.info(f"[{self.thread_id}]: xvfb has been kill. port: {self.display_port}")
            self.xvfb.kill()
            self.xvfb = subprocess.Popen(
                ["Xvfb", f":{self.display_port}", "-ac", "-maxclients", "2048"])
        ops = FirefoxOptions()
        profile = FirefoxProfile()
        profile.set_preference("app.update.auto", "false")
        profile.set_preference("app.update.enabled", "false")

        try:
            logging.info(f"[{self.thread_id}]: start launching")
            os.environ['FIREFOX_ERROR'] = self.firefox_error
            ops = FirefoxOptions()
            ops.set_preference("app.update.auto", "false")
            ops.set_preference("app.update.enabled", "false")
            if self.use_xvfb:
                temp_lock = Lock()
                with temp_lock:
                    os.environ["DISPLAY"] = f":{self.display_port}"
                    self.browser = Firefox(firefox_binary=self.firefox_path,
                                           executable_path=self.firefox_driver_path,
                                           service_log_path=self.msg_path,
                                           options=ops)
            logging.info(f"[{self.thread_id}]: end launching")
            browser_pid = self.browser.service.process.pid
            logging.info(f"[{self.thread_id}]: firefox pid: {browser_pid}")
            # self.browser_process = psutil.Process(browser_pid)
            self.browser.set_page_load_timeout(self.timeout_sec)
            self.browser.command_executor.set_timeout(self.timeout_sec * 5)
            self.browser.implicitly_wait(self.timeout_sec * 5)
            # ops.add_argument("--safe-mode")
            # ops.add_argument("--headless")
            # ops.add_argument(f"--MOZ_LOG=ObserverService:5")
            # ops.add_argument(f"--MOZ_LOG_FILE={self.msg_path}")
            # ops.add_argument("--display=:"+ str(13+self.thread_id))
            # ops.add_argument("--new-tab")
            # ops.add_argument(f"--profile={self.profile_dir}")
            # ops.add_argument("--url=http://www.baidu.com")
            # ops.log.level = "trace"
            # ops.binary_location = self.firefox_path
            # os.environ['FIREFOX_ERROR'] = self.firefox_error
            # self.browser = webdriver.WebDriver(
            # executable_path=self.firefox_driver_path,
            # options=ops,
            # desired_capabilities=self.caps,
            # firefox_profile = FirefoxProfile(self.profile_dir),
            # service_log_path=self.msg_path)

            # logging.info(f"[{self.thread_id}]: end launching")
            # browser_pid = self.browser.service.process.pid
            # self.browser_process = psutil.Process(browser_pid)
            # logging.info(f"[{self.thread_id}]: firefox pid: {browser_pid}")
        except KeyboardInterrupt as e:
            logging.info(f"interrupted by user: {e}")
        except BaseException as e:
            logging.error(f"[{self.thread_id}]: cannot launch browser. {repr(e)}")
            # raise
            logging.error(f"[{self.thread_id}]: try again")
            # exit(1)
            self.launch_browser()

    def close_browser(self):
        if self.seperate:
            firefox_pid = self.firefox.pid
            processes = psutil.Process(firefox_pid).children(recursive=True)
        driver_pid = self.browser.service.process.pid
        process = psutil.Process(driver_pid)
        child_procs = process.children(recursive=True)
        try:
            self.browser.quit()
            logging.info(f"[{self.thread_id}]: successfully quit")
        except BaseException as e:
            logging.info(f"[{self.thread_id}]: cannot normally quit. cause: {repr(e)}")
            os.kill(driver_pid, signal.SIGKILL)
        if self.seperate:
            logging.info(f"[{self.thread_id}]: try to kill firefox pid: {firefox_pid}")
            try:
                os.kill(firefox_pid, signal.SIGKILL)
                logging.info(f"[{self.thread_id}]: successfully kill firefox pid: {firefox_pid}")
            except BaseException as e:
                logging.info(
                    f"[{self.thread_id}]: cannot kill firefox pid :{firefox_pid}; cause: {repr(e)}")
            for pid in processes:
                logging.info(f"[{self.thread_id}]: try to kill pid: {pid.pid}")
                try:
                    os.kill(pid.pid, signal.SIGKILL)
                    logging.info(f"[{self.thread_id}]: successfully kill pid {pid.pid}")
                except BaseException as e:
                    logging.info(f"[{self.thread_id}]: cannot kill {pid.pid}; cause: {repr(e)}")
        for pid in child_procs:
            # logging.info(f"[{self.thread_id}]: try to kill pid: {pid.pid}")
            try:
                os.kill(pid.pid, signal.SIGKILL)
                # logging.info(f"[{self.thread_id}]: successfully kill pid {pid.pid}")
            except BaseException as e:
                # logging.info(f"[{self.thread_id}]: cannot kill {pid.pid}; cause: {repr(e)}")
                pass
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
                    if len(self.browser.window_handles) == 1:
                        break
            handle_0 = self.browser.window_handles[0]
            self.browser.switch_to.window(handle_0)
        except BaseException as e:
            raise

    def new_page(self):
        try:
            self.close_all_tabs()
            self.browser.switch_to.window(self.browser.window_handles[0])
            self.browser.execute_script("window.open('', '_blank');")
            self.browser.switch_to.window(self.browser.window_handles[1])
        except UnexpectedAlertPresentException as e:
            logging.info(f"[{self.thread_id}]: {repr(e)}!")
            self.browser.switch_to.alert.accept()
            return True
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
            # self.browser.execute_script("alert(\"Test\")")
            # self.browser.switch_to_alert().accept()
            self.browser.get(path)
            if len(self.browser.window_handles) == 0:
                logging.info(f"[{self.thread_id}]: there are no handles")
                return False
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
                try:
                    self.browser.close()
                except InvalidSessionIdException as e:
                    logging.info(
                        f"[{self.thread_id}]: timeout, invalid session. {repr(e)}")
                    self.close_browser()
                    self.launch_browser()
                    return True
                except BaseException as e:
                    logging.info(
                        f"[{self.thread_id}]: timeout, but cannot close current window. {repr(e)}")
                    self.close_browser()
                    self.launch_browser()
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

    def get_statement_valid_feedback(self) -> Optional[str]:
        try:
            feedback = self.browser.execute_script("return JSON.stringify(myFeedback)")
            return feedback
        except BaseException as e:
            return None

    # def safe_close_tab(self):
    #     try:
    #         self.browser.close()
    #     except BaseException as e:
    #         raise
    #     child_procs = self.browser_process.children(recursive=True)
    #     if len(child_procs) > 30:
    #         logging.warning(f"[{self.thread_id}]: too much zombie processes, restarting")
    #         self.close_browser()
    #         self.launch_browser()
