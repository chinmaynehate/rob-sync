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
GETNEWCODE=false  # Default value for copying the .py file
FILE_PATH=""  # Default path for the .py file

# Argument Parsing with getopts (override .env values if provided)
while getopts ":u:w:s:r:m:g:f:" opt; do
    case $opt in
        u) SSH_PASSWORD="$OPTARG" ;;
        w) WIFI_PASSWORD="$OPTARG" ;;
        s) MAIN_WIFI_SSID="$OPTARG" ;;
        r) RETRIES="$OPTARG" ;;
        m) MAIN_WIFI_PASSWORD="$OPTARG" ;;
        g) GETNEWCODE="$OPTARG" ;;
        f) FILE_PATH="$OPTARG" ;;
        \?) echo "Invalid option: -$OPTARG" >&2; exit 1 ;;
        :) echo "Option -$OPTARG requires an argument." >&2; exit 1 ;;
    esac
done
shift $((OPTIND -1))

# Function to reconnect to the main Wi-Fi network
reconnect_to_main_wifi() {
    local retries=0
    local max_retries=3
    local backoff=5

    echo "Attempting to reconnect to main Wi-Fi: $MAIN_WIFI_SSID"

    while [ $retries -lt $max_retries ]; do
        if nmcli dev wifi connect "$MAIN_WIFI_SSID" password "$MAIN_WIFI_PASSWORD"; then
            echo "Successfully reconnected to main Wi-Fi ($MAIN_WIFI_SSID)."
            return 0
        else
            echo "Failed to reconnect. Retrying in $backoff seconds..."
            sleep $backoff
            retries=$((retries + 1))
            backoff=$((backoff * 2))
        fi
    done

    echo "Failed to reconnect to main Wi-Fi after $max_retries attempts."
    return 1
}

reconnect_to_main_wifi

# Get the IP address of the laptop
laptop_ip=$(hostname -I | awk '{print $1}')
if [ -z "$laptop_ip" ]; then
    echo "Failed to determine the laptop's IP address."
    exit 1
else
    echo "Laptop IP address: $laptop_ip"
fi

# Check if required arguments are provided either via .env or getopts
if [ -z "$SSH_PASSWORD" ] || [ -z "$WIFI_PASSWORD" ] || [ -z "$MAIN_WIFI_PASSWORD" ]; then
    echo "SSH password, Wi-Fi password, or main Wi-Fi password not provided!"
    exit 1
fi

# Array of dynamically detected Raspberry Pi hotspots
pis=($(nmcli -t -f SSID dev wifi list | grep 'Unitree_Go'))

