import os
import shutil
from collections import OrderedDict

file_name_mapping_glue = {
    "ax": ["AX.tsv"],
    "cola": ["CoLA.tsv"],
    "mnli": ["MNLI-m.tsv", "MNLI-mm.tsv"],
    "mrpc": ["MRPC.tsv"],
    "qnli": ["QNLI.tsv"],
    "qqp": ["QQP.tsv"],
    "rte": ["RTE.tsv"],
    "sst2": ["SST-2.tsv"],
    "stsb": ["STS-B.tsv"],
    "wnli": ["WNLI.tsv"]
}

default_prediction_glue = {
    "ax": ["entailment"],
    "cola": ["0"],
    "mnli": ["neutral", "neutral"],
    "mrpc": ["0"],
    "qnli": ["not_entailment"],
    "qqp": ["0"],
    "rte": ["not_entailment"],
    "sst2": ["0"],
    "stsb": ["0.0"],
    "wnli": ["0"]
}

test_size_glue = {
    "ax": [1104],
    "cola": [1064],
    "mnli": [9796, 9847],
    "mrpc": [1725],
    "qnli": [5463],
    "qqp": [390965],
    "rte": [3000],
    "sst2": [1821],
    "stsb": [1379],
    "wnli": [146]
}


def output_prediction_glue(output_path, zip_file_name, predictions, train_data, dev_name, subdataset_name):
    output_dir = os.path.join(output_path, zip_file_name)
    if os.path.exists(output_dir):
        assert os.path.isdir(output_dir)
    else:
        import pathlib
        pathlib.Path(output_dir).mkdir(parents=True, exist_ok=True)
    if subdataset_name != "stsb":
        label_list = train_data.features["label"].names

    output_blank_tsv(output_dir)
    for each_subdataset_name in file_name_mapping_glue.keys():
        for idx in range(len(file_name_mapping_glue[each_subdataset_name])):
            each_file = file_name_mapping_glue[each_subdataset_name][idx]
            if subdataset_name != "mnli":
                is_match = subdataset_name == each_subdataset_name
            else:
                if dev_name == "validation_matched":
                    is_match = each_file == "MNLI-m.tsv"
                else:
                    is_match = each_file == "MNLI-mm.tsv"
            if is_match:
                with open(os.path.join(output_dir, each_file), "w") as writer:
                    writer.write("index\tprediction\n")
                    for index, item in enumerate(predictions):
                        if subdataset_name == "stsb":
                            if item > 5.0:
                                item = 5.0
                            writer.write(f"{index}\t{item:3.3f}\n")
                        else:
                            if subdataset_name in ("rte", "qnli", "mnli"):
                                item = label_list[item]
                                writer.write(f"{index}\t{item}\n")
                            else:
                                if int(item) == item:
                                    item = int(item)
                                    writer.write(f"{index}\t{item}\n")
                                else:
                                    writer.write(f"{index}\t{item:3.3f}\n")

    shutil.make_archive(os.path.join(output_path, zip_file_name), 'zip', output_dir)
    return os.path.join(output_path, zip_file_name + ".zip")


OUTPUT_PREDICTION_MAPPING = OrderedDict(
    [
        ("glue", output_prediction_glue),
    ]
)


def auto_output_prediction(dataset_name_list: list,
                           output_path,
                           zip_file_name,
                           predictions,
                           train_data,
                           dev_name,
                           subset_name):
    from ..result_analysis.azure_utils import JobID
    dataset_name = JobID.dataset_list_to_str(dataset_name_list)
    if dataset_name in OUTPUT_PREDICTION_MAPPING.keys():
        return OUTPUT_PREDICTION_MAPPING[dataset_name](output_path,
                                                       zip_file_name,
                                                       predictions,
                                                       train_data,
                                                       dev_name,
                                                       subset_name)
    else:
        raise ValueError(
            "Unrecognized dataset {}. \n"
            "Should be one of {}.".format(dataset_name, ", ".join(c.__name__ for c in OUTPUT_PREDICTION_MAPPING.keys())
                                          )
        )


def output_blank_tsv(output_dir):
    for each_subdataset_name in file_name_mapping_glue.keys():
        for idx in range(len(file_name_mapping_glue[each_subdataset_name])):
            each_file = file_name_mapping_glue[each_subdataset_name][idx]
            default_prediction = default_prediction_glue[each_subdataset_name][idx]
            test_size = test_size_glue[each_subdataset_name][idx]
            with open(os.path.join(output_dir, each_file), "w") as writer:
                writer.write("index\tprediction\n")
                for index in range(test_size):
                    writer.write(f"{index}\t{default_prediction}\n")
