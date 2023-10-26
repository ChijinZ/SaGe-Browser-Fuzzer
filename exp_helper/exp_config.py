import os
import socket
from optparse import OptionParser

common_envs = {"DISPLAY": ":13", "ASAN_OPTIONS": "detect_odr_violation=0:detect_leaks=0"}
tool_list = ["sage", "sage2", "minerva", "minerva-", "domato", "freedom", "favocado"]
exp_type_list = ["sancov", "memdep"]
browser_list = ["webkit", "firefox", "chromium"]

def free_port():
    """
    Determines a free port using sockets.
    """
    free_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    free_socket.bind(('0.0.0.0', 0))
    free_socket.listen(5)
    port = free_socket.getsockname()[1]
    free_socket.close()
    return port


def get_option() -> dict:
    required = ["browser", "fuzzer", "exp_type", "experiment_time", "output_dir", "parallel"]
    usage = "python run.py -b <browser> -f <fuzzer> -e <exp_type> -t <experiment_time> " \
            "-p <parallel> -o <output_dir>"
    parser = OptionParser(usage)
    parser.add_option("-b", "--browser", dest="browser",
                      help="choose a browser (webkit, firefox, chromium)")
    parser.add_option("-f", "--fuzzer", dest="fuzzer",
                      help="choose a fuzzer (sage, Minerva, Minerva-, Domato, FreeDom, Favocado)")
    parser.add_option("-e", "--exp_type", dest="exp_type",
                      help="type of target binary: (sancov, memdep)")
    parser.add_option("-t", "--experiment_time", dest="experiment_time",
                      help="experiment_time (hours, default 24)", default="24")
    parser.add_option("-o", "--output_dir", dest="output_dir",
                      help="output directory")
    parser.add_option("-p", "--parallel", dest="parallel",
                      help="how many instances in parallel (default 1)",
                      default="1")
    parser.add_option("-x", "--execution_iteration", dest="execution_iteration",
                      help="exit after this iteration", default=None)
    (options, args) = parser.parse_args()
    if len(args) != 0:
        print(f"unused arguments: {args}")
        exit()
    options = vars(options)
    for var in required:
        if var not in options or options[var] is None:
            print(f"{var} is not set")
            exit()
    print(f"options: {options}")
    return options


# return server_args and fuzzer_args
def get_cmd_arguments(exp_type, tool, browser, time, target_output_dir, execution_iteration) -> (list, list):
    server_args = []
    fuzzer_args = []

    if "FUZZER_PATH" not in os.environ:
        print("FUZZER_PATH not in the env var")
        exit()
    if "PORT" not in os.environ:
        print("PORT not in the env var")
        exit()
    name = "-".join([exp_type, tool, browser, time])
    port = os.environ["PORT"]
    fuzzer_path = os.environ["FUZZER_PATH"]
    fuzzer_args.append("python3")
    fuzzer_args.append(fuzzer_path)

    if exp_type == "sancov":
        if "SANCOV_SERVER_PATH" not in os.environ:
            print("SANCOV_SERVER_PATH not in the env var")
            exit()
        server_path = os.environ["SANCOV_SERVER_PATH"]
        server_args.append(server_path)
        server_args.append("-p")
        server_args.append(port)
        server_args.append("-o")
        server_args.append(target_output_dir + "/" + name + "-cov")

        timeout = "10000"
        fuzzer_args.append("-t")
        fuzzer_args.append(timeout)
    elif exp_type == "memdep":
        pass
    else:
        print("invalid exp type: " + exp_type)
        exit()

    # fuzzer_args.append("-e")
    # fuzzer_args.append(str(time))
    fuzzer_args.append("-o")
    fuzzer_args.append(target_output_dir + "/" + name + "-cov-output")
    if execution_iteration:
        fuzzer_args.append("-x")
        fuzzer_args.append(str(execution_iteration))

    if browser == "webkit":
        server_args.append("-m")
        server_args.append("webkit")
        # server_args.append("normal_lib")
        fuzzer_args.append("-b")
        fuzzer_args.append("webkitgtk")
    elif browser == "firefox":
        server_args.append("-m")
        # server_args.append("firefox")
        server_args.append("normal_lib")
        fuzzer_args.append("-b")
        fuzzer_args.append("firefox")
    elif browser == "chromium":
        server_args.append("-m")
        # server_args.append("chrome")
        server_args.append("normal_lib")
        fuzzer_args.append("-b")
        fuzzer_args.append("chromium")
    else:
        print("invalid browser: " + browser)
        exit()

    fuzzer_args.append("-f")
    if tool == "domato":
        fuzzer_args.append("domato")
    elif tool == "minerva":
        fuzzer_args.append("minerva")
    elif tool == "minerva-":
        fuzzer_args.append("minerva")
    elif tool == "favocado":
        fuzzer_args.append("favocado")
    elif tool == "freedom":
        fuzzer_args.append("freedom")
    elif tool == "sage" or tool == "sage2":
        fuzzer_args.append("sage")
    else:
        print("invalid fuzzer: " + tool)
        exit()
    return server_args, fuzzer_args


