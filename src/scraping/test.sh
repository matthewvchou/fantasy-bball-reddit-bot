#!/bin/bash

# Kill any process currently using port 4444
PORT=4444
PID=$(lsof -ti:$PORT) # Get the PID of the process using the port
if [ -n "$PID" ]; then
  echo "Killing process on port $PORT (PID: $PID)"
  kill -9 $PID
else
  echo "No process found using port $PORT"
fi

# Start Selenium server
java -jar /Users/matthewvchou/Downloads/selenium-server-4.25.0.jar standalone --host 127.0.0.1 --port 4444 &
SELENIUM_PID=$!  # Capture the process ID of the Java process
echo "Selenium server started with PID: $SELENIUM_PID"

# Wait for the Selenium server to initialize
sleep 5

# SCRIPT GOES HERE
/Users/matthewvchou/fantasy-bball-reddit-bot/venv/bin/python /Users/matthewvchou/fantasy-bball-reddit-bot/src/scraping/basketball_monster_scraper.py

# Check if the Selenium server is still running and force kill if necessary
if ps -p $SELENIUM_PID > /dev/null; then
  echo "Graceful shutdown failed, killing Selenium process (PID: $SELENIUM_PID)..."
  kill -9 $SELENIUM_PID
fi

echo "Script completed."