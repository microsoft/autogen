#!/usr/bin/env python3
"""
Simple test script for Workbench tool name and description overrides.
This script tests the implementation without requiring full package installation.
"""

import sys
from pathlib import Path

# Add the package source to Python path
sys.path.insert(0, str(Path(__file__).parent / "python" / "packages" / "autogen-core" / "src"))

# Mock the version check
sys.modules['importlib.metadata'] = type(sys)('mock_metadata')
sys.modules['importlib.metadata'].version = lambda x: "0.6.1"

try:
    from autogen_core.tools._static_workbench import ToolOverride, StaticWorkbenchConfig
    from pydantic import BaseModel
    
    def test_tool_override_model():
        """Test ToolOverride model works correctly."""
        print("Testing ToolOverride model...")
        
        # Test with both name and description
        override1 = ToolOverride(name="new_name", description="new description")
        assert override1.name == "new_name"
        assert override1.description == "new description"
        
        # Test with just name
        override2 = ToolOverride(name="new_name")
        assert override2.name == "new_name"
        assert override2.description is None
        
        # Test with just description
        override3 = ToolOverride(description="new description")
        assert override3.name is None
        assert override3.description == "new description"
        
        # Test empty override
        override4 = ToolOverride()
        assert override4.name is None
        assert override4.description is None
        
        print("✓ ToolOverride model tests passed!")
        
    def test_static_workbench_config():
        """Test StaticWorkbenchConfig with tool_overrides."""
        print("Testing StaticWorkbenchConfig...")
        
        overrides = {
            "tool1": ToolOverride(name="new_tool1", description="New description for tool1"),
            "tool2": ToolOverride(description="New description for tool2")
        }
        
        config = StaticWorkbenchConfig(tools=[], tool_overrides=overrides)
        assert len(config.tool_overrides) == 2
        assert config.tool_overrides["tool1"].name == "new_tool1"  
        assert config.tool_overrides["tool1"].description == "New description for tool1"
        assert config.tool_overrides["tool2"].name is None
        assert config.tool_overrides["tool2"].description == "New description for tool2"
        
        # Test default empty overrides
        config_empty = StaticWorkbenchConfig(tools=[])
        assert len(config_empty.tool_overrides) == 0
        
        print("✓ StaticWorkbenchConfig tests passed!")
        
    def test_serialization():
        """Test that overrides can be serialized and deserialized."""
        print("Testing serialization...")
        
        overrides = {
            "tool1": ToolOverride(name="new_tool1", description="New description"),
        }
        
        config = StaticWorkbenchConfig(tools=[], tool_overrides=overrides)
        
        # Serialize to dict
        config_dict = config.model_dump()
        print(f"Serialized config: {config_dict}")
        
        # Deserialize from dict
        config_restored = StaticWorkbenchConfig.model_validate(config_dict)
        assert len(config_restored.tool_overrides) == 1
        assert config_restored.tool_overrides["tool1"].name == "new_tool1"
        assert config_restored.tool_overrides["tool1"].description == "New description"
        
        print("✓ Serialization tests passed!")
        
    # Run tests
    test_tool_override_model()
    test_static_workbench_config()
    test_serialization()
    
    print("\n🎉 All basic tests passed!")
    
except Exception as e:
    print(f"❌ Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)