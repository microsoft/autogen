import pytest

def pytest_addoption(parser):
    parser.addoption(
        "--grpc", action="store_true", default=False, help="run grpc tests"
    )

def pytest_collection_modifyitems(config, items):
    grpc_option_passed = config.getoption("--grpc")
    skip_grpc = pytest.mark.skip(reason="Need --grpc option to run")
    skip_non_grpc = pytest.mark.skip(reason="Skipped since --grpc passed")

    for item in items:
        if "grpc" in item.keywords and not grpc_option_passed:
            item.add_marker(skip_grpc)
        elif "grpc" not in item.keywords and grpc_option_passed:
            item.add_marker(skip_non_grpc)
