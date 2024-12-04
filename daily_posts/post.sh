#!/bin/bash
# Start Selenium server
java -jar Downloads/selenium-server-4.25.0.jar standalone --host 127.0.0.1 --port 4444 &
SELENIUM_PID=$!  # Capture the process ID

# Perform your tasks here, like running tests
sleep 5

# Run script
/Users/matthewvchou/fantasy-bball-reddit-bot/venv/bin/python /Users/matthewvchou/fantasy-bball-reddit-bot/daily_posts/daily_top_10.py

# Shutdown Selenium server gracefully
curl -X POST http://127.0.0.1:4444/se/grid/stop

# Alternatively, kill the process if curl fails
if ps -p $SELENIUM_PID > /dev/null; then
  kill $SELENIUM_PID
fi
