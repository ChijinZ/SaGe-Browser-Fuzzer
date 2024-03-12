#!/bin/bash

# Check for and install missing dependencies
install_missing_deps() {
    local missing_deps=""

    # List of essential commands and their corresponding packages
    declare -A essential_cmds=( ["dialog"]="dialog" ["sudo"]="sudo" ["git"]="git" ["wget"]="wget" ["cmake"]="cmake" ["ninja-build"]="ninja-build" ["apt-get"]="apt" )

    # Check each command and record missing ones
    for cmd in "${!essential_cmds[@]}"; do
        if ! command -v $cmd &> /dev/null; then
            missing_deps+="${essential_cmds[$cmd]} "
        fi
    done

    # Install missing dependencies, if any
    if [ -n "$missing_deps" ]; then
        echo "The following dependencies are missing and will be installed: $missing_deps"
        sudo apt-get update
        sudo apt-get install -y $missing_deps
    else
        echo "All essential dependencies are already installed."
    fi
}

# Initial setup
clear
echo "Checking and installing missing dependencies..."
install_missing_deps

# Request sudo access at the beginning
echo "Requesting administrative access for initial setup..."
sudo -v
while true; do sudo -n true; sleep 60; kill -0 "$$" || exit; done 2>/dev/null &

# Function to execute commands within dialog boxes, showing output in a progress box
execute_command() {
    local cmd=$1
    local title=$2
    dialog --title "$title" --infobox "Preparing execution..." 10 70
    eval "$cmd" 2>&1 | dialog --title "$title" --progressbox 50 100
}

# Function to display welcome message using dialog
welcome_message() {
    dialog --clear --title "Welcome" --msgbox "Welcome to the Setup Wizard. This will guide you through setting up the environment." 10 50
}

# Function to get WebKitGTK version from the user
get_webkitgtk_version() {
    WEBKITGTK_VERSION=$(dialog --title "WebKitGTK Version" --inputbox "Enter the version of WebKitGTK you want to build:" 8 40 "2.42.5" 2>&1 >/dev/tty)
}

# Function to show build options menu and capture selections
show_build_options_menu() {
    BUILD_OPTIONS=$(dialog --checklist "Choose build options:" 22 76 15 \
    "ENABLE_BUBBLEWRAP_SANDBOX" "Bubblewrap Sandbox" ON \
    "ENABLE_DOCUMENTATION" "Documentation" OFF \
    "ENABLE_DRAG_SUPPORT" "Drag Support" ON \
    "ENABLE_GAMEPAD" "Gamepad Support" ON \
    "ENABLE_INTROSPECTION" "Introspection" ON \
    "ENABLE_JOURNALD_LOG" "Journald Log" ON \
    "ENABLE_MINIBROWSER" "Mini Browser" ON \
    "ENABLE_PDFJS" "PDF.js" ON \
    "ENABLE_QUARTZ_TARGET" "Quartz Target" OFF \
    "ENABLE_SPELLCHECK" "Spellcheck" ON \
    "ENABLE_TOUCH_EVENTS" "Touch Events" ON \
    "ENABLE_VIDEO" "Video" ON \
    "ENABLE_WAYLAND_TARGET" "Wayland Target" ON \
    "ENABLE_WEBDRIVER" "WebDriver" ON \
    "ENABLE_WEB_AUDIO" "Web Audio" ON \
    "ENABLE_WEB_CRYPTO" "Web Crypto" ON \
    "ENABLE_X11_TARGET" "X11 Target" ON \
    "USE_AVIF" "AVIF Images" ON \
    "USE_GBM" "GBM" ON \
    "USE_GSTREAMER_TRANSCODER" "GStreamer Transcoder" ON \
    "USE_GSTREAMER_WEBRTC" "GStreamer WebRTC" OFF \
    "USE_GTK4" "GTK4" OFF \
    "USE_JPEGXL" "JPEG XL" ON \
    "USE_LCMS" "Little CMS" ON \
    "USE_LIBHYPHEN" "LibHyphen" ON \
    "USE_LIBSECRET" "Libsecret" ON \
    "USE_OPENGL_OR_ES" "OpenGL or ES" ON \
    "USE_OPENJPEG" "OpenJPEG" ON \
    "USE_SOUP2" "Soup2" OFF \
    "USE_WOFF2" "WOFF2 Fonts" ON 2>&1 >/dev/tty)
}

# Install all required packages at once, silently, with no user interaction
install_packages() {
    packages="libgcrypt20 libgcrypt20-dev libtasn1-6 libtasn1-6-dev unifdef libwebp-dev libgtk-4-dev libsoup3-dev libsoup3 libsoup-3.0-dev libmanette-0.2-dev libxslt1-dev libsecret-1-dev libdrm-dev libgbm-dev libenchant-2-dev libjxl-dev afl++ libstdc++-11-dev build-essential clang llvm-17 libstdc++-12-dev libhyphen-dev libwoff-dev libavif-dev libsystemd-dev liblcms2-dev libgcc-11-dev libseccomp-dev libgstreamer-plugins-base1.0-dev gstreamer1.0-plugins-base gstreamer1.0-plugins-good libgstreamer1.0-dev gstreamer1.0-libav gstreamer1.0-plugins-bad libgstreamer-plugins-bad1.0-dev gstreamer1.0-plugins-good libgstrtspserver-1.0-dev gperf gettext libxt-dev libopenjp2-7-dev gi-docgen libwebkit2gtk-4.1-dev ninja-build"
    execute_command "sudo apt-get update && sudo apt-get install -y $packages" "Installing required packages"
}

