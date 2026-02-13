source bin/activate
#send_chan_msg() is flaky unless we do this manual redirection
nohup python mc-discord-bridge.py > output.txt 2>&1 &


