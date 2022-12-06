def test_load_args_sub():
    from flaml.automl.nlp.huggingface.training_args import TrainingArgumentsForAuto

    TrainingArgumentsForAuto.load_args_from_console()


if __name__ == "__main__":
    test_load_args_sub()
