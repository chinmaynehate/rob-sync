#!/bin/bash

# Load configuration from .env file
if [ -f ".env" ]; then
    source .env
else
    echo ".env file not found! Please create one with the necessary configurations."
    exit 1
fi

# Default number of retries (from .env, can be overridden)
RETRIES="${MAX_RETRIES:-3}"
LOGFILE="report_log.csv"
ERROR_LOGFILE="error_log.txt"
DRY_RUN=false  # By default, dry run is off
INTERNET_CHECK_MAX_TRIES=10  # Maximum number of checks for internet connectivity
INTERNET_CHECK_DELAY=5       # Delay in seconds between internet checks
SSH_TIMEOUT=15               # Timeout for SSH connections
WGET_TIMEOUT=30              # Timeout for wget commands
BACKOFF_DELAY=5              # Initial delay for exponential backoff

# Global error trap: Capture all unexpected exits or interruptions and log the state
trap 'on_exit' EXIT

on_exit() {
    echo "Global Exit Trap: Cleaning up and logging state..." | tee -a $ERROR_LOGFILE
    reconnect_to_main_wifi
    echo "Log has been saved to $LOGFILE"
    echo "Error log has been saved to $ERROR_LOGFILE"
    exit 1
}

# Argument Parsing with getopts (override .env values if provided)
while getopts ":u:w:s:r:m:d" opt; do
    case $opt in
        u) SSH_PASSWORD="$OPTARG" ;;         # Override SSH password
        w) WIFI_PASSWORD="$OPTARG" ;;        # Override Wi-Fi password
        s) MAIN_WIFI_SSID="$OPTARG" ;;       # Override main Wi-Fi SSID
        r) RETRIES="$OPTARG" ;;              # Override max retries
        m) MAIN_WIFI_PASSWORD="$OPTARG" ;;   # Override main Wi-Fi password
        d) DRY_RUN=true ;;                   # Enable dry run mode
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

# Initialize the report log and error log files with headers
echo "Pi SSID,Pi Suffix,Connection Successful,Retries,Update Successful,Connection Attempt Time,Update Duration,Final Status" > $LOGFILE
echo "Logging errors to $ERROR_LOGFILE"
echo "Error Log" > $ERROR_LOGFILE

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

# Function to connect to Pi's hotspot using SSID with timeout and retries
connect_to_hotspot() {
    local pi_ssid="$1"
    local retries=0
    while [ $retries -lt $RETRIES ]; do
        echo "Connecting to $pi_ssid..."
        if timeout $SSH_TIMEOUT nmcli dev wifi connect "$pi_ssid" password "$WIFI_PASSWORD"; then
            echo "Successfully connected to $pi_ssid"
            return 0
        else
            echo "Failed to connect to $pi_ssid. Retrying..." | tee -a $ERROR_LOGFILE
            retries=$((retries + 1))
            sleep $((BACKOFF_DELAY * retries))  # Exponential backoff
        fi
    done
    echo "Failed to connect to $pi_ssid after $RETRIES retries" | tee -a $ERROR_LOGFILE
    return 1
}

# Function to extract the last three digits from the SSID (ignoring the trailing 'A')
get_pi_suffix() {
    local pi_ssid="$1"
    # Extract last three digits, remove the trailing 'A' if present
    local pi_suffix=$(echo "$pi_ssid" | grep -oE '[0-9]{3}A$' | sed 's/A//')
    echo "$pi_suffix"
}

# Function to check if the Pi has internet access
check_internet_access() {
    local pi_ssid="$1"
    local tries=0
    while [ $tries -lt $INTERNET_CHECK_MAX_TRIES ]; do
        # Check internet connectivity by pinging Google's DNS server
        if sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=$SSH_TIMEOUT pi@192.168.12.1 ping -c 1 8.8.8.8 > /dev/null 2>&1; then
            echo "$pi_ssid has internet access"
            return 0
        else
            echo "Waiting for $pi_ssid to get internet access... (Attempt $((tries + 1))/$INTERNET_CHECK_MAX_TRIES)"
            tries=$((tries + 1))
            sleep $INTERNET_CHECK_DELAY
        fi
    done
    echo "$pi_ssid failed to get internet access after $INTERNET_CHECK_MAX_TRIES tries" | tee -a $ERROR_LOGFILE
    return 1
}

# Function to check if dhclient successfully obtained an IP address
check_dhclient_success() {
    local pi_ssid="$1"
    echo "Checking if dhclient succeeded on $pi_ssid..."
    if sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=$SSH_TIMEOUT pi@192.168.12.1 'ip addr show wlan0' | grep 'inet ' > /dev/null 2>&1; then
        echo "$pi_ssid obtained an IP address"
        return 0
    else
        echo "$pi_ssid failed to obtain an IP address" | tee -a $ERROR_LOGFILE
        return 1
    fi
}

