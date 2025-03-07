# monitor.py

from utils.common import run_command, format_number
from api.handler import resolve_payload, send_request
from config.settings import GlobalSettings
import config.constants as c
import base64
import binascii

class Monitor:
    def __init__(self):
        self.monitors = []
        self.collected_monitors = []
        self.detect_monitors()

    def detect_monitors(self):
        """Detect all connected monitors and their basic information."""
        # First, detect if this is a laptop/notebook
        is_laptop = False
        try:
            chassis_type = run_command("(Get-WmiObject -Class Win32_SystemEnclosure).ChassisTypes")
            # ChassisTypes values for laptops are typically 8, 9, 10, 11, 12, 14, 18, 21, 30, 31 or 32
            laptop_chassis_types = ['8', '9', '10', '11', '12', '14', '18', '21', '30', '31', '32']
            if any(laptop_type in chassis_type for laptop_type in laptop_chassis_types):
                is_laptop = True
                print("System detected as laptop/notebook")
        except Exception as e:
            print(f"Could not determine if system is a laptop: {e}")
        
        # Use our enhanced PowerShell script to get detailed monitor information
        ps_script = """
        function Get-MonitorDetails {
            [CmdletBinding()]
            param()

            # Define a helper function to convert hex-encoded names to readable strings
            function ConvertFrom-HexName {
                param([byte[]] $HexName)
                if ($null -eq $HexName -or $HexName.Length -eq 0) { return "Unknown" }
                # Remove any trailing zeros and convert to ASCII
                return [System.Text.Encoding]::ASCII.GetString($HexName -ne 0)
            }

            # Get monitor information from WMI
            $monitors = @()
            $monitorIds = Get-WmiObject -Namespace root\wmi -Class WmiMonitorID
            $displayParams = Get-WmiObject -Namespace root\wmi -Class WmiMonitorBasicDisplayParams
            $connections = Get-WmiObject -Namespace root\wmi -Class WmiMonitorConnectionParams

            foreach ($monitor in $monitorIds) {
                # Get matching display parameters
                $displayParam = $displayParams | Where-Object { $_.InstanceName -eq $monitor.InstanceName }
                $connection = $connections | Where-Object { $_.InstanceName -eq $monitor.InstanceName }
                
                # Try to detect if this is an internal laptop display
                $isInternalDisplay = $false
                if ($connection) {
                    # VideoOutputTechnology 0 typically means internal connection
                    $isInternalDisplay = ($connection.VideoOutputTechnology -eq 0)
                }
                
                # Extract manufacturer - properly handle common three-letter codes
                $rawManufacturer = ConvertFrom-HexName $monitor.ManufacturerName
                $mappedManufacturer = switch ($rawManufacturer) {
                    "DEL" { "Dell Inc." }
                    "AUO" { "AUO Corporation" }
                    "ACI" { "ASUS" }
                    "ACR" { "Acer" }
                    "HPN" { "HP" }
                    "HWP" { "HP" }
                    "LEN" { "Lenovo" }
                    "SAM" { "Samsung" }
                    "SEC" { "Samsung" }
                    "LGD" { "LG Electronics" }
                    "PHL" { "Philips" }
                    "SNY" { "Sony" }
                    "MSI" { "MSI" }
                    "BNQ" { "BenQ" }
                    "AOC" { "AOC" }
                    "NEC" { "NEC" }
                    "VSC" { "ViewSonic" }
                    default { $rawManufacturer }
                }
                
                # Extract model - look for complete model name
                $model = ConvertFrom-HexName $monitor.UserFriendlyName
                # If model is still "Unknown", try the product ID
                if ($model -eq "Unknown" -and $monitor.ProductCodeID) {
                    $model = ConvertFrom-HexName $monitor.ProductCodeID
                }
                
                # Extract serial number
                $serial = ConvertFrom-HexName $monitor.SerialNumberID
                
                # Calculate screen size in inches (approximate) if display parameters are available
                $screenSize = "Unknown"
                if ($displayParam) {
                    $widthCm = $displayParam.MaxHorizontalImageSize / 10
                    $heightCm = $displayParam.MaxVerticalImageSize / 10
                    
                    # Use Pythagorean theorem to calculate diagonal
                    $diagonalCm = [Math]::Sqrt([Math]::Pow($widthCm, 2) + [Math]::Pow($heightCm, 2))
                    
                    # Convert to inches (1 inch = 2.54 cm)
                    $diagonalInches = $diagonalCm / 2.54
                    
                    # Round to 1 decimal place
                    $screenSize = [Math]::Round($diagonalInches, 1)
                }
                
                # Further determine if this is an internal laptop display
                # Common laptop display manufacturers
                $laptopDisplayManufacturers = @("LG Philips", "Samsung", "AU Optronics", "AUO", "Chi Mei", "BOE", "Innolux", "Sharp", "LGD")
                if (-not $isInternalDisplay -and $model -match "LCD|Panel|Internal|Laptop|Notebook" -or $laptopDisplayManufacturers -contains $mappedManufacturer) {
                    # Additional check if this might be an internal display
                    $isInternalDisplay = $true
                }
                
                # Create monitor object with all details
                $monitorObj = [PSCustomObject]@{
                    Manufacturer = $mappedManufacturer
                    Model = $model
                    SerialNumber = $serial
                    YearOfManufacture = $monitor.YearOfManufacture
                    WeekOfManufacture = $monitor.WeekOfManufacture
                    InstanceName = $monitor.InstanceName
                    ScreenWidth = if ($displayParam) { $displayParam.MaxHorizontalImageSize } else { 0 }
                    ScreenHeight = if ($displayParam) { $displayParam.MaxVerticalImageSize } else { 0 }
                    ScreenSizeInches = $screenSize
                    IsActive = $monitor.Active
                    IsInternalDisplay = $isInternalDisplay
                    ConnectionType = if ($connection) { $connection.VideoOutputTechnology } else { "Unknown" }
                }
                
                $monitors += $monitorObj
            }
            
            # Return the collected monitor details as JSON
            return $monitors | ConvertTo-Json -Depth 4
        }

        # Run the function and return results
        Get-MonitorDetails
        """
        
        wmi_monitors = run_command(ps_script)
        
        try:
            import json
            # If multiple monitors are found, this will be a JSON array
            # If single monitor is found, this will be a JSON object
            parsed_monitors = json.loads(wmi_monitors)
            
            # Ensure we always have a list
            if isinstance(parsed_monitors, dict):
                parsed_monitors = [parsed_monitors]
            
            # Filter out laptop built-in displays if on a laptop
            filtered_monitors = []
            for monitor in parsed_monitors:
                # Skip built-in displays on laptops
                if is_laptop and monitor.get('IsInternalDisplay', False):
                    print(f"Skipping built-in laptop display: {monitor.get('Manufacturer')} {monitor.get('Model')}")
                    continue
                    
                # Additional checks for laptop internal displays
                if is_laptop and (
                    # Common patterns in laptop display names
                    "internal" in monitor.get('Model', '').lower() or
                    "built-in" in monitor.get('Model', '').lower() or
                    "panel" in monitor.get('Model', '').lower() or
                    # Connection type 0 is often internal
                    monitor.get('ConnectionType') == 0 or
                    # Manufacturers that typically make laptop displays
                    monitor.get('Manufacturer') in ['LG Electronics', 'AUO Corporation', 'BOE', 'Innolux', 'Sharp', 'Chi Mei']
                ):
                    print(f"Skipping likely laptop display: {monitor.get('Manufacturer')} {monitor.get('Model')}")
                    continue
                
                # If model is still unknown, create a generic name based on screen size
                if monitor.get('Model') == "Unknown" and monitor.get('ScreenSizeInches') != "Unknown":
                    monitor['Model'] = f"{monitor.get('ScreenSizeInches')}\" Display Monitor"
                
                # Clean up serial number (some monitors return "0" or very short values)
                if not monitor.get('SerialNumber') or monitor.get('SerialNumber') == "0" or len(monitor.get('SerialNumber', '')) < 2:
                    # Generate a unique identifier based on other properties if serial is missing
                    if monitor.get('Model') != "Unknown":
                        # Create a hash from the model name and screen dimensions as a pseudo-serial number
                        import hashlib
                        unique_str = f"{monitor.get('Manufacturer')}-{monitor.get('Model')}-{monitor.get('ScreenWidth')}x{monitor.get('ScreenHeight')}"
                        # Generate a hash and take the first 10 characters as the serial
                        hash_object = hashlib.md5(unique_str.encode())
                        monitor['SerialNumber'] = f"GEN-{hash_object.hexdigest()[:10].upper()}"
                    else:
                        monitor['SerialNumber'] = "Unknown"
                
                filtered_monitors.append(monitor)
            
            # Update the monitors list with filtered results
            self.monitors = filtered_monitors
            
            if len(filtered_monitors) == 0:
                print("No external monitors detected for collection")
                
        except json.JSONDecodeError:
            print(f"Error parsing monitor data: {wmi_monitors}")
            self.monitors = []

    def collect_monitor_data(self):
        """Collect additional data for each detected monitor."""
        for monitor in self.monitors:
            monitor_data = {
                'manufacturer': monitor.get('Manufacturer', 'Unknown'),
                'model': monitor.get('Model', 'Unknown'),
                'serial_number': monitor.get('SerialNumber', 'Unknown')
            }
            
            # Collect just custom fields without requiring static fields configuration
            collected_hardware = {}
            
            # Collect dynamic fields from custom_fields section
            dynamic_fields = GlobalSettings().custom_fields.get("monitor_fields", {}).get("custom_fields", {})
            for field, value in dynamic_fields.items():
                if value["enabled"] is False:
                    continue
                
                # Special handling for screen size - use calculated value from our script if available
                if field == "_snipeit_screen_size_21" and monitor.get('ScreenSizeInches') != "Unknown":
                    result = str(monitor.get('ScreenSizeInches'))
                else:
                    # Add the instance name to the command if available
                    instance_name = monitor.get('InstanceName')
                    ps_command = value["ps_command"]
                    
                    if instance_name:
                        # For commands that need to target a specific monitor
                        ps_command = ps_command.replace('Select-Object -First 1', f'Where-Object {{ $_.InstanceName -eq "{instance_name}" }}')
                    
                    result = run_command(ps_command)
                
                if value.get("float_number", False) is True:
                    result = format_number(result)
                collected_hardware[field] = result
            
            # Also add manufacture year and week if available (even if not in custom fields)
            if monitor.get('YearOfManufacture'):
                manufacture_date_field = next((field for field, value in dynamic_fields.items() 
                                             if value.get("name") == "Manufacture Date" and value["enabled"]), None)
                if manufacture_date_field:
                    # Format date as YYYY-MM (using week of year as a rough month approximation)
                    year = monitor.get('YearOfManufacture')
                    week = monitor.get('WeekOfManufacture', 1)
                    # Rough conversion from week to month (52 weeks / 12 months ≈ 4.33 weeks per month)
                    month = max(1, min(12, int(week / 4.33)))
                    collected_hardware[manufacture_date_field] = f"{year}-{month:02d}"
            
            # Add screen dimensions if available
            if monitor.get('ScreenWidth') and monitor.get('ScreenHeight'):
                # Look for a field to store this information
                dimensions_field = next((field for field, value in dynamic_fields.items() 
                                        if "dimension" in value.get("name", "").lower() and value["enabled"]), None)
                if dimensions_field:
                    collected_hardware[dimensions_field] = f"{monitor.get('ScreenWidth')}x{monitor.get('ScreenHeight')} mm"
            
            monitor_data['collected_hardware'] = collected_hardware
            self.collected_monitors.append(monitor_data)

    def get_manufacturer(self, manufacturer_name):
        """Get manufacturer ID from Snipe-IT."""
        endpoint = f'manufacturers?name={manufacturer_name}'
        response = send_request('GET', endpoint)
        # Check for API error response
        if response.get('status') == 'error':
            print("API Error:", response.get('messages', 'Unknown error'))
            return None
        # Handle case where 'total' key is missing or 0
        if response.get('total', 0) != 0:
            try:
                res_handler = response['rows'][0]
                if res_handler['name'] == manufacturer_name:
                    return response['rows'][0]['id']
                else: return None
            except (KeyError, IndexError):
                raise KeyError("Unexpected response format or empty 'rows'")
        else:
            return None

    def post_manufacturer(self, manufacturer_name):
        """Create a new manufacturer in Snipe-IT."""
        endpoint = 'manufacturers'
        values = {
            'manufacturer_name': manufacturer_name,
        }
        payload = resolve_payload("manufacturer", values)
        response = send_request('POST', endpoint, payload=payload)
        if response.get('status') == 'success':
            return True
        else:
            raise Exception(f"Failed to post manufacturer: {response.get('messages')}")

    def get_or_create_manufacturer(self, manufacturer_name):
        """Get or create manufacturer in Snipe-IT."""
        manufacturer_id = self.get_manufacturer(manufacturer_name)
        if manufacturer_id is None:
            print(f"Creating new manufacturer: {manufacturer_name}")
            success = self.post_manufacturer(manufacturer_name)
            if success:
                manufacturer_id = self.get_manufacturer(manufacturer_name)
        return manufacturer_id

    def get_model(self, model_name, manufacturer_id):
        """Get model ID from Snipe-IT."""
        endpoint = f'models?limit=1&search={model_name}&manufacturer_id={manufacturer_id}&sort=name&order=asc'
        response = send_request('GET', endpoint)
        # Check for API error response
        if response.get('status') == 'error':
            print("API Error:", response.get('messages', 'Unknown error'))
            return None
        # Handle case where 'total' key is missing or 0
        if response.get('total', 0) != 0:
            try:
                res_handler = response['rows'][0]
                if res_handler['name'] == model_name:
                    return response['rows'][0]['id']
                else: return None
            except (KeyError, IndexError):
                raise KeyError("Unexpected response format or empty 'rows'")
        else:
            return None

    def post_model(self, model_name, model_number, manufacturer_id, category_id, fieldset_id):
        """Create a new model in Snipe-IT."""
        endpoint = 'models'
        values = {
            'model': model_name,
            'model_number': model_number,
            'manufacturer_id': manufacturer_id,
            'category_id': category_id,
            'fieldset_id': fieldset_id
        }
        payload = resolve_payload("model", values)
        response = send_request('POST', endpoint, payload=payload)
        if response.get('status') == 'success':
            return True
        else:
            raise Exception(f"Failed to post model: {response.get('messages')}")

    def get_or_create_model(self, model_name, model_number, manufacturer_id):
        """Get or create model in Snipe-IT."""
        model_id = self.get_model(model_name, manufacturer_id)
        if model_id is None:
            print(f"Creating new model: {model_name}")
            success = self.post_model(
                model_name, 
                model_number, 
                manufacturer_id, 
                GlobalSettings().config['DEFAULTS']['snipeit_monitor_category_id'], 
                GlobalSettings().config['DEFAULTS']['snipeit_monitor_fieldset_id']
            )
            if success:
                model_id = self.get_model(model_name, manufacturer_id)
        return model_id

    def get_hardware(self, serial_number):
        """Get hardware asset ID from Snipe-IT using serial number."""
        endpoint = f'hardware/byserial/{serial_number}?deleted=false'
        try:
            response = send_request('GET', endpoint)
            # Check for API error response
            if response.get('status') == 'error':
                # "Asset does not exist" is an expected message when checking for new monitors
                if "Asset does not exist" in str(response.get('messages', '')):
                    return None
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
                    print("Unexpected response format or empty 'rows'")
                    return None
            else:
                return None
        except Exception as e:
            print(f"Error checking for existing hardware: {e}")
            return None

    def post_hardware(self, serial_number, model_id, monitor_name, status_id, company_id, collected_hardware):
        """Create a new hardware asset in Snipe-IT."""
        endpoint = 'hardware'
        values = {
            'serial_number': serial_number,
            'hostname': monitor_name,
            'model_id': model_id
        }
        payload = resolve_payload("hardware", values, collected_hardware)
        payload['company_id'] = company_id
        payload['status_id'] = status_id
        response = send_request('POST', endpoint, payload=payload)
        if response.get('status') == 'success':
            return True
        else:
            raise Exception(f"Failed to post hardware: {response.get('messages')}")

    def patch_hardware(self, hardware_id, serial_number, model_id, monitor_name, collected_hardware):
        """Update existing hardware asset in Snipe-IT."""
        endpoint = f'hardware/{hardware_id}?deleted=false'
        values = {
            'serial_number': serial_number,
            'hostname': monitor_name,
            'model_id': model_id
        }
        payload = resolve_payload("hardware", values, collected_hardware)
        response = send_request('PATCH', endpoint, payload=payload)
        if response.get('status') == 'success':
            return True
        else:
            print(f"Failed to update hardware: {response.get('messages')}")
            return False

    def process_monitors(self):
        """Process all detected monitors and sync with Snipe-IT."""
        self.collect_monitor_data()
        results = []
        
        for monitor in self.collected_monitors:
            manufacturer_name = monitor['manufacturer']
            model_name = monitor['model']
            serial_number = monitor['serial_number']
            collected_hardware = monitor['collected_hardware']
            
            # Skip monitors with invalid data
            if (serial_number == "Unknown" or not serial_number or 
                serial_number == "0" or len(serial_number) < 2 or
                model_name == "Unknown" or not model_name):
                print(f"Skipping monitor with insufficient data: {manufacturer_name} {model_name} - {serial_number}")
                continue
                
            # Get or create manufacturer
            manufacturer_id = self.get_or_create_manufacturer(manufacturer_name)
            
            # Get or create model
            model_id = self.get_or_create_model(model_name, model_name, manufacturer_id)
            
            # Check if monitor already exists
            hardware_id = self.get_hardware(serial_number)
            
            # Create monitor name (for display purposes)
            monitor_name = f"{manufacturer_name} {model_name}"
            
            if hardware_id is None:
                print(f"Creating new monitor: {monitor_name} - {serial_number}")
                try:
                    success = self.post_hardware(
                        serial_number, 
                        model_id, 
                        monitor_name, 
                        GlobalSettings().config['DEFAULTS']['snipeit_status_id'], 
                        GlobalSettings().config['DEFAULTS']['snipeit_company_id'],
                        collected_hardware
                    )
                    if success:
                        hardware_id = self.get_hardware(serial_number)
                except Exception as e:
                    print(f"Error creating monitor {monitor_name}: {e}")
                    continue
            else:
                print(f"Updating monitor: {monitor_name} - {serial_number}")
                try:
                    success = self.patch_hardware(
                        hardware_id,
                        serial_number, 
                        model_id, 
                        monitor_name,
                        collected_hardware
                    )
                except Exception as e:
                    print(f"Error updating monitor {monitor_name}: {e}")
                    continue
            
            results.append({
                'hardware_id': hardware_id,
                'manufacturer_id': manufacturer_id, 
                'manufacturer_name': manufacturer_name,
                'model_id': model_id, 
                'model_name': model_name,
                'serial_number': serial_number
            })
            
        return results