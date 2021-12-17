# Installation

FLAML requires **Python version >= 3.6**. It can be installed from pip:

```bash
pip install flaml
```

or conda:
```
conda install flaml -c conda-forge
```

FLAML has a .NET implementation as well from [ML.NET Model Builder](https://dotnet.microsoft.com/apps/machinelearning-ai/ml-dotnet/model-builder) in [Visual Studio](https://visualstudio.microsoft.com/) 2022.

## Optional Dependencies

### Notebook
To run the [notebook examples](https://github.com/microsoft/FLAML/tree/main/notebook),
install flaml with the [notebook] option:

```bash
pip install flaml[notebook]
```

### Extra learners
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

### Distributed tuning
* ray
```bash
pip install flaml[ray]
```
* nni
```bash
pip install flaml[nni]
```
* blendsearch
```bash
pip install flaml[blendsearch]
```

### Test and Benchmark
* test
```bash
pip install flaml[test]
```
* benchmark
```bash
pip install flaml[benchmark]
```