# Function to update the Pi with backup, including running dhclient to get internet
update_pi() {
    local pi_ssid="$1"
    local pi_suffix=$(get_pi_suffix "$pi_ssid")  # Get last three digits excluding 'A'

    # Check if dry run is enabled
    if [ "$DRY_RUN" = true ]; then
        echo "[Dry Run] Would have updated $pi_ssid with suffix $pi_suffix."
        return 0
    fi

    # Connect the Pi to the internet by running dhclient
    echo "Running dhclient on $pi_ssid to get internet access..."
    sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=$SSH_TIMEOUT pi@192.168.12.1 'sudo dhclient wlan0'

    # Ensure dhclient successfully gets an IP address
    if ! check_dhclient_success "$pi_ssid"; then
        echo "Update aborted for $pi_ssid due to dhclient failure" | tee -a $ERROR_LOGFILE
        return 1
    fi

    # Wait for the Pi to have internet access
    if ! check_internet_access "$pi_ssid"; then
        echo "Update aborted for $pi_ssid due to no internet access" | tee -a $ERROR_LOGFILE
        return 1
    fi

    # Backup old file before updating
    sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=$SSH_TIMEOUT pi@192.168.12.1 <<EOF
        cd unitree_legged_sdk/example_py || { echo "Failed to change directory on $pi_ssid"; exit 1; }
        if [ -f client_udp_test.py ]; then cp client_udp_test.py client_udp_test.py.bak; fi
        timeout $WGET_TIMEOUT wget -O client_udp_test.py "$WGET_URL" || { echo "Failed to download new file on $pi_ssid"; exit 1; }
        python3 client_udp_test.py $pi_suffix || { echo "Failed to run the script on $pi_ssid"; exit 1; }
EOF
}

# Function to log results to the CSV file
log_result() {
    local pi_ssid="$1"
    local pi_suffix="$2"
    local connection_success="$3"
    local retries="$4"
    local update_success="$5"
    local connection_time="$6"
    local update_duration="$7"
    local final_status="$8"

    echo "$pi_ssid,$pi_suffix,$connection_success,$retries,$update_success,$connection_time,$update_duration,$final_status" >> $LOGFILE
}

# Function to handle updating a single Pi, including retry mechanism with exponential backoff
update_single_pi() {
    local pi_ssid="$1"
    local retries=0
    local connection_success=false
    local update_success=false
    local final_status="Fail"
    local connection_time=$(date '+%Y-%m-%d %H:%M:%S')

    # Record the start time for update duration calculation
    local start_time=$(date +%s)

    while [ $retries -lt $RETRIES ]; do
        # Step 1: Ping the Pi to check if it's reachable
        if ping -c 1 192.168.12.1 > /dev/null 2>&1; then
            echo "Ping successful for $pi_ssid"
        else
            echo "Ping failed for $pi_ssid. Skipping..." | tee -a $ERROR_LOGFILE
            break
        fi

        # Step 2: Connect to the Pi's hotspot
        if connect_to_hotspot "$pi_ssid"; then
            connection_success=true
            break
        else
            retries=$((retries + 1))
            sleep $((BACKOFF_DELAY * retries))  # Exponential backoff
        fi
    done

    # If connection successful, attempt update
    if [ "$connection_success" = true ]; then
        if update_pi "$pi_ssid"; then
            update_success=true
            final_status="Success"
        fi
    else
        echo "Connection failed after $retries retries for $pi_ssid" | tee -a $ERROR_LOGFILE
    fi

    # Record the end time for update duration calculation
    local end_time=$(date +%s)
    local update_duration=$((end_time - start_time))" seconds"

    # Get the Pi suffix
    local pi_suffix=$(get_pi_suffix "$pi_ssid")

    # Log the result for this Pi
    log_result "$pi_ssid" "$pi_suffix" "$connection_success" "$retries" "$update_success" "$connection_time" "$update_duration" "$final_status"
}

# Sequential execution (since only one Pi can be connected at a time)
for pi_ssid in "${pis[@]}"; do
    update_single_pi "$pi_ssid"
    echo "Waiting for 5 seconds before proceeding to the next Pi..."
    sleep 5  # Wait a bit before moving on to the next Pi
done

# After all Pis are processed, reconnect to the main Wi-Fi network
if [ "$DRY_RUN" = false ]; then
    reconnect_to_main_wifi
fi

# Final log message
echo -e "\nLog has been saved to $LOGFILE"
