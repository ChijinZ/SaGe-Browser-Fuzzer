#!/bin/bash

# Function to kill all spawned processes and specific browser processes
cleanup() {
    echo "Terminating all spawned processes and browser processes..."
    kill $(jobs -p) 2>/dev/null
    pkill -P $$  # Kills all processes spawned by this script

    # Killing specific browser processes
    pkill -f "python3 webkit" 2>/dev/null
    pkill -f "WebKitWebProcess" 2>/dev/null
    pkill -f "chromeChrome" 2>/dev/null
    pkill -f "firefox" 2>/dev/null
}

# Handle Ctrl-C (SIGINT)
trap cleanup SIGINT

# Set SAGE_PATH to the directory of this script
SAGE_PATH=$(dirname $(readlink -f $0))

# Export environment variables
export COLLECT_TREE_INFO=true
export USE_INVALID_TREE=true
export PRINT_TIME=true
export INVALID_TREE_PATH="$SAGE_PATH/invalid_tree/invalid_tree.pickle"
export RULE_INFO_PATH="$SAGE_PATH/invalid_tree/global_info.pickle"
export CHROMIUM_PATH="$SAGE_PATH/browser_bins/chrome-asan/chrome"
export CHROMEDRIVER_PATH="$SAGE_PATH/browser_bins/chromedriver"
export FIREFOX_PATH="$SAGE_PATH/browser_bins/firefox-asan/firefox"
export FIREFOXDRIVER_PATH="$SAGE_PATH/browser_bins/geckodriver"
export WEBKIT_BINARY_PATH="$SAGE_PATH/browser_bins/MiniBrowser"
export WEBKIT_WEBDRIVER_PATH="$SAGE_PATH/browser_bins/WebKitWebDriver"

# Default values
NUM_INSTANCES=10
TODAYS_DATE=$(date +%Y-%m-%d)
BROWSERS=()

# Check command line arguments
for arg in "$@"
do
    case $arg in
        --firefox)
        BROWSERS+=("firefox")
        ;;
        --webkitgtk)
        BROWSERS+=("webkitgtk")
        ;;
        --chromium)
        BROWSERS+=("chromium")
        ;;
        --number=*)
        NUM_INSTANCES="${arg#*=}"
        ;;
        *)
        echo "Unsupported option: $arg"
        echo "Supported browsers are --firefox, --webkitgtk, and --chromium."
        echo "Use --number to specify the number of instances."
        exit 1
        ;;
    esac
done

# Fuzz each browser in the background
for BROWSER in "${BROWSERS[@]}"
do
    PYTHON_OUTPUT_DIR=$PWD/output/$BROWSER/$TODAYS_DATE
    mkdir -p "$PYTHON_OUTPUT_DIR"
    LOG_FILE="$SAGE_PATH/output/${BROWSER}_main.log"

    # Start main.py with specified parameters and redirect output to both the log file and terminal
    python3 main.py -t 10000 -b $BROWSER -p $NUM_INSTANCES -o $PYTHON_OUTPUT_DIR 2>&1 | tee "$LOG_FILE" &

    # Record the start time and write it to a file
    echo $(date +%s) > "$PYTHON_OUTPUT_DIR/start_time.txt"
done

# Wait for all background processes to finish
wait