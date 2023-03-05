# Installation

## Python

FLAML requires **Python version >= 3.7**. It can be installed from pip:

```bash
pip install flaml
```

or conda:
```
conda install flaml -c conda-forge
```

### Optional Dependencies

#### Notebook

To run the [notebook examples](https://github.com/microsoft/FLAML/tree/main/notebook),
install flaml with the [notebook] option:

```bash
pip install flaml[notebook]
```

#### Extra learners/models
* openai models
```bash
pip install flaml[openai]
```
* catboost
```bash
pip install flaml[catboost]
```
* vowpal wabbit
```bash
pip install flaml[vw]
```
* time series forecaster: prophet, statsmodels
```bash
pip install flaml[forecast]
```
* huggingface transformers
```bash
pip install flaml[hf]
```

#### Distributed tuning

* ray
```bash
pip install flaml[ray]
```
* spark
> *Spark support is added in v1.1.0*
```bash
pip install flaml[spark]>=1.1.0
```

For cloud platforms such as [Azure Synapse](https://azure.microsoft.com/en-us/products/synapse-analytics/), Spark clusters are provided.
But you may also need to install `Spark` manually when setting up your own environment.
For latest Ubuntu system, you can install Spark 3.3.0 standalone version with below script.
For more details of installing Spark, please refer to [Spark Doc](https://spark.apache.org/docs/latest/api/python/getting_started/install.html).
```bash
sudo apt-get update && sudo apt-get install -y --allow-downgrades --allow-change-held-packages --no-install-recommends \
    ca-certificates-java ca-certificates openjdk-17-jdk-headless \
    && sudo apt-get clean && sudo rm -rf /var/lib/apt/lists/*
wget --progress=dot:giga "https://www.apache.org/dyn/closer.lua/spark/spark-3.3.0/spark-3.3.0-bin-hadoop2.tgz?action=download" \
    -O - | tar -xzC /tmp; archive=$(basename "spark-3.3.0/spark-3.3.0-bin-hadoop2.tgz") \
    bash -c "sudo mv -v /tmp/\${archive/%.tgz/} /spark"
export SPARK_HOME=/spark
export PYTHONPATH=/spark/python/lib/py4j-0.10.9.5-src.zip:/spark/python
export PATH=$PATH:$SPARK_HOME/bin
```

* nni
```bash
pip install flaml[nni]
```
* blendsearch
```bash
pip install flaml[blendsearch]
```

* synapse
> *To install flaml in Azure Synapse and similar cloud platform*
```bash
pip install flaml[synapse]
```

#### Test and Benchmark

* test
```bash
pip install flaml[test]
```
* benchmark
```bash
pip install flaml[benchmark]
```

## .NET

FLAML has a .NET implementation in [ML.NET](http://dot.net/ml), an open-source, cross-platform machine learning framework for .NET.

You can use FLAML in .NET in the following ways:

**Low-code**

- [*Model Builder*](https://dotnet.microsoft.com/apps/machinelearning-ai/ml-dotnet/model-builder) - A Visual Studio extension for training ML models using FLAML. For more information on how to install the, see the [install Model Builder](https://docs.microsoft.com/dotnet/machine-learning/how-to-guides/install-model-builder?tabs=visual-studio-2022) guide.
- [*ML.NET CLI*](https://docs.microsoft.com/dotnet/machine-learning/automate-training-with-cli) - A dotnet CLI tool for training machine learning models using FLAML on Windows, MacOS, and Linux. For more information on how to install the ML.NET CLI, see the [install the ML.NET CLI](https://docs.microsoft.com/dotnet/machine-learning/how-to-guides/install-ml-net-cli?tabs=windows) guide.

**Code-first**

- [*Microsoft.ML.AutoML*](https://www.nuget.org/packages/Microsoft.ML.AutoML/0.20.0-preview.22313.1) - NuGet package that provides direct access to the FLAML AutoML APIs that power low-code solutions like Model Builder and the ML.NET CLI. For more information on installing NuGet packages, see the install and use a NuGet package in [Visual Studio](https://docs.microsoft.com/nuget/quickstart/install-and-use-a-package-in-visual-studio) or [dotnet CLI](https://docs.microsoft.com/nuget/quickstart/install-and-use-a-package-using-the-dotnet-cli) guides.

To get started with the ML.NET API and AutoML, see the [csharp-notebooks](https://github.com/dotnet/csharp-notebooks#machine-learning).
