import importlib.metadata

try:
    __version__ = importlib.metadata.version("autogen_ext")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.6.1-dev"
