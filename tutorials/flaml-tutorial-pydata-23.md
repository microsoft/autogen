# PyData Seattle 2023 - Automated Machine Learning & Tuning with FLAML

## Session Information

**Date and Time**: 04-26, 09:00–10:30 PT.

Location:  Microsoft Conference Center, Seattle, WA.

Duration: 1.5 hours

For the most up-to-date information, see the [PyData Seattle 2023 Agenda](https://seattle2023.pydata.org/cfp/talk/BYRA8H/)

## [Lab Forum Slides](https://drive.google.com/file/d/14uG0N7jnf18-wizeWWfmXcBUARTQn61w/view?usp=share_link)

## What Will You Learn?

In this session, we will provide an in-depth and hands-on tutorial on Automated Machine Learning & Tuning with a fast python library named FLAML. We will start with an overview of the AutoML problem and the FLAML library. We will then introduce the hyperparameter optimization methods empowering the strong performance of FLAML. We will also demonstrate how to make the best use of FLAML to perform automated machine learning and hyperparameter tuning in various applications with the help of rich customization choices and advanced functionalities provided by FLAML. At last, we will share several new features of the library based on our latest research and development work around FLAML and close the tutorial with open problems and challenges learned from AutoML practice.

## Tutorial Outline

### **Part 1. Overview**
- Overview of AutoML & Hyperparameter Tuning

### **Part 2. Introduction to FLAML**
- Introduction to FLAML
- AutoML and Hyperparameter Tuning with FLAML
    - [Notebook: AutoML with FLAML Library](https://github.com/microsoft/FLAML/blob/d047c79352a2b5d32b72f4323dadfa2be0db8a45/notebook/automl_flight_delays.ipynb)
    - [Notebook: Hyperparameter Tuning with FLAML](https://github.com/microsoft/FLAML/blob/d047c79352a2b5d32b72f4323dadfa2be0db8a45/notebook/tune_synapseml.ipynb)

### **Part 3. Deep Dive into FLAML**
- Advanced Functionalities
- Parallelization with Apache Spark
    - [Notebook: FLAML AutoML on Apache Spark](https://github.com/microsoft/FLAML/blob/d047c79352a2b5d32b72f4323dadfa2be0db8a45/notebook/automl_bankrupt_synapseml.ipynb)

### **Part 4. New features in FLAML**
- Targeted Hyperparameter Optimization With Lexicographic Objectives
    - [Notebook: Tune models with lexicographic preference across objectives](https://github.com/microsoft/FLAML/blob/7ae410c8eb967e2084b2e7dbe7d5fa2145a44b79/notebook/tune_lexicographic.ipynb)
- OpenAI GPT-3, GPT-4 and ChatGPT tuning
    - [Notebook: Use FLAML to Tune OpenAI Models](https://github.com/microsoft/FLAML/blob/a0b318b12ee8288db54b674904655307f9e201c2/notebook/autogen_openai_completion.ipynb)
    - [Notebook: Use FLAML to Tune ChatGPT](https://github.com/microsoft/FLAML/blob/a0b318b12ee8288db54b674904655307f9e201c2/notebook/autogen_chatgpt_gpt4.ipynb)
