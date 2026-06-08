from pathlib import Path
from typing import Dict

this_file_dir = Path(__file__).parent

files = [
    this_file_dir / "packages/autogen-ext/src/autogen_ext/runtimes/grpc/protos/agent_worker_pb2_grpc.py",
    this_file_dir / "packages/autogen-ext/src/autogen_ext/runtimes/grpc/protos/agent_worker_pb2_grpc.pyi",
    this_file_dir / "packages/autogen-ext/src/autogen_ext/runtimes/grpc/protos/agent_worker_pb2.py",
    this_file_dir / "packages/autogen-ext/src/autogen_ext/runtimes/grpc/protos/agent_worker_pb2.pyi",
    this_file_dir / "packages/autogen-ext/src/autogen_ext/runtimes/grpc/protos/cloudevent_pb2_grpc.py",
    this_file_dir / "packages/autogen-ext/src/autogen_ext/runtimes/grpc/protos/cloudevent_pb2_grpc.pyi",
    this_file_dir / "packages/autogen-ext/src/autogen_ext/runtimes/grpc/protos/cloudevent_pb2.py",
    this_file_dir / "packages/autogen-ext/src/autogen_ext/runtimes/grpc/protos/cloudevent_pb2.pyi",
]

substitutions: Dict[str, str] = {
    "\nimport agent_worker_pb2 as agent__worker__pb2\n": "\nfrom . import agent_worker_pb2 as agent__worker__pb2\n",
    "\nimport agent_worker_pb2\n": "\nfrom . import agent_worker_pb2\n",
    "\nimport cloudevent_pb2 as cloudevent__pb2\n": "\nfrom . import cloudevent_pb2 as cloudevent__pb2\n",
    "\nimport cloudevent_pb2\n": "\nfrom . import cloudevent_pb2\n",
}


def main():
    for file in files:
        with open(file, "r") as f:
            content = f.read()

        print("Fixing imports in file:", file)
        for old, new in substitutions.items():
            content = content.replace(old, new)

        with open(file, "w") as f:
            f.write(content)
