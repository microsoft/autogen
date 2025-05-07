import base64
import pandas as pd
import io
from typing import Sequence, Union
from autogen_agentchat.messages import ChatMessage, MultiModalMessage, TextMessage
from autogen_core import Image
from autogen_core.models import UserMessage
from loguru import logger
from PyPDF2 import PdfReader

def construct_task(query: str, files: list[dict] | None = None) -> Sequence[ChatMessage]:
    """
    Construct a task from a query string and list of files.
    Returns a list of ChatMessage objects suitable for processing by the agent system.
    Args:
        query: The text query from the user
        files: List of file objects with properties name, content, and type
    Returns:
        List of BaseChatMessage objects (TextMessage, MultiModalMessage)
    """
    if files is None:
        files = []
    
    messages = []
    
    # Add the user's text query as a TextMessage
    if query:
        messages.append(TextMessage(source="user", content=query))
    
    # Process each file based on its type
    for file in files:
        try:
            if file.get("type", "").startswith("image/"):
                # Handle image file using from_base64 method
                image = Image.from_base64(file["content"])
                messages.append(
                    MultiModalMessage(
                        source="user", content=[image], metadata={"filename": file.get("name", "unknown.img")}
                    )
                )
            
            elif file.get("type", "").startswith("text/"):
                # Handle text file as TextMessage
                text_content = base64.b64decode(file["content"]).decode("utf-8")
                messages.append(
                    TextMessage(
                        source="user", content=text_content, metadata={"filename": file.get("name", "unknown.txt")}
                    )
                )

            elif file.get("type", "").startswith("application/pdf"):
                # Handle PDF file - extract text using PyPDF2
                pdf_content = extract_pdf_text(file["content"])
                messages.append(
                    TextMessage(
                        source="user", content=pdf_content, metadata={"filename": file.get("name", "unknown.pdf")}
                    )
                )

            elif file.get("type", "").startswith("text/csv"):
                # Handle CSV file - retain structure as a pandas DataFrame
                csv_df = extract_csv_to_df(file["content"])
                # Optionally, you can now use csv_df as a DataFrame for further operations.
                messages.append(
                    TextMessage(
                        source="user", content=csv_df.to_string(index=False), metadata={"filename": file.get("name", "unknown.csv")}
                    )
                )

            elif file.get("type", "").startswith("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"):
                # Handle Excel file - retain structure as a pandas DataFrame
                excel_dfs = extract_excel_to_df(file["content"])
                # You can now access and work with each sheet as a DataFrame.
                for sheet_name, df in excel_dfs.items():
                    messages.append(
                        TextMessage(
                            source="user", content=df.to_string(index=False), metadata={"filename": file.get("name", "unknown.xlsx"), "sheet": sheet_name}
                        )
                    )

            else:
                # Log unsupported file types but still try to process based on best guess
                logger.warning(f"Potentially unsupported file type: {file.get('type')} for file {file.get('name')}")
                if file.get("type", "").startswith("application/"):
                    # Try to treat as text if it's an application type (like JSON)
                    text_content = base64.b64decode(file["content"]).decode("utf-8")
                    messages.append(
                        TextMessage(
                            source="user",
                            content=text_content,
                            metadata={
                                "filename": file.get("name", "unknown.file"),
                                "filetype": file.get("type", "unknown"),
                            },
                        )
                    )
        except Exception as e:
            logger.error(f"Error processing file {file.get('name')}: {str(e)}")
            # Continue processing other files even if one fails
    print("MESSAGES",messages)
    return messages

def extract_pdf_text(pdf_base64: str) -> str:
    """
    Extract text from a base64-encoded PDF file.
    """
    pdf_data = base64.b64decode(pdf_base64)
    pdf_reader = PdfReader(io.BytesIO(pdf_data))
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() + "\n"
    return text

def extract_csv_to_df(csv_base64: str) -> pd.DataFrame:
    """
    Extract the content from a base64-encoded CSV file and return as a pandas DataFrame.
    """
    csv_data = base64.b64decode(csv_base64)
    return pd.read_csv(io.BytesIO(csv_data))

def extract_excel_to_df(excel_base64: str) -> dict[str, pd.DataFrame]:
    """
    Extract the content from a base64-encoded Excel file and return as a dictionary of pandas DataFrames.
    Each sheet will be stored as a DataFrame with its sheet name as the key.
    """
    excel_data = base64.b64decode(excel_base64)
    excel_df = pd.read_excel(io.BytesIO(excel_data), sheet_name=None)  # Load all sheets
    return excel_df





# import base64
# from typing import Sequence

# from autogen_agentchat.messages import ChatMessage, MultiModalMessage, TextMessage
# from autogen_core import Image
# from autogen_core.models import UserMessage
# from loguru import logger


# def construct_task(query: str, files: list[dict] | None = None) -> Sequence[ChatMessage]:
#     """
#     Construct a task from a query string and list of files.
#     Returns a list of ChatMessage objects suitable for processing by the agent system.

#     Args:
#         query: The text query from the user
#         files: List of file objects with properties name, content, and type

#     Returns:
#         List of BaseChatMessage objects (TextMessage, MultiModalMessage)
#     """
#     if files is None:
#         files = []

#     messages = []

#     # Add the user's text query as a TextMessage
#     if query:
#         messages.append(TextMessage(source="user", content=query))

#     # Process each file based on its type
#     for file in files:
#         try:
#             if file.get("type", "").startswith("image/"):
#                 # Handle image file using from_base64 method
#                 # The content is already base64 encoded according to the convertFilesToBase64 function
#                 image = Image.from_base64(file["content"])
#                 messages.append(
#                     MultiModalMessage(
#                         source="user", content=[image], metadata={"filename": file.get("name", "unknown.img")}
#                     )
#                 )
#             elif file.get("type", "") in ["text/plain", "application/json"]:
#                 # Handle text-based files as TextMessage
#                 text_content = base64.b64decode(file["content"]).decode("utf-8")
#                 messages.append(
#                     TextMessage(
#                         source="user", content=text_content, metadata={"filename": file.get("name", "unknown.txt")}
#                     )
#                 )
#             elif file.get("type", "") in ["application/pdf", "application/csv","application/vnd.ms-excel", 
#                                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
#                 # Handle binary files as attachments
#                 # For these types, we'll create a text message that references the attachment
#                 messages.append(
#                     TextMessage(
#                         source="user",
#                         content=f"I've uploaded a file: {file.get('name', 'unknown.file')}",
#                         metadata={
#                             "filename": file.get("name", "unknown.file"),
#                             "filetype": file.get("type", "unknown"),
#                             "is_attachment": True,
#                         },
#                     )
#                 )
#             else:
#                 # Log unsupported file types but still try to process based on best guess
#                 logger.warning(f"Potentially unsupported file type: {file.get('type')} for file {file.get('name')}")
#                 if file.get("type", "").startswith("application/"):
#                     # Try to treat as text if it's an application type (like JSON)
#                     text_content = base64.b64decode(file["content"]).decode("utf-8")
#                     messages.append(
#                         TextMessage(
#                             source="user",
#                             content=text_content,
#                             metadata={
#                                 "filename": file.get("name", "unknown.file"),
#                                 "filetype": file.get("type", "unknown"),
#                             },
#                         )
#                     )
#         except Exception as e:
#             logger.error(f"Error processing file {file.get('name')}: {str(e)}")
#             # Continue processing other files even if one fails

#     return messages

