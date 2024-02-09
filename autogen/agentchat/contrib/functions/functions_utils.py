import os
import subprocess
import sys
import functools
import pkg_resources


def requires_python_packages(*packages, **pip_packages):
    """
    Decorator that ensures the required Python packages are installed before executing the decorated function.

    Args:
        *packages: Variable length argument list of Python package names that should be installed.
        **pip_packages: Keyword arguments specifying Python package names and versions in the format `package_name=version`.

    Examples:
        @requires_python_packages('numpy', 'pandas')
        def my_function():
            # Code that depends on numpy and pandas

        @requires_python_packages(matplotlib='3.2.1', seaborn='0.11.1')
        def another_function():
            # Code that depends on matplotlib version 3.2.1 and seaborn version 0.11.1

        @requires_python_packages('numpy', 'pandas', matplotlib='3.2.1', PIL='8.1.0')
        def yet_another_function():
            # Code that depends on numpy, pandas, matplotlib version 3.2.1, and PIL version 8.1.0
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            all_packages = {**{pkg: None for pkg in packages}, **pip_packages}
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
                    raise e
            return func(*args, **kwargs)

        return wrapper

    return decorator


def requires_secret(*env):
    """
    Decorator that ensures the required environment variables are set before executing the decorated function.

    Args:
        *env: Variable length argument list of environment variable names that should be set.

    Examples:
        @requires_secret('OPENAI_API_KEY')
        def my_function():
            # Code that depends on the OPENAI_API_KEY environment variable

        @requires_secret('AWS', 'AWS_ACCESS')
        def another_function():
            # Code that depends on the AWS and AWS_ACCESS environment variables
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for name in env:
                if name not in os.environ:
                    raise EnvironmentError(f"Environment variable {name} is not set")
            return func(*args, **kwargs)

        return wrapper

    return decorator
