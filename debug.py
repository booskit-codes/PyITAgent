import logging
import subprocess
import json
import os
import sys
import requests
import configparser

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class PowerShellLogging:
    def __init__(self, data):
        self.data = data
        self.manufacturer = self.determine_manufacturer()
        self.serial_number = self.determine_serial_number()
        self.hardware = {}

    def determine_manufacturer(self):
        manufacturer = run_command("(gwmi win32_computersystem).manufacturer")
        # Specific case for HP and Hewlett-Packard
        if manufacturer == "Hewlett-Packard":
            manufacturer = "HP"
        return manufacturer

    def determine_serial_number(self):
        serial_number = run_command("(gwmi win32_baseboard).serialnumber")
        if self.manufacturer == 'Dell Inc.':
            return serial_number.split('/')[1]
        elif self.manufacturer == 'HP':
            return run_command('(gwmi win32_bios).serialnumber')
        return serial_number

    def collect_hardware_data(self):
        static_fields = self.data["enabled_static_fields"]
        for field, value in static_fields.items():
            if value["enabled"] is True:
                print(f"{field} is enabled")
            else:
                print(f"{field} is disabled")
        dynamic_fields = self.data["custom_fields"]
        for field, value in dynamic_fields.items():
            print(value)
            if value["enabled"] is False:
                continue
            result = run_command(value["ps_command"])
            print(f"{value["name"]}: {result}")
            self.hardware[field] = result

    def resolve_payload(self, type, values):
        match type:
            case "hardware":
                hardware = {
                    'serial': values['serial_number'],
                    'name': self.hostname,
                    'asset_tag': values['serial_number'],
                    'status_id': values['status_id'],
                    'model_id': values['model_id'],
                    'company_id': values['company_id']
                }
                for field, value in self.hardware_info.items():
                    hardware[field] = value
                return hardware
            case "model":
                return {
                    "name": self.model,
                    "model_number": self.model_number,
                    "category_id": values['category_id'],
                    "manufacturer_id": values['manufacturer_id'],
                    "fieldset_id": values['fieldset_id']
                }
            case "manufacturer":
                return {
                    values['manufacturer_name']
                }

def run_command(cmd):
    try:
        # The flag to prevent the console window from showing up
        CREATE_NO_WINDOW = 0x08000000
        
        # Execute the command without showing a window
        process = subprocess.Popen(["powershell.exe", "-Command", cmd],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, creationflags=CREATE_NO_WINDOW)
        
        # Wait for the command to complete and capture the output and error
        stdout, stderr = process.communicate()
        
        # Check if the command was executed successfully
        if process.returncode == 0:
            logging.info(f"Command executed successfully: {cmd}")
            return stdout.strip()
        else:
            # Log an error if the command failed
            logging.error(f"Command failed with return code {process.returncode}: {cmd}")
            logging.error(f"Error output: {stderr.strip()}")
            return None
    except Exception as e:
        # Log any exceptions that occur during execution
        logging.exception(f"An exception occurred while executing the command: {cmd}")
        return None
        
# Resolve pyinstaller's stoopid windows executable path issue
def resolve_path(path):
    if getattr(sys, "frozen", False):
        # If the 'frozen' flag is set, we are in bundled-app mode!
        # Use the directory of the executable
        application_path = os.path.dirname(sys.executable)
        resolved_path = os.path.abspath(os.path.join(application_path, path))
    else:
        # Normal development mode.
        resolved_path = os.path.abspath(os.path.join(os.getcwd(), path))

    return resolved_path

def send_to_slack(message, webhook_url):
    payload = {
        'text': message,
        'username': 'PyITAgent - Debugger',
        'icon_emoji': 'hammer_and_wrench',
        }
    try:
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error sending message to Slack: {e}")

def get_config():
    config_path = resolve_path('config.ini')
    
    if not os.path.exists(config_path):
        raise Exception("config.ini not found. Please create it at:", config_path)
    config = configparser.ConfigParser()
    config.read(config_path)
    return config
    
def debug():

    with open(resolve_path('custom_fields.json'), 'r') as file:
        data = json.load(file)

    ps = PowerShellLogging(data)
    
    # This will serve as both debugging purposes & just general information, nothing bad with information.
    print(f"""
          Debug Results
          -------------------------
          
          Manufacturer: {ps.manufacturer}
          """)
    
    ps.collect_hardware_data()

    config = get_config()
    hostname = run_command("(Get-WmiObject Win32_OperatingSystem).CSName")
    windows_user = run_command("[System.Security.Principal.WindowsIdentity]::GetCurrent().Name")
    debug_message = f"Debugger script initiated for powershell logging.\n"
    debug_message += f"Debug script ran on computer: {hostname}\n"
    debug_message += f"Debug script ran on user: {windows_user}\n"
    debug_message += "```"  # Slack formatting for code blocks
    debug_message += f"Manufacturer: {ps.manufacturer}\n"
    debug_message += f"Serial Number: {ps.serial_number}\n"
    debug_message += f"Hardware: {str(ps.hardware)}"
    debug_message += "```"
    slack_webhook_url = config['DEBUGGING']['slack_webhook']  # Replace with your actual Slack webhook URL
    send_to_slack(debug_message, slack_webhook_url)

if __name__ == "__main__":
    debug()