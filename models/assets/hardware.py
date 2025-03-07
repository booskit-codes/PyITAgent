# hardware.py

from utils.common import run_command, format_number
from api.handler import resolve_payload, send_request
from models.assets.edgecases import hardware_fixes
from config.settings import GlobalSettings
import config.constants as c

class Hardware:
    def __init__(self):
        self.collected_hardware = {}
        self.disk_size = None
        self.disk_info = None
        self.disk_used = None
        self.serial_number = self.determine_serial_number()

    def determine_serial_number(self):
        # Use BIOS serial number which is more reliable across manufacturers
        serial_number = run_command("(gwmi win32_bios).serialnumber")
        return serial_number

    def collect_hardware_data(self):
        static_fields = GlobalSettings().custom_fields["enabled_static_fields"]
        for field, value in static_fields.items():
            if value["enabled"]:
                match field:
                    case "mac_address": self.collected_hardware[value["field_name"]] = run_command("(Get-WmiObject Win32_NetworkAdapterConfiguration | Where-Object {$_.IPEnabled -eq $true} | Select-Object -First 1).MACAddress")
                    case "total_storage" | "storage_information" | "disk_space_used":
                        self.disk_size, self.disk_info, self.disk_used = self.determine_disk_info()
                        if field == "total_storage":
                            self.collected_hardware[value["field_name"]] = format_number(self.disk_size)
                        elif field == "storage_information":
                            self.collected_hardware[value["field_name"]] = self.disk_info
                        elif field == "disk_space_used":
                            self.collected_hardware[value["field_name"]] = format_number(self.disk_used)
                    case "pyitagent_version": self.collected_hardware[value["field_name"]] = c.VERSION
        dynamic_fields = GlobalSettings().custom_fields["custom_fields"]
        for field, value in dynamic_fields.items():
            if value["enabled"] is False:
                continue
            result = run_command(value["ps_command"])
            if value["float_number"] is True: result = format_number(result)
            self.collected_hardware[field] = result

    def determine_disk_info(self):
        disk_size = run_command("""
        $total=0
        (Get-WmiObject -Class Win32_DiskDrive | Where-Object { $_.MediaType -eq 'Fixed hard disk media' }).Size | foreach-object { $total=$total+$_/1gb }
        [Math]::Round($total, 2)
        """)
        disk_info = run_command("""
        (Get-WmiObject -Class Win32_DiskDrive | Where-Object { $_.MediaType -eq 'Fixed hard disk media' }) | ForEach-Object{
            echo "$($_.MediaType) - $($_.Model) - $($_.SerialNumber) - $([Math]::Round($_.Size/1gb,2)) GB"
        }
        """)
        disk_used = run_command("[Math]::Round(((Get-WmiObject Win32_LogicalDisk -Filter \"DeviceID='C:'\").Size - (Get-WmiObject Win32_LogicalDisk -Filter \"DeviceID='C:'\").FreeSpace) / 1GB, 2)")
        return disk_size, disk_info, disk_used

    def post_hardware(self, serial_number, model_id, hostname, status_id, company_id):
        endpoint = 'hardware'
        values = {
            'serial_number': serial_number,
            'hostname': hostname,
            'model_id': model_id
        }
        payload = resolve_payload("hardware", values, self.collected_hardware)
        payload['company_id'] = company_id
        payload['status_id'] = status_id
        response = send_request('POST', endpoint, payload=payload)
        if response.get('status') == 'success':
            return True
        else:
            raise Exception(f"Failed to post hardware: {response.get('messages')}")

    def get_hardware(self, serial_number):
        endpoint = f'hardware/byserial/{serial_number}?deleted=false'
        response = send_request('GET', endpoint)
        # Check for API error response
        if response.get('status') == 'error':
            print("API Error:", response.get('messages', 'Unknown error'))
            return None
        # Handle case where 'total' key is missing or 0
        if response.get('total', 0) != 0:
            try:
                res_handler = response['rows'][0]
                if res_handler['serial'] == serial_number:
                    return response['rows'][0]['id']
                else: return None
            except (KeyError, IndexError):
                raise KeyError("Unexpected response format or empty 'rows'")
        else:
            return None

    def patch_hardware(self, hardware_id, serial_number, model_id, hostname):
        endpoint = f'hardware/{hardware_id}?deleted=false'
        values = {
            'serial_number': serial_number,
            'hostname': hostname,
            'model_id': model_id
        }
        payload = resolve_payload("hardware", values, self.collected_hardware)
        response = send_request('PATCH', endpoint, payload=payload)
        if response.get('status') == 'success':
            return True
        else:
            print(f"Failed to update hardware: {response.get('messages')}")
            return False
    
    def get_or_create_hardware(self, metadata, hardware):
        update_hardware = True
        self.serial_number = hardware_fixes(self.serial_number, metadata, hardware)
        self.collect_hardware_data()
        hardware_id = self.get_hardware(self.serial_number)
        if hardware_id is None:
            print("Creating new hardware")
            update_hardware = False
            success = self.post_hardware(self.serial_number, metadata['model_id'], metadata['hostname'], GlobalSettings().config['DEFAULTS']['snipeit_status_id'], GlobalSettings().config['DEFAULTS']['snipeit_company_id'])
            if success:
                hardware_id = self.get_hardware(self.serial_number)
        if update_hardware:
            print("Patching hardware")
            self.patch_hardware(hardware_id, self.serial_number, metadata['model_id'], metadata['hostname'])
        return hardware_id, self.collected_hardware