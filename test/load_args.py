def test_load_args_sub():
    from flaml.nlp.utils import TrainingArgumentsForAuto

    TrainingArgumentsForAuto.load_args_from_console()


if __name__ == "__main__":
    test_load_args_sub()
