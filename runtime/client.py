# client.py

from models.assets.manager import AssetManager
from config.settings import GlobalSettings
import config.constants as c
from utils.progress_bar import ProgressBar
from utils.common import run_command

class PyITAgent:
    def __init__(self):
        self.progress_bar = ProgressBar(total=100)
        self.config = GlobalSettings().config
        self.custom_fields = GlobalSettings().custom_fields
        self.metadata = {}
        self.hardware = {}

    def runtime(self):
        print("PyITAgent", c.VERSION)
        self.progress_bar.update_progress(0, 'Initiating runtime')
        if self.config['GENERAL']['pyitagent_asset_collection']:
            self.progress_bar.update_progress(5, 'Initiating AssetManager instance')
            asset_manager = AssetManager()  # Create a single instance of AssetManager

            self.progress_bar.update_progress(10, 'Fetching hostname information')
            self.metadata['hostname'] = run_command("(Get-WmiObject Win32_OperatingSystem).CSName")
            self.progress_bar.update_progress(30, 'Running AssetManager.Manufacturer')
            self.metadata['manufacturer_id'], self.hardware['manufacturer_name'] = asset_manager.manufacturer.get_or_create_manufacturer()
            self.progress_bar.update_progress(50, 'Running AssetManager.Model')
            self.metadata['model_id'], self.hardware['model_number'], self.hardware['model'] = asset_manager.model.get_or_create_model(self.metadata, self.hardware)
            self.progress_bar.update_progress(80, 'Running AssetManager.Hardware')
            self.metadata['hardware_id'], temp_new_hardware = asset_manager.hardware.get_or_create_hardware(self.metadata, self.hardware)
            self.progress_bar.update_progress(95, 'Finalizing')
            self.hardware.update(temp_new_hardware)
            self.progress_bar.update_progress(100, 'Finished')
            self.progress_bar.finish()

            print(self.metadata)
            print(self.hardware)

    # Other methods...
