"""
This example demonstrates how to use AutoGen's File and MultiModalMessage classes
to handle files with language models.

This script showcases two ways to send files to a model:
1. Directly using file content (which will be base64 encoded by the underlying system).
2. By first uploading a file to get a file_id, and then referencing this ID.
   (This part currently relies on the model client supporting file uploads
   and the assistant agent or message transformation logic knowing how to use file_ids.)

To run this example, you need an OpenAI API key and a model that supports
file processing (e.g., gpt-4o or newer).
"""

import asyncio
import json
from pathlib import Path
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import MultiModalMessage
from autogen_core import File, CancellationToken
from autogen_core._image import Image
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.ui import Console

# Module-level variable for the shared model client
module_model_client: OpenAIChatCompletionClient | None = None

async def get_model_client() -> OpenAIChatCompletionClient:
    """Gets or initializes the shared OpenAI Chat Completion client."""
    global module_model_client
    # Simplistic approach: if it's None or we assume it might have been closed by a previous example,
    # re-initialize. A more robust app might check client.closed if available or use a context manager.
    if module_model_client is None: # Basic check, could be enhanced 
        config_path = Path(__file__).parent / "config.json"
        if not config_path.exists():
            # This path should ideally not be hit if examples call this after checking config themselves,
            # but added for robustness of the getter.
            raise FileNotFoundError(f"Configuration file not found. Please create: {config_path}")
        
        with open(config_path, "r") as f:
            config = json.load(f)
        
        print("Initializing shared OpenAI model client...")
        module_model_client = OpenAIChatCompletionClient(
            model=config.get("model", "gpt-4o"),
            api_key=config.get("api_key"),
            base_url=config.get("base_url"),
        )
    return module_model_client

async def close_model_client():
    """Closes the shared model client if it exists."""
    global module_model_client
    if module_model_client is not None:
        print("Closing shared OpenAI model client...")
        await module_model_client.close()
        module_model_client = None # Set to None so it can be re-initialized if needed

async def create_sample_file():
    """Create a sample PDF document or ensure the pre-existing PDF file is available."""
    sample_dir = Path(__file__).parent
    sample_dir.mkdir(exist_ok=True)
    
    sample_file_pdf = sample_dir / "sample_document.pdf"

    # Prefer using the pre-existing PDF file
    if sample_file_pdf.exists():
        print(f"Using pre-existing PDF file: {sample_file_pdf}")
        return sample_file_pdf
    else:
        # If the pre-existing PDF is not found, raise an error.
        # Users should ensure 'sample_document.pdf' is present in the directory.
        # Dynamic creation code (e.g., using reportlab) can be added here if desired.
        raise FileNotFoundError(
            f"Sample PDF file '{sample_file_pdf}' not found. "
            f"Please place a sample PDF in the '{sample_dir}' directory."
        )

async def create_sample_image_file():
    """Ensure a sample image file exists or raise an error."""
    sample_dir = Path(__file__).parent
    # Try common image extensions
    for ext in ["jpg", "png", "jpeg"]:
        sample_image_file = sample_dir / f"sample_image.{ext}"
        if sample_image_file.exists():
            print(f"Using pre-existing sample image: {sample_image_file}")
            return sample_image_file
    raise FileNotFoundError(
        f"Sample image file (e.g., sample_image.jpg or sample_image.png) not found in {sample_dir}. "
        f"Please place a sample image in the directory."
    )

async def direct_file_example():
    """Demonstrates sending file content directly."""
    print("\n===== Example: Sending File Content Directly =====")
    
    # Config check is still good practice here before attempting to get client
    config_path = Path(__file__).parent / "config.json"
    if not config_path.exists():
        print(f"Configuration file not found. Please create: {config_path}")
        return

    model_client = await get_model_client()
    
    # Create assistant agent
    assistant = AssistantAgent(
        name="file_assistant",
        system_message="You are an assistant specializing in processing files and answering questions. Please carefully read the provided file and answer the user's questions.",
        model_client=model_client,
    )
    
    # Create sample file (PDF)
    sample_file_path = await create_sample_file()
    
    # Create File object and MultiModalMessage
    autogen_file_obj = File.from_path(sample_file_path)
    message = MultiModalMessage(
        content=[autogen_file_obj, "What information about AutoGen does this document contain?"],
        source="user", 
    )
    
    print(f"Sending file content from '{sample_file_path.name}' and asking a question...")
    await Console(assistant.run_stream(task=message, cancellation_token=CancellationToken()))
    # Note: Client is not closed here; will be closed in main or by close_model_client()

