import logging
import subprocess
import json
import os
import sys

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class PowerShellLogging:
    def __init__(self, data):
        self.data = data
        self.manufacturer = self.run_command("(gwmi win32_computersystem).manufacturer")
        self.hardware = {}

    def collect_hardware_data(self):
        static_fields = self.data["enabled_static_fields"]
        for field, is_enabled in static_fields.items():
            if is_enabled:
                print(f"{field} is enabled")
            else:
                print(f"{field} is disabled")
        dynamic_fields = self.data["custom_fields"]
        for field, value in dynamic_fields.items():
            print(value)
            if value["enabled"] is False:
                continue
            result = self.run_command(value["ps_command"])
            print(f"{value["name"]}: {result}")
            self.hardware[field] = result

    def run_command(self, cmd):
        try:
            # The flag to prevent the console window from showing up
            CREATE_NO_WINDOW = 0x08000000
            
            # Execute the command without showing a window
            process = subprocess.Popen(["powershell.exe", "-Command", cmd],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    text=True, creationflags=CREATE_NO_WINDOW)
            
            # Wait for the command to complete and capture the output and error
            stdout, stderr = process.communicate()
            
            # Check if the command was executed successfully
            if process.returncode == 0:
                logging.info(f"Command executed successfully: {cmd}")
                return stdout.strip()
            else:
                # Log an error if the command failed
                logging.error(f"Command failed with return code {process.returncode}: {cmd}")
                logging.error(f"Error output: {stderr.strip()}")
                return None
        except Exception as e:
            # Log any exceptions that occur during execution
            logging.exception(f"An exception occurred while executing the command: {cmd}")
            return None
        
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
    
def test_powershell():

    with open(resolve_path('custom_fields.json'), 'r') as file:
        data = json.load(file)

    ps = PowerShellLogging(data)
    
    # This will serve as both debugging purposes & just general information, nothing bad with information.
    print(f"""
          Powershell Logging
          -------------------------
          
          Manufacturer: {ps.manufacturer}
          """)
    
    print(ps.collect_hardware_data())
    print(ps.hardware)

if __name__ == "__main__":
    test_powershell()