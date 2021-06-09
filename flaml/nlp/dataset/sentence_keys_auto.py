sentence_keys_glue = {
    "cola": ["sentence"],
    "mnli": ["premise", "hypothesis"],
    "mrpc": ["sentence1", "sentence2"],
    "qnli": ["sentence", "question"],
    "qqp": ["question1", "question2"],
    "rte": ["sentence1", "sentence2"],
    "sst2": ["sentence"],
    "stsb": ["sentence1", "sentence2"],
    "wnli": ["sentence1", "sentence2"]
}

sentence_keys_super_glue = {
    "rte": ["hypothesis", "premise"],
    "wic": ["sentence1", "sentence2"],
    "wsc": ["text"]
}


def get_sentence_keys(dataset_name, subdataset_name=None):
    eval_name_mapping = globals()["sentence_keys_" + dataset_name]
    if isinstance(eval_name_mapping, dict):
        assert subdataset_name and subdataset_name in eval_name_mapping, \
            "dataset_name and subdataset_name not correctly specified"
        sentence_keys = eval_name_mapping[subdataset_name]
    else:
        sentence_keys = eval_name_mapping
    return sentence_keys
