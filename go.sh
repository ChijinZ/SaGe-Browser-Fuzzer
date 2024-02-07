#!/bin/bash

# Function to kill all spawned processes, browser processes, and any process from SAGE_PATH
cleanup() {
    echo "Terminating all spawned processes, browser processes, and any process from SAGE_PATH..."

    # Kills jobs spawned by this script
    kill $(jobs -p) 2>/dev/null

    # Kills all child processes spawned by this script
    pkill -P $$ 2>/dev/null

    # Explicitly kill processes started from SAGE_PATH
    pkill -f "$SAGE_PATH" 2>/dev/null
}

# Function to kill old processes from SAGE_PATH before starting new ones
kill_old_processes() {
    echo "Killing old processes started from $SAGE_PATH..."
    pkill -f "$SAGE_PATH" 2>/dev/null
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
export FIREFOXDRIVER_PATH="$SAGE_PATH/browser_bins/firefox-asan/geckodriver"
export WEBKIT_BINARY_PATH="$SAGE_PATH/browser_bins/webkit/MiniBrowser"
export WEBKIT_WEBDRIVER_PATH="$SAGE_PATH/browser_bins/webkit/WebKitWebDriver"

# Default values
NUM_INSTANCES=15
TODAYS_DATE=$(date +%Y-%m-%d)
BROWSERS=()
KILL_OLD=false

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
        --kill-old)
            KILL_OLD=true
            ;;
        *)
            echo "Unsupported option: $arg"
            echo "Supported browsers are --firefox, --webkitgtk, and --chromium."
            echo "Use --number to specify the number of instances."
            echo "Use --kill-old to kill old processes before starting."
            exit 1
            ;;
    esac
done

# If --kill-old was specified, kill old processes
if [ "$KILL_OLD" = true ]; then
    kill_old_processes
fi

# Fuzz each browser in the background
for BROWSER in "${BROWSERS[@]}"
do
    PYTHON_OUTPUT_DIR=$PWD/output/$BROWSER/$TODAYS_DATE
    mkdir -p "$PYTHON_OUTPUT_DIR"
    LOG_FILE="$SAGE_PATH/output/main.log"

    # Start main.py with specified parameters and redirect output to both the log file and terminal
    python3 main.py -t 10000 -b $BROWSER -p $NUM_INSTANCES -o $PYTHON_OUTPUT_DIR 2>&1 | tee "$LOG_FILE" &

    # Record the start time and write it to a file
    echo $(date +%s) > "$PYTHON_OUTPUT_DIR/start_time.txt"
done

# Wait for all background processes to finish
wait
