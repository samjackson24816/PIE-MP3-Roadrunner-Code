#!/bin/bash

echo "Setting up dependencies"
sudo apt update
sudo apt install -y python3-flask python3-opencv v4l-utils


echo "Setup complete"
echo "You can now run ./run.sh to start the robot"
