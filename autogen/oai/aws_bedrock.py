
from __future__ import annotations

import copy
import inspect
import json
import os
import time
import warnings
from typing import Any, Dict, List, Tuple, Union


from autogen.oai.client_utils import validate_parameter

import boto3

class AWSBedrock:
    def __init__(self, **kwargs: Any):
        self.aws_access_key = kwargs.get("aws_access_key", None)
        self.aws_session_key = kwargs.get("aws_session_key", None)
        self.aws_secret_key = kwargs.get("aws_secret_key", None)
        self.aws_region = kwargs.get("aws_region", None)

        if not self.aws_access_key:
            self.aws_access_key = os.getenv("AWS_ACCESS_KEY")

        if not self.aws_secret_key:
            self.aws_secret_key = os.getenv("AWS_SECRET_KEY")

        if not self.aws_region:
            self.aws_region = os.getenv("AWS_REGION")

        assert self.aws_access_key, "AWS_ACCESS_KEY is required, set the environment variable AWS_ACCESS_KEY"
        assert self.aws_secret_key, "AWS_SECRET_KEY is required, set the environment variable AWS_SECRET_KEY"
        assert self.aws_region, "AWS_REGION is required, set the environment variable AWS_REGION"
        
        self.client = boto3.client('bedrock-runtime',
                                   aws_access_key_id=self.aws_access_key,
                                   aws_secret_access_key=self.aws_secret_key,
                                   region_name=self.aws_region)
    
    @property
    def aws_access_key(self):
        return self.aws_access_key

    @property
    def aws_secret_key(self):
        return self.aws_secret_key
    
    @property
    def aws_region(self):
        return self.aws_region

