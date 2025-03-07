# manager.py

from .manufacturer import Manufacturer
from .model import Model
from .hardware import Hardware
from .monitor import Monitor

class AssetManager:
    def __init__(self):
        self.manufacturer = Manufacturer()
        self.model = Model()
        self.hardware = Hardware()
        self.monitor = Monitor()

    # Additional asset management methods...