import re
import pathlib
import os
from datetime import datetime
from dataclasses import dataclass, field
import json
from typing import Tuple, List, Union, Optional
import argparse


class ConfigScore:
    trial_id: str = field(default=None)
    start_time: float = field(default=None)
    last_update_time: float = field(default=None)
    config: dict = field(default=None)
    metric_score: dict = field(default=None)
    time_stamp: float = field(default=None)

    def __init__(self,
                 trial_id: str = None,
                 start_time: float = None,
                 last_update_time: float = None,
                 config: dict = None,
                 metric_score: dict = None,
                 time_stamp: float = None
                 ):
        self.trial_id = trial_id
        self.start_time = start_time
        self.last_update_time = last_update_time
        self.config = config
        self.metric_score = metric_score
        self.time_stamp = time_stamp


class ConfigScoreList:

    def __init__(self,
                 config_score_list: List[ConfigScore],
                 jobid_config=None,
                 blob_file=None,
                 ):
        self._config_score_list = config_score_list
        self._blob_file = blob_file
        self._jobid_config = jobid_config

    def sorted(self, sort_method="unsorted", metric_mode="max"):
        if sort_method == "unsorted":
            self._config_score_list = self._config_score_list
        elif sort_method == "sort_time":
            self._config_score_list = sorted(self._config_score_list, key=lambda x: x.start_time, reverse=False)
        else:
            self._config_score_list = sorted(self._config_score_list,
                                             key=lambda x: getattr(x, "metric_score")
                                             [metric_mode], reverse=True)

    def get_best_config(self,
                        metric_mode="max"):
        return max(self._config_score_list, key=lambda x: getattr(x, "metric_score")
                   [metric_mode])


