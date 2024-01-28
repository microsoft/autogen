import datasets


def get_dataset_from_task(task, data_path) -> datasets.Dataset:
    if task == "math":
        return datasets.load_dataset("json", data_files={
            'test': f"{data_path}/MATH/test.jsonl",
        })
    elif task == "ml-bench":
        pass
    elif task == "sci-bench":
        pass
    else:
        raise ValueError("Unknown task: {}".format(task))