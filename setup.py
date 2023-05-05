import setuptools
import os

here = os.path.abspath(os.path.dirname(__file__))

with open("README.md", "r", encoding="UTF-8") as fh:
    long_description = fh.read()


# Get the code version
version = {}
with open(os.path.join(here, "flaml/version.py")) as fp:
    exec(fp.read(), version)
__version__ = version["__version__"]

install_requires = [
    "NumPy>=1.17.0rc1",
    "lightgbm>=2.3.1",
    "xgboost>=0.90",
    "scipy>=1.4.1",
    "pandas>=1.1.4",
    "scikit-learn>=0.24",
]


setuptools.setup(
    name="FLAML",
    version=__version__,
    author="Microsoft Corporation",
    author_email="hpo@microsoft.com",
    description="A fast library for automated machine learning and tuning",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/microsoft/FLAML",
    packages=setuptools.find_packages(include=["flaml*"]),
    package_data={
        "flaml.default": ["*/*.json"],
    },
    include_package_data=True,
    install_requires=install_requires,
    extras_require={
        "notebook": [
            "jupyter",
            "matplotlib",
            "openml==0.10.2",
        ],
        "spark": [
            "pyspark>=3.2.0",
            "joblibspark>=0.5.0",
        ],
        "test": [
            "thop",
            "pytest>=6.1.1",
            "coverage>=5.3",
            "pre-commit",
            "torch",
            "torchvision",
            "catboost>=0.26,<1.2",
            "rgf-python",
            "optuna==2.8.0",
            "openml==0.10.2",
            "statsmodels>=0.12.2",
            "psutil==5.8.0",
            "dataclasses",
            "transformers[torch]==4.26",
            "datasets",
            "nltk",
            "rouge_score",
            "hcrystalball==0.1.10",
            "seqeval",
            "pytorch-forecasting>=0.9.0,<=0.10.1",
            "mlflow",
            "pyspark>=3.2.0",
            "joblibspark>=0.5.0",
            "nbconvert",
            "nbformat",
            "ipykernel",
            "pytorch-lightning<1.9.1",  # test_forecast_panel
            "requests<2.29.0",  # https://github.com/docker/docker-py/issues/3113
        ],
        "catboost": ["catboost>=0.26"],
        "blendsearch": ["optuna==2.8.0"],
        "ray": [
            "ray[tune]~=1.13",
        ],
        "azureml": [
            "azureml-mlflow",
        ],
        "nni": [
            "nni",
        ],
        "vw": [
            "vowpalwabbit>=8.10.0, <9.0.0",
        ],
        "hf": [
            "transformers[torch]==4.26",
            "datasets",
            "nltk",
            "rouge_score",
            "seqeval",
        ],
        "nlp": [  # for backward compatibility; hf is the new option name
            "transformers[torch]==4.26",
            "datasets",
            "nltk",
            "rouge_score",
            "seqeval",
        ],
        "ts_forecast": [
            "holidays<0.14",  # to prevent installation error for prophet
            "prophet>=1.0.1",
            "statsmodels>=0.12.2",
            "hcrystalball==0.1.10",
        ],
        "forecast": [
            "holidays<0.14",  # to prevent installation error for prophet
            "prophet>=1.0.1",
            "statsmodels>=0.12.2",
            "hcrystalball==0.1.10",
            "pytorch-forecasting>=0.9.0",
        ],
        "benchmark": ["catboost>=0.26", "psutil==5.8.0", "xgboost==1.3.3"],
        "openai": ["openai==0.27.4", "diskcache"],
        "autogen": ["openai==0.27.4", "diskcache", "docker"],
        "synapse": ["joblibspark>=0.5.0", "optuna==2.8.0", "pyspark>=3.2.0"],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
)
