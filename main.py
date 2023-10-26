# from playwright.sync_api import sync_playwright
import logging
import signal
import threading
import os
import shutil
import json

import config
import common
from fuzzer import get_fuzzer, EvoGrammarFuzzer
from browser_selenium import get_browser
import time


def check_if_semantic_error(s: str) -> bool:
    for error_type in ["TypeError", "ReferenceError", "NotSupportedError"]:
        if error_type in s:
            return True

    return False


def process_feedback(feedback):
    logging.info("process")
    total_num = 0
    error_num = 0
    for line in feedback:
        if not isinstance(line, list):
            continue
        if len(line) != 2:
            continue
        if "GetVariable" in line[0] or "SetVariable" in line[0]:
            continue
        error = check_if_semantic_error(line[1])
        # logging.info(f"{line[0]}: {line[1]}")
        total_num += 1
        error_num += 1 if error else 0
    if total_num != 0:
        logging.info(f"error rate: {error_num / total_num} ({error_num}/{total_num}) ({time.time()})")


class FuzzingLoop(threading.Thread):
    # class FuzzingLoop:
    def __init__(self, threadId, options):
        threading.Thread.__init__(self)
        self.threadId = threadId
        self.options = options
        self.exit_time = None
        if self.options["time_to_exit"]:
            self.exit_time = int(self.options["time_to_exit"]) * 3600
        self.execution_iteration = None
        if self.options["execution_iteration"]:
            self.execution_iteration = int(self.options["execution_iteration"])
        self.dir = os.path.join(self.options["output_dir"], f"thread-{threadId}")
        self.crash = os.path.join(self.dir, "crash")
        self.interesting = os.path.join(self.dir, "interesting")
        os.makedirs(self.dir, exist_ok=True)
        os.makedirs(self.crash, exist_ok=True)
        os.makedirs(self.interesting, exist_ok=True)

        self.print_time = False
        self.print_time_start = time.time()
        if "PRINT_TIME" in os.environ:
            self.print_time = os.environ["PRINT_TIME"] == "true"

    def move_to_crash(self, source_path, message, dest_path):
        shutil.move(source_path, os.path.join(self.crash, dest_path))
        with open(os.path.join(self.crash, dest_path + ".log"), "w") as f:
            f.write(message)

    def move_to_interesting(self, source_path, dest_path):
        shutil.move(source_path, os.path.join(self.interesting, dest_path))

    def run(self):
        # with sync_playwright() as playwright:
        fuzzer = get_fuzzer(self.options["fuzzer"], self.threadId)
        browser = get_browser(self.threadId, self.options["browser"],
                              int(self.options["timeout"]))
        start_time = time.time()
        try:
            i = 0
            while True:
                if self.print_time:
                    self.print_time_start = time.time()
                path = fuzzer.generate_input()
                if self.print_time:
                    logging.info(f"fuzzer time: {time.time() - self.print_time_start} s")
                    self.print_time_start = time.time()
                browser.ready()
                if i % 10 == 0:
                    logging.info(f"[{self.threadId}]: iteration: {i}")

                if self.exit_time is not None:
                    if (time.time() - start_time) > self.exit_time:
                        return
                if self.execution_iteration is not None:
                    if i >= self.execution_iteration:
                        return

                logging.info(f"[{self.threadId}]: timestamp of the begin of iteration {i}: {int(time.time())}")
                # if i == 0, then we just omit it because we need a baseline coverage that exclude excution.
                if i != 0:
                    res = browser.fuzz(path)
                    if self.print_time:
                        logging.info(f"browser time: {time.time() - self.print_time_start} s")
                        self.print_time_start = time.time()
                    if not res:
                        message = browser.message()
                        self.move_to_crash(path, message, str(i) + ".html")
                        logging.info(f"[{self.threadId}]: error message: \n{message}")
                    elif fuzzer.is_interesting():
                        self.move_to_interesting(path, str(i) + ".html")
                    else:  # normal execution

                        feed_back_str = browser.get_statement_valid_feedback()
                        # logging.info(feed_back_str is not None)
                        if feed_back_str is not None:
                            feedback_raw = json.loads(feed_back_str)
                            process_feedback(feedback_raw)
                        if isinstance(fuzzer, EvoGrammarFuzzer):
                            if feed_back_str is not None:
                                fuzzer.handle_feedback(feed_back_str)
                            else:
                                logging.info(f"[{self.threadId}]: cannot obtain feedback")
                logging.info(f"[{self.threadId}]: timestamp of the end of iteration {i}: {int(time.time())}")
                i += 1
        except KeyboardInterrupt as e:
            logging.info(f"exit the loop: thread id: {self.threadId}, event: {e}")
            # browser.close()
            return


def main():
    logging.basicConfig(level=logging.INFO)
    options = config.get_main_option()
    common.create_output_directory(options["output_dir"])

    threads = []
    for i in range(int(options["parallel"])):
        thread = FuzzingLoop(i, options)
        thread.start()
        threads.append(thread)
        # time.sleep(20)
    for t in threads:
        t.join()
    logging.info("normal exit the fuzzing")


if __name__ == '__main__':
    main()
