#!/bin/bash

# Set the path to monitor
#SAGE_PATH=${SAGE_PATH:-"$HOME/SaGe-Browser-Fuzzer"}
MONITOR_PATH="$SAGE_PATH/output/"
LOG_FILE="$MONITOR_PATH/main.log"
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

# Attach to tmux session
tmux attach-session -t $SESSION_NAME
