"""
Test for JupyterCodeExecutor temporary directory cleanup - Issue #7217
This test should be added to the existing test suite.
"""
import asyncio
import os
import tempfile
from pathlib import Path

import pytest
from autogen_core import CancellationToken
from autogen_core.code_executor import CodeBlock
from autogen_ext.code_executors.jupyter import JupyterCodeExecutor


@pytest.mark.asyncio
async def test_jupyter_executor_temp_directory_cleanup():
    """Test that JupyterCodeExecutor properly cleans up temporary directories when no output_dir is provided."""
    temp_dirs = []
    
    # Create multiple executors without providing output_dir
    for i in range(3):
        executor = JupyterCodeExecutor()
        
        # Store the output directory path for verification
        output_dir_path = str(executor.output_dir)
        temp_dirs.append(output_dir_path)
        
        # Verify the directory was created
        assert os.path.exists(output_dir_path), f"Output directory {output_dir_path} should exist"
        
        # Start and stop the executor
        await executor.start()
        await executor.stop()
    
    # Verify all temporary directories were cleaned up
    for temp_dir in temp_dirs:
        assert not os.path.exists(temp_dir), f"Temporary directory {temp_dir} should be cleaned up after stop()"


@pytest.mark.asyncio
async def test_jupyter_executor_preserves_user_provided_directory():
    """Test that JupyterCodeExecutor does NOT clean up user-provided output directories."""
    
    # Create a temporary directory that we control
    with tempfile.TemporaryDirectory() as user_temp_dir:
        user_output_dir = Path(user_temp_dir) / "user_provided_output"
        user_output_dir.mkdir()
        
        # Create executor with user-provided output_dir
        executor = JupyterCodeExecutor(output_dir=str(user_output_dir))
        
        # Start and stop the executor
        await executor.start()
        await executor.stop()
        
        # User-provided directory should still exist
        assert user_output_dir.exists(), "User-provided directory should not be cleaned up"


@pytest.mark.asyncio
async def test_jupyter_executor_cleanup_on_exception():
    """Test that temporary directories are cleaned up even if an exception occurs."""
    executor = JupyterCodeExecutor()
    output_dir_path = str(executor.output_dir)
    
    # Verify the directory exists
    assert os.path.exists(output_dir_path)
    
    # Manually call stop() (simulating cleanup after exception)
    await executor.stop()
    
    # Directory should be cleaned up
    assert not os.path.exists(output_dir_path)


@pytest.mark.asyncio 
async def test_jupyter_executor_multiple_stop_calls():
    """Test that calling stop() multiple times doesn't cause errors."""
    executor = JupyterCodeExecutor()
    output_dir_path = str(executor.output_dir)
    
    # Call stop multiple times
    await executor.stop()
    await executor.stop()  # Should not raise an error
    
    # Directory should be cleaned up
    assert not os.path.exists(output_dir_path)