from autogen_core.tools import ParametersSchema, ToolSchema

TOOL_SEND_EMAIL = ToolSchema(
    name="send_email",
    description="Send an email with the specified subject, content, and optional attachments or images.",
    parameters=ParametersSchema(
        type="object",
        properties={
            "subject": {
                "type": "string",
                "description": "The subject of the email.",
            },
            "html": {
                "type": "boolean",
                "description": "Whether to use HTML format for the email, default to True",
            },
            "receiver": {
                "type": "array",
                "items": {"type": "string"},
                "description": "The list of recipients to send the email to.",
            },
            "images": {
                "type": "array",
                "items": {"type": "string"},
                "description": "A list of image filenames to include in the email.",
            },
            "attachments": {
                "type": "array",
                "items": {"type": "string"},
                "description": "A list of file paths for attachments to include in the email.",
            },
        },
        required=["subject"],
    ),
)

TOOL_GET_ATTACH_DATA = ToolSchema(
    name="get_attach_data",
    description="Retrieve attachment data from a specified file path.",
    parameters=ParametersSchema(
        type="object",
        properties={
            "attach_path": {
                "type": "string",
                "description": "The file path to get the attachment data.",
            },
        },
        required=["attach_path"],
    ),
)

TOOL_GENERATE_IMAGE = ToolSchema(
    name="generate_image",
    description="Generate an image based on a given prompt and optional size.",
    parameters=ParametersSchema(
        type="object",
        properties={
            "prompt": {
                "type": "string",
                "description": """The prompt used to generate the image. \n Format: \n 1. Main subject + Perspective description + Relevant elements\n 2. Additional elements + Detailed characteristics \n 3.Art style (soft, dark) + Detail quality (4K) + Camera style ("Shot with a macro lens (f/2.8, 50mm) and a Canon EOS R5") \n Example: \n A tiny red dragon curled up asleep in its nest on a medieval wizard's desk. Shot with a macro lens (f/2.8, 50mm) and a Canon EOS R5, the soft focus captures the scene of gentle morning light streaming through a nearby window. Subtle colors and fantastical steam shapes enhance the tranquil atmosphere, evoking a scene from an RPG game called DnD. This image is presented in 16K and 8K resolution, highlighting its intricate details and medieval charm.""",
            },
            "size": {
                "type": "string",
                "description": "The dimensions of the generated image (default: '1024x1024').",
            },
        },
        required=["prompt"],
    ),
)

TOOL_GET_IMAGE_DATA = ToolSchema(
    name="get_image_data",
    description="Retrieve image data from a specified file path. if the image is from generation, do not use it, it had already load",
    parameters=ParametersSchema(
        type="object",
        properties={
            "image_path": {
                "type": "string",
                "description": "The file path to get the image data.",
            },
        },
        required=["image_path"],
    ),
)
