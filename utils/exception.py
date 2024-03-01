# exception.py

from api.slack import SlackAPI
from config.settings import GlobalSettings
import config.constants as c
import sys
import traceback
from utils.common import run_command

class ExceptionHandler:
    @staticmethod
    def raise_for_error(self, e = None):
        error_message = f"An error occurred in the PyITAgent script: {e}"
        print(error_message)
        config = GlobalSettings().config

        if config['DEBUGGING']['slack_logging']:
            slack = SlackAPI()
            hostname = run_command("(Get-WmiObject Win32_OperatingSystem).CSName")
            windows_user = run_command("[System.Security.Principal.WindowsIdentity]::GetCurrent().Name")
            error_message += f"\nError occured on computer: {hostname}\n"
            error_message += f"Error occured on user: {windows_user}\n"
            error_message += f"Error occured on version: {c.VERSION}\n"
            error_message += "```"  # Slack formatting for code blocks
            error_message += traceback.format_exc()
            error_message += "```"
            slack_webhook_url = config['DEBUGGING']['slack_webhook']  # Replace with your actual Slack webhook URL
            slack.send_to_slack(error_message, slack_webhook_url)
        if not config['DEBUGGING']['silent_mode']:
            raise
            
        return sys.exit(1) # Exit the script with an error status