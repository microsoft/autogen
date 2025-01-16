
async def eval_without_learning(fast_learner, evaluator, client, page_log, settings):
    """An evaluation"""
    page = page_log.begin_page(
        summary="eval_without_learning",
        details='',
        method_call="eval_without_learning")

    task_details = evaluator.get_task_details_by_name(settings["task_name"])
    num_trials = settings["num_trials"]

    # Clear memory then run a baseline test.
    page.add_lines("To get a baseline, clear memory, then assign the task.")
    fast_learner.reset_memory()
    num_successes, num_trials = await evaluator.test_fast_learner(
        fast_learner=fast_learner, task_details=task_details, num_trials=num_trials,
        use_memory=True, client=client, page_log=page_log)
    success_rate = round((num_successes / num_trials) * 100)
    page.add_lines("\nSuccess rate:  {}%\n".format(success_rate), flush=True)

    page_log.finish_page(page)
