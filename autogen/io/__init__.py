from .base import InputStream, IOStream, OutputStream
from .console import IOConsole
from .websockets import IOWebsockets

# Set the default input/output stream to the console
IOStream.set_global_default(IOConsole())
IOStream.set_default(IOConsole())

__all__ = ("IOConsole", "IOStream", "InputStream", "OutputStream", "IOWebsockets")
