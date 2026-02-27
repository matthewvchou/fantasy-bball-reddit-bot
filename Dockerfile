FROM --platform=linux/amd64 mcr.microsoft.com/azure-functions/python:4-python3.11

# Install Chromium and ChromeDriver (always version-matched via apt)
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Tell the scraper to use system Chromium instead of webdriver-manager
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

ENV AzureWebJobsScriptRoot=/home/site/wwwroot \
    AzureFunctionsJobHost__Logging__Console__IsEnabled=true

# Install project dependencies
COPY requirements.txt /tmp/project-requirements.txt
COPY azure-function/requirements.txt /tmp/function-requirements.txt
RUN pip install -r /tmp/project-requirements.txt -r /tmp/function-requirements.txt

# Copy function entrypoint and project source
COPY azure-function/ /home/site/wwwroot/
COPY src/ /home/site/wwwroot/src/