if [ ${#pis[@]} -eq 0 ]; then
    echo "No Raspberry Pi hotspots detected."
    exit 1
fi

echo "Found ${#pis[@]} Raspberry Pi hotspots:"
for pi in "${pis[@]}"; do
    echo " - $pi"
done

exec > >(while IFS= read -r line; do echo "$(date '+%Y-%m-%d %H:%M:%S') $line"; done | tee -a "$LOGFILE") 2>&1


# Function to kill any process running on port 8000
kill_server_script() {
    local pid=$(pgrep -f "python3 server.py")
    if [ -n "$pid" ]; then
        echo "Killing existing server.py process with PID $pid"
        kill -9 $pid
    else
        echo "No running instance of server.py found."
    fi
}

# Function to kill any process running on port 8000
kill_process_on_port() {
    local port=8000
    local pid=$(lsof -ti:$port)
    if [ -n "$pid" ]; then
        echo "Killing process on port $port with PID $pid"
        kill -9 $pid
    else
        echo "No process found on port $port."
    fi
}
kill_firefox() {
    local pid=$(pgrep -f firefox)
    if [ -n "$pid" ]; then
        echo "Killing existing Firefox process with PID $pid"
        kill -9 $pid
    else
        echo "No running instance of Firefox found."
    fi
}
# Function to start the server.py script
start_server() {
    echo "Starting server.py..."
    nohup python3 server.py > server.log 2>&1 &
    sleep 2  # Give the server time to start

}

# Kill any process on port 8000 and start the server
reconnect_to_main_wifi
kill_server_script
kill_process_on_port
start_server

# Function to copy and replace the Python file on the Raspberry Pi
copy_new_code() {
    local pi_ssid="$1"
    local remote_path="/home/pi/unitree_legged_sdk/example_py/$(basename $FILE_PATH)"

    if [ -z "$FILE_PATH" ]; then
        echo "No file path provided. Skipping code copy."
        return 1
    fi

    echo "Checking if $remote_path exists on $pi_ssid..."
    if sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no pi@192.168.12.1 "[ -f $remote_path ]"; then
        echo "File exists on $pi_ssid. Deleting the old file..."
        sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no pi@192.168.12.1 "rm -f $remote_path"
    fi

    echo "Copying $FILE_PATH to $pi_ssid..."
    sshpass -p "$SSH_PASSWORD" scp -o StrictHostKeyChecking=no "$FILE_PATH" pi@192.168.12.1:/home/pi/unitree_legged_sdk/example_py/
    if [ $? -eq 0 ]; then
        echo "Successfully copied $FILE_PATH to $pi_ssid."
        return 0
    else
        echo "Failed to copy $FILE_PATH to $pi_ssid."
        return 1
    fi
}

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

# Function to get the Pi suffix
get_pi_suffix() {
    local pi_ssid="$1"
    echo "$pi_ssid" | grep -oE '[0-9]{3}A$' | sed 's/A//'
}

# Function to kill any running Python process for local_client_udp_test.py
# kill_python_process() {
#     sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no pi@192.168.12.1 'pgrep -f local_client_udp_test.py && sudo pkill -f local_client_udp_test.py' > /dev/null 2>&1
# }

kill_python_process() {
    sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no pi@192.168.12.1 'pgrep -f python3 && sudo pkill -f python3' > /dev/null 2>&1
}

# Function to run dhclient and check connection to router
# get_internet_access() {
#     local pi_ssid="$1"
#     echo "Running dhclient to connect $pi_ssid to router..."
#     sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no pi@192.168.12.1 'sudo dhclient wlan0' > /dev/null 2>&1
#     if sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no pi@192.168.12.1 'ip a | grep "inet 192.168"' > /dev/null 2>&1; then
#         echo "$pi_ssid connected to the router."
#         return 0
#     else
#         echo "$pi_ssid failed to connect to the router."
#         return 1
#     fi
# }

# Function to run dhclient with timeout and check connection to router with retry
get_internet_access() {
    local pi_ssid="$1"
    local attempts=0
    local max_attempts=10
    local delay=2
    local timeout_duration=5

    echo "Running dhclient to connect $pi_ssid to router..."

    while [ $attempts -lt $max_attempts ]; do
        # Run systemctl daemon-reload before dhclient
        sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no pi@192.168.12.1 'sudo systemctl daemon-reload' > /dev/null 2>&1

        # Run dhclient in the background
        sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no pi@192.168.12.1 'sudo dhclient wlan0' &
        dhclient_pid=$!
        
        # Wait for dhclient or timeout
        sleep $timeout_duration
        
        # Check if dhclient is still running and kill if needed
        if ps -p $dhclient_pid > /dev/null; then
            echo "dhclient timed out. Terminating..."
            kill -9 $dhclient_pid
        fi

        # Check if the Pi is connected
        if sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no pi@192.168.12.1 'ip a | grep "inet 192.168"' > /dev/null 2>&1; then
            echo "$pi_ssid connected to the router."
            return 0
        else
            echo "$pi_ssid failed to connect to the router. Retrying in $delay seconds..."
            sleep $delay
            attempts=$((attempts + 1))
        fi
    done

    echo "$pi_ssid failed to connect to the router after $max_attempts attempts."
    return 1
}



# Function to update the Pi
update_pi() {
    local pi_ssid="$1"
    local pi_suffix=$(get_pi_suffix "$pi_ssid")

    if [ -z "$pi_suffix" ]; then
        echo "Failed to extract Pi suffix for $pi_ssid"
        return 1
    fi

    kill_python_process "$pi_ssid"

    if ! get_internet_access "$pi_ssid"; then
        echo "Update aborted for $pi_ssid due to connection failure."
        return 1
    fi

    if $GETNEWCODE; then
        copy_new_code "$pi_ssid"
    fi

    sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no pi@192.168.12.1 <<EOF
        cd /home/pi/unitree_legged_sdk/example_py || { echo "Failed to change directory on $pi_ssid"; exit 1; }
        nohup python3 hotspot_hardcode.py $pi_suffix $laptop_ip > /dev/null 2>&1 &
EOF

    echo "Pi $pi_ssid has been updated successfully and SSH session closed."
}
#  nohup python3 local_hardcode.py $pi_suffix $laptop_ip > /dev/null 2>&1 &


# Function to handle updating a single Pi with retry logic
update_single_pi() {
    local pi_ssid="$1"
    local retries=0

    while [ $retries -lt $RETRIES ]; do
        if connect_to_hotspot "$pi_ssid"; then
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

# Process each Pi sequentially
for pi_ssid in "${pis[@]}"; do
    update_single_pi "$pi_ssid"
done

# Reconnect to main Wi-Fi
reconnect_to_main_wifi

kill_firefox
# Open the server in Firefox on laptop_ip:8000
echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
echo "Laptop IP: $laptop_ip"
url="http://$laptop_ip:8000" 
echo "Opening server in Mozilla Firefox at $url..."
firefox "$url" &

echo -e "\nLog has been saved to $LOGFILE"