@dataclass
class JobID:
    dat: list = field(default=None)
    subdat: str = field(default=None)
    mod: str = field(default=None)
    spa: str = field(default=None)
    arg: str = field(default=None)
    alg: str = field(default=None)
    pru: str = field(default=None)
    pre_full: str = field(default=None)
    pre: str = field(default=None)
    presz: str = field(default=None)
    spt: str = field(default=None)
    rep: int = field(default=0)
    sddt: int = field(default=None)
    sdhf: int = field(default=None)
    var1: Optional[float] = field(default=None)
    var2: Optional[float] = field(default=None)

    def __init__(self,
                 console_args=None):
        if console_args:
            self.set_jobid_from_console_args(console_args)

    def set_unittest_config(self):
        """
            set the JobID config for unit test
        """
        self.dat = ["glue"]
        self.subdat = "mrpc"
        self.mod = "hpo"
        self.spa = "uni_test"
        self.arg = "cus"
        self.alg = "bs"
        self.pru = "None"
        self.pre_full = "google/mobilebert-uncased"
        self.pre = "mobilebert"
        self.presz = "small"
        self.spt = "rspt"
        self.rep = 0
        self.sddt = 43
        self.sdhf = 42
        self.var1 = None
        self.var2 = None

    def is_match(self, partial_jobid):
        """
            return a boolean variable whether the current object matches the partial jobid defined
            in partial_jobid. For example,
            self = JobID(dat = ['glue'],
                            subdat = 'cola',
                            mod = 'bestnn',
                            spa = 'buni',
                            arg = 'cus',
                            alg = 'bs',
                            pru = 'None',
                            pre = 'funnel',
                            presz = 'xlarge',
                            spt = 'rspt',
                            rep = 0,
                            sddt = 43,
                            sdhf = 42)
            partial_jobid1 = JobID(dat = ['glue'],
                                  subdat = 'cola',
                                  mod = 'hpo')
           partial_jobid2 = JobID(dat = ['glue'],
                                  subdat = 'cola',
                                  mod = 'bestnn')
            return False for partial_jobid1 and True for partial_jobid2
        """
        is_not_match = False
        for key, val in partial_jobid.__dict__.items():
            if val is None:
                continue
            if getattr(self, key) != val:
                is_not_match = True
        return not is_not_match

    def to_wandb_string(self):
        """
            preparing for the job ID for wandb
        """
        field_dict = self.__dict__
        keytoval_str = "_".join([JobID.dataset_list_to_str(field_dict[key])
                                 if type(field_dict[key]) == list
                                 else str(field_dict[key])
                                 for key in field_dict.keys() if not key.endswith("_full")])
        return keytoval_str

    def to_jobid_string(self):
        """
            convert the current JobID into a blob name string which contains all the fields
        """
        list_keys = list(JobID.__dataclass_fields__.keys())
        field_dict = self.__dict__
        keytoval_str = "_".join([key + "=" + JobID.dataset_list_to_str(field_dict[key])
                                 if type(field_dict[key]) == list
                                 else key + "=" + str(field_dict[key])
                                 for key in list_keys if not key.endswith("_full")])
        return keytoval_str

    def to_partial_jobid_string(self):
        """
            convert the current JobID into a blob name string which only contains the fields whose values are not "None"
        """
        list_keys = list(JobID.__dataclass_fields__.keys())
        field_dict = self.__dict__  # field_dict contains fields whose values are not None
        keytoval_str = "_".join([key + "=" + JobID.dataset_list_to_str(field_dict[key])
                                 if type(field_dict[key]) == list
                                 else key + "=" + str(field_dict[key])
                                 for key in list_keys if key in field_dict.keys()])
        return keytoval_str

    @staticmethod
    def blobname_to_jobid_dict(keytoval_str):
        """
            converting an azure blobname to a JobID config,
            e.g., blobname = "dat=glue_subdat=cola_mod=bestnn_spa=buni_arg=cus_
                              alg=bs_pru=None_pre=funnel_presz=xlarge_spt=rspt_rep=0.json"
            the converted jobid dict = {dat = ['glue'], subdat = 'cola', mod = 'bestnn',
                                   spa = 'buni', arg = 'cus', alg = 'bs', pru = 'None',
                                   pre = 'funnel', presz = 'xlarge', spt = 'rspt',
                                   rep = 0, sddt = 43, sdhf = 42)
        """
        field_keys = [key for key in list(JobID.__dataclass_fields__.keys()) if not key.endswith("_full")]
        regex_expression = ".*"
        is_first = True
        for key in field_keys:
            if is_first:
                prefix = ""
                is_first = False
            else:
                prefix = "_"
            if key.startswith("sd") or key.startswith("var"):
                regex_expression += "(" + prefix + key + "=(?P<" + key + ">[^_]*))?"
            else:
                regex_expression += prefix + key + "=(?P<" + key + ">[^_]*)"
        regex_expression += ".(json|zip)"
        result = re.search(regex_expression, keytoval_str)
        if result:
            result_dict = {}
            for key in field_keys:
                if key == "dat":
                    result_dict[key] = [result.group(key)]
                elif key == "rep":
                    try:
                        try:
                            result_dict[key] = int(result.group(key))
                        except IndexError:
                            print("No group {} in the regex result".format(key))
                            result_dict[key] = -1
                    except ValueError:
                        print("Cannot parse integer {}".format(result.group(key)))
                        result_dict[key] = -1
                else:
                    result_dict[key] = result.group(key)
            return result_dict
        else:
            return None

    @staticmethod
    def dataset_list_to_str(dataset_name, key="dat"):
        if isinstance(dataset_name, list):
            return "-".join(dataset_name)
        else:
            return dataset_name

    def set_jobid_from_arg_list(self,
                                **jobid_list
                                ):
        """
            set the jobid from a dict object
        """
        for key in jobid_list.keys():
            assert key in JobID.__dataclass_fields__.keys()
            setattr(self, key, jobid_list[key])
        if self.mod == "grid":
            self.alg = "grid"

    @staticmethod
    def convert_blobname_to_jobid(blobname):
        """
            converting a blobname string to a JobID object
        """
        jobconfig_dict = JobID.blobname_to_jobid_dict(blobname)
        if jobconfig_dict:
            jobconfig = JobID()
            jobconfig.set_jobid_from_arg_list(**jobconfig_dict)
            return jobconfig
        else:
            return None

    @staticmethod
    def get_full_data_name(dataset_name: Union[list, str], subdataset_name=None):
        """
            convert a dataset name and sub dataset name to a full dataset name
        """
        if isinstance(dataset_name, list):
            full_dataset_name = JobID.dataset_list_to_str(dataset_name)
        else:
            full_dataset_name = dataset_name
        if subdataset_name:
            full_dataset_name = full_dataset_name + "_" + subdataset_name
        return full_dataset_name

    def get_jobid_full_data_name(self):
        """
            get the full dataset name of the current JobID object
        """
        return JobID.get_full_data_name(JobID.dataset_list_to_str(self.dat), self.subdat)

    @staticmethod
    def _extract_model_type_with_keywords_match(pre_full):
        from ..hpo.grid_searchspace_auto import HF_MODEL_LIST
        matched_model_type = []
        for each_model_type in HF_MODEL_LIST:
            if each_model_type in pre_full:
                matched_model_type.append(each_model_type)
        assert len(matched_model_type) > 0
        return max(enumerate(matched_model_type), key=lambda x: len(x[1]))[1]

    @staticmethod
    def extract_model_type(full_model_name):
        from transformers import AutoConfig
        model_config = AutoConfig.from_pretrained(full_model_name)
        config_json_file = model_config.get_config_dict(full_model_name)[0]
        try:
            model_type = config_json_file["model_type"]
        except KeyError:
            print("config_json_file does not contain model_type, re-extracting with keywords matching")
            model_type = JobID._extract_model_type_with_keywords_match(full_model_name)
        return model_type

    @staticmethod
    def get_attrval_from_arg_or_dict(console_args: Union[argparse.ArgumentParser, dict], each_key):
        if type(console_args) == argparse.Namespace:
            return getattr(console_args, each_key)
        else:
            return console_args[each_key]

    def set_jobid_from_console_args(self, console_args: Union[argparse.ArgumentParser, dict]):
        from ..utils import pretrained_model_size_format_check, dataset_subdataset_name_format_check
        console_to_jobid_key_mapping = {
            "pretrained_model_size": "pre",
            "dataset_subdataset_name": "dat",
            "algo_mode": "mod",
            "space_mode": "spa",
            "search_alg_args_mode": "arg",
            "algo_name": "alg",
            "pruner": "pru",
            "resplit_mode": "spt",
            "rep_id": "rep",
            "seed_data": "sddt",
            "seed_transformers": "sdhf",
            "optarg1": "var1",
            "optarg2": "var2"
        }
        for each_key in console_to_jobid_key_mapping.keys():
            try:
                try:
                    if each_key == "dataset_subdataset_name":
                        dataset_subdataset_name_format_check(JobID.get_attrval_from_arg_or_dict(console_args, each_key))
                        self.dat = JobID.get_attrval_from_arg_or_dict(console_args, each_key).split(":")[0].split(",")
                        self.subdat = JobID.get_attrval_from_arg_or_dict(console_args, each_key).split(":")[1]
                    elif each_key == "pretrained_model_size":
                        pretrained_model_size_format_check(JobID.get_attrval_from_arg_or_dict(console_args, each_key))
                        self.pre_full = JobID.get_attrval_from_arg_or_dict(console_args, each_key).split(":")[0]
                        self.pre = JobID.extract_model_type(self.pre_full)
                        self.presz = JobID.get_attrval_from_arg_or_dict(console_args, each_key).split(":")[1]
                    else:
                        jobid_key = console_to_jobid_key_mapping[each_key]
                        attrval = JobID.get_attrval_from_arg_or_dict(console_args, each_key)
                        setattr(self, jobid_key, attrval)
                except AttributeError:
                    print("console_args has no attribute {}, continue".format(each_key))
                    continue
            except KeyError:
                print("console_args has no attribute {}, continue".format(each_key))
                continue
        if self.mod == "grid":
            self.alg = "grid"


