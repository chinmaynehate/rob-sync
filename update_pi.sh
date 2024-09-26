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
RETRIES="$MAX_RETRIES"

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

# Array of dynamically detected Raspberry Pi hotspots by SSID (assuming SSID contains 'Unitree_Go')
pis=($(nmcli dev wifi list | grep 'Unitree_Go' | awk '{print $1}'))

# If no Pi hotspots are found, exit
if [ ${#pis[@]} -eq 0 ]; then
    echo "No Raspberry Pi hotspots detected."
    exit 1
fi

# Print how many Pi hotspots were found and list their SSIDs
echo "Found ${#pis[@]} Raspberry Pi hotspots:"
for pi in "${pis[@]}"; do
    echo " - $pi"
done

# Log output to both the terminal and a log file with timestamps
exec > >(while IFS= read -r line; do echo "$(date '+%Y-%m-%d %H:%M:%S') $line"; done | tee -a "$LOGFILE") 2>&1

# Function to connect to Pi's hotspot using SSID
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

# Function to extract the last three digits from the SSID (ignoring the trailing 'A')
get_pi_suffix() {
    local pi_ssid="$1"
    # Extract last four characters, remove the trailing 'A' if present
    local pi_suffix=$(echo "$pi_ssid" | grep -oE '[0-9]{3}A$' | sed 's/A//')
    echo "$pi_suffix"
}

# Function to update the Pi
update_pi() {
    local pi_ssid="$1"
    local pi_suffix=$(get_pi_suffix "$pi_ssid")  # Get last three digits excluding 'A'
    sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no pi@192.168.12.1 <<EOF
        cd unitree_legged_sdk/example_py || { echo "Failed to change directory on $pi_ssid"; exit 1; }
        rm -rf client_udp_test.py || { echo "Failed to remove old file on $pi_ssid"; exit 1; }
        wget -O client_udp_test.py "$WGET_URL" || { echo "Failed to download new file on $pi_ssid"; exit 1; }
        python3 client_udp_test.py $pi_suffix || { echo "Failed to run the script on $pi_ssid"; exit 1; }
EOF
}

# Function to reconnect to the main Wi-Fi network with password
reconnect_to_main_wifi() {
    echo "Reconnecting to main Wi-Fi..."
    if nmcli dev wifi connect "$MAIN_WIFI_SSID" password "$MAIN_WIFI_PASSWORD"; then
        echo "Successfully reconnected to main Wi-Fi."
    else
        echo "Failed to reconnect to main Wi-Fi."
    fi
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
    echo "Waiting for 5 seconds before proceeding to the next Pi..."
    sleep 5  # Wait a bit before moving on to the next Pi
done

# After all Pis are processed, reconnect to the main Wi-Fi network
reconnect_to_main_wifi

# Final log message
echo -e "\nLog has been saved to $LOGFILE"
