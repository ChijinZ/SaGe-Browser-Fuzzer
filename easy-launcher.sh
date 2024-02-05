#!/bin/bash

export COLLECT_TREE_INFO=true
export USE_INVALID_TREE=true
export PRINT_TIME=true
export INVALID_TREE_PATH="$SAGE_PATH/invalid_tree/invalid_tree.pickle"
export RULE_INFO_PATH="$SAGE_PATH/invalid_tree/global_info.pickle"

# Define the output directory and log file
OUTPUT_DIR=$PWD/output
LOG_FILE="$OUTPUT_DIR/main.log"

# Start main.py with specified parameters and redirect output to both the log file and terminal
python3 main.py -t 10000 -b webkitgtk -p 10 -o $OUTPUT_DIR 2>&1 | tee "$LOG_FILE" &

# Record the start time and write it to a file
echo $(date +%s) > "$OUTPUT_DIR/start_time.txt"

# Wait for main.py to finish
wait
