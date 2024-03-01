# common.py

import sys
import subprocess
import os

# Resolve pyinstaller's stoopid windows executable path issue
def resolve_path(path):
    if getattr(sys, "frozen", False):
        # If the 'frozen' flag is set, we are in bundled-app mode!
        # Use the directory of the executable
        application_path = os.path.dirname(sys.executable)
        resolved_path = os.path.abspath(os.path.join(application_path, path))
    else:
        # Normal development mode.
        resolved_path = os.path.abspath(os.path.join(os.getcwd(), path))

    return resolved_path

def run_command(cmd):
    # The flag to prevent the console window from showing up
    CREATE_NO_WINDOW = 0x08000000
    
    # Execute the command without showing a window
    try:
        completed = subprocess.Popen(["powershell.exe", "-Command", cmd],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    text=True,
                                    creationflags=CREATE_NO_WINDOW)
    except:
        raise Exception("Could not open powershell.exe")
    
    # Wait for the command to complete and get the output
    stdout, stderr = completed.communicate()
    
    # Return the standard output
    return stdout.strip()

def format_number(val):
    try:
        # Try converting the input to a float, replacing commas with dots if necessary
        number = float(val.replace(',', '.'))
        # Check if the number is an integer by comparing it with its integer version
        if number == int(number):
            # If it's an integer, return the integer part
            return str(int(number))
        else:
            # If it's a float, format it with a comma instead of a dot
            return "{:.1f}".format(number).replace('.', ',')
    except ValueError:
        # If conversion to a float fails, return the original input
        return val