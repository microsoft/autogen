def test_config_constraint():
    from flaml import tune

    # Test dict return value
    def evaluate_config_dict(config):
        metric = (round(config["x"]) - 85000) ** 2 - config["x"] / config["y"]
        return {"metric": metric}

    def config_constraint(config):
        if config["y"] >= config["x"]:
            return 1
        else:
            return 0

    analysis = tune.run(
        evaluate_config_dict,
        config={
            "x": tune.qloguniform(lower=1, upper=100000, q=1),
            "y": tune.qrandint(lower=2, upper=100000, q=2),
        },
        config_constraints=[(config_constraint, "<", 0.5)],
        metric="metric",
        mode="max",
        num_samples=100,
        log_file_name="logs/config_constraint.log",
    )

    assert analysis.best_config["x"] > analysis.best_config["y"]
    assert analysis.trials[0].config["x"] > analysis.trials[0].config["y"]
