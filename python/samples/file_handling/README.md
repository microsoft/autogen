# AutoGen File Handling Example

This example demonstrates how to use AutoGen to process file content. It utilizes AutoGen's `MultiModalMessage` and `File` classes, enabling agents to handle files and answer questions based on their content.

## Prerequisites

1.  **Install necessary libraries**:
    From the root directory of the AutoGen project, run:
    ```bash
    pip install -e ".[all]"
    ```

2.  **OpenAI API Key**:
    Ensure you have a valid OpenAI API key.

3.  **Configuration File**:
    Create a configuration file named `config.json` in the `python/samples/file_handling/` directory. This file should contain your API key and the model you wish to use (e.g., a model that supports file processing like `gpt-4o`).

    Example `config.json`:
    ```json
    {
        "model": "gpt-4o",
        "api_key": "YOUR_OPENAI_API_KEY"
    }
    ```
    Replace `"YOUR_OPENAI_API_KEY"` with your actual OpenAI API key.

4.  **Sample Files**:
    Place the following sample files in the `python/samples/file_handling/` directory:
    *   `sample_document.pdf`: A sample PDF document.
    *   `sample_image.jpg` (or `.png`, `.jpeg`): A sample image file.
    The example script `file_example.py` is configured to look for these files.

## Running the Example

Navigate to the `python/samples/file_handling/` directory in your terminal and run:

```bash
python file_example.py
```

## Example Script Overview (`file_example.py`)

The script demonstrates different ways to send files to a model:

1.  **Direct File Content**: 
    The file content (e.g., of a PDF) is sent directly in the request. The underlying system typically handles base64 encoding.

2.  **File ID Reference**: 
    A file (e.g., a PDF) is first uploaded to the OpenAI service (or a similar service supported by the model client) to obtain a `file_id`. This `file_id` is then used to reference the file in subsequent messages.

3.  **Combined Image and File (PDF)**:
    Demonstrates sending a `MultiModalMessage` that includes:
    *   An image (sent as direct content).
    *   A PDF document (referenced by its `file_id` after uploading, or sent as direct content depending on the active example in `main()`).

By default, the `main()` function in `file_example.py` is set up to run the example that combines an image and a PDF (using `file_id` for the PDF). You can uncomment other examples within `main()` to test different scenarios.

You can modify the `file_example.py` script to experiment with different file types, prompts, and handling methods.