# Function to clone, build, and install dependencies
git_clone_and_setup() {
    local git_url=$1
    local folder_name=$2
    local setup_commands=$3
    local title=$4
    execute_command "rm -rf $folder_name && git clone $git_url $folder_name --recursive --shallow-submodules && cd $folder_name && $setup_commands" "$title"
}

# Welcome the user and get necessary input
welcome_message

# Function to create a swapfile
create_swapfile() {
    # Ask user for the swapfile size and location
    SWAPFILE_DETAILS=$(dialog --title "Swapfile Configuration" --form "Enter the details for the swapfile:" 15 50 0 \
    "Size (e.g., 128G):" 1 1 "128G" 1 25 25 0 \
    "Location (path):" 2 1 "$(pwd)/swapfile" 2 25 100 0 \
    2>&1 >/dev/tty)

    # Parse input
    SWAPFILE_SIZE=$(echo "$SWAPFILE_DETAILS" | sed -n 1p)
    SWAPFILE_LOCATION=$(echo "$SWAPFILE_DETAILS" | sed -n 2p)

    # Remove existing swapfile if it exists
    [ -f "$SWAPFILE_LOCATION" ] && sudo swapoff "$SWAPFILE_LOCATION" && rm -f "$SWAPFILE_LOCATION"

    # Create new swapfile
    execute_command "sudo fallocate -l $SWAPFILE_SIZE $SWAPFILE_LOCATION && sudo chmod 600 $SWAPFILE_LOCATION && sudo mkswap $SWAPFILE_LOCATION && sudo swapon $SWAPFILE_LOCATION" "Creating Swapfile"
    
    # Confirmation message
    dialog --title "Swapfile Creation" --msgbox "Swapfile created successfully at $SWAPFILE_LOCATION with a size of $SWAPFILE_SIZE." 10 50
}

# Create swapfile as part of the setup process
create_swapfile

get_webkitgtk_version
show_build_options_menu

# Install essential packages
install_packages

# Clone and setup libjxl
git_clone_and_setup "https://github.com/libjxl/libjxl.git" "libjxl" "sudo apt install -y cmake pkg-config libbrotli-dev libgif-dev libjpeg-dev libopenexr-dev libpng-dev libwebp-dev clang && export CC=clang CXX=clang++ && mkdir build && cd build && cmake -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF .. && cmake --build . -- -j\$(nproc) && sudo cmake --install ." "Setting up libjxl"

# Clone and setup libbacktrace
git_clone_and_setup "https://github.com/ianlancetaylor/libbacktrace" "libbacktrace" "./configure && make && sudo make install" "Installing libbacktrace"

# Convert dialog output to CMake and Ninja build options
CONVERTED_OPTIONS=""
IFS=' ' read -ra ADDR <<< "$BUILD_OPTIONS"
for option in "${ADDR[@]}"; do
    if [[ "$option" == "\"USE_WPE_RENDERER\"" ]]; then
        CONVERTED_OPTIONS+="-DUSE_WPE_RENDERER=ON "
    else
        CONVERTED_OPTIONS+="-D${option//\"/}=ON "
    fi
done

# Build and install WebKitGTK using Ninja as per user-selected options, removing any previous extracted folder
BUILD_COMMAND="rm -rf webkitgtk-${WEBKITGTK_VERSION} && wget https://webkitgtk.org/releases/webkitgtk-${WEBKITGTK_VERSION}.tar.xz && tar xf webkitgtk-${WEBKITGTK_VERSION}.tar.xz && cd webkitgtk-${WEBKITGTK_VERSION} && mkdir build && cd build && cmake -DCMAKE_BUILD_TYPE=Debug -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_SKIP_RPATH=ON -DPORT=GTK -DLIB_INSTALL_DIR=/usr $CONVERTED_OPTIONS -Wno-dev -G Ninja .. && ninja && sudo ninja install"
execute_command "$BUILD_COMMAND" "Building and installing WebKitGTK ${WEBKITGTK_VERSION} with Ninja"

# Function to remove a swapfile
remove_swapfile() {
    local location=$(dialog --title "Remove Swapfile" --inputbox "Enter the location of the swap file to remove:" 8 40 "./swapfile" 2>&1 >/dev/tty)

    if [ -f "$location" ]; then
        # Deactivate the swapfile
        sudo swapoff "$location"

        # Remove the swapfile
        rm -f "$location"

        # Display completion message
        dialog --title "Swapfile Removal" --msgbox "Swapfile removed successfully from $location." 10 50
    else
        dialog --title "Swapfile Removal" --msgbox "Swapfile not found at $location." 10 50
    fi
}

# Optionally remove the swapfile as part of the cleanup process
# remove_swapfile

# Final message to indicate completion
dialog --clear --title "Completion" --msgbox "All steps completed successfully. Your environment is now set up." 10 50

clear