class AzureUtils:

    def __init__(self,
                 root_log_path=None,
                 console_args=None,
                 autohf=None):
        from ..utils import get_wandb_azure_key
        if root_log_path:
            self.root_log_path = root_log_path
        else:
            self.root_log_path = "logs_azure"
        self.jobid = autohf.jobid_config
        self.console_args = console_args
        self.autohf = autohf
        if console_args:
            wandb_key, azure_key, container_name = get_wandb_azure_key(console_args.key_path)
            self._container_name = container_name
            self._azure_key = azure_key
        else:
            self._container_name = self._azure_key = ""

    def _get_complete_connection_string(self):
        try:
            return "DefaultEndpointsProtocol=https;AccountName=docws5141197765;AccountKey=" \
                + self._azure_key + ";EndpointSuffix=core.windows.net"
        except AttributeError:
            return "DefaultEndpointsProtocol=https;AccountName=docws5141197765;AccountKey=" \
                ";EndpointSuffix=core.windows.net"

    def _init_azure_clients(self):
        try:
            from azure.storage.blob import ContainerClient
            connection_string = self._get_complete_connection_string()
            try:
                container_client = ContainerClient.from_connection_string(conn_str=connection_string,
                                                                          container_name=self._container_name)
                return container_client
            except ValueError:
                print("AzureUtils._container_name is specified as: {}, "
                      "please correctly specify AzureUtils._container_name".format(self._container_name))
                return None
        except ImportError:
            print("To use the azure storage component in flaml.nlp, run pip install azure-storage-blob")

    def _init_blob_client(self,
                          local_file_path):
        try:
            from azure.storage.blob import BlobServiceClient

            connection_string = self._get_complete_connection_string()
            blob_service_client = BlobServiceClient.from_connection_string(connection_string)
            try:
                blob_client = blob_service_client.get_blob_client(container=self._container_name, blob=local_file_path)
                return blob_client
            except ValueError:
                print("_container_name is unspecified or wrongly specified, please specify _container_name in AzureUtils")
                return None
        except ImportError:
            print("To use the azure storage component in flaml.nlp, run pip install azure-storage-blob")

    def upload_local_file_to_azure(self, local_file_path):
        try:
            from azure.core.exceptions import HttpResponseError
            try:
                blob_client = self._init_blob_client(local_file_path)
                if blob_client:
                    with open(local_file_path, "rb") as fin:
                        blob_client.upload_blob(fin, overwrite=True)
            except HttpResponseError as err:
                print("Cannot upload blob due to {}: {}".format("azure.core.exceptions.HttpResponseError",
                      err))
        except ImportError:
            print("To use the azure storage component in flaml.nlp, run pip install azure-storage-blob")

    def download_azure_blob(self, blobname):
        blob_client = self._init_blob_client(blobname)
        if blob_client:
            pathlib.Path(re.search("(?P<parent_path>^.*)/[^/]+$", blobname).group("parent_path")).mkdir(
                parents=True, exist_ok=True)
            with open(blobname, "wb") as fout:
                fout.write(blob_client.download_blob().readall())

    def extract_configscore_list_from_analysis(self,
                                               analysis):
        """
            Extracting a json object for storing the key information returned from tune.run
        """
        configscore_list = []
        for each_trial in analysis.trials:
            trial_id = each_trial.trial_id
            start_time = each_trial.start_time
            last_update_time = each_trial.last_update_time
            config = each_trial.config
            try:
                metric_score = each_trial.metric_analysis["eval_" + analysis.default_metric]
                time_stamp = each_trial.metric_analysis['timestamp']
            except KeyError:
                print("KeyError, {} does not contain the key {} or {}".format("each_trial.metric_analysis",
                                                                              "eval_" + analysis.default_metric,
                                                                              "timestamp"))
                metric_score = 0
                time_stamp = 0
            configscore_list.append(ConfigScore(
                trial_id=trial_id,
                start_time=start_time,
                last_update_time=last_update_time,
                config=config,
                metric_score=metric_score,
                time_stamp=time_stamp))
        return configscore_list

    def write_autohf_output(self,
                            configscore_list=None,
                            valid_metric=None,
                            predictions=None,
                            duration=None):
        """
            write the key info from a job and upload to azure blob storage
        """
        local_file_path = self.generate_local_json_path()
        output_json = {}
        if configscore_list:
            output_json["val_log"] = [configscore.__dict__ for configscore in configscore_list]
        if valid_metric:
            output_json["valid_metric"] = valid_metric
        if duration:
            output_json["duration"] = duration
        if len(output_json) > 0:
            self.create_local_json_and_upload(output_json, local_file_path)
        if predictions is not None:
            self.create_local_prediction_and_upload(local_file_path, predictions)

    def generate_local_json_path(self):
        """
            return a path string for storing the json file locally
        """
        full_dataset_name = self.jobid.get_jobid_full_data_name()
        jobid_str = self.jobid.to_jobid_string()
        local_file_path = os.path.join(self.root_log_path, full_dataset_name, jobid_str + ".json")
        pathlib.Path(os.path.join(self.root_log_path, full_dataset_name)).mkdir(parents=True, exist_ok=True)
        return local_file_path

    def create_local_json_and_upload(self, result_json, local_file_path):
        with open(local_file_path, "w") as fout:
            fout.write(json.dumps(result_json))
            fout.flush()
            self.upload_local_file_to_azure(local_file_path)

    def create_local_prediction_and_upload(self,
                                           local_json_file,
                                           predictions):
        """
            store predictions (a .zip file) locally and upload
        """
        azure_save_file_name = local_json_file.split("/")[-1][:-5]
        try:
            output_dir = self.console_args.data_root_dir
        except AttributeError:
            print("console_args does not contain data_root_dir, loading the default value")
            from ..utils import load_dft_args
            console_args = load_dft_args()
            output_dir = getattr(console_args, "data_root_dir")
        local_archive_path = self.autohf.output_prediction(predictions,
                                                           output_prediction_path=output_dir + "result/",
                                                           output_zip_file_name=azure_save_file_name)
        self.upload_local_file_to_azure(local_archive_path)

    @staticmethod
    def is_after_earliest_time(this_blob, earliest_time: Tuple[int, int, int]):
        import pytz
        utc = pytz.UTC
        if this_blob.last_modified >= utc.localize(datetime(earliest_time[0], earliest_time[1], earliest_time[2])):
            return True
        return False

    def get_configblob_from_partial_jobid(self,
                                          root_log_path,
                                          partial_jobid,
                                          earliest_time: Tuple[int, int, int] = None):
        """
            get all blobs whose jobid configs match the partial_jobid
        """
        blob_list = []
        container_client = self._init_azure_clients()
        if container_client:
            for each_blob in container_client.list_blobs():
                if each_blob.name.startswith(root_log_path):
                    each_jobconfig = JobID.convert_blobname_to_jobid(each_blob.name)
                    is_append = False
                    if each_jobconfig:
                        if each_jobconfig.is_match(partial_jobid):
                            is_append = True
                        if earliest_time and not AzureUtils.is_after_earliest_time(each_blob, earliest_time):
                            is_append = False
                        if is_append:
                            blob_list.append((each_jobconfig, each_blob))
        return blob_list

    def get_config_and_score_from_partial_jobid(self,
                                                root_log_path: str,
                                                partial_jobid: JobID,
                                                earliest_time: Tuple[int, int, int] = None):
        """
           Extract the config and score list from a partial config id

           Args:
               root_log_path:
                   The root log path in azure blob storage, e.g., "logs_seed/"

               partial_jobid:
                   The partial jobid for matching the blob list

               earliest_time (optional):
                   The earliest starting time for any matched blob, for filtering out out-dated jobs,
                   format: (YYYY, MM, DD)

           Return:
               a ConfigScore list object which stores the config and scores list for each matched blob lists

       """
        assert isinstance(root_log_path, str), "root_log_path must be of type str"
        assert isinstance(partial_jobid, JobID), "partial_jobid must be of type JobID"
        if earliest_time:
            assert isinstance(earliest_time, tuple), "earliest_time must be a tuple of (YYYY, MM, DD)"

        matched_blob_list = self.get_configblob_from_partial_jobid(
            root_log_path,
            partial_jobid,
            earliest_time=earliest_time)
        return self.get_config_and_score_from_matched_blob_list(matched_blob_list,
                                                                earliest_time)

    def get_config_and_score_from_matched_blob_list(self,
                                                    matched_blob_list,
                                                    earliest_time: Tuple[int, int, int] = None):
        """
            Extract the config and score list of one or multiple blobs

            Args:
                matched_blob_list:
                    matched blob list

            Return:
                a ConfigScore list object which stores the config and scores list for each matched blob lists

        """
        matched_config_score_lists = []
        for (each_jobconfig, each_blob) in matched_blob_list:
            self.download_azure_blob(each_blob.name)
            data_json = json.load(open(each_blob.name, "r"))
            each_config_and_score_list = ConfigScoreList(
                jobid_config=each_jobconfig,
                blob_file=each_blob,
                config_score_list=[ConfigScore(**each_dict) for each_dict in data_json['val_log']])
            matched_config_score_lists.append(each_config_and_score_list)
        return matched_config_score_lists
