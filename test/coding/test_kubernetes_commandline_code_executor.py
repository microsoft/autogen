import importlib
import os
import sys
from pathlib import Path

import pytest

from autogen.code_utils import TIMEOUT_MSG
from autogen.coding.base import CodeBlock, CodeExecutor

try:
    from autogen.coding.kubernetes import PodCommandLineCodeExecutor

    client = importlib.import_module("kubernetes.client")
    config = importlib.import_module("kubernetes.config")

    kubeconfig = Path(".kube/config")
    if os.environ.get("KUBECONFIG", None):
        kubeconfig = Path(os.environ["KUBECONFIG"])
    elif sys.platform == "win32":
        kubeconfig = os.environ["userprofile"] / kubeconfig
    else:
        kubeconfig = os.environ["HOME"] / kubeconfig

    if kubeconfig.is_file():
        config.load_config(config_file=str(kubeconfig))
        api_client = client.CoreV1Api()
        api_client.list_namespace()
        skip_kubernetes_tests = False
    else:
        skip_kubernetes_tests = True

    pod_spec = client.V1Pod(
        metadata=client.V1ObjectMeta(
            name="abcd", namespace="default", annotations={"sidecar.istio.io/inject": "false"}
        ),
        spec=client.V1PodSpec(
            restart_policy="Never",
            containers=[
                client.V1Container(
                    args=["-c", "while true;do sleep 5; done"],
                    command=["/bin/sh"],
                    name="abcd",
                    image="python:3.11-slim",
                    env=[
                        client.V1EnvVar(name="TEST", value="TEST"),
                        client.V1EnvVar(
                            name="POD_NAME",
                            value_from=client.V1EnvVarSource(
                                field_ref=client.V1ObjectFieldSelector(field_path="metadata.name")
                            ),
                        ),
                    ],
                )
            ],
        ),
    )
except Exception:
    skip_kubernetes_tests = True


@pytest.mark.skipif(skip_kubernetes_tests, reason="kubernetes not accessible")
def test_create_default_pod_executor():
    with PodCommandLineCodeExecutor(namespace="default", kube_config_file=str(kubeconfig)) as executor:
        assert executor.timeout == 60
        assert executor.work_dir == Path("/workspace")
        assert executor._container_name == "autogen-code-exec"
        assert executor._pod.metadata.name.startswith("autogen-code-exec-")
        _test_execute_code(executor)


@pytest.mark.skipif(skip_kubernetes_tests, reason="kubernetes not accessible")
def test_create_node_pod_executor():
    with PodCommandLineCodeExecutor(
        image="node:22-alpine",
        namespace="default",
        work_dir="./app",
        timeout=30,
        kube_config_file=str(kubeconfig),
        execution_policies={"javascript": True},
    ) as executor:
        assert executor.timeout == 30
        assert executor.work_dir == Path("./app")
        assert executor._container_name == "autogen-code-exec"
        assert executor._pod.metadata.name.startswith("autogen-code-exec-")
        assert executor.execution_policies["javascript"]

        # Test single code block.
        code_blocks = [CodeBlock(code="console.log('hello world!')", language="javascript")]
        code_result = executor.execute_code_blocks(code_blocks)
        assert code_result.exit_code == 0 and "hello world!" in code_result.output and code_result.code_file is not None

        # Test multiple code blocks.
        code_blocks = [
            CodeBlock(code="console.log('hello world!')", language="javascript"),
            CodeBlock(code="let a = 100 + 100; console.log(a)", language="javascript"),
        ]
        code_result = executor.execute_code_blocks(code_blocks)
        assert (
            code_result.exit_code == 0
            and "hello world!" in code_result.output
            and "200" in code_result.output
            and code_result.code_file is not None
        )

        # Test running code.
        file_lines = ["console.log('hello world!')", "let a = 100 + 100", "console.log(a)"]
        code_blocks = [CodeBlock(code="\n".join(file_lines), language="javascript")]
        code_result = executor.execute_code_blocks(code_blocks)
        assert (
            code_result.exit_code == 0
            and "hello world!" in code_result.output
            and "200" in code_result.output
            and code_result.code_file is not None
        )


