#!/bin/bash
# Dependency check and install function
install_missing_dependencies() {
    echo "Checking and installing missing dependencies..."
    local dependencies=("tmux" "python3" "python3-pip")
    local missing_deps=()
    local install_cmd=""

    for dep in "${dependencies[@]}"; do
        if ! dpkg -l | grep -qw "$dep"; then
            missing_deps+=("$dep")
        fi
    done

    if [ ${#missing_deps[@]} -gt 0 ]; then
        echo "Missing dependencies: ${missing_deps[*]}"
        sudo apt-get update

        for dep in "${missing_deps[@]}"; do
            echo "Installing $dep..."
            sudo apt-get install -y $dep
            if [ $? -ne 0 ]; then
                echo "Failed to install $dep. Please try to install it manually."
                exit 1
            fi
        done
        echo "All dependencies installed successfully."
    else
        echo "All dependencies are already installed."
    fi
}

# Run the dependency check and installation
install_missing_dependencies


#if [ "$(id -u)" != "0" ]; then echo "This script must be run as root" >&2; exit 1; fi
# Set SAGE_PATH to the directory of this script
SAGE_PATH=$(dirname "$(readlink -f "$0")")

# Unlimit the amount of open files
current_limit=$(ulimit -n)
[[ "$(lsb_release -rs)" > "22" ]] && export WEBKIT_DISABLE_COMPOSITING_MODE=1

# Define the desired minimum limit
desired_limit=80000

# Path to the GDM3 custom configuration file
GDM3_CUSTOM_CONF="/etc/gdm3/custom.conf"
WAYLAND_ENABLED=false
WATCHDOG_PID=0

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
export FREEDOM_PATH="$SAGE_PATH/freedom/main.py"

export FREEDOM_PATH="$SAGE_PATH/freedom/main.py"
export ORIGAMI_PATH="/home/user/SaGe-Browser-Fuzzer/origami/bin/"
export FAVOCADO_PATH="/home/user/SaGe-Browser-Fuzzer/favocado/Generator/Run/"

# Check for webkit deps
dpkg -l | grep -qw libwebkitgtk-6.0-4 || (sudo apt-get update && sudo apt-get install -y libwebkitgtk-6.0-4)
dpkg -l | grep -qw libavif-dev || (sudo apt-get update && sudo apt-get install -y libavif-dev)

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

# Function to kill all spawned processes, browser processes, and any process from SAGE_PATH
cleanup() {
    echo "Terminating all spawned processes, browser processes, any process from SAGE_PATH, and the watchdog..."

    # Kills jobs spawned by this script
    kill $(jobs -p) 2>/dev/null

    # Kills all child processes spawned by this script
    pkill -P $$ 2>/dev/null

    # Explicitly kill processes started from SAGE_PATH
    pkill -f "$SAGE_PATH" 2>/dev/null && pkill tmux

    # If watchdog is running, kill it
    if [ $WATCHDOG_PID -ne 0 ]; then
        kill -9 $WATCHDOG_PID 2>/dev/null
        echo "Watchdog (PID $WATCHDOG_PID) terminated."
    fi
}

# Function to kill old processes from SAGE_PATH before starting new ones
kill_old_processes() {
    echo "Killing old processes started from $SAGE_PATH..."
    pkill -f "$SAGE_PATH" 2>/dev/null
}

# Function to monitor system memory, restart browser bins/drivers if needed, and auto-kill processes after a set timeout
watchdog() {
    local start_time=$(date +%s)
    local browser_bin_names=("chrome" "chromedriver" "firefox" "geckodriver" "MiniBrowser" "WebKitWebDriver")
    local exclude_utilities=("tmux" "tree" "watch" "lolcat" "stat" "tail" "find" "comm" "basename" "btop" "ifne" "grep" "ps")

    while :; do
        local current_time=$(date +%s)
        local elapsed_time=$((current_time - start_time))

        if [[ -n "$TIMER_PURGE" && "$elapsed_time" -ge "$TIMER_PURGE" ]]; then
            echo "Timer purge limit reached. Performing cleanup..."
            for bin_name in "${browser_bin_names[@]}"; do
                for pid in $(pgrep -f "$bin_name"); do
                    local cmd=$(ps -p $pid -o comm=)
                    local exclude=false
                    for exclude_cmd in "${exclude_utilities[@]}"; do
                        if [[ "$cmd" == *"$exclude_cmd"* ]]; then
                            exclude=true
                            break
                        fi
                    done
                    if [ "$exclude" = false ]; then
                        kill -9 $pid 2>/dev/null
                    fi
                done
            done
            start_time=$(date +%s)
        fi

        local free_ram=$(awk '/MemAvailable/ {print $2}' /proc/meminfo)
        local available_ram_mb=$((free_ram/1024))
        if [[ "$available_ram_mb" -lt 2000 ]]; then
            for bin_name in "${browser_bin_names[@]}"; do
                for pid in $(pgrep -f "$bin_name"); do
                    local cmd=$(ps -p $pid -o comm=)
                    local exclude=false
                    for exclude_cmd in "${exclude_utilities[@]}"; do
                        if [[ "$cmd" == *"$exclude_cmd"* ]]; then
                            exclude=true
                            break
                        fi
                    done
                    if [ "$exclude" = false ]; then
                        kill -9 $pid 2>/dev/null
                    fi
                done
            done
        fi
        sleep 5
    done
}

# Handle Ctrl-C (SIGINT) and script exit (EXIT)
trap cleanup SIGINT EXIT

# Initialize the fuzzer variable with a default value
FUZZER="sage"

# Initialize browsers and their instance counts
declare -A BROWSER_INSTANCES
KILL_OLD=false
WATCHDOG_ENABLED=false
TIMER_PURGE=""

# General output directory for logs
GENERAL_OUTPUT_DIR=$SAGE_PATH/output
mkdir -p "$GENERAL_OUTPUT_DIR"
LOG_FILE="$GENERAL_OUTPUT_DIR/main.log"

# Function to check and trim the log file
# Set default log size limit (in MB)
LOG_SIZE_LIMIT=${LOG_SIZE_LIMIT:-500}
USE_LOLCAT=true
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

# Start trimming log file in the background
trim_log_file &

# Check command line arguments
while (( "$#" )); do
    case "$1" in
        --firefox|--webkitgtk|--chromium)
            BROWSER=${1#--}
            if [[ -n "$2" && "$2" =~ ^[0-9]+$ ]]; then
                BROWSER_INSTANCES[$BROWSER]=$2
                shift 2
            else
                echo "Error: Expected a number of instances after $1"
                exit 1
            fi
            ;;
        --fuzzer)
            if [[ -n "$2" && "$2" =~ ^(domato|minerva|freedom|sage|favocado)$ ]]; then
                FUZZER=$2
                shift 2
            else
                echo "Error: Unsupported fuzzer. Supported fuzzers are domato, minerva, freedom, sage, and favocado."
                exit 1
            fi
            ;;
        --kill-old)
            KILL_OLD=true
            shift
            ;;
        --watchdog)
            WATCHDOG_ENABLED=true
            shift
            ;;
        --timerpurge)
            if [[ -n "$2" && "$2" =~ ^[0-9]+$ ]]; then
                TIMER_PURGE=$2
                shift 2
            else
                echo "Error: Expected a numeric value for --timerpurge"
                exit 1
            fi
            ;;
        *)
            echo "Unsupported option: $1"
            exit 1
            ;;
    esac
