# AAAI 2023 Lab Forum - LSHP2: Automated Machine Learning & Tuning with FLAML

## Session Information

**Date and Time**: February 8, 2023 at 2-6pm ET.

Location: Walter E. Washington Convention Center, Washington DC, USA

Duration: 4 hours (3.5 hours + 0.5 hour break)

For the most up-to-date information, see the [AAAI'23 Program Agenda](https://aaai.org/Conferences/AAAI-23/aaai23tutorials/)

## [Lab Forum Slides](https://1drv.ms/b/s!Ao3suATqM7n7iokCQbF7jUUYwOqGqQ?e=cMnilV)

## What Will You Learn?

- What FLAML is and how to use FLAML to
    - find accurate ML models with low computational resources for common ML tasks
    - tune hyperparameters generically
- How to leverage the flexible and rich customization choices
  - finish the last mile for deployment
  - create new applications
- Code examples, demos, use cases
- Research & development opportunities

## Session Agenda

### **Part 1. Overview of FLAML**

- Overview of AutoML and FLAML
- Basic usages of FLAML
    - Task-oriented AutoML
        - [Documentation](https://microsoft.github.io/FLAML/docs/Use-Cases/Task-Oriented-AutoML)
        - [Notebook: A classification task with AutoML](https://github.com/microsoft/FLAML/blob/tutorial-aaai23/notebook/automl_classification.ipynb); [Open In Colab](https://colab.research.google.com/github/microsoft/FLAML/blob/tutorial-aaai23/notebook/automl_classification.ipynb)
    - Tune User-Defined-functions with FLAML
        - [Documentation](https://microsoft.github.io/FLAML/docs/Use-Cases/Tune-User-Defined-Function)
        - [Notebook: Tune user-defined function](https://github.com/microsoft/FLAML/blob/tutorial-aaai23/notebook/tune_demo.ipynb); [Open In Colab](https://colab.research.google.com/github/microsoft/FLAML/blob/tutorial-aaai23/notebook/tune_demo.ipynb)
    - Zero-shot AutoML
        - [Documentation](https://microsoft.github.io/FLAML/docs/Use-Cases/Zero-Shot-AutoML)
        - [Notebook: Zeroshot AutoML](https://github.com/microsoft/FLAML/blob/tutorial-aaai23/notebook/zeroshot_lightgbm.ipynb); [Open In Colab](https://colab.research.google.com/github/microsoft/FLAML/blob/tutorial-aaai23/notebook/zeroshot_lightgbm.ipynb)
- [ML.NET demo](https://learn.microsoft.com/dotnet/machine-learning/tutorials/predict-prices-with-model-builder)

Break (15m)

### **Part 2. Deep Dive into FLAML**
- The Science Behind FLAML’s Success
    - [Economical hyperparameter optimization methods in FLAML](https://microsoft.github.io/FLAML/docs/Use-Cases/Tune-User-Defined-Function/#hyperparameter-optimization-algorithm)
    - [Other research in FLAML](https://microsoft.github.io/FLAML/docs/Research)

- Maximize the Power of FLAML through Customization and Advanced Functionalities
    - [Notebook: Customize your AutoML with FLAML](https://github.com/microsoft/FLAML/blob/tutorial-aaai23/notebook/customize_your_automl_with_flaml.ipynb); [Open In Colab](https://colab.research.google.com/github/microsoft/FLAML/blob/tutorial-aaai23/notebook/customize_your_automl_with_flaml.ipynb)
    - [Notebook: Further acceleration of AutoML with FLAML](https://github.com/microsoft/FLAML/blob/tutorial-aaai23/notebook/further_acceleration_of_automl_with_flaml.ipynb); [Open In Colab](https://colab.research.google.com/github/microsoft/FLAML/blob/tutorial-aaai23/notebook/further_acceleration_of_automl_with_flaml.ipynb)
    - [Notebook: Neural network model tuning with FLAML ](https://github.com/microsoft/FLAML/blob/tutorial-aaai23/notebook/tune_pytorch.ipynb); [Open In Colab](https://colab.research.google.com/github/microsoft/FLAML/blob/tutorial-aaai23/notebook/tune_pytorch.ipynb)


### **Part 3. New features in FLAML**
- Natural language processing
    - [Notebook: AutoML for NLP tasks](https://github.com/microsoft/FLAML/blob/tutorial-aaai23/notebook/automl_nlp.ipynb); [Open In Colab](https://colab.research.google.com/github/microsoft/FLAML/blob/tutorial-aaai23/notebook/automl_nlp.ipynb)
- Time Series Forecasting
    - [Notebook: AutoML for Time Series Forecast tasks](https://github.com/microsoft/FLAML/blob/tutorial-aaai23/notebook/automl_time_series_forecast.ipynb); [Open In Colab](https://colab.research.google.com/github/microsoft/FLAML/blob/tutorial-aaai23/notebook/automl_time_series_forecast.ipynb)
- Targeted Hyperparameter Optimization With Lexicographic Objectives
    - [Documentation](https://microsoft.github.io/FLAML/docs/Use-Cases/Tune-User-Defined-Function/#lexicographic-objectives)
    - [Notebook: Find accurate and fast neural networks with lexicographic objectives](https://github.com/microsoft/FLAML/blob/tutorial-aaai23/notebook/tune_lexicographic.ipynb); [Open In Colab](https://colab.research.google.com/github/microsoft/FLAML/blob/tutorial-aaai23/notebook/tune_lexicographic.ipynb)
- Online AutoML
    - [Notebook: Online AutoML with Vowpal Wabbit](https://github.com/microsoft/FLAML/blob/tutorial-aaai23/notebook/autovw.ipynb); [Open In Colab](https://colab.research.google.com/github/microsoft/FLAML/blob/tutorial-aaai23/notebook/autovw.ipynb)
- Fair AutoML
### Challenges and open problems