def get_env(exp_type, tool, browser) -> dict:
    if exp_type not in exp_type_list:
        print("wrong exp type")
        exit()
    if tool not in tool_list:
        print("wrong tool")
        exit()
    if browser not in browser_list:
        print("wrong browser")
        exit()
    return_envs = common_envs.copy()
    return_envs["CURRENT_USED_FUZZER"] = tool
    port = str(free_port())
    return_envs["PORT"] = port

    if exp_type == "sancov":
        shm_dir = "/tmp/sancov_output/shm"
        if not os.path.exists(shm_dir):
            os.makedirs(shm_dir, exist_ok=True)
        return_envs["SHM_DIR"] = shm_dir
        return_envs["REGISTRATION_ADDR"] = "127.0.0.1:" + port
        return_envs["CLOSE_BROWSER_PROB"] = "1"
    elif exp_type == "memdep":
        pass
    else:
        print("in valid exp type: " + exp_type)
        exit()

    if browser == "webkit":
        if "WEBKIT_PATH" not in os.environ:
            print("WEBKIT_PATH not in the env var")
            exit()
        webkit_path = os.environ["WEBKIT_PATH"]
        return_envs["LD_LIBRARY_PATH"] = webkit_path + "/lib"
        return_envs["WEBKIT_BINARY_PATH"] = webkit_path + "/libexec/webkit2gtk-4.0/MiniBrowser"
        return_envs["WEBKIT_WEBDRIVER_PATH"] = webkit_path + "/bin/WebKitWebDriver"
    elif browser == "firefox":
        if "FIREFOX_PATH" not in os.environ:
            print("FIREFOX_PATH not in the env var")
            exit()
        if "FIREFOXDRIVER_PATH" not in os.environ:
            print("FIREFOXDRIVER_PATH not in the env var")
            exit()
        return_envs["MOZ_DISABLE_CONTENT_SANDBOX"] = "true"
    elif browser == "chromium":
        if "CHROMEDRIVER_PATH" not in os.environ:
            print("CHROMEDRIVER_PATH not in the env var")
            exit()
        if "CHROMIUM_PATH" not in os.environ:
            print("CHROMEDRIVER_PATH not in the env var")
            exit()
    else:
        print("invalid browser: " + browser)
        exit()

    if tool == "domato":
        domato_env = get_domato_env()
        for key, val in domato_env.items():
            return_envs[key] = val
    elif tool == "minerva":
        minerva_env = get_minerva_env(browser)
        for key, val in minerva_env.items():
            return_envs[key] = val
    elif tool == "minerva-":
        minerva_ablation_env = get_minerva_ablation_env(browser)
        for key, val in minerva_ablation_env.items():
            return_envs[key] = val
    elif tool == "favocado":
        favocado_env = get_favocado_env()
        for key, val in favocado_env.items():
            return_envs[key] = val
    elif tool == "freedom":
        freedom_env = get_freedom_env()
        for key, val in freedom_env.items():
            return_envs[key] = val
    elif tool == "sage" or tool == "sage2":
        sage = get_sage_env()
        for key, val in sage.items():
            return_envs[key] = val
    else:
        print("invalid fuzzer: " + tool)
        exit()

    return return_envs


def get_domato_env():
    return_envs = {"BROWSER_GRAMMAR": "ORIGINAL_DOMATO"}
    if "MEM_DEP_JSON_PATH" in os.environ:
        print("MEM_DEP_JSON_PATH in the env var, we remove it")
        os.environ.pop("MEM_DEP_JSON_PATH")
    return return_envs


def get_sage_env():
    return_envs = {"BROWSER_GRAMMAR": "WEBREF"}
    if "MEM_DEP_JSON_PATH" in os.environ:
        print("MEM_DEP_JSON_PATH in the env var, we remove it")
        os.environ.pop("MEM_DEP_JSON_PATH")
    return return_envs


def get_minerva_env(browser_name):
    return_envs = {}
    return return_envs


def get_favocado_env():
    if "FAVOCADO_PATH" not in os.environ:
        print("FAVOCADO_PATH not in the env var")
        exit()
    return {}


def get_freedom_env():
    if "FREEDOM_PATH" not in os.environ:
        print("FREEDOM_PATH not in the env var")
        exit()
    return {}
