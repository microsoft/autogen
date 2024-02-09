import os
import subprocess
import sys
import functools
import pkg_resources
from typing import List, Optional, Tuple


class FunctionWithRequirements:
    """Decorator class that adds requirements and setup functionality to a function."""

    def __init__(self, python_packages: Optional[List[str]] = None, secrets: Optional[List[str]] = None):
        self.python_packages = python_packages or []
        self.secrets = secrets or []

    def __call__(self, func: callable) -> callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            self.setup()
            return func(*args, **kwargs)

        wrapper.setup = self.setup
        wrapper.get_requirements = self.get_requirements
        return wrapper

    def get_requirements(self) -> Tuple[List[str], List[str]]:
        """Returns the Python packages and secrets required by the function."""
        return self.python_packages, self.secrets

    def setup(self) -> None:
        """Installs the required Python packages and checks the required secrets."""
        # Install Python packages
        all_packages = {pkg: None if "==" not in pkg else pkg.split("==")[1] for pkg in self.python_packages}
        for name, version in all_packages.items():
            if "==" in name:
                name, version = name.split("==")
            print("requested package:", name, version)
            try:
                try:
                    installed_package = pkg_resources.get_distribution(name)
                except pkg_resources.DistributionNotFound:
                    print(f"Package {name} not found")
                    installed_package = None
                    raise ImportError

                print("found package", installed_package)
                if version is not None and installed_package.parsed_version != pkg_resources.parse_version(version):
                    print("Package mismatch detected")
                    raise ImportError
            except ImportError or pkg_resources.DistributionNotFound:
                print(f"Installing {name}{'==' + version if version else ''}...")
                subprocess.check_call(
                    [
                        sys.executable,
                        "-m",
                        "pip",
                        "install",
                        name + "==" + version if version else name,
                        "--upgrade",
                        "--quiet",
                    ]
                )
            except Exception as e:
                print(f"Error: {e}")

        # Check secrets
        for name in self.secrets:
            if name not in os.environ:
                raise EnvironmentError(f"Environment variable {name} is not set")
            else:
                print(f"Environment variable {name} is set")
