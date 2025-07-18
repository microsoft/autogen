"""
Pytest configuration for workflow process tests.
"""
import pytest
import logging
import asyncio

# Configure logging for tests
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
