with open("python/packages/autogen-ext/src/autogen_ext/memory/canvas/_text_canvas.py", "r") as f:
    content = f.read()

old_code = """        for hunk in patched_file:
            # Calculate the slice boundaries in the *current* working copy.
            start = hunk.source_start - 1 + line_offset
            end = start + hunk.source_length
            # Build the replacement block for this hunk.
            replacement: List[str] = []
            for line in hunk:
                if line.is_added or line.is_context:
                    replacement.append(line.value)
                # removed lines (line.is_removed) are *not* added.
            # Replace the slice with the hunk‑result.
            working_lines[start:end] = replacement
            line_offset += len(replacement) - (end - start)"""

new_code = """        for hunk in patched_file:
            # Calculate the slice boundaries in the *current* working copy.
            start = hunk.source_start - 1 + line_offset
            end = start + hunk.source_length
            
            # Build the expected source and replacement block for this hunk.
            expected_source: List[str] = []
            replacement: List[str] = []
            for line in hunk:
                if line.is_context or line.is_removed:
                    expected_source.append(line.value)
                if line.is_added or line.is_context:
                    replacement.append(line.value)
                    
            # Validate context lines
            if "".join(working_lines[start:end]) != "".join(expected_source):
                raise ValueError("Patch failed: context lines do not match the target file.")
                
            # Replace the slice with the hunk‑result.
            working_lines[start:end] = replacement
            line_offset += len(replacement) - (end - start)"""

content = content.replace(old_code, new_code)
with open("python/packages/autogen-ext/src/autogen_ext/memory/canvas/_text_canvas.py", "w") as f:
    f.write(content)
