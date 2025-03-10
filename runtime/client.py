# client.py

from models.assets.manager import AssetManager
from config.settings import GlobalSettings
from utils.common import run_command

class PyITAgent:
    def __init__(self):
        self.config = GlobalSettings().config
        self.custom_fields = GlobalSettings().custom_fields
        self.metadata = {}
        self.hardware = {}
        self.monitors = []

    def runtime(self):
        asset_manager = AssetManager()  # Create a single instance of AssetManager

        # Process computer asset if enabled
        if self.config['GENERAL']['pyitagent_asset_collection']:
            self.metadata['hostname'] = run_command("(Get-WmiObject Win32_OperatingSystem).CSName")
            self.metadata['manufacturer_id'], self.hardware['manufacturer_name'] = asset_manager.manufacturer.get_or_create_manufacturer()
            self.metadata['model_id'], self.hardware['model_number'], self.hardware['model'] = asset_manager.model.get_or_create_model(self.metadata, self.hardware)
            self.metadata['hardware_id'], temp_new_hardware = asset_manager.hardware.get_or_create_hardware(self.metadata, self.hardware)
            self.hardware.update(temp_new_hardware)

            print(self.metadata)
            print(self.hardware)
        
        # Process monitor assets if enabled
        if self.config['GENERAL'].get('pyitagent_asset_monitor_collection', False):
            print("Collecting monitor information...")
            self.monitors = asset_manager.monitor.process_monitors()
            
            if self.monitors:
                print(f"Processed {len(self.monitors)} monitors")
                print(self.monitors)
            else:
                print("No monitors detected or processed")

    # Other methods...