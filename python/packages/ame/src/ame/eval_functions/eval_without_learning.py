
async def eval_without_learning(fast_learner, evaluator, client, logger, settings, run_dict):
    """An evaluation"""
    logger.enter_function()

    num_trials = settings["num_trials"]

    # Get the task and advice strings.
    task_file = run_dict["task_file"]
    task_description, expected_answer = evaluator.get_task_description_and_answer_from_file(task_file)

    # Clear memory then run a baseline test.
    logger.info("To get a baseline, clear memory, then assign the task.")
    fast_learner.reset_memory()
    num_successes, num_trials = await evaluator.test_fast_learner(
        fast_learner=fast_learner, task_description=task_description, expected_answer=expected_answer,
        num_trials=num_trials, use_memory=True, client=client, logger=logger)
    success_rate = round((num_successes / num_trials) * 100)
    logger.info("\nSuccess rate:  {}%\n".format(success_rate), flush=True)

    logger.leave_function()
