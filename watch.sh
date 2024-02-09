#!/bin/bash


# Path to the GDM3 custom configuration file
GDM3_CUSTOM_CONF="/etc/gdm3/custom.conf"
WAYLAND_ENABLED=false

# Function to check Wayland in GDM3 configuration
check_gdm3_conf() {
    if [ -f "$GDM3_CUSTOM_CONF" ]; then
        if grep -E "^[^#]*WaylandEnable=false" "$GDM3_CUSTOM_CONF" &>/dev/null; then
            echo "Wayland is already disabled in GDM3 configuration."
        elif grep -E "^[^#]*WaylandEnable=true" "$GDM3_CUSTOM_CONF" &>/dev/null; then
            echo "Wayland is enabled in GDM3 configuration. Please disable it to prevent instability when fuzzing."
            WAYLAND_ENABLED=true
        else
            echo "Wayland setting not found in GDM3 configuration. If you are using Wayland, please disable it to prevent instability when fuzzing."
        fi
    else
        echo "GDM3 custom configuration file not found. Skipping..."
    fi
}

# Function to check Wayland in environment variables
check_env_vars() {
    if [ "$XDG_SESSION_TYPE" == "wayland" ] || [ "$WAYLAND_DISPLAY" != "" ]; then
        echo "Wayland session detected via environment variables. Please switch to an X11 session to prevent instability when fuzzing."
        WAYLAND_ENABLED=true
    fi
}

# Execute checks
check_gdm3_conf
check_env_vars

# Final decision
if $WAYLAND_ENABLED; then
    echo "To disable Wayland in GDM3, edit /etc/gdm3/custom.conf and set 'WaylandEnable=false' or comment out the line."
    echo "Then, restart your system or log out and select an X11 session from the login screen."
    exit 1
else
    echo "Continuing with the script..."
fi

# Check if apport is installed
if dpkg-query -W -f='${Status}' apport 2>/dev/null | grep -q "install ok installed"; then
    echo "Apport is currently installed on your system. This can get messy."
    echo "Please uninstall apport before proceeding with this script."
    echo "You can uninstall apport by running: sudo apt-get remove --purge apport"
    exit 1
else
    echo "apport is not installed, proceeding..."
fi


# Dependency list
declare -a dependencies=("tmux" "tree" "watch" "lolcat" "stat" "tail" "find" "comm" "basename" "btop" "ifne")

# Function to check and install missing dependencies
check_and_install_deps() {
    local missing_deps=()
    for dep in "${dependencies[@]}"; do
        # Special handling for 'ifne' which is part of 'moreutils'
        if [[ $dep == "ifne" ]]; then
            if ! command -v $dep &> /dev/null; then
                missing_deps+=("moreutils")
            fi
        elif ! command -v $dep &> /dev/null; then
            missing_deps+=($dep)
        fi
    done

    if [ ${#missing_deps[@]} -ne 0 ]; then
        echo "Missing dependencies: ${missing_deps[*]}"
        echo "Attempting to install missing dependencies..."
        # Attempt to detect package manager
        if command -v apt-get &> /dev/null; then
            sudo apt-get update
            for dep in "${missing_deps[@]}"; do
                # Special handling for 'ifne' which is part of 'moreutils'
                [[ $dep == "ifne" ]] && dep="moreutils"
                sudo apt-get install -y $dep
            done
        elif command -v yum &> /dev/null; then
            sudo yum update
            for dep in "${missing_deps[@]}"; do
                [[ $dep == "ifne" ]] && dep="moreutils"
                sudo yum install -y $dep
            done
        elif command -v brew &> /dev/null; then
            for dep in "${missing_deps[@]}"; do
                [[ $dep == "ifne" ]] && dep="moreutils"
                brew install $dep
            done
        else
            echo "Unsupported package manager. Please install the missing dependencies manually."
            exit 1
        fi
    fi
}

# Run the dependency check and install function
check_and_install_deps

# Set default log size limit (in MB)
LOG_SIZE_LIMIT=${LOG_SIZE_LIMIT:-500}
USE_LOLCAT=true

# Parse command line arguments for --logsize and --boring
for arg in "$@"
do
    case $arg in
        --logsize=*)
        LOG_SIZE_LIMIT="${arg#*=}"
        shift
        ;;
        --boring)
        USE_LOLCAT=false
        shift
        ;;
    esac
