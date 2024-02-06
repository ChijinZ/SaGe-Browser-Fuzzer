#!/bin/bash

# Set SAGE_PATH to the directory of this script
SAGE_PATH=$(dirname $(readlink -f $0))

export COLLECT_TREE_INFO=true
export USE_INVALID_TREE=true
export PRINT_TIME=true
export INVALID_TREE_PATH="$SAGE_PATH/invalid_tree/invalid_tree.pickle"
export RULE_INFO_PATH="$SAGE_PATH/invalid_tree/global_info.pickle"

# Define the output directory and log file
OUTPUT_DIR=$PWD/output
LOG_FILE="$OUTPUT_DIR/main.log"

# Default browser
BROWSER="webkitgtk"

# Check command line arguments for browser choice
for arg in "$@"
do
    case $arg in
        --firefox)
        BROWSER="firefox"
        shift # Remove --firefox from processing
        ;;
        --webkitgtk)
        BROWSER="webkitgtk"
        shift # Remove --webkitgtk from processing
        ;;
        --chrome)
        BROWSER="chrome"
        shift # Remove --chrome from processing
        ;;
        *)
        # Unsupported browser
        echo "Unsupported browser option: $arg"
        echo "Supported browsers are --firefox, --webkitgtk, and --chrome."
        exit 1
        ;;
    esac
done

# Function to kill all spawned processes
cleanup() {
    echo "Cleaning up spawned processes..."
    # Kill the process group of the script to stop all child processes
    kill -- -$$
}

# Set trap for SIGINT
trap 'cleanup' SIGINT

# Start main.py with specified parameters and redirect output to both the log file and terminal
python3 main.py -t 10000 -b $BROWSER -p 10 -o $OUTPUT_DIR 2>&1 | tee "$LOG_FILE" &

# Record the start time and write it to a file
echo $(date +%s) > "$OUTPUT_DIR/start_time.txt"

# Wait for main.py to finish
wait
