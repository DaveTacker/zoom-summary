# Zoom Meeting Summary

This Python script fetches and summarizes Zoom meetings for the last two weeks, including participant information.

## Features

- Fetches meetings for the last 14 days
- Retrieves detailed participant information for each meeting
- Summarizes meeting duration and participant attendance
- Implements caching for API tokens to reduce API calls
- Provides both console output and detailed logging

## Prerequisites

- Python 3.7+
- Zoom API credentials (Client ID, Client Secret, and Account ID)

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/DaveTacker/zoom-summary.git
   cd zoom-summary
   ```

2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy the `config.example.py` file to `config.py`:
   ```bash
   cp config.example.py config.py
   ```

4. Edit `config.py` and add your Zoom API credentials:
   ```python
   CLIENT_ID = "your_client_id"
   CLIENT_SECRET = "your_client_secret"
   ACCOUNT_ID = "your_account_id"
   ```

## Usage

Run the script with:

```
python zoom_meeting_summary.py
```

The script will fetch and summarize the Zoom meetings for the last two weeks, including participant information.

## License

This project is licensed under the MIT License. See the `LICENSE` file for more details.
