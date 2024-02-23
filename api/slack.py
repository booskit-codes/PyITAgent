# slack.py

import requests

class SlackAPI:
    def send_to_slack(self, message, webhook_url):
        payload = {
            'text': message,
            'username': 'PyITAgent',
            'icon_emoji': 'hammer_and_wrench',
            }
        try:
            response = requests.post(webhook_url, json=payload)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error sending message to Slack: {e}")