from setuptools import setup, find_packages

setup(
    name="aprofile",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "openai",
        "diskcache",
        "matplotlib",
        "networkx",
    ],
    package_data={
        "profiler": ["viz/*.html"],  # include all html files in the package
    },
    entry_points={
        "console_scripts": [
            "aprofile=profiler.cli:main",
        ],
    },
)
