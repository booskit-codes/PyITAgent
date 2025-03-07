# edgecases.py

from utils.common import run_command

def manufacturer_fixes(manufacturer):
    # Specific case for HP and Hewlett-Packard
    match manufacturer:
        case "Hewlett-Packard": manufacturer = "HP"
        case _: manufacturer = manufacturer
    return manufacturer

def model_fixes(hardware, model, model_number):
    manufacturer = hardware['manufacturer_name']
    if manufacturer == 'Lenovo':
            return model, model_number
    return model_number, model

def hardware_fixes(serial_number, metadata, hardware):
    manufacturer = hardware['manufacturer_name']
    hostname = metadata['hostname']
    
    # Special handling for Dell which may have format like "CN12345/SERVICE_TAG"
    if manufacturer == "Dell Inc.":
        try:
            serial_number = serial_number.split('/')[1]
        except (IndexError):
            # Keep original if splitting fails
            pass
    
    # Use hostname only as fallback if serial number is empty or default placeholder
    invalid_serials = ["", "To be filled by O.E.M.", "System Serial Number", "Chassis Serial Number", "N/A"]
    if not serial_number or serial_number.strip() in invalid_serials:
        serial_number = hostname
        
    return serial_number