#!/bin/bash

# Function to kill all spawned processes
cleanup() {
    echo "Terminating all spawned processes..."
    kill $(jobs -p) 2>/dev/null
    pkill -P $$  # Kills all processes spawned by this script
}

# Handle Ctrl-C (SIGINT)
trap cleanup SIGINT

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

# Default values
BROWSER="webkitgtk"
NUM_INSTANCES=10

# Check command line arguments
for arg in "$@"
do
    case $arg in
        --firefox)
        BROWSER="firefox"
        shift
        ;;
        --webkitgtk)
        BROWSER="webkitgtk"
        shift
        ;;
        --chrome)
        BROWSER="chrome"
        shift
        ;;
        --number=*)
        NUM_INSTANCES="${arg#*=}"
        shift
        ;;
        *)
        echo "Unsupported option: $arg"
        echo "Supported browsers are --firefox, --webkitgtk, and --chrome."
        echo "Use --number to specify the number of instances."
        exit 1
        ;;
    esac
done

# Start main.py with specified parameters and redirect output to both the log file and terminal
python3 main.py -t 10000 -b $BROWSER -p $NUM_INSTANCES -o $OUTPUT_DIR 2>&1 | tee "$LOG_FILE" &

# Record the start time and write it to a file
echo $(date +%s) > "$OUTPUT_DIR/start_time.txt"

# Wait for main.py to finish
wait
