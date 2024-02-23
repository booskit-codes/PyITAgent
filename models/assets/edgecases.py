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
    match manufacturer:
        case "Dell Inc.": serial_number = serial_number.split('/')[1]
        case "HP": serial_number = run_command('(gwmi win32_bios).serialnumber')
        case _: serial_number = hostname
    return serial_number