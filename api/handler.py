# handler.py

import requests
from config.settings import GlobalSettings

def send_request(method, endpoint, payload=None):
    print(f"API Request: {method} {endpoint}")
    if payload:
        print(f"Payload: {payload}")
        
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
        result = response.json()
        print(f"API Response: Status={response.status_code}")
        return result
    else:
        print(f"API Error: Status={response.status_code}, Response={response.text}")
        response.raise_for_status()

def resolve_payload(type, values, collected_hardware = None):
    print(f"Resolving payload for type: {type} with values: {values}")
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
            print(f"Generated hardware payload: {hardware}")
            return hardware
        case "model":
            payload = {
                "name": values['model'],
                "model_number": values['model_number'],
                "category_id": values['category_id'],
                "manufacturer_id": values['manufacturer_id'],
                "fieldset_id": values['fieldset_id']
            }
            print(f"Generated model payload: {payload}")
            return payload
        case "manufacturer":
            payload = {
                "name": values['manufacturer_name']
            }
            print(f"Generated manufacturer payload: {payload}")
            return payload