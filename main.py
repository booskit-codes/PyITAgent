__author__ = 'Booskit'
__version__ = '1.2-nightly'
__description__ = 'PyITAgent - Python agent for sending computer information to your Snipe-IT instance.'

import requests
import subprocess
import configparser
import os
import sys
import json
import traceback

class ITInventoryClient:
    def __init__(self, config, custom_fields):
        self.config = config
        self.access_token = config['DEFAULT']['api_key']
        self.headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {self.access_token}",
            "content-type": "application/json"
        }
        self.url_prefix = config['DEFAULT']['site']
        self.manufacturer = self.determine_manufacturer()
        self.serial_number = self.determine_serial_number()
        self.hostname = self.run_command("(Get-WmiObject Win32_OperatingSystem).CSName")
        self.model_number, self.model = self.determine_model_info()
        self.custom_fields = custom_fields
        self.hardware_info = {}

    def collect_hardware_data(self):
        static_fields = self.custom_fields["enabled_static_fields"]
        for field, value in static_fields.items():
            if value["enabled"]:
                match field:
                    case "mac_address": self.hardware_info[value["field_name"]] = self.run_command("(Get-WmiObject Win32_NetworkAdapterConfiguration | Where-Object {$_.IPEnabled -eq $true} | Select-Object -First 1).MACAddress")
                    case "total_storage" | "storage_information" | "disk_space_used":
                        self.disk_size, self.disk_info, self.disk_used = self.determine_disk_info()
                        if field == "total_storage":
                            self.hardware_info[value["field_name"]] = self.disk_size
                        elif field == "storage_information":
                            self.hardware_info[value["field_name"]] = self.disk_info
                        elif field == "disk_space_used":
                            self.hardware_info[value["field_name"]] = self.disk_used
                    case "pyitagent_version": self.hardware_info[value["field_name"]] = __version__
        dynamic_fields = self.custom_fields["custom_fields"]
        for field, value in dynamic_fields.items():
            if value["enabled"] is False:
                continue
            result = self.run_command(value["ps_command"])
            self.hardware_info[field] = result

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

    def run_command(self, cmd):
        completed = subprocess.run(["powershell.exe", "-Command", cmd], capture_output=True)
        return completed.stdout.decode("utf-8").strip()
    
    def determine_manufacturer(self):
        manufacturer = self.run_command("(gwmi win32_computersystem).manufacturer")
        # Specific case for HP and Hewlett-Packard
        if manufacturer == "Hewlett-Packard":
            manufacturer = "HP"
        return manufacturer

    def determine_serial_number(self):
        serial_number = self.run_command("(gwmi win32_baseboard).serialnumber")
        if self.manufacturer == 'Dell Inc.':
            return serial_number.split('/')[1]
        elif self.manufacturer == 'HP':
            return self.run_command('(gwmi win32_bios).serialnumber')
        return serial_number

    def determine_model_info(self):
        model_number = self.run_command("(gwmi win32_baseboard).product")
        model = self.run_command("(Get-WmiObject -Class:Win32_ComputerSystem).Model")
        if self.manufacturer == 'Lenovo':
            return model, model_number
        return model_number, model

    def determine_disk_info(self):
        disk_size = self.run_command("""
        $total=0
        (Get-WmiObject -Class Win32_DiskDrive | Where-Object { $_.MediaType -eq 'Fixed hard disk media' }).Size | foreach-object { $total=$total+$_/1gb }
        [Math]::Round($total, 2)
        """)
        disk_info = self.run_command("""
        (Get-WmiObject -Class Win32_DiskDrive | Where-Object { $_.MediaType -eq 'Fixed hard disk media' }) | ForEach-Object{
            echo "$($_.MediaType) - $($_.Model) - $($_.SerialNumber) - $([Math]::Round($_.Size/1gb,2)) GB"
        }
        """)
        disk_used = self.run_command("[Math]::Round(((Get-WmiObject Win32_LogicalDisk -Filter \"DeviceID='C:'\").Size - (Get-WmiObject Win32_LogicalDisk -Filter \"DeviceID='C:'\").FreeSpace) / 1GB, 2)")
        return disk_size, disk_info, disk_used

    def send_request(self, method, endpoint, payload=None):
        url = f"{self.url_prefix}/{endpoint}"
        if method == 'GET':
            response = requests.get(url, headers=self.headers)
        elif method == 'POST':
            response = requests.post(url, json=payload, headers=self.headers)
        elif method == 'PATCH':
            response = requests.patch(url, json=payload, headers=self.headers)
        else:
            raise ValueError("Unsupported HTTP method")

        if response.ok:
            return response.json()
        else:
            response.raise_for_status()

    def get_manufacturer(self, manufacturer_name):
        endpoint = f'manufacturers?name={manufacturer_name}'
        response = self.send_request('GET', endpoint)
        try:
            if response['total'] != 0:
                return response['rows'][0]['id']
            else:
                print("No manufacturer found in database, perhaps create a new one?")
                return None
        except KeyError:
            raise
        
    def post_manufacturer(self, manufacturer_name):
        endpoint = 'manufacturers'
        values = {
            'manufacturer_name': manufacturer_name,
        }
        payload = self.resolve_payload("manufacturer", values)
        response = self.send_request('POST', endpoint, payload=payload)
        if response.get('status') == 'success':
            return True
        else:
            raise Exception(f"Failed to post manufacturer: {response.get('messages')}")

    def get_or_create_manufacturer(self, manufacturer_name):
        manufacturer_id = self.get_manufacturer(manufacturer_name)
        if manufacturer_id is None:
            print("Creating new manufacturer")
            success = self.post_manufacturer(manufacturer_name)
            if success:
                manufacturer_id = self.get_manufacturer(manufacturer_name)
        return manufacturer_id
    
    def post_model(self, manufacturer_id, category_id = 3, fieldset_id = 1):
        endpoint = 'models'
        values = {
            'manufacturer_id': manufacturer_id,
            'category_id': category_id,
            'fieldset_id': fieldset_id
        }
        payload = self.resolve_payload("model", values)
        response = self.send_request('POST', endpoint, payload=payload)
        if response.get('status') == 'success':
            return True
        else:
            raise Exception(f"Failed to post model: {response.get('messages')}")

    def get_model(self, model_name):
        endpoint = f'models?limit=1&search={model_name}&sort=name'
        response = self.send_request('GET', endpoint)
        try:
            if response['total'] != 0:
                return response['rows'][0]['id']
        except KeyError:
            raise
        print("No model found in database, perhaps create a new one?")
        return None
    
    def get_or_create_model(self, manufacturer_id):
        model_id = self.get_model(self.model)
        if model_id is None:
            print("Creating new model")
            success = self.post_model(manufacturer_id, self.config['GENERAL']['snipeit_category_id'], self.config['GENERAL']['snipeit_fieldset_id'])
            if success:
                model_id = self.get_model(self.model)
        return model_id
    
    def post_hardware(self, serial_number, model_id, status_id, company_id):
        endpoint = 'hardware'
        values = {
            'serial_number': serial_number,
            'status_id': status_id,
            'model_id': model_id,
            'company_id': company_id,
        }
        payload = self.resolve_payload("hardware", values)
        response = self.send_request('POST', endpoint, payload=payload)
        if response.get('status') == 'success':
            return True
        else:
            raise Exception(f"Failed to post hardware: {response.get('messages')}")

    def get_hardware(self, serial_number):
        endpoint = f'hardware/byserial/{serial_number}?deleted=false'
        response = self.send_request('GET', endpoint)
        try:
            if response['total'] != 0:
                return response['rows'][0]['id']
        except KeyError:
            raise
        print("No hardware found in database, perhaps create a new one?")
        return None
    
    def patch_hardware(self, hardware_id, serial_number, model_id, status_id, company_id):
        endpoint = f'hardware/{hardware_id}?deleted=false'
        values = {
            'serial_number': serial_number,
            'status_id': status_id,
            'model_id': model_id,
            'company_id': company_id,
        }
        payload = self.resolve_payload("hardware", values)
        response = self.send_request('PATCH', endpoint, payload=payload)
        if response.get('status') == 'success':
            return True
        else:
            print(f"Failed to update hardware: {response.get('messages')}")
            return False
    
    def get_or_create_hardware(self, model_id, update_hardware, status_id = 2, company_id = 1):
        hardware_id = self.get_hardware(self.serial_number)
        if hardware_id is None:
            print("Creating new hardware")
            update_hardware = False
            success = self.post_hardware(self.serial_number, model_id, status_id, company_id)
            if success:
                hardware_id = self.get_hardware(self.serial_number)
        if update_hardware:
            print("Patching hardware")
            self.patch_hardware(hardware_id, self.serial_number, model_id, status_id, company_id)
        return hardware_id

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

