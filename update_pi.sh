#!/bin/bash

# Load configuration from .env file
if [ -f ".env" ]; then
    source .env
else
    echo ".env file not found! Please create one with the necessary configurations."
    exit 1
fi

# Trap to handle Ctrl+C (SIGINT) for graceful exit
trap 'echo -e "\n\nScript interrupted! Reconnecting to main Wi-Fi..."; reconnect_to_main_wifi; exit 1' INT

# Default number of retries (from .env, can be overridden)
RETRIES="${MAX_RETRIES:-3}"

# Argument Parsing with getopts (override .env values if provided)
while getopts ":u:w:s:r:m:" opt; do
    case $opt in
        u) SSH_PASSWORD="$OPTARG" ;;         # Override SSH password
        w) WIFI_PASSWORD="$OPTARG" ;;        # Override Wi-Fi password
        s) MAIN_WIFI_SSID="$OPTARG" ;;       # Override main Wi-Fi SSID
        r) RETRIES="$OPTARG" ;;              # Override max retries
        m) MAIN_WIFI_PASSWORD="$OPTARG" ;;   # Override main Wi-Fi password
        \?) echo "Invalid option: -$OPTARG" >&2; exit 1 ;;
        :) echo "Option -$OPTARG requires an argument." >&2; exit 1 ;;
    esac
done
shift $((OPTIND -1))

# Check if required arguments are provided either via .env or getopts
if [ -z "$SSH_PASSWORD" ] || [ -z "$WIFI_PASSWORD" ] || [ -z "$MAIN_WIFI_PASSWORD" ]; then
    echo "SSH password, Wi-Fi password, or main Wi-Fi password not provided! Please check your .env file or use -u, -w, and -m options."
    exit 1
fi

# Array of dynamically detected Raspberry Pi hotspots using SSID and ensuring it doesn't show MAC addresses
pis=($(nmcli -t -f SSID dev wifi list | grep 'Unitree_Go'))

# If no Pi hotspots are found, exit
if [ ${#pis[@]} -eq 0 ]; then
    echo "No Raspberry Pi hotspots detected."
    exit 1
fi

# Print how many Pi hotspots were found and list their names
echo "Found ${#pis[@]} Raspberry Pi hotspots:"
for pi in "${pis[@]}"; do
    echo " - $pi"
done

# Log output to both the terminal and a log file with timestamps
exec > >(while IFS= read -r line; do echo "$(date '+%Y-%m-%d %H:%M:%S') $line"; done | tee -a "$LOGFILE") 2>&1

# Function to connect to Pi's hotspot
connect_to_hotspot() {
    local pi_ssid="$1"
    echo "Connecting to $pi_ssid..."
    if nmcli dev wifi connect "$pi_ssid" password "$WIFI_PASSWORD"; then
        echo "Successfully connected to $pi_ssid"
        return 0
    else
        echo "Failed to connect to $pi_ssid"
        return 1
    fi
}

# Function to get the Pi suffix (last 3 digits, ignoring the trailing 'A')
get_pi_suffix() {
    local pi_ssid="$1"
    # Extract the last three digits, ignoring the trailing 'A' character
    local pi_suffix=$(echo "$pi_ssid" | grep -oE '[0-9]{3}A$' | sed 's/A//')
    echo "$pi_suffix"
}

# Function to kill any running python3 process for client_udp_test.py
kill_python_process() {
    local pi_ssid="$1"
    echo "Checking for running python3 processes on $pi_ssid..."
    sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no pi@192.168.12.1 'pgrep -f client_udp_test.py && sudo pkill -f client_udp_test.py' > /dev/null 2>&1
    echo "Killed python3 process for pid.py on $pi_ssid"
}

# Function to run dhclient and get internet access on the Pi
get_internet_access() {
    local pi_ssid="$1"
    echo "Running dhclient to get internet access on $pi_ssid..."
    sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no pi@192.168.12.1 'sudo dhclient wlan0' > /dev/null 2>&1
    if sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no pi@192.168.12.1 'curl -s -I https://www.google.com' > /dev/null 2>&1; then
        echo "$pi_ssid has internet access."
        return 0
    else
        echo "$pi_ssid failed to get internet access."
        return 1
    fi
}

# Function to update the Pi
update_pi() {
    local pi_ssid="$1"
    local pi_suffix=$(get_pi_suffix "$pi_ssid")  # Get the last 3 digits

    if [ -z "$pi_suffix" ]; then
        echo "Failed to extract Pi suffix for $pi_ssid"
        return 1
    fi

    # Kill any running python3 process for client_udp_test.py
    kill_python_process "$pi_ssid"

    # Run dhclient to get internet access
    if ! get_internet_access "$pi_ssid"; then
        echo "Update aborted for $pi_ssid due to no internet access"
        return 1
    fi

    # Run the update and immediately close the SSH session after the Python script is started
    sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no pi@192.168.12.1 <<EOF
        cd unitree_legged_sdk/example_py || { echo "Failed to change directory on $pi_ssid"; exit 1; }
        rm -rf pid.py || { echo "Failed to remove old file on $pi_ssid"; exit 1; }
        wget -O pid.py "$WGET_URL" || { echo "Failed to download new file on $pi_ssid"; exit 1; }
        nohup python3 pid.py $pi_suffix > /dev/null 2>&1 &
EOF

    echo "Pi $pi_ssid has been updated successfully and SSH session closed. Moving to the next Pi..."
}

# Function to reconnect to the main Wi-Fi network with retries and logging
reconnect_to_main_wifi() {
    local retries=0
    local max_retries=3
    local backoff=5  # seconds

    echo "Attempting to reconnect to main Wi-Fi: $MAIN_WIFI_SSID"

    while [ $retries -lt $max_retries ]; do
        if nmcli dev wifi connect "$MAIN_WIFI_SSID" password "$MAIN_WIFI_PASSWORD"; then
            echo "Successfully reconnected to main Wi-Fi ($MAIN_WIFI_SSID)."
            return 0
        else
            echo "Failed to reconnect to main Wi-Fi. Retrying in $backoff seconds..."
            sleep $backoff
            retries=$((retries + 1))
            backoff=$((backoff * 2))  # Exponential backoff
        fi
    done

    echo "Failed to reconnect to main Wi-Fi after $max_retries attempts."
    return 1
}

# Function to handle updating a single Pi, including retry mechanism
update_single_pi() {
    local pi_ssid="$1"
    local retries=0

    while [ $retries -lt $RETRIES ]; do
        # Step 1: Connect to the Pi's hotspot
        if connect_to_hotspot "$pi_ssid"; then
            # Step 2: Try to update the Pi
            if update_pi "$pi_ssid"; then
                echo "Successfully updated $pi_ssid"
                return 0
            else
                echo "Failed to update $pi_ssid. Retrying..."
                retries=$((retries + 1))
            fi
        else
            echo "Failed to connect to $pi_ssid. Retrying..."
            retries=$((retries + 1))
        fi
    done

    echo "Giving up on $pi_ssid after $RETRIES attempts."
    return 1
}

# Sequential execution (since only one Pi can be connected at a time)
for pi_ssid in "${pis[@]}"; do
    update_single_pi "$pi_ssid"
done

# After all Pis are processed, reconnect to the main Wi-Fi network
reconnect_to_main_wifi

# Final log message
echo -e "\nLog has been saved to $LOGFILE"
