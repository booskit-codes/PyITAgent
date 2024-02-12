import logging
import subprocess

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class PowerShellLogging:
    def __init__(self):
        self.manufacturer = self.run_command("(gwmi win32_computersystem).manufacturer")

    def run_command(self, cmd):
        try:
            completed = subprocess.run(["powershell.exe", "-Command", cmd], capture_output=True, text=True)
            
            # Check if the command was executed successfully
            if completed.returncode == 0:
                logging.info(f"Command executed successfully: {cmd}")
                return completed.stdout.strip()
            else:
                # Log an error if the command failed
                logging.error(f"Command failed with return code {completed.returncode}: {cmd}")
                logging.error(f"Error output: {completed.stderr.strip()}")
                return None
        except Exception as e:
            # Log any exceptions that occur during execution
            logging.exception(f"An exception occurred while executing the command: {cmd}")
            return None
    
def test_powershell():

    ps = PowerShellLogging()
    
    # This will serve as both debugging purposes & just general information, nothing bad with information.
    print(f"""
          Powershell Logging
          -------------------------
          
          Manufacturer: {ps.manufacturer}
          """)

if __name__ == "__main__":
    test_powershell()