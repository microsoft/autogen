import subprocess
import sys
import functools
import pkg_resources


def requires(*packages):
    """
    Decorator that ensures the specified packages are installed before executing the decorated function.

    Args:
        *packages: Variable number of package names to be checked and installed if necessary.

    Returns:
        The decorated function.

    Raises:
        ImportError: If a required package is not found or has an incompatible version.

    For example,

    @requires("youtube_transcript_api==0.6.0")
    def get_youtube_transcript(youtube_link: str) -> str:
        from youtube_transcript_api import YouTubeTranscriptApi
        ...

    This will ensure that the "youtube_transcript_api" package is installed and has version 0.6.0 before executing the "get_youtube_transcript" function.

    @requires("youtube_transcript_api", "requests")
    def my_function():
        ...

    This will ensure that the "youtube_transcript_api" and "requests" packages are installed before executing the "my_function" function.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for package in packages:
                if "==" in package:
                    name, version = package.split("==")
                else:
                    name, version = package, None
                try:
                    installed_package = pkg_resources.get_distribution(name)
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
