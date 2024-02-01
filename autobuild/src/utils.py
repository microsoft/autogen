import datasets


def get_dataset_from_scene(scene, data_path) -> datasets.Dataset:
    if scene == "math":
        return datasets.load_dataset("json", data_files={
            'test': f"{data_path}/MATH/test.jsonl",
        })
    elif scene == "coding":
        pass
    elif scene == "tabular":
        return datasets.load_dataset("json", data_files={
            'test': f"{data_path}/SciBench/q_selected_balanced.jsonl",
        })
    else:
        raise ValueError("Unknown scene: {}".format(scene))