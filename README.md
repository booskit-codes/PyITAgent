# PyITAgent

![PyITAgent Logo](logo.png)

PyITAgent is a Python-based Windows executable designed to serve as an agent for your computer, allowing it to sync seamlessly with your Snipe-IT asset management system.

## Features

The program automatically collects and sends the following information from your computer to Snipe-IT:

- MAC Address (`_snipeit_mac_address_1`)
- Memory / RAM (`_snipeit_memory_ram_2`)
- Operating System (`_snipeit_operating_system_3`)
- OS Install Date (`_snipeit_os_install_date_4`)
- Total Storage (`_snipeit_total_storage_6`)
- Storage Information (`_snipeit_storage_information_7`)
- Processor / CPU (`_snipeit_processor_cpu_8`)
- IP Address (`_snipeit_ip_address_9`)

[Download the latest version here](https://github.com/booskit-codes/PyITAgent/releases/).

## Usage Instructions

For best results, integrate PyITAgent within an environment that utilizes Active Directory and Group Policy Management:

1. **Download and place the executable** in a network-accessible location.
2. **Configure the `config.ini` file** with your Snipe-IT URL and API key.
3. **Create a Group Policy Object (GPO)** in Active Directory to schedule the executable's run. Use an "on idle" trigger based on your timing preferences.
4. **In the task scheduler, set the action trigger** to point to the network location of the executable.
5. **Run the scheduled task as the SYSTEM user** for optimal execution.

## Developer Notes

To modify or extend PyITAgent, you can rebuild the executable using PyInstaller:

```
pyinstaller PyITAgent.spec
```

Feel free to tweak the source code to suit your needs or contribute enhancements.

## Credits

This project is inspired by and builds upon [https://github.com/aadrsh/snipe-it-python-agent](https://github.com/aadrsh/snipe-it-python-agent). Special thanks to the original contributors for their groundwork in Snipe-IT integration.