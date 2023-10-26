# from exp_helper import exp_config
import exp_config
import os
import subprocess
import random
import time as time_package
import sys
import threading
import signal


class Exp:
    def __init__(self, browser, tool, exp_type, time, output_dir, pid, execution_iteration):
        target_output_dir = output_dir + "/" + "-".join(
            [exp_type, tool, browser, time, str(random.randint(0, 1000000))])
        if not os.path.exists(target_output_dir):
            os.makedirs(target_output_dir, exist_ok=True)
        else:
            print(target_output_dir + "has already created, you need to take care of it")
            exit()
        env = exp_config.get_env(exp_type=exp_type, tool=tool, browser=browser)
        for key, val in env.items():
            os.environ[key] = val
        server_args, fuzzer_args = exp_config.get_cmd_arguments(exp_type=exp_type, tool=tool,
                                                                browser=browser,
                                                                time=time,
                                                                target_output_dir=target_output_dir,
                                                                execution_iteration=execution_iteration)

        print(f"[{pid}]: {server_args}; {fuzzer_args}")
        server_file = open(target_output_dir + "/serverstdout", "w+")
        fuzzer_file = open(target_output_dir + "/fuzzerstdout", "w+")
        self.server_process = subprocess.Popen(server_args, stdout=server_file, stderr=server_file)
        self.fuzzer_process = subprocess.Popen(fuzzer_args, stdout=fuzzer_file,
                                               stderr=fuzzer_file)

        t = float(time) * 3600
        start_time = time_package.time()
        print(f"[{pid}]: sleep {t} s")
        try:
            while time_package.time() - start_time < t:
                if self.fuzzer_process.poll() is not None:
                    print(f"[{pid}]: child process has been terminated")
                    break
                time_package.sleep(1)
        except BaseException as e:
            print(f"error during sleep: {e}")
        print(f"[{pid}]: wake up")
        # fuzzer_log = fuzzer_process.stdout.readlines()

        print(f"[{pid}]: closing, take roughly 5 seconds")
        while (self.fuzzer_process and self.fuzzer_process.poll() is None) \
                or (self.server_process and self.server_process.poll() is None):
            try:
                self.fuzzer_process.send_signal(signal.SIGINT)
            except BaseException as e:
                print(e)
                self.fuzzer_process.send_signal(signal.SIGKILL)
            try:
                self.server_process.send_signal(signal.SIGINT)
            except BaseException as e:
                print(e)
                self.server_process.send_signal(signal.SIGKILL)

            time_package.sleep(1)
        print(f"[{pid}]: done")

    def __del__(self):
        print(f"closing, take roughly 5 seconds")
        while (self.fuzzer_process and self.fuzzer_process.poll() is None) \
                or (self.server_process and self.server_process.poll() is None):
            try:
                self.fuzzer_process.send_signal(signal.SIGINT)
            except BaseException as e:
                print(e)
                self.fuzzer_process.send_signal(signal.SIGKILL)
            try:
                self.server_process.send_signal(signal.SIGINT)
            except BaseException as e:
                print(e)
                self.server_process.send_signal(signal.SIGKILL)
            time_package.sleep(1)
        print(f"done")


def spawn_child(sub_args, i, pid):
    p = subprocess.Popen(sub_args)
    p.wait()
    print(f"[{pid}]: {i} thread is finished")


def main():
    options = exp_config.get_option()
    browser = options["browser"]
    tool = options["fuzzer"]
    exp_type = options["exp_type"]
    time = options["experiment_time"]
    output_dir = options["output_dir"]
    parallel = int(options["parallel"])
    execution_iteration = options["execution_iteration"]
    pid = os.getpid()
    if parallel == 1:
        exp = Exp(browser, tool, exp_type, time, output_dir, pid, execution_iteration)
    # server_log = server_process.stdout.readlines()
    # with open(target_output_dir + "/serverstdout", "w+") as f:
    #     for line in server_log:
    #         f.write(line.decode("utf-8"))
    # with open(target_output_dir + "/fuzzerstdout", "w+") as f:
    #     for line in fuzzer_log:
    #         f.write(line.decode("utf-8"))
    else:
        script_path = sys.argv[0]
        sub_args = ["python3", script_path, "-b", browser, "-f", tool, "-e", exp_type, "-t", time,
                    "-o", output_dir, "-p", "1"] + ["-x", str(execution_iteration)] if execution_iteration else []
        threads = []
        for i in range(parallel):
            t = threading.Thread(target=spawn_child, args=(sub_args, i, pid), name=str(i))
            t.start()
            threads.append(t)
        for t in threads:
            t.join()
        print(f"[{pid}] the parallel task has been finished")


if __name__ == '__main__':
    main()
