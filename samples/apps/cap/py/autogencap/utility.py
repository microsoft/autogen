from autogencap.DebugLog import Error
from autogencap.proto.CAP_pb2 import Error as ErrorMsg
from autogencap.proto.CAP_pb2 import ErrorCode


def report_error_msg(msg: ErrorMsg, src: str):
    if msg is not None:
        err = ErrorMsg()
        err.ParseFromString(msg)
        if err.code != ErrorCode.EC_OK:
            Error(src, f"Error response: code[{err.code}] msg[{err.message}]")
