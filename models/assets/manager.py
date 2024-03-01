# manager.py

from .manufacturer import Manufacturer
from .model import Model
from .hardware import Hardware

class AssetManager:
    def __init__(self):
        self.manufacturer = Manufacturer()
        self.model = Model()
        self.hardware = Hardware()

    # Additional asset management methods...