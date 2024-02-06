#!/bin/bash

# Set default log size limit (in MB)
LOG_SIZE_LIMIT=${LOG_SIZE_LIMIT:-500}

# Parse command line arguments for --logsize
for arg in "$@"
do
    case $arg in
        --logsize=*)
        LOG_SIZE_LIMIT="${arg#*=}"
        shift
        ;;
    esac
done

# Function to check and trim the log file
trim_log_file() {
    local max_size=$((LOG_SIZE_LIMIT * 1024 * 1024)) # Convert MB to bytes
    while true; do
        local file_size=$(stat -c%s "$LOG_FILE")
        if (( file_size > max_size )); then
            echo "Trimming $LOG_FILE (size: $file_size, limit: $max_size)"
            tail -c "$max_size" "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"
        fi
        sleep 60 # Check every 60 seconds
    done
}

# Start log trimming in background
SAGE_PATH=${SAGE_PATH:-"$HOME/SaGe-Browser-Fuzzer"}
LOG_FILE="$SAGE_PATH/output/main.log"
trim_log_file &

# Set the path to monitor
MONITOR_PATH="$SAGE_PATH/output/"
INITIAL_STATE_FILE="/tmp/initial_state.txt"
CURRENT_STATE_FILE="/tmp/current_state.txt"

# Create an initial state file
find "$MONITOR_PATH" -type f | sort > "$INITIAL_STATE_FILE"

# Start a new tmux session
SESSION_NAME="monitoring"
tmux new-session -d -s $SESSION_NAME

# Split tmux window horizontally for directory summary and file monitoring
tmux split-window -h

# Split the second pane horizontally for main.py output
tmux split-window -t $SESSION_NAME.1 -v

# Directory Summary in Pane 0 (Colorized Tree of All Current Files, Recursively)
tmux send-keys -t $SESSION_NAME.0 "watch -n 10 'tree \"$MONITOR_PATH\"' | lolcat" C-m

# New Files in Output Directory in Pane 1 (Colorized, Only Filenames, Recursively)
tmux send-keys -t $SESSION_NAME.1 "echo 'New Findings' | lolcat; watch -n 10 'find \"$MONITOR_PATH\" -type f | sort > \"$CURRENT_STATE_FILE\"; comm -13 \"$INITIAL_STATE_FILE\" \"$CURRENT_STATE_FILE\" | while read line; do basename \"\$line\"; done' | lolcat" C-m

# Main.py Output in Pane 2 (Colorized)
tmux send-keys -t $SESSION_NAME.2 "tail -f $LOG_FILE | lolcat" C-m

# Add tmux key binding for closing all windows and clearing terminal
tmux bind-key C-k run-shell "tmux kill-session; clear"

# Attach to tmux session
tmux attach-session -t $SESSION_NAME
