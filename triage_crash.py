import config
# import threading
from browser_selenium import get_browser
# from playwright.sync_api import sync_playwright
import os
# import shutil
import json
import logging
from tqdm import tqdm
from datetime import datetime


def process_log(log: str) -> [str]:
    res = set()
    splited = log.splitlines()
    for i, line in enumerate(splited):
        if "SUMMARY" in line:
            res.add(line)
        elif "WTFCrash" in line:
            root = splited[i + 1].split(" ")[-2]
            res.add(f"{line}\n{root}")
    if len(res) == 0:
        return ["normal_crash"]
    else:
        return res


def multiple_mode(options):
    res_dic = {}
    browser = get_browser(0, options["browser"], options["timeout"])
    crash_dir = options["crash_dir"]
    loop_number = int(os.getenv("LOOP_NUMBER") if "LOOP_NUMBER" in os.environ else 1)
    time = 0
    cnt = 0
    for file in tqdm(os.listdir(crash_dir)):
        crash_path = os.path.abspath(os.path.join(crash_dir, file))
        split_name = file.split(".")
        if len(split_name) > 2:
            logging.info(f"strange thing: {split_name}")
        if split_name[-1] == "log":  # if it is a log file
            with open(crash_path, "r") as f:
                log = f.read()
                logging.info(log)
                keys = process_log(log)
                for key in keys:
                    if key in res_dic:
                        res_dic[key].append(split_name[0])
                    else:
                        res_dic[key] = [split_name[0]]
            logging.info(f"{keys}, {split_name[0]}")
            continue
        if os.path.exists(crash_path + ".log"):  # if it has been processed
            continue
        # then it is a crash file without processing

        for _ in range(loop_number):
            browser.ready()
            start = datetime.now()
            res = browser.fuzz(crash_path)
            end = datetime.now()
            time += (end - start).microseconds
            cnt += 1
            if not res:
                log = browser.message()
                with open(crash_path + ".log", "w") as f:
                    f.write(log)
                    logging.info(log)
                keys = process_log(log)
                for key in keys:
                    if key in res_dic:
                        res_dic[key].append(split_name[0])
                    else:
                        res_dic[key] = [split_name[0]]
                logging.info(f"{keys}, {split_name[0]}")
            else:
                key = "false-positive"
                if key in res_dic:
                    res_dic[key].append(split_name[0])
                else:
                    res_dic[key] = [split_name[0]]
                logging.info(f"{key}, {split_name[0]}")
    logging.info(f"average time: {time / cnt} us")
    with open("res.json", "w") as f:
        json.dump(res_dic, f)


def single_mode(options):
    browser = get_browser(0, options["browser"], options["timeout"])
    crash_path = os.path.abspath(options["crash_dir"])
    file_name = crash_path.split("/")[-1]
    loop_number = int(os.getenv("LOOP_NUMBER") if "LOOP_NUMBER" in os.environ else 1)
    for i in range(loop_number):
        logging.info(f"iteration: {i}")
        browser.ready()
        res = browser.fuzz(crash_path)
        if not res:
            log = browser.message()
            logging.info(log)
            if not os.path.exists(crash_path + ".log"):
                with open(crash_path + ".log", "w") as f:
                    f.write(log)
            keys = process_log(log)
            logging.info(f"{keys}, {file_name}")
        else:
            key = "false-positive"
            logging.info(f"{key}, {file_name}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    options = config.get_triage_option()
    if options["mode"] == "multiple":
        multiple_mode(options)
    elif options["mode"] == "single":
        single_mode(options)