done

# If --kill-old was specified, kill old processes
if [ "$KILL_OLD" = true ]; then
    kill_old_processes
fi

# If --watchdog was specified, start the watchdog function in the background
if [ "$WATCHDOG_ENABLED" = true ]; then
    watchdog &
    WATCHDOG_PID=$!
fi

# Function to generate a unique output directory
generate_unique_output_dir() {
    local browser_name=$1
    local datetime=$(date +%Y-%m-%d-%H-%M-%S)
    local uid=$(uuidgen | cut -d'-' -f1) # Generates a short UID from uuidgen
    local output_dir="$SAGE_PATH/output/$browser_name/$datetime-$uid"
    echo $output_dir
}

# Replace the section where PYTHON_OUTPUT_DIR is set with the below code
# This ensures a unique directory is created for each session

# Initialize browsers and their instance counts
declare -A BROWSER_INSTANCES
KILL_OLD=false
WATCHDOG_ENABLED=false
TIMER_PURGE=""

# General output directory for logs and modification for unique output directories
GENERAL_OUTPUT_DIR=$SAGE_PATH/output
mkdir -p "$GENERAL_OUTPUT_DIR"
LOG_FILE="$GENERAL_OUTPUT_DIR/main.log"

# Start trimming log file in the background function (if previously defined in your script)
trim_log_file &

# Check command line arguments and setup (Keep your existing argument parsing logic here)

# Logic to start fuzzing sessions with unique output directories
for BROWSER in "${!BROWSER_INSTANCES[@]}"
do
    NUM_INSTANCES=${BROWSER_INSTANCES[$BROWSER]}
    # Generate a unique output directory for this session
    PYTHON_OUTPUT_DIR=$(generate_unique_output_dir $BROWSER)
    mkdir -p "$PYTHON_OUTPUT_DIR"

    # Start main.py with specified parameters and redirect output to both the log file and terminal
    python3 $SAGE_PATH/main.py -t 50000 -b $BROWSER -p $NUM_INSTANCES --fuzzer $FUZZER -o $PYTHON_OUTPUT_DIR 2>&1 | tee -a "$LOG_FILE" &

    # Record the start time and write it to a file
    echo $(date +%s) > "$PYTHON_OUTPUT_DIR/start_time.txt"
done

# Wait for all background processes to finish
wait
