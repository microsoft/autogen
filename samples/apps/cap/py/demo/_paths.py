# Add autogencap to system path in case autogencap is not pip installed
# Since this library has not been published to PyPi, it is not easy to install using pip
import sys
import os

absparent = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(absparent)
