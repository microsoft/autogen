# Test Environment for autogen.coding.kubernetes.PodCommandLineCodeExecutor

To test PodCommandLineCodeExecutor, the following environment is required.
- kubernetes cluster config file
- autogen package

## kubernetes cluster config file

kubernetes cluster config file, kubeconfig file's location should be set on environment variable `KUBECONFIG` or
It must be located in the .kube/config path of your home directory.

For Windows, `C:\Users\<<user>>\.kube\config`,
For Linux or MacOS, place the kubeconfig file in the `/home/<<user>>/.kube/config` directory.

## package install

Clone autogen github repository for package install and testing

Clone the repository with the command below.

before contribution
```sh
git clone -b k8s-code-executor https://github.com/questcollector/autogen.git
```

after contribution
```sh
git clone https://github.com/microsoft/autogen.git
```

install autogen with kubernetes >= 27.0.2

```sh
cd autogen
pip install .[kubernetes] -U
```

## test execution

Perform the test with the following command

```sh
pytest test/coding/test_kubernetes_commandline_code_executor.py
```