done

decorate_cmd() {
    if [ "$USE_LOLCAT" = true ]; then
        echo "$1 | lolcat"
    else
        echo "$1"
    fi
}

# Function to check and trim the log file
trim_log_file() {
    local max_size=$((LOG_SIZE_LIMIT * 1024 * 1024)) # Convert MB to bytes
    while true; do
        local file_size=$(stat -c%s "$LOG_FILE" 2>/dev/null || echo 0)
        if (( file_size > max_size )); then
            echo "Trimming $LOG_FILE (size: $file_size, limit: $max_size)"
            tail -c "$max_size" "$LOG_FILE" > "$LOG_FILE.tmp"
            if [ -s "$LOG_FILE.tmp" ]; then
                mv "$LOG_FILE.tmp" "$LOG_FILE"
            else
                echo "Temporary file not created or is empty, skipping move operation."
            fi
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

# Split the first pane (Pane 0) vertically for btop
tmux split-window -t $SESSION_NAME.0 -v

# Split the third pane (originally second before adding btop) horizontally for main.py output
tmux split-window -t $SESSION_NAME.2 -v

# Directory Summary in Pane 0
tmux send-keys -t $SESSION_NAME.0 "$(decorate_cmd "watch -n 1 'pgrep -afl \"chrome|chromium|webkitgtk|webkit|webdriver|geckodriver|chromedriver|generator.py\" | grep -Ev \"watch|sed\" | sed -e \"s@.*/@@\" -e \"s/chrome$/🌏 &/\" -e \"s/chromium$/🌐 &/\" -e \"s/webkitgtk$/🌍 &/\" -e \"s/webkit$/🌍 &/\" -e \"s/webdriver$/🚗 &/\" -e \"s/geckodriver$/🦊 &/\" -e \"s/chromedriver$/🌈 &/\" -e \"s/generator.py$/⚙️ &/\" | pr -T -2'")" C-m






# btop in Pane 1
tmux send-keys -t $SESSION_NAME.1 "btop" C-m

# Define browser names and corresponding emojis
declare -A browser_emojis=(
    ["webkit"]="🌐 WebKit"
    ["firefox"]="🦊 Firefox"
    ["chromium"]="🌏 Chrome"
)

# New Files in Output Directory in Pane 2 (Timestamp Fixed, Corrected Order, and Logging)

tmux send-keys -t $SESSION_NAME.2 "$(decorate_cmd "echo 'New Findings'; watch -n 1 'find \"$MONITOR_PATH\" -type f -name \"*.html\" | sort > \"$CURRENT_STATE_FILE\"; comm -13 \"$INITIAL_STATE_FILE\" \"$CURRENT_STATE_FILE\" | while IFS= read -r line; do browser=\"\"; case \"\$line\" in *chromium*) browser=\"Chromium CRASHED! 🌏\";; *webkitgtk*) browser=\"WebKitGTK CRASHED! 🌐\";; *firefox*) browser=\"Firefox CRASHED! 🦊\";; esac; relative_path=\${line#$SAGE_PATH/}; crash_message=\"🎉 \$browser - Location: \$relative_path\"; echo \"\$crash_message\"; echo \"\$crash_message\" >> \"$SAGE_PATH/results.txt\"; done'")" C-m





# Main.py Output in Pane 3
tmux send-keys -t $SESSION_NAME.3 "$(decorate_cmd "tail -f $LOG_FILE")" C-m

# Function to perform cleanup
cleanup() {
    tmux list-sessions | awk 'BEGIN{FS=":"}{print $1}' | ifne xargs -n 1 tmux kill-session -t
    clear
    echo "Cleaned up all tmux sessions."
    exit
}

# Set the trap for Ctrl-C (SIGINT) now that the script has control
trap cleanup SIGINT

# Detach from tmux session to allow the script to continue running and catch signals
tmux detach-client -s $SESSION_NAME

# Attach to tmux session in a way that allows the script to capture Ctrl-C
tmux attach-session -t $SESSION_NAME

# Optionally, call cleanup function here if you want to ensure cleanup happens
# even if the script exits without Ctrl-C interruption
cleanup
