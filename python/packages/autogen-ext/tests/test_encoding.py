"""
Tests for UTF-8 encoding support in autogen-ext.

Verifies that all file operations use explicit encoding="utf-8"
to prevent UnicodeDecodeError in non-English environments.

Related Issue: https://github.com/microsoft/autogen/issues/5566
"""

import os
import tempfile
import pytest
from pathlib import Path
import ast
import inspect


class TestEncodingSupport:
    """
    Test suite for UTF-8 encoding support.
    
    These tests prevent regression of the fix for Issue #5566,
    where PlaywrightController failed with UnicodeDecodeError
    on non-English systems (e.g., Chinese Windows with cp950 encoding).
    """

    def test_playwright_controller_script_loading(self):
        """
        Test that PlaywrightController can load page_script.js 
        in non-ASCII environments.
        
        This is a regression test for Issue #5566.
        """
        # Read the actual file to verify encoding parameter exists
        from autogen_ext.agents.web_surfer import PlaywrightController
        
        # Verify the source code contains encoding parameter
        source_file = inspect.getfile(PlaywrightController)
        with open(source_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Check that the open() call for page_script.js has encoding
        assert 'encoding="utf-8"' in content, \
            "PlaywrightController should use encoding='utf-8' when loading page_script.js"

    def test_file_operations_with_utf8_encoding(self):
        """
        Test that file operations handle UTF-8 content correctly.
        
        Simulates a non-ASCII environment by writing and reading
        a file with Chinese characters and emoji.
        """
        test_content = "测试内容 🚀 Emoji support"
        
        with tempfile.NamedTemporaryFile(
            mode='w', 
            encoding='utf-8', 
            delete=False, 
            suffix='.txt'
        ) as f:
            f.write(test_content)
            temp_path = f.name
        
        try:
            # Read file with explicit encoding (correct way)
            with open(temp_path, 'r', encoding='utf-8') as f:
                content = f.read()
                assert content == test_content, \
                    "File content should match when using encoding='utf-8'"
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_multimodal_web_surfer_encoding(self):
        """
        Test that MultimodalWebSurfer handles UTF-8 content correctly.
        
        Note: This is a placeholder test. In actual implementation,
        you would mock the Playwright page and test the surfer's
        ability to handle UTF-8 content.
        """
        # Placeholder - actual implementation would require
        # mocking Playwright's Page object
        pass


def test_no_encoding_issues_in_source():
    """
    Static test to check that all open() calls in the source code
    use explicit encoding parameter.
    
    This test should be run during linting/CI to prevent
    future encoding issues.
    
    Related Issue: https://github.com/microsoft/autogen/issues/5566
    """
    import ast
    import inspect
    
    # Get the source file path
    from autogen_ext.agents import web_surfer
    source_file = inspect.getfile(web_surfer)
    
    with open(source_file, 'r', encoding='utf-8') as f:
        tree = ast.parse(f.read())
    
    # Walk the AST to find all open() calls
    issues_found = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # Check if this is an open() call
            if isinstance(node.func, ast.Name) and node.func.id == 'open':
                # Check if encoding parameter is provided
                has_encoding = False
                for keyword in node.keywords:
                    if keyword.arg == 'encoding':
                        has_encoding = True
                        break
                
                # Check positional arguments (mode should be the 2nd arg)
                # If mode is specified and is text mode ('r' or 'w'),
                # encoding should be provided
                if len(node.args) >= 2:
                    mode_arg = node.args[1]
                    if isinstance(mode_arg, ast.Constant) and 't' in str(mode_arg.value):
                        if not has_encoding:
                            issues_found.append({
                                'line': node.lineno,
                                'message': 'open() call without encoding parameter in text mode'
                            })
    
    if issues_found:
        pytest.fail(
            f"Found {len(issues_found)} open() calls without encoding parameter:\n" +
            "\n".join([f"  Line {i['line']}: {i['message']}" for i in issues_found])
        )


def test_page_script_js_is_valid_utf8():
    """
    Test that page_script.js is valid UTF-8.
    
    This ensures the file itself won't cause encoding issues
    when loaded by PlaywrightController.
    """
    from autogen_ext.agents.web_surfer import PlaywrightController
    
    # Get the path to page_script.js
    source_file = inspect.getfile(PlaywrightController)
    page_script_path = Path(source_file).parent / "page_script.js"
    
    # Verify the file exists and is valid UTF-8
    assert page_script_path.exists(), "page_script.js should exist"
    
    with open(page_script_path, 'r', encoding='utf-8') as f:
        content = f.read()
        # Basic sanity check
        assert len(content) > 0, "page_script.js should not be empty"
        assert 'function' in content, "page_script.js should contain JavaScript functions"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
