# dynamic_naming.py

import json
import os
import re
from utils.common import resolve_path

class DynamicNaming:
    def __init__(self):
        print("init dynamic naming...")
        self.config = self.load_config()
        # Check both the JSON config and the INI setting
        from config.settings import GlobalSettings
        ini_enabled = GlobalSettings().config.get('GENERAL', {}).get('pyitagent_dynamic_naming', False)
        self.enabled = self.config.get('enabled', False) and ini_enabled
        print(f"Dynamic naming enabled: {self.enabled} (JSON: {self.config.get('enabled', False)}, INI: {ini_enabled})")
        if self.enabled:
            print(f"Loaded patterns: {len(self.config.get('patterns', []))}")
            for pattern in self.config.get('patterns', []):
                print(f"  - {pattern.get('prefix')}: category_id={pattern.get('category_id')}")
            print(f"Loaded company mappings: {self.config.get('company_mappings', {})}")
        
    def load_config(self):
        """Load the dynamic naming configuration file."""
        config_path = resolve_path('dynamic_names.json')
        
        if not os.path.exists(config_path):
            print("dynamic_names.json not found, dynamic naming disabled")
            return {"enabled": False}
        
        try:
            with open(config_path, 'r') as file:
                return json.load(file)
        except json.JSONDecodeError:
            print("Error parsing dynamic_names.json, dynamic naming disabled")
            return {"enabled": False}
        except Exception as e:
            print(f"Error loading dynamic_names.json: {e}, dynamic naming disabled")
            return {"enabled": False}
    
    def parse_asset_name(self, name):
        """Parse an asset name to extract prefix and numeric part."""
        if not name or not self.enabled:
            return None, None, None
        
        print(f"Parsing asset name: {name}")
        
        # Match a pattern like LAP1234, DES5678, MON9012, etc.
        match = re.match(r'([A-Za-z]+)(\d)(\d+)', name)
        if not match:
            print(f"Asset name {name} doesn't match pattern")
            return None, None, None
        
        prefix = match.group(1).upper()  # Get the alphabetic prefix
        company_digit = match.group(2)   # Get the first digit (company identifier)
        asset_number = match.group(3)    # Get the rest of the number
        
        print(f"Parsed: prefix={prefix}, company_digit={company_digit}, asset_number={asset_number}")
        
        return prefix, company_digit, asset_number
    
    def get_company_id(self, name):
        """Get the company ID based on the asset name pattern."""
        if not self.enabled:
            print(f"Dynamic naming disabled - can't get company ID for {name}")
            return None
            
        _, company_digit, _ = self.parse_asset_name(name)
        
        if company_digit and company_digit in self.config.get('company_mappings', {}):
            company_id = self.config['company_mappings'][company_digit]
            print(f"Found company_id {company_id} for asset {name}")
            return company_id
        
        print(f"No company mapping found for asset {name}")
        return None
    
    def get_category_id(self, name):
        """Get the category ID based on the asset name prefix."""
        if not self.enabled:
            print(f"Dynamic naming disabled - can't get category ID for {name}")
            return None
            
        prefix, _, _ = self.parse_asset_name(name)
        
        if not prefix:
            print(f"No prefix found in {name}")
            return None
            
        for pattern in self.config.get('patterns', []):
            if pattern.get('prefix') == prefix:
                category_id = pattern.get('category_id')
                print(f"Found category_id {category_id} for prefix {prefix} in asset {name}")
                return category_id
        
        print(f"No category pattern found for prefix {prefix} in asset {name}")
        return None
    
    def generate_monitor_name(self, computer_name):
        """Generate a monitor name based on the computer's asset name."""
        if not self.enabled or not computer_name:
            print(f"Can't generate monitor name - dynamic naming disabled or no computer name")
            return None
            
        prefix, company_digit, asset_number = self.parse_asset_name(computer_name)
        
        if not prefix or not company_digit or not asset_number:
            print(f"Can't generate monitor name from {computer_name} - invalid pattern")
            return None
            
        # Use the configured monitor prefix (default to "MON" if not specified)
        monitor_prefix = self.config.get('monitor_prefix', 'MON')
        
        # Create the monitor name using the same company digit and asset number
        monitor_name = f"{monitor_prefix}{company_digit}{asset_number}"
        print(f"Generated monitor name {monitor_name} from computer {computer_name}")
        return monitor_name
    
    def is_valid_name_pattern(self, name):
        """Check if a name follows the configured pattern."""
        if not self.enabled:
            return False
            
        prefix, _, _ = self.parse_asset_name(name)
        
        if not prefix:
            return False
            
        # Check if the prefix is in our configured patterns
        is_valid = any(pattern.get('prefix') == prefix for pattern in self.config.get('patterns', []))
        print(f"Is {name} a valid pattern? {is_valid}")
        return is_valid