# The other thing is to be continued, thanks ChatGPT
def get_config():
    config_path = resolve_path('config.ini')
    
    if not os.path.exists(config_path):
        # config.ini does not exist, you can generate a default one or notify the user to create it
        print("config.ini not found. Please create it at:", config_path)
        # Example code to generate a default config.ini, uncomment and modify as needed
        # config = configparser.ConfigParser()
        # config['DEFAULT'] = {'Setting1': 'Value1', 'Setting2': 'Value2'}
        # with open(config_path, 'w') as configfile:
        #     config.write(configfile)
        # print("A default config.ini has been created at:", config_path)
        return None  # or return a default config object

    # If config.ini exists, read it
    config = configparser.ConfigParser()
    config.read(config_path)
    return config

def get_custom_fields():
    custom_fields_path = resolve_path('custom_fields.json')

    if not os.path.exists(custom_fields_path):
        print("custom_fields.json not found. Please create it at:", custom_fields_path)
        return None
    
    with open(custom_fields_path, 'r') as file:
        return json.load(file)
    
def send_to_slack(message, webhook_url):
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

def main():
    try:
        # VV Seriously just don't change any of this. VV
        config = get_config()
        custom_fields = get_custom_fields()
        it_client = ITInventoryClient(config, custom_fields)
        it_client.collect_hardware_data()
        # ΛΛ Seriously just don't change any of this. ΛΛ

        # Debugging data! Case you need it!
        print(it_client.hardware_info)
        
        # Get the manufacturer
        manufacturer_id = it_client.get_or_create_manufacturer(it_client.manufacturer)
        if manufacturer_id is None:
            return print("Failed to fetch manufacturer")
        print("Manufacturer fetched: ", manufacturer_id)

        # Get the model
        model_id = it_client.get_or_create_model(manufacturer_id)
        if model_id is None:
            return print("Failed to fetch model")
        print("Model fetched: ", model_id)

        # Get the hardware, if it exists, update it properly.
        snipeit_status_id = config['GENERAL']['snipeit_status_id']
        snipeit_company_id = config['GENERAL']['snipeit_company_id']
        update_hardware = True
        hardware_id = it_client.get_or_create_hardware(model_id, update_hardware, snipeit_status_id, snipeit_company_id)
        if hardware_id is None:
            return print("Failed to fetch hardware")
        print("Hardware fetched: ", hardware_id)

    except Exception as e:
        config = get_config()
        hostname = subprocess.run(["powershell.exe", "-Command", "(Get-WmiObject Win32_OperatingSystem).CSName"], capture_output=True).stdout.decode("utf-8").strip()
        windows_user = subprocess.run(["powershell.exe", "-Command", "[System.Security.Principal.WindowsIdentity]::GetCurrent().Name"], capture_output=True).stdout.decode("utf-8").strip()
        error_message = f"An error occurred in the ITInventoryClient script: {e}\n"
        error_message += f"Error occured on computer: {hostname}\n"
        error_message += f"Error occured on user: {windows_user}\n"
        error_message += "```"  # Slack formatting for code blocks
        error_message += traceback.format_exc()
        error_message += "```"
        slack_webhook_url = config['DEBUGGING']['slack_webhook']  # Replace with your actual Slack webhook URL
        send_to_slack(error_message, slack_webhook_url)
        raise  # Optionally re-raise the exception if you want the script to stop on error

if __name__ == "__main__":
    main()