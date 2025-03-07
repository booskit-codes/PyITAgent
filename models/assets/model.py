# model.py

from utils.common import run_command
from api.handler import resolve_payload, send_request
from config.settings import GlobalSettings
from models.assets.edgecases import model_fixes
from utils.dynamic_naming import DynamicNaming

class Model:
    def __init__(self):
        self.model_number, self.model = self.determine_model_info()
        self.dynamic_naming = DynamicNaming()
        self.hostname = None

    def determine_model_info(self):
        model_number = run_command("(gwmi win32_baseboard).product")
        model = run_command("(Get-WmiObject -Class:Win32_ComputerSystem).Model")
        return model_number, model
    
    def set_hostname(self, hostname):
        """Set the hostname for dynamic category determination."""
        self.hostname = hostname
    
    def get_dynamic_category_id(self):
        """Get category ID based on dynamic naming rules."""
        if not self.dynamic_naming.enabled or not self.hostname:
            return None
        
        return self.dynamic_naming.get_category_id(self.hostname)
    
    def post_model(self, manufacturer_id, category_id = None, fieldset_id = 1):
        # Determine category_id from dynamic naming if possible
        dynamic_category_id = self.get_dynamic_category_id()
        if dynamic_category_id is not None:
            # Use the dynamic category ID from the naming pattern
            print(f"Using dynamic category ID: {dynamic_category_id}")
            category_id = dynamic_category_id
        elif category_id is None:
            # Fallback to default category ID
            print(f"Using default category ID: {GlobalSettings().config['DEFAULTS']['snipeit_category_id']}")
            category_id = GlobalSettings().config['DEFAULTS']['snipeit_category_id']
            
        endpoint = 'models'
        values = {
            'manufacturer_id': manufacturer_id,
            'model': self.model,
            'model_number': self.model_number,
            'category_id': category_id,
            'fieldset_id': fieldset_id
        }
        payload = resolve_payload("model", values)
        response = send_request('POST', endpoint, payload=payload)
        if response.get('status') == 'success':
            return True
        else:
            raise Exception(f"Failed to post model: {response.get('messages')}")

    def get_model(self, model_name):
        """Get model ID and details from Snipe-IT."""
        endpoint = f'models?limit=1&search={model_name}&sort=name&order=asc'
        response = send_request('GET', endpoint)
        # Check for API error response
        if response.get('status') == 'error':
            print("API Error:", response.get('messages', 'Unknown error'))
            return None, None, None
        
        # Handle case where 'total' key is missing or 0
        if response.get('total', 0) != 0:
            try:
                res_handler = response['rows'][0]
                if res_handler['name'] == model_name:
                    model_id = response['rows'][0]['id']
                    category_id = response['rows'][0].get('category', {}).get('id')
                    print(f"Found existing model: {model_name}, id: {model_id}, category_id: {category_id}")
                    return model_id, category_id, response['rows'][0]
                else: 
                    return None, None, None
            except (KeyError, IndexError):
                raise KeyError("Unexpected response format or empty 'rows'")
        else:
            return None, None, None
    
    def update_model_category(self, model_id, category_id, fieldset_id=None):
        """Update an existing model's category."""
        if not fieldset_id:
            fieldset_id = GlobalSettings().config['DEFAULTS']['snipeit_fieldset_id']
            
        endpoint = f'models/{model_id}'
        print(f"Updating model {model_id} category to {category_id}")
        
        # We only update the category_id to minimize changes
        values = {
            'category_id': category_id
        }
        
        response = send_request('PATCH', endpoint, payload=values)
        if response.get('status') == 'success':
            print(f"Successfully updated model {model_id} category to {category_id}")
            return True
        else:
            print(f"Failed to update model category: {response.get('messages')}")
            return False
    
    def get_or_create_model(self, metadata, hardware):
        # Set hostname for dynamic category determination
        if 'hostname' in metadata:
            self.set_hostname(metadata['hostname'])
            
        # Get dynamic category ID if available
        dynamic_category_id = self.get_dynamic_category_id()
        print(f"Dynamic category ID for {self.hostname}: {dynamic_category_id}")
        
        # Get existing model if it exists
        model_id, current_category_id, model_details = self.get_model(self.model)
        
        if model_id is None:
            print("Creating new model")
            # If we have a dynamic category ID, use it, otherwise use the default
            category_id = dynamic_category_id if dynamic_category_id is not None else GlobalSettings().config['DEFAULTS']['snipeit_category_id']
            
            success = self.post_model(
                metadata['manufacturer_id'], 
                category_id, 
                GlobalSettings().config['DEFAULTS']['snipeit_fieldset_id']
            )
            if success:
                model_id, _, _ = self.get_model(self.model)
        else:
            # If the model exists and we have a dynamic category ID that's different from the current category
            if (dynamic_category_id is not None and 
                current_category_id is not None and 
                int(dynamic_category_id) != int(current_category_id)):
                
                print(f"Model exists but has wrong category. Current: {current_category_id}, Should be: {dynamic_category_id}")
                # Update the model's category
                self.update_model_category(model_id, dynamic_category_id)
        
        self.model_number, self.model = model_fixes(hardware, self.model, self.model_number)
        return model_id, self.model_number, self.model