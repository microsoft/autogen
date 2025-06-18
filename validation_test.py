#!/usr/bin/env python3
"""
Quick validation test that the implementation works as expected.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

# Test the ToolOverride models can be imported and used
try:
    sys.path.insert(0, str(Path(__file__).parent / "python" / "packages" / "autogen-core" / "src" / "autogen_core" / "tools"))
    
    # Import models directly to test basic functionality
    from _static_workbench import ToolOverride as StaticToolOverride, StaticWorkbenchConfig
    
    print("Testing StaticWorkbench ToolOverride...")
    
    # Test ToolOverride model
    override = StaticToolOverride(name="new_name", description="new_desc")
    assert override.name == "new_name"
    assert override.description == "new_desc"
    
    # Test config with overrides
    overrides_dict = {
        "tool1": StaticToolOverride(name="renamed_tool1", description="New description"),
        "tool2": StaticToolOverride(description="Only description override")
    }
    
    config = StaticWorkbenchConfig(tools=[], tool_overrides=overrides_dict)
    assert len(config.tool_overrides) == 2
    assert config.tool_overrides["tool1"].name == "renamed_tool1"
    assert config.tool_overrides["tool2"].name is None
    assert config.tool_overrides["tool2"].description == "Only description override"
    
    # Test serialization
    config_dict = config.model_dump()
    restored_config = StaticWorkbenchConfig.model_validate(config_dict)
    assert len(restored_config.tool_overrides) == 2
    
    print("✓ StaticWorkbench ToolOverride tests passed!")
    
except ImportError as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"Test failed: {e}")
    import traceback
    traceback.print_exc()

# Test MCP ToolOverride
try:
    sys.path.insert(0, str(Path(__file__).parent / "python" / "packages" / "autogen-ext" / "src" / "autogen_ext" / "tools" / "mcp"))
    
    from _workbench import ToolOverride as McpToolOverride, McpWorkbenchConfig
    
    print("\nTesting McpWorkbench ToolOverride...")
    
    # Test ToolOverride model
    override = McpToolOverride(name="new_name", description="new_desc")
    assert override.name == "new_name"
    assert override.description == "new_desc"
    
    # Test config with overrides
    overrides_dict = {
        "fetch": McpToolOverride(name="web_fetch", description="Enhanced fetching"),
        "search": McpToolOverride(description="Only description override")
    }
    
    # Mock server params since we can't import the full structure
    mock_params = MagicMock()
    mock_params.command = "echo"
    
    config = McpWorkbenchConfig(server_params=mock_params, tool_overrides=overrides_dict)
    assert len(config.tool_overrides) == 2
    assert config.tool_overrides["fetch"].name == "web_fetch"
    assert config.tool_overrides["search"].name is None
    assert config.tool_overrides["search"].description == "Only description override"
    
    print("✓ McpWorkbench ToolOverride tests passed!")
    
except ImportError as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"Test failed: {e}")
    import traceback
    traceback.print_exc()

print("\n🎉 Basic validation tests completed!")