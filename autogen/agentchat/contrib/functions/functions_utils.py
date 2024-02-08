import subprocess
import sys
import functools
import pkg_resources


def requires(*packages, **pip_packages):
    """
    Decorator that ensures the required packages are installed before executing the decorated function.

    Args:
        *packages: Variable length argument list of package names that should be installed.
        **pip_packages: Keyword arguments specifying package names and versions in the format `package_name=version`.

    Examples:
        @requires('numpy', 'pandas')
        def my_function():
            # Code that depends on numpy and pandas

        @requires(matplotlib='3.2.1', seaborn='0.11.1')
        def another_function():
            # Code that depends on matplotlib version 3.2.1 and seaborn version 0.11.1

        @requires('numpy', 'pandas', matplotlib='3.2.1', PIL='8.1.0')
        def yet_another_function():
            # Code that depends on numpy, pandas, matplotlib version 3.2.1, and PIL version 8.1.0
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            all_packages = {**{pkg: pkg for pkg in packages}, **pip_packages}
            for python_name, pip_name in all_packages.items():
                if "==" in pip_name:
                    name, version = pip_name.split("==")
                else:
                    name, version = pip_name, None
                try:
                    installed_package = pkg_resources.get_distribution(python_name)
                    if version is not None and installed_package.parsed_version != pkg_resources.parse_version(version):
                        raise ImportError
                except ImportError:
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
            return func(*args, **kwargs)

        return wrapper

    return decorator
