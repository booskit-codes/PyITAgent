# handler.py

import requests
from config.settings import GlobalSettings

def send_request(method, endpoint, payload=None):
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {GlobalSettings().config['SERVER']['api_key']}",
        "content-type": "application/json"
    }
    url = f"{GlobalSettings().config['SERVER']['site']}/{endpoint}"
    match method:
        case 'GET':
            response = requests.get(url, headers=headers)
        case 'POST':
            response = requests.post(url, json=payload, headers=headers)
        case 'PATCH':
            response = requests.patch(url, json=payload, headers=headers)
        case _:
            raise ValueError("Unsupported HTTP method")

    if response.ok:
        return response.json()
    else:
        response.raise_for_status()

def resolve_payload(type, values, collected_hardware = None):
    match type:
        case "hardware":
            hardware = {
                'serial': values['serial_number'],
                'name': values['hostname'],
                'asset_tag': values['serial_number'],
                'model_id': values['model_id']
            }
            if not GlobalSettings().config['GENERAL'].get('pyitagent_asset_tag_generation', True):
                hardware.pop('asset_tag')
            if collected_hardware:
                for field, value in collected_hardware.items():
                    hardware[field] = value
            return hardware
        case "model":
            return {
                "name": values['model'],
                "model_number": values['model_number'],
                "category_id": values['category_id'],
                "manufacturer_id": values['manufacturer_id'],
                "fieldset_id": values['fieldset_id']
            }
        case "manufacturer":
            return {
                "name": values['manufacturer_name']
            }