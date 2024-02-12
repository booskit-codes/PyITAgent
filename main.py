import requests
import subprocess
import configparser
import os
import sys

class ITInventoryClient:
    def __init__(self, url, access_token):
        self.access_token = access_token
        self.headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {self.access_token}",
            "content-type": "application/json"
        }
        self.url_prefix = url
        self.manufacturer = self.run_command("(gwmi win32_computersystem).manufacturer")
        self.serial_number = self.determine_serial_number()
        self.hostname = self.run_command("(Get-WmiObject Win32_OperatingSystem).CSName")
        self.os = self.run_command("(Get-WmiObject Win32_OperatingSystem).Caption")
        self.ram_available = self.run_command("[Math]::Round((Get-WmiObject Win32_ComputerSystem).totalphysicalmemory / 1gb,1)")
        self.os_install_date = self.run_command("[math]::Round((New-TimeSpan -Start (Get-Date '1970-01-01') -End (Get-CimInstance Win32_OperatingSystem).InstallDate).TotalSeconds)")
        self.bios_release_date = self.run_command("[math]::Round((New-TimeSpan -Start (Get-Date '1970-01-01') -End (Get-CimInstance Win32_BIOS).ReleaseDate).TotalSeconds)")
        self.model_number, self.model = self.determine_model_info()
        self.ip_address = self.run_command("(Test-Connection (hostname) -count 1).IPv4Address.IPAddressToString")
        self.disk_size, self.disk_info = self.determine_disk_info()
        self.mac_addresses = self.run_command("(Get-WmiObject Win32_NetworkAdapterConfiguration | Where-Object {$_.IPEnabled -eq $true} | Select-Object -First 1).MACAddress")
        self.processor = self.run_command("(gwmi Win32_processor).name")
        self.current_user = self.run_command("[System.Security.Principal.WindowsIdentity]::GetCurrent().Name")

    def run_command(self, cmd):
        completed = subprocess.run(["powershell.exe", "-Command", cmd], capture_output=True)
        return completed.stdout.decode("utf-8").strip()

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
        return disk_size, disk_info

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
            return None
        
    def post_manufacturer(self, manufacturer_name):
        endpoint = 'manufacturers'
        payload = {'name': manufacturer_name}
        response = self.send_request('POST', endpoint, payload=payload)
        if response.get('status') == 'success':
            return True
        else:
            print(f"Failed to post manufacturer: {response.get('messages')}")
            return False

    def get_or_create_manufacturer(self, manufacturer_name):
        manufacturer_id = self.get_manufacturer(manufacturer_name)
        if manufacturer_id is None:
            print("Creating new manufacturer")
            success = self.post_manufacturer(manufacturer_name)
            if success:
                manufacturer_id = self.get_manufacturer(manufacturer_name)
        return manufacturer_id
    
    def post_model(self, manufacturer_id, category_id=3, fieldset_id=1):
        endpoint = 'models'
        payload = {
            "name": self.model,
            "model_number": self.model_number,
            "category_id": category_id,
            "manufacturer_id": manufacturer_id,
            "fieldset_id": fieldset_id
        }
        response = self.send_request('POST', endpoint, payload=payload)
        if response.get('status') == 'success':
            return True
        else:
            print(f"Failed to post model: {response.get('messages')}")
            return False

    def get_model(self, model_name):
        endpoint = f'models?limit=1&search={model_name}&sort=name'
        response = self.send_request('GET', endpoint)
        try:
            if response['total'] != 0:
                return response['rows'][0]['id']
        except KeyError:
            return None
        print("No model found in database, perhaps create a new one?")
        return None
    
    def get_or_create_model(self, manufacturer_id):
        model_id = self.get_model(self.model)
        if model_id is None:
            print("Creating new model")
            success = self.post_model(manufacturer_id)
            if success:
                model_id = self.get_model(self.model)
        return model_id
    
    def post_hardware(self, serial_number, model_id, status_id, company_id):
        endpoint = 'hardware'
        payload = {
            'serial': serial_number,
            'name': self.hostname,
            'asset_tag': serial_number,  # Assuming this method exists
            'status_id': status_id,
            'model_id': model_id,
            'company_id': company_id,
            '_snipeit_mac_address_1': self.mac_addresses,
            '_snipeit_memory_ram_2': self.ram_available,
            '_snipeit_operating_system_3': self.os,
            '_snipeit_os_install_date_4': self.os_install_date,
            '_snipeit_ip_address_9': self.ip_address,
            '_snipeit_total_storage_6': self.disk_size,
            '_snipeit_storage_information_7': self.disk_info,
            '_snipeit_processor_cpu_8': self.processor,
            '_snipeit_bios_release_date_10': self.bios_release_date,
            '_snipeit_windows_username_11': self.current_user
        }
        response = self.send_request('POST', endpoint, payload=payload)
        if response.get('status') == 'success':
            return True
        else:
            print(f"Failed to post hardware: {response.get('messages')}")
            return False

    def get_hardware(self, serial_number):
        endpoint = f'hardware/byserial/{serial_number}?deleted=false'
        response = self.send_request('GET', endpoint)
        try:
            if response['total'] != 0:
                return response['rows'][0]['id']
        except KeyError:
            return None
        print("No hardware found in database, perhaps create a new one?")
        return None
    
    def patch_hardware(self, hardware_id, serial_number, model_id, status_id, company_id):
        endpoint = f'hardware/{hardware_id}?deleted=false'
        payload = {
            'serial': serial_number,
            'name': self.hostname,
            'asset_tag': serial_number,  # Assuming this method exists
            'status_id': status_id,
            'model_id': model_id,
            'company_id': company_id,
            '_snipeit_mac_address_1': self.mac_addresses,
            '_snipeit_memory_ram_2': self.ram_available,
            '_snipeit_operating_system_3': self.os,
            '_snipeit_os_install_date_4': self.os_install_date,
            '_snipeit_ip_address_9': self.ip_address,
            '_snipeit_total_storage_6': self.disk_size,
            '_snipeit_storage_information_7': self.disk_info,
            '_snipeit_processor_cpu_8': self.processor,
            '_snipeit_bios_release_date_10': self.bios_release_date,
            '_snipeit_windows_username_11': self.current_user
        }
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

def main():

    # VV Seriously just don't change any of this. VV
    config = get_config()

    url = config['DEFAULT']['site']
    api_key = config['DEFAULT']['api_key']

    it_client = ITInventoryClient(url, api_key)
    # ΛΛ Seriously just don't change any of this. ΛΛ
    
    # This will serve as both debugging purposes & just general information, nothing bad with information.
    print(f"""
          Hardware Information
          -------------------------
          
          Manufacturer: {it_client.manufacturer}
          Serial Number: {it_client.serial_number}
          Hostname: {it_client.hostname}
          OS: {it_client.os}
          Ram Available: {it_client.ram_available}
          OS Install Date: {it_client.os_install_date}
          Model Number: {it_client.model_number}
          IP Address: {it_client.ip_address}
          Disk Size: {it_client.disk_size}
          MAC Address: {it_client.mac_addresses}
          Processor: {it_client.processor}
          Current User: {it_client.current_user}
          BIOS Release Date: {it_client.bios_release_date}
          """)
    
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

if __name__ == "__main__":
    main()