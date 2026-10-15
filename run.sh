#!/bin/bash

# make sure the port is available to run the viewer
echo "Freeing port"
fuser -k 5000/tcp 2>/dev/null || true

echo "Restarting app"
arduino-app-cli app restart . 2>/dev/null || arduino-app-cli app start .
echo "Started app"
arduino-app-cli app logs . --follow

