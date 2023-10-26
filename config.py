from optparse import OptionParser
import logging
import os

TIMEOUT = 5000
PARALLEL = 1


def get_main_option() -> dict:
    usage = "python main [-options] -o output_dir"
    parser = OptionParser(usage)
    parser.add_option("-f", "--fuzzer", dest="fuzzer",
                      help="choose a fuzzer (default: sage)", default="sage")
    parser.add_option("-b", "--browser", dest="browser",
                      help="choose a browser (default: webkitgtk)", default="webkitgtk")
    parser.add_option("-t", "--timeout", dest="timeout",
                      help="timeout of each test (ms) (default: 5000ms)",
                      default=TIMEOUT)
    parser.add_option("-p", "--parallel", dest="parallel",
                      help="how many instances in parallel (default: 1)",
                      default=PARALLEL)
    parser.add_option("-o", "--output_dir", dest="output_dir",
                      help="where the result should output")
    parser.add_option("-e", "--time_to_exit", dest="time_to_exit",
                      help="time to exit the fuzzing (hour)", default=None)
    parser.add_option("-x", "--execution_iteration", dest="execution_iteration",
                      help="exit after this iteration", default=None)
    (options, args) = parser.parse_args()
    if len(args) != 0:
        logging.warning(f"unused arguments: {args}")
    browser_name = os.getenv("BROWSER_GRAMMAR")
    if browser_name is None:
        logging.warning("not set BROWSER_GRAMMAR env var")
        # exit()
    logging.info(f"options: {options}")
    return vars(options)


def get_triage_option() -> dict:
    usage = "TODO: show how to use it"
    parser = OptionParser(usage)
    parser.add_option("-b", "--browser", dest="browser", help="choose a browser",
                      default="webkitgtk")
    parser.add_option("-t", "--timeout", dest="timeout", help="timeout of each test (s)",
                      default=TIMEOUT)
    parser.add_option("-m", "--mode", dest="mode", help="multiple | single; default multiple",
                      default="multiple")
    parser.add_option("-i", "--crash_dir", dest="crash_dir",
                      help="if mode is single, then it will be a file path; if is multiple, "
                           "then it will be a file directory")
    parser.add_option("-p", "--parallel", dest="parallel", help="how many instances in parallel",
                      default=PARALLEL)
    (options, args) = parser.parse_args()
    if len(args) != 0:
        logging.error(f"unused arguments: {args}")
        exit()
    logging.info(f"options: {options}")
    return vars(options)


def get_minimizer_option() -> dict:
    usage = "python minimizer.py -b browser -i input_path -o output_path"
    parser = OptionParser(usage)
    parser.add_option("-b", "--browser", dest="browser", help="choose a browser",
                      default="webkitgtk")
    parser.add_option("-t", "--timeout", dest="timeout",
                      help="timeout of each test (ms) (default: 5000ms)",
                      default=TIMEOUT)
    parser.add_option("-i", "--input", dest="input_path",
                      help="path of the seed you want to minimize")
    parser.add_option("-o", "--output", dest="output_path",
                      help="path you want to save the minimized seed")
    (options, args) = parser.parse_args()
    if len(args) != 0:
        logging.error(f"unused arguments: {args}")
        exit()
    logging.info(f"options: {options}")
    return vars(options)


def get_generation_only_option() -> dict:
    usage = "python fuzzer.py -f <fuzzer> -n <number> -o <output_dir>"
    parser = OptionParser(usage)
    parser.add_option("-f", "--fuzzer", dest="fuzzer",
                      help="choose a fuzzer (default: modified-domato)", default="domato")
    parser.add_option("-n", "--number", dest="number",
                      help="how many test cases we should generate", default="1")
    parser.add_option("-o", "--output", dest="output_dir",
                      help="directory you want to save the output test cases")
    (options, args) = parser.parse_args()
    if len(args) != 0:
        logging.error(f"unused arguments: {args}")
        exit()
    logging.info(f"options: {options}")
    return vars(options)


def get_dry_run_option() -> dict:
    usage = "python dry_run.py -b <browser> -t <timeout> -i <input_dir>"
    parser = OptionParser(usage)
    parser.add_option("-b", "--browser", dest="browser",
                      help="choose a browser (default: webkitgtk)", default="webkitgtk")
    parser.add_option("-t", "--timeout", dest="timeout",
                      help="timeout of each test (ms) (default: 5000ms)",
                      default=TIMEOUT)
    parser.add_option("-i", "--input_dir", dest="input_dir",
                      help="directory which contains test cases")
    (options, args) = parser.parse_args()
    if len(args) != 0:
        logging.error(f"unused arguments: {args}")
        exit()
    logging.info(f"options: {options}")
    return vars(options)
