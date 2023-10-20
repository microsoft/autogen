import fnmatch
import os

from utils.utils import copy_utils


class RAWorkflow:
    def __init__(
        self,
        utils_dir,
        work_dir,
        ra_config=None,
        llm_config=None,
        silent=False,
        agent_on_receive=None,
    ) -> None:
        self.utils_dir = utils_dir
        self.work_dir = work_dir
        self.ra_config = ra_config
        self.llm_config = llm_config
        self.silent = silent
        self.agent_on_receive = agent_on_receive

        if not os.path.exists(self.work_dir):
            os.makedirs(self.work_dir)

        # check if utils dir is a str or list of dirs
        # if it is a str, convert it to a list
        if isinstance(self.utils_dir, str):
            self.utils_dir = [self.utils_dir]
        for dirpath in self.utils_dir:
            if not os.path.exists(dirpath):
                os.makedirs(dirpath)

        # copy all files from utils_dir to work_dir
        copy_utils(self.utils_dir, self.work_dir)

        self.define_agents()

    def define_agents(self):
        """
        This function should be implemented by the child class.
        Specifically, it should
            - define the agents
            - register the auto reply functions (if applicable)
        """
        raise NotImplementedError

    def process_message(self, message, history=None):
        """
        Generate a response and reply with metadata (e.g., files generated/modified)

        Args:
            message (str): the message from the user
            history (List[Dict]): the list of messages in the chat history

        Returns:
            Dict: with three fileds
                - message (str): generated response or execution output
                - code (str): the code that was executed
                - metadata (Dict): dict of files generated/modified
        """
        # get the timestamp of the latest file in the work_dir
        timestamp = 0
        for root, dirs, files in os.walk(self.work_dir):
            for file in files:
                file_path = os.path.join(root, file)
                file_timestamp = os.path.getmtime(file_path)
                if file_timestamp > timestamp:
                    timestamp = file_timestamp

        response, code = self.generate_response(message, history)

        dir2filename = self.get_sorted_new_files(timestamp)

        return {
            "role": "assistant",
            "content": response,
            "code": code,
            "metadata": dir2filename,
        }

    def generate_response(self, message, history):
        """
        Generate the response for the message.
        """
        raise NotImplementedError

    def get_sorted_new_files(self, timestamp):
        """
        Get all the files that were created or modified after the timestamp.
        """

        ignore_patterns = [
            "__pycache__",
            "*.pyc",
            "__init__.py",
            "*.cache",
        ]

        def is_ignored(file_or_dir):
            for pattern in ignore_patterns:
                if fnmatch.fnmatch(file_or_dir, pattern):
                    return True
            return False

        # get all files that were created or modified after the timestamp
        new_files = []
        for root, dirs, files in os.walk(self.work_dir):
            dirs[:] = [d for d in dirs if not is_ignored(d)]  # Ignore specified directories
            for file in files:
                if is_ignored(file):  # Ignore specified files
                    continue
                file_path = os.path.join(root, file)
                file_timestamp = os.path.getmtime(file_path)
                if file_timestamp > timestamp:
                    new_files.append(file_path)

        # Mapping of file extensions to directories
        ext_to_dir = {
            # Scripts
            ".py": "scripts",
            ".sh": "scripts",
            ".bat": "scripts",
            ".rb": "scripts",
            ".pl": "scripts",
            # Images
            ".png": "images",
            ".jpg": "images",
            ".jpeg": "images",
            ".gif": "images",
            ".bmp": "images",
            ".svg": "images",
            ".ico": "images",
        }

        # Initialize directory to file list mapping
        dir2filename = {dir: [] for dir in set(ext_to_dir.values())}
        dir2filename["files"] = []  # For files not matching any extension

        # Sort new files into respective directories
        for f in new_files:
            file_ext = os.path.splitext(f)[1]
            # file_path = os.path.join(self.work_dir, f)

            dir_category = None
            if file_ext in ext_to_dir:
                dir_category = ext_to_dir[file_ext]
            else:
                dir_category = "files"

            dir2filename[dir_category].append(f)

        return dir2filename
