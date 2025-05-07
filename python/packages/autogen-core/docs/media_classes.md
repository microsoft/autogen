## Media Class Hierarchy in AutoGen Core

This document describes the Media class hierarchy in AutoGen Core, which provides a unified approach to handling different types of media content that can be sent to language models.

### Overview

The `Media` class serves as a base class for all media types, providing common functionality and a consistent interface. Currently, it has two concrete implementations:
- `Image`: For handling image content
- `File`: For handling file attachments of any type

This design makes the system more elegant, maintainable, and extensible, allowing for:
- Easy addition of new media types
- Consistent API across all media types
- Simplified type validation in messages

### Media Base Class

The `Media` base class defines the common interface and functionality for all media types:

```python
from autogen_core import Media

# The Media class provides common methods that all media types implement:
# - to_base64(): Convert to base64 string
# - to_data_uri(): Convert to data URI
# - to_openai_format(): Format for OpenAI API
# - from_base64(), from_file(), from_data_uri(): Factory methods
```

### Image Class

The `Image` class represents image content:

```python
from autogen_core import Image
from PIL import Image as PILImage
from pathlib import Path

# Create an Image from a file
image = Image.from_file(Path("image.png"))

# Create from a PIL Image
pil_img = PILImage.new("RGB", (100, 100), color="red")
image = Image.from_pil(pil_img)

# Create from base64 string
image = Image.from_base64("base64_encoded_string")

# Convert to OpenAI format for API calls
openai_format = image.to_openai_format()
# Result: {"type": "image_url", "image_url": {"url": "data:image/png;base64,...", "detail": "auto"}}
```

### File Class

The `File` class represents file attachments of any type:

```python
from autogen_core import File
from pathlib import Path

# Create a File from a file path
file_obj = File.from_file(Path("document.pdf"))

# Create from bytes with filename and optional MIME type
file_obj = File.from_bytes(b"file content", "document.txt", "text/plain")

# Create from base64 string
file_obj = File.from_base64("base64_encoded_string", "document.txt")

# Convert to OpenAI format for API calls
openai_format = file_obj.to_openai_format()
# Result: {"type": "file", "file": {"filename": "document.txt", "file_data": "data:text/plain;base64,..."}}
```

### Using Media in Messages

The `UserMessage` class can now accept any `Media` subclass in its content:

```python
from autogen_core import Image, File, Media
from autogen_core.models import UserMessage
from pathlib import Path

# Create media objects
image = Image.from_file(Path("image.png"))
file_obj = File.from_file(Path("document.pdf"))

# Use in a message with multiple media types
message = UserMessage(
    content=["Here's the information:", image, file_obj],
    source="user"
)

# The Media class hierarchy makes it easy to validate and process media content
assert isinstance(message.content[1], Media)  # True for any media type
assert isinstance(message.content[1], Image)  # True for the image
assert isinstance(message.content[2], File)   # True for the file
```

### Extending with New Media Types

To add new media types, create a new class that extends `Media`:

```python
from autogen_core import Media
import base64
from typing import Dict, Any

class Audio(Media):
    media_type = "audio"
    
    def __init__(self, audio_data: bytes, format: str = "mp3"):
        self.audio_data = audio_data
        self.format = format
    
    def to_base64(self) -> str:
        return base64.b64encode(self.audio_data).decode("utf-8")
        
    def to_data_uri(self) -> str:
        return f"data:audio/{self.format};base64,{self.to_base64()}"
        
    def to_openai_format(self) -> Dict[str, Any]:
        return {
            "type": "audio",
            "audio": {
                "url": self.to_data_uri()
            }
        }
    
    # Implement factory methods (from_file, from_base64, etc.)
```

The `Media` base class automatically registers subclasses, making them compatible with the validation system.

### Benefits

This hierarchical approach provides several benefits:

1. **Consistency**: All media types share a common interface and behavior
2. **Extensibility**: New media types can be added by extending the `Media` base class
3. **Type Safety**: The `UserMessage` class can properly validate any media type
4. **API Compatibility**: All media types can be formatted for different APIs consistently
5. **Simplified Code**: Model transformers can handle any media type without special-casing each one

The Media class hierarchy is designed to grow with AutoGen's needs, providing a foundation for supporting rich, multimodal interactions with language models.
