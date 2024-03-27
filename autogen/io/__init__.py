from .base import InputStream, IOStream, OutputStream
from .console import IOConsole
from .websockets import IOWebsockets

# Set the default input/output stream to the console
IOStream._default_io_stream.set(IOConsole())

__all__ = ("IOConsole", "IOStream", "InputStream", "OutputStream", "IOWebsockets")