async def file_id_example():
    """Demonstrates using a file_id to reference an uploaded file."""
    print("\n===== Example: Referencing File by file_id =====")

    config_path = Path(__file__).parent / "config.json"
    if not config_path.exists():
        print(f"Configuration file not found. Please create: {config_path}")
        return

    model_client = await get_model_client()
    
    assistant = AssistantAgent(
        name="file_id_assistant",
        system_message="You are an assistant specializing in processing files and answering questions. Please carefully read the provided file (referenced by ID) and answer the user's questions.",
        model_client=model_client,
    )
        
    sample_file_path = await create_sample_file()
    
    print(f"Uploading file '{sample_file_path.name}' to OpenAI service...")
    file_id = await model_client.upload_file(
        file_path=str(sample_file_path),
        purpose="user_data"
    )
    print(f"Obtained file_id: {file_id}")
    
    autogen_file_obj = File.from_file_id(file_id, filename=sample_file_path.name)
    message = MultiModalMessage(
        content=[autogen_file_obj, "What is the main design model mentioned in this document?"],
        source="user",
    )
    
    print(f"Sending file_id reference '{file_id}' and asking a question...")
    await Console(assistant.run_stream(task=message, cancellation_token=CancellationToken()))
    
    print(f"Cleaning up: Deleting uploaded file {file_id}...")
    await model_client.delete_file(file_id)

async def image_and_pdf_example():
    """Demonstrates sending both an image (as content) and a PDF file (as file_id) in one message."""
    print("\n===== Example: Sending Image (Content) and PDF (file_id) =====")
    
    config_path = Path(__file__).parent / "config.json"
    if not config_path.exists():
        print(f"Configuration file not found. Please create: {config_path}")
        return

    model_client = await get_model_client()
    
    assistant = AssistantAgent(
        name="multimodal_eval_assistant",
        system_message="You are an assistant capable of processing text, images, and PDF documents. Please analyze all provided content to answer the user's questions accurately.",
        model_client=model_client,
    )
        
    sample_pdf_path = await create_sample_file()
    sample_image_path = await create_sample_image_file()
    
    print(f"Uploading PDF file '{sample_pdf_path.name}' to get a file_id...")
    pdf_file_id = await model_client.upload_file(
        file_path=str(sample_pdf_path),
        purpose="user_data"
    )
    print(f"Obtained PDF file_id: {pdf_file_id}")
    
    pdf_autogen_obj = File.from_file_id(pdf_file_id, filename=sample_pdf_path.name)
    image_autogen_obj = Image.from_file(sample_image_path)
    
    message = MultiModalMessage(
        content=[
            "Please describe the content of the attached image and summarize the key points in the PDF document. And please tell me what this image means in the document?",
            image_autogen_obj, 
            pdf_autogen_obj, 
        ],
        source="user",
    )
    
    print(f"Sending image ('{sample_image_path.name}') and PDF file_id ('{pdf_file_id}') with a question...")
    await Console(assistant.run_stream(task=message, cancellation_token=CancellationToken()))
    
    print(f"Cleaning up: Deleting uploaded PDF file {pdf_file_id}...")
    await model_client.delete_file(pdf_file_id)

async def main():
    """Main function to run the examples."""
    
    print("Starting AutoGen file handling examples...")

    # Example 1: Using direct file content (PDF)
    print("\n--- Running Direct File Example ---")
    await direct_file_example()
    
    # Example 2: Using file_id reference (PDF)
    print("\n--- Running File ID Example ---")
    await file_id_example()

    # Example 3: Using both image and PDF content
    print("\n--- Running Image and PDF Example ---")
    await image_and_pdf_example()


    await close_model_client() # Close client

    print("\nAll examples finished.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except FileNotFoundError as e:
        print(f"Error: A required sample file was not found: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")