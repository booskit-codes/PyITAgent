# model.py

from utils.common import run_command
from api.handler import resolve_payload, send_request
from config.settings import GlobalSettings
from models.assets.edgecases import model_fixes

class Model:
    def __init__(self):
        self.model_number, self.model = self.determine_model_info()

    def determine_model_info(self):
        model_number = run_command("(gwmi win32_baseboard).product")
        model = run_command("(Get-WmiObject -Class:Win32_ComputerSystem).Model")
        return model_number, model
    
    def post_model(self, manufacturer_id, category_id = 3, fieldset_id = 1):
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
        endpoint = f'models?limit=1&search={model_name}&sort=name&order=asc'
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
    
    def get_or_create_model(self, metadata, hardware):
        model_id = self.get_model(self.model)
        if model_id is None:
            print("Creating new model")
            success = self.post_model(metadata['manufacturer_id'], GlobalSettings().config['DEFAULTS']['snipeit_category_id'], GlobalSettings().config['DEFAULTS']['snipeit_fieldset_id'])
            if success:
                model_id = self.get_model(self.model)
        self.model_number, self.model = model_fixes(hardware, self.model, self.model_number)
        return model_id, self.model_number, self.model