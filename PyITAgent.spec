# -*- mode: python ; coding: utf-8 -*-

import os
from modulefinder import ModuleFinder

# Use the current directory
root_dir = os.getcwd()

finder = ModuleFinder()
for subdir, dirs, files in os.walk(root_dir):
    for file in files:
        if file.endswith('.py'):
            finder.run_script(os.path.join(subdir, file))

# Get the names of all the imported modules
imported_modules = list(finder.modules.keys())

# Optionally, filter out standard library and built-in modules
excluded_modules = ['__future__', '__main__', 'sys', 'os']

hidden_imports = [module for module in imported_modules if module not in excluded_modules]

# Print the list or write it to a file
print(hidden_imports)

def collect_subdirectories(base_path, target_folder):
    """Recursively collect all subdirectories and files from base_path."""
    data_files = []
    for root, dirs, files in os.walk(base_path):
        for file in files:
            file_path = os.path.join(root, file)
            # Create a relative path for files to preserve the directory structure
            relative_path = os.path.relpath(file_path, base_path)
            # Append the tuple (source, target) to the data_files list
            data_files.append((file_path, os.path.join(target_folder, os.path.dirname(relative_path))))
    return data_files

# Collect all subdirectories and files from 'models' directory
models_data = collect_subdirectories('models', 'models')

a = Analysis(
    ['main.py'],
    datas=[
        ('api/*', 'api'), 
        ('config/*', 'config'), 
        *models_data,  # Add the collected model data here
        ('runtime/*', 'runtime'), 
        ('utils/*', 'utils')
    ],
    pathex=[],
    binaries=[],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='PyITAgent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['app_icon.ico'],
)