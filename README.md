# PyITAgent

![PyITAgent Logo](logo.png)

PyITAgent is a Python-based Windows executable designed to serve as an agent for your computer, allowing it to sync seamlessly with your Snipe-IT asset management system.

## Features

The program automatically collects hardware data, computer information and user data before sending it to your Snipe-IT instance.

By **default**, the program collects and syncs the following information, this can be modified, more information below under "Advanced Usage - Custom Fields":

- MAC Address (`_snipeit_mac_address_1`)
- Memory / RAM (`_snipeit_memory_ram_2`)
- Operating System (`_snipeit_operating_system_3`)
- OS Install Date (`_snipeit_os_install_date_4`)
- Total Storage (`_snipeit_total_storage_6`)
- Storage Information (`_snipeit_storage_information_7`)
- Processor / CPU (`_snipeit_processor_cpu_8`)
- IP Address (`_snipeit_ip_address_9`)
- BIOS Release Date (`_snipeit_bios_release_date_10`)
- Windows Username (`_snipeit_windows_username_11`)
- RAM Usage (`_snipeit_ram_used_12`)
- Disk Space Used (`_snipeit_disk_space_used_13`)

[Download the latest version here](https://github.com/booskit-codes/PyITAgent/releases/).

## Usage Instructions

For best results, integrate PyITAgent within an environment that utilizes Active Directory and Group Policy Management:

1. **Download and place the executable** in a network-accessible location.
2. **Configure the `config.ini` file** with your Snipe-IT URL and API key.
3. **Create a Group Policy Object (GPO)** in Active Directory to schedule the executable's run. Use an "on idle" trigger based on your timing preferences.
4. **In the task scheduler, set the action trigger** to point to the network location of the executable.
5. **Run the scheduled task as the SYSTEM user** for optimal execution.

## Advanced Usage - Custom Fields

For those that wish to add, modify or edit their custom fields, you can do so in the `custom_fields.json` file.

Fields categorized under **enabled_static_fields** cannot be modified, but can be freely disabled or enabled.

For example, if you wish to disable the collection of your MAC Address or change the db field, you can do so by modifying the JSON file like so:

```json
"mac_address": {
    "enabled": false,
    "field_name": "_snipeit_mac_address_3"
},
```

All other custom fields can be modified under the **custom_fields** section and you can freely add more fields as well. It uses powershell commands to collect information from your computer.

For example, if you wish to determine your current CPU usage, create a new text field on your Snipe-IT instance, copy the DB field and modify the JSON by adding the following:

```json
"_snipeit_cpu_usage_13": {
    "name": "CPU Usage",
    "enabled": true,
    "ps_command": "(Get-Counter -Counter '\\Processor(_Total)\\% Processor Time').CounterSamples[0].CookedValue"
}
```

## Developer Notes

In order for the program to work, you're required to make a copy of `config-example.ini` and rename it to `config.ini`.

You are required to do the same for `custom_fields-example.json`, rename it to `custom_fields.json`

When modifying the program, you can rebuild the executable using PyInstaller:

```
pyinstaller PyITAgent.spec
```

Feel free to tweak the source code to suit your needs or contribute enhancements.

Testing or debugging custom fields / modifications to `custom_fields.json` can be done using `ps.py` without sending any sort of information to your Snipe-IT instance.

If you have a python windows enviroment, you can do so via the following command:

```
py ps.py
```

## Credits

This project is inspired by and builds upon [https://github.com/aadrsh/snipe-it-python-agent](https://github.com/aadrsh/snipe-it-python-agent). Special thanks to the original contributors for their groundwork in Snipe-IT integration.