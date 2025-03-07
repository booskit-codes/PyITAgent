# settings.py

import configparser
import os
import json

from utils.common import resolve_path

class GlobalSettings:
    def __init__(self):
        self.config = self.get_config()
        self.custom_fields = self.get_custom_fields()
    
    def get_config(self):
        config_path = resolve_path('config.ini')
        
        if not os.path.exists(config_path):
            # Example code to generate a default config.ini, uncomment and modify as needed
            # config = configparser.ConfigParser()
            # config['DEFAULT'] = {'Setting1': 'Value1', 'Setting2': 'Value2'}
            # with open(config_path, 'w') as configfile:
            #     config.write(configfile)
            # print("A default config.ini has been created at:", config_path)
            # or return a default config object
            raise Exception(f"config.ini not found. Please create it at: {config_path}")

        config = configparser.ConfigParser()
        config.read(config_path)
        
        # Assuming you know which keys should be treated as boolean
        boolean_keys = ['silent_mode', 'slack_logging', 'pyitagent_asset_collection', 'pyitagent_asset_tag_generation', 'pyitagent_asset_monitor_collection', 'pyitagent_dynamic_naming']  # Add your boolean keys here
        
        # Dictionary to hold the parsed configuration
        parsed_config = {}

        for section in config.sections():
            parsed_config[section] = {}
            for key in config[section]:
                if key in boolean_keys:
                    # Use getboolean() for known boolean keys
                    parsed_config[section][key] = config.getboolean(section, key)
                else:
                    # Keep other values as strings
                    parsed_config[section][key] = config.get(section, key)

        return parsed_config


    def get_custom_fields(self):
        custom_fields_path = resolve_path('custom_fields.json')

        if not os.path.exists(custom_fields_path):
            raise Exception("custom_fields.json not found. Please create it at:", custom_fields_path)
        
        with open(custom_fields_path, 'r') as file:
            return json.load(file)
