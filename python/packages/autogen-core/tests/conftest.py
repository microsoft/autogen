import os

# Allow test utility namespaces so that component config tests can load
# components defined in the test suite itself.
os.environ.setdefault(
    "AUTOGEN_ALLOWED_PROVIDER_NAMESPACES",
    "test_component_config,autogen_test_utils",
)