@pytest.mark.skipif(skip_kubernetes_tests, reason="kubernetes not accessible")
def test_create_pod_spec_pod_executor():
    with PodCommandLineCodeExecutor(
        pod_spec=pod_spec, container_name="abcd", kube_config_file=str(kubeconfig)
    ) as executor:
        assert executor.timeout == 60
        assert executor._container_name == "abcd"
        assert executor._pod.metadata.name == pod_spec.metadata.name
        assert executor._pod.metadata.namespace == pod_spec.metadata.namespace
        _test_execute_code(executor)

        # Test bash script.
        if sys.platform not in ["win32"]:
            code_blocks = [CodeBlock(code="echo $TEST $POD_NAME", language="bash")]
            code_result = executor.execute_code_blocks(code_blocks)
            assert (
                code_result.exit_code == 0 and "TEST abcd" in code_result.output and code_result.code_file is not None
            )


@pytest.mark.skipif(skip_kubernetes_tests, reason="kubernetes not accessible")
def test_pod_executor_timeout():
    with PodCommandLineCodeExecutor(namespace="default", timeout=5, kube_config_file=str(kubeconfig)) as executor:
        assert executor.timeout == 5
        assert executor.work_dir == Path("/workspace")
        assert executor._container_name == "autogen-code-exec"
        assert executor._pod.metadata.name.startswith("autogen-code-exec-")
        # Test running code.
        file_lines = ["import time", "time.sleep(10)", "a = 100 + 100", "print(a)"]
        code_blocks = [CodeBlock(code="\n".join(file_lines), language="python")]
        code_result = executor.execute_code_blocks(code_blocks)
        assert code_result.exit_code == 124 and TIMEOUT_MSG in code_result.output and code_result.code_file is not None


def _test_execute_code(executor: CodeExecutor) -> None:
    # Test single code block.
    code_blocks = [CodeBlock(code="import sys; print('hello world!')", language="python")]
    code_result = executor.execute_code_blocks(code_blocks)
    assert code_result.exit_code == 0 and "hello world!" in code_result.output and code_result.code_file is not None

    # Test multiple code blocks.
    code_blocks = [
        CodeBlock(code="import sys; print('hello world!')", language="python"),
        CodeBlock(code="a = 100 + 100; print(a)", language="python"),
    ]
    code_result = executor.execute_code_blocks(code_blocks)
    assert (
        code_result.exit_code == 0
        and "hello world!" in code_result.output
        and "200" in code_result.output
        and code_result.code_file is not None
    )

    # Test bash script.
    if sys.platform not in ["win32"]:
        code_blocks = [CodeBlock(code="echo 'hello world!'", language="bash")]
        code_result = executor.execute_code_blocks(code_blocks)
        assert code_result.exit_code == 0 and "hello world!" in code_result.output and code_result.code_file is not None

    # Test running code.
    file_lines = ["import sys", "print('hello world!')", "a = 100 + 100", "print(a)"]
    code_blocks = [CodeBlock(code="\n".join(file_lines), language="python")]
    code_result = executor.execute_code_blocks(code_blocks)
    assert (
        code_result.exit_code == 0
        and "hello world!" in code_result.output
        and "200" in code_result.output
        and code_result.code_file is not None
    )

    # Test running code has filename.
    file_lines = ["# filename: test.py", "import sys", "print('hello world!')", "a = 100 + 100", "print(a)"]
    code_blocks = [CodeBlock(code="\n".join(file_lines), language="python")]
    code_result = executor.execute_code_blocks(code_blocks)
    print(code_result.code_file)
    assert (
        code_result.exit_code == 0
        and "hello world!" in code_result.output
        and "200" in code_result.output
        and code_result.code_file.find("test.py") > 0
    )

    # Test error code.
    code_blocks = [CodeBlock(code="print(sys.platform)", language="python")]
    code_result = executor.execute_code_blocks(code_blocks)
    assert code_result.exit_code == 1 and "Traceback" in code_result.output and code_result.code_file is not None
