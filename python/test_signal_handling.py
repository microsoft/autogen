#!/usr/bin/env python3
"""
Test script for robust signal handling in container environments.

This script tests the new signal handling implementation for Azure Container Apps
and other container environments.
"""

import asyncio
import logging
import os
import signal
import sys
import time
from pathlib import Path

# Add the packages to the path for testing
sys.path.insert(0, str(Path(__file__).parent / "packages" / "autogen-ext" / "src"))

from autogen_ext.runtimes.grpc import GrpcWorkerAgentRuntimeHost


async def test_signal_handling():
    """Test the robust signal handling implementation."""
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("Starting signal handling test...")
    
    # Create a host instance
    host = GrpcWorkerAgentRuntimeHost(address="localhost:50051")
    
    try:
        # Start the host
        host.start()
        logger.info("Host started successfully")
        
        # Test the signal handling
        logger.info("Testing signal handling (will wait for 5 seconds, then send SIGTERM)")
        
        # Create a task to send a signal after 5 seconds
        async def send_signal_after_delay():
            await asyncio.sleep(5)
            logger.info("Sending SIGTERM signal...")
            os.kill(os.getpid(), signal.SIGTERM)
        
        # Start the signal sender task
        signal_task = asyncio.create_task(send_signal_after_delay())
        
        # Wait for signal (this should return after receiving SIGTERM)
        start_time = time.time()
        await host.stop_when_signal()
        end_time = time.time()
        
        logger.info(f"Signal handling completed in {end_time - start_time:.2f} seconds")
        
        # Cancel the signal task if it's still running
        if not signal_task.done():
            signal_task.cancel()
            
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        raise
    finally:
        # Ensure the host is stopped
        try:
            await host.stop()
            logger.info("Host stopped successfully")
        except Exception as e:
            logger.warning(f"Error stopping host: {e}")


async def test_container_detection():
    """Test container environment detection."""
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Import the detection functions
    from autogen_ext.runtimes.grpc._worker_runtime_host import is_running_in_container, is_pid_1

    logger.info("Testing container environment detection...")

    in_container = is_running_in_container()
    is_pid_1 = is_pid_1()
    
    logger.info(f"Running in container: {in_container}")
    logger.info(f"Running as PID 1: {is_pid_1}")
    logger.info(f"Current PID: {os.getpid()}")
    
    # Check environment variables
    container_vars = [
        "CONTAINER_APP_NAME",
        "CONTAINER",
        "DOCKER_CONTAINER",
    ]
    
    for var in container_vars:
        value = os.environ.get(var)
        if value:
            logger.info(f"Environment variable {var}: {value}")
    
    # Check for container files
    container_files = [
        "/.dockerenv",
        "/var/run/secrets/kubernetes.io",
    ]
    
    for file_path in container_files:
        if os.path.exists(file_path):
            logger.info(f"Container file found: {file_path}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "detect":
        asyncio.run(test_container_detection())
    else:
        asyncio.run(test_signal_handling())
