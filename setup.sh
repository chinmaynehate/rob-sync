pip3 install virtualenv
sudo apt-get install sshpass
cd
python3 -m venv venv
source venv/bin/activate
pip3 install fastapi "uvicorn[standard]"
deactivate
cd
git clone https://github.com/chinmaynehate/rob-sync.git
cd ~/rob-sync
