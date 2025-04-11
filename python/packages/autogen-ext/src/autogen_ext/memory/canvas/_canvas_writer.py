import json
from pydantic import BaseModel
from autogen_core import CancellationToken
from autogen_core.tools import BaseTool

from ._text_canvas import TextCanvas


class UpdateFileArgs(BaseModel):
    filename: str
    new_content: str


class UpdateFileResult(BaseModel):
    status: str


class UpdateFileTool(BaseTool[UpdateFileArgs, UpdateFileResult]):
    """
    Overwrites or creates a file in the canvas.
    """

    def __init__(self, canvas: TextCanvas):
        super().__init__(
            args_type=UpdateFileArgs,
            return_type=UpdateFileResult,
            name="update_file",
            description="Create/update a file on the canvas with the provided content.",
        )
        self._canvas = canvas

    async def run(self, args: UpdateFileArgs, cancellation_token: CancellationToken) -> UpdateFileResult:
        self._canvas.add_or_update_file(args.filename, args.new_content)
        return UpdateFileResult(status="OK")


class ApplyPatchArgs(BaseModel):
    filename: str
    patch_text: str


class ApplyPatchResult(BaseModel):
    status: str


class ApplyPatchTool(BaseTool[ApplyPatchArgs, ApplyPatchResult]):
    """
    Applies a unified diff patch to the given file on the canvas.
    """

    def __init__(self, canvas: TextCanvas):
        super().__init__(
            args_type=ApplyPatchArgs,
            return_type=ApplyPatchResult,
            name="apply_patch",
            description=(
                "Apply a unified diff patch to an existing file on the canvas. "
                "The patch must be in diff/patch format. The file must exist or be created first."
            ),
        )
        self._canvas = canvas

    async def run(self, args: ApplyPatchArgs, cancellation_token: CancellationToken) -> ApplyPatchResult:
        self._canvas.apply_patch(args.filename, args.patch_text)
        return ApplyPatchResult(status="PATCH APPLIED")
