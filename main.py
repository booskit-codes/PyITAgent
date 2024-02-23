# main.py

from runtime.client import PyITAgent
from utils.exception import ExceptionHandler
import config.constants as c

__author__ = c.AUTHOR
__version__ = c.VERSION

def main():
    try:
        pyitagent = PyITAgent()
        pyitagent.runtime()
    except Exception as e:
        handler = ExceptionHandler()  # Create an instance
        handler.raise_for_error(e)  # Call the instance method

if __name__ == "__main__":
    main()