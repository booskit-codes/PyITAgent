# manufactuer.py

from utils.common import run_command
from api.handler import resolve_payload, send_request
from models.assets.edgecases import manufacturer_fixes

class Manufacturer:
    def __init__(self):
        self.manufacturer_name = self.determine_manufacturer()

    def determine_manufacturer(self):
        manufacturer = run_command("(gwmi win32_computersystem).manufacturer")
        return manufacturer_fixes(manufacturer)
    
    def get_manufacturer(self, manufacturer_name):
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

    def get_or_create_manufacturer(self):
        manufacturer_id = self.get_manufacturer(self.manufacturer_name)
        if manufacturer_id is None:
            print("Creating new manufacturer")
            success = self.post_manufacturer(self.manufacturer_name)
            if success:
                manufacturer_id = self.get_manufacturer(self.manufacturer_name)
        return manufacturer_id, self.manufacturer_name