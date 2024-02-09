#!/bin/bash

# Unlimit the amount of open files
# Retrieve the current limit on open files
current_limit=$(ulimit -n)

# Define the desired minimum limit
desired_limit=100000

# Check if the current limit is less than the desired limit
if [[ "$current_limit" -lt 1025 ]]; then
  echo "Current ulimit for open files ($current_limit) is under 1024. Adjusting it to $desired_limit."

  # Attempt to adjust the limit using prlimit for the current shell
  sudo prlimit --nofile=$desired_limit --pid $$

  # Attempt to adjust the shell's soft limit
  ulimit -n $desired_limit

  # Inform the user of the new limit
  echo "Ulimit adjusted to: $(ulimit -n)"
else
  # Inform the user that no adjustment was needed
  echo "Current ulimit for open files ($current_limit) is sufficient."
fi

# Path to the GDM3 custom configuration file
GDM3_CUSTOM_CONF="/etc/gdm3/custom.conf"
WAYLAND_ENABLED=false
WATCHDOG_PID=0

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
    # Define an array with names of binaries you're targeting for fuzzier matching
    local browser_bin_names=("chrome" "chromedriver" "firefox" "geckodriver" "MiniBrowser" "WebKitWebDriver")
    # Define an array of utilities to exclude from being terminated
    local exclude_utilities=("tmux" "tree" "watch" "lolcat" "stat" "tail" "find" "comm" "basename" "btop" "ifne" "grep" "ps")

    while :; do
        local current_time=$(date +%s)
        local elapsed_time=$((current_time - start_time))

        if [[ -n "$TIMER_PURGE" && "$elapsed_time" -ge "$TIMER_PURGE" ]]; then
            for bin_name in "${browser_bin_names[@]}"; do
                # Use pgrep to list all matching processes, then filter out excludes
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
            break # Exit the loop and stop the watchdog
        fi

        local free_ram=$(awk '/MemAvailable/ {print $2}' /proc/meminfo) # Use MemAvailable for a more accurate reading
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

# Set SAGE_PATH to the directory of this script
SAGE_PATH=$(dirname "$(readlink -f "$0")")

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

# Initialize browsers and their instance counts
declare -A BROWSER_INSTANCES
KILL_OLD=false
WATCHDOG_ENABLED=false

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
        --kill-old)
            KILL_OLD=true
            shift
            ;;
        --watchdog)
            WATCHDOG_ENABLED=true
            shift
            ;;
        *)
            echo "Unsupported option: $1"
            echo "Supported browsers are --firefox, --webkitgtk, and --chromium."
            echo "Specify the number of instances after each browser option."
            echo "Use --kill-old to kill old processes before starting."
            echo "Use --watchdog to enable the RAM monitoring and auto-restart functionality."
            exit 1
            ;;
    esac
done

# If --kill-old was specified, kill old processes
if [ "$KILL_OLD" = true ]; then
    kill_old_processes
fi

# General output directory for logs
GENERAL_OUTPUT_DIR=$SAGE_PATH/output
mkdir -p "$GENERAL_OUTPUT_DIR"
LOG_FILE="$GENERAL_OUTPUT_DIR/main.log"

# If --watchdog was specified, start the watchdog function in the background
if [ "$WATCHDOG_ENABLED" = true ]; then
    watchdog &
    WATCHDOG_PID=$!
fi

# Fuzz each specified browser with its number of instances
for BROWSER in "${!BROWSER_INSTANCES[@]}"
do
    NUM_INSTANCES=${BROWSER_INSTANCES[$BROWSER]}
    PYTHON_OUTPUT_DIR=$SAGE_PATH/output/$BROWSER/$(date +%Y-%m-%d)
    mkdir -p "$PYTHON_OUTPUT_DIR"

    # Start main.py with specified parameters and redirect output to both the log file and terminal
    python3 main.py -t 10000 -b $BROWSER -p $NUM_INSTANCES -o $PYTHON_OUTPUT_DIR 2>&1 | tee -a "$LOG_FILE" &

    # Record the start time and write it to a file
    echo $(date +%s) > "$PYTHON_OUTPUT_DIR/start_time.txt"
done

# Wait for all background processes to finish
wait
