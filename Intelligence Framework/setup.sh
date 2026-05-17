#!/bin/bash

# Script: Forex Fundamental Analysis Setup
# Description: Creates a fundaupmental analysis toolkit for currency pairs

set -euo pipefail  # Exit on error, undefined vars, and pipe failures

# Ensure script is run inside the Forex directory
if [[ $(basename "$PWD") != "Forex" ]]; then
    echo "❌ Error: Please run this script from within the Forex directory"
    exit 1
fi

# Files to create
FILES=("config.py" "scraper.py" "news_analysis.py" "trade_logic.py" "main.py" "requirements.txt")

# Function to create files with their content
create_file() {
    local filename="$1"
    local content="$2"
    echo "$content" > "$filename"
    chmod +x "$filename"
    echo "✅ Created: $filename"
}

# Create each file with its content
create_file "config.py" "
# Currency pairs to track
CURRENCY_PAIRS = [\"GBP/AUD\"]
FOREX_FACTORY_URL = \"https://www.forexfactory.com/calendar.php\"
"

create_file "scraper.py" "
import requests
from bs4 import BeautifulSoup
from config import FOREX_FACTORY_URL, CURRENCY_PAIRS

def scrape_economic_news():
    \"\"\"Scrape economic news from Forex Factory.\"\"\"
    headers = {\"User-Agent\": \"Mozilla/5.0\"}
    response = requests.get(FOREX_FACTORY_URL, headers=headers)
    soup = BeautifulSoup(response.text, \"html.parser\")

    economic_events = []
    for event in soup.find_all(\"tr\", class_=\"calendar__row\"):
        time = event.find(\"td\", class_=\"time\").text.strip()
        currency = event.find(\"td\", class_=\"currency\").text.strip()
        event_name = event.find(\"td\", class_=\"event\").text.strip()
        forecast = event.find(\"td\", class_=\"forecast\").text.strip()
        previous = event.find(\"td\", class_=\"previous\").text.strip()

        if currency in CURRENCY_PAIRS:
            economic_events.append({
                \"time\": time,
                \"currency\": currency,
                \"event\": event_name,
                \"forecast\": forecast,
                \"previous\": previous
            })

    return economic_events
"

create_file "news_analysis.py" "
def analyze_economic_event(event, forecast, previous):
    \"\"\"Analyze economic events and provide market insights.\"\"\"
    if \"Interest Rate\" in event:
        return \"🔹 Higher rates strengthen currency. If BoE raises rates, GBP may rise.\"
    elif \"CPI\" in event:
        return f\"📊 Higher CPI → Bullish GBP if above {forecast}.\"
    elif \"Employment\" in event:
        return \"💼 Strong jobs data supports currency.\"
    else:
        return \"📌 Compare actual vs forecast.\"
"

create_file "trade_logic.py" "
def analyze_impact(event, actual, forecast):
    \"\"\"Analyze the potential market impact of economic data.\"\"\"
    try:
        actual_value = float(actual)
        forecast_value = float(forecast)

        if \"CPI\" in event and actual_value > forecast_value:
            return \"✅ Bullish signal → Consider GBP/AUD longs\"
        elif \"Unemployment\" in event and actual_value > forecast_value:
            return \"❌ Bearish signal → Consider GBP/AUD shorts\"
        else:
            return \"⚠️ No clear directional bias.\"
    except ValueError:
        return \"⚠️ Missing data.\"
"

create_file "main.py" "
from scraper import scrape_economic_news
from news_analysis import analyze_economic_event
from trade_logic import analyze_impact

def analyze_market():
    economic_events = scrape_economic_news()

    for event in economic_events:
        event_name = event[\"event\"]
        forecast = event[\"forecast\"]
        previous = event[\"previous\"]
        analysis = analyze_economic_event(event_name, forecast, previous)

        print(f\"\"\"
        📊 ECONOMIC INDICATOR:
        📌 Event: {event_name}
        📈 Forecast: {forecast}
        📉 Previous: {previous}
        📖 Analysis: {analysis}
        \"\"\")
if __name__ == \"__main__\":
    analyze_market()
"

create_file "requirements.txt" "
requests
beautifulsoup4
"

# Set up virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    deactivate
else
    echo "✅ Virtual environment already exists."
fi

echo "🚀 Setup complete!"