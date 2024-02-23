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

    def runtime(self):
        if self.config['GENERAL']['pyitagent_asset_collection']:
            asset_manager = AssetManager()  # Create a single instance of AssetManager

            self.metadata['hostname'] = run_command("(Get-WmiObject Win32_OperatingSystem).CSName")
            self.metadata['manufacturer_id'], self.hardware['manufacturer_name'] = asset_manager.manufacturer.get_or_create_manufacturer()
            self.metadata['model_id'], self.hardware['model_number'], self.hardware['model'] = asset_manager.model.get_or_create_model(self.metadata, self.hardware)
            self.metadata['hardware_id'], temp_new_hardware = asset_manager.hardware.get_or_create_hardware(self.metadata, self.hardware)
            self.hardware.update(temp_new_hardware)

            print(self.metadata)
            print(self.hardware)

    # Other methods...
