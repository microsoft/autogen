class DatabaseError(Exception):
    pass


class ChatMessageError(DatabaseError):
    pass


class ToolUpdateError(DatabaseError):
    pass


class InvalidToolError(Exception):
    pass


class SubprocessError(Exception):
    pass


class FileManagerError(Exception):
    pass
