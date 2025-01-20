
async def eval_self_teaching(fast_learner, evaluator, client, page_log, settings, run_dict):
    """An evaluation"""
    page = page_log.begin_page(
        summary="eval_self_teaching",
        details='',
        method_call="eval_self_teaching")

    num_loops = settings["num_loops"]
    num_final_test_trials = settings["num_final_test_trials"]

    # This eval function needs 2 data strings for each run.
    task_file_1 = run_dict["task_file_1"]  # Train and test on this task.
    task_file_2 = run_dict["task_file_2"]  # Test generalization on a different, similar task.

    # Get the actual task and advice strings from their files.
    task_description_1, expected_answer_1 = evaluator.get_task_description_and_answer_from_file(task_file_1)
    task_description_2, expected_answer_2 = evaluator.get_task_description_and_answer_from_file(task_file_2)

    # Start the test with empty memory.
    fast_learner.reset_memory()

    total_num_successes_1 = 0
    total_num_successes_2 = 0
    total_num_trials = 0
    for i in range(num_loops):
        # Train on the first task.
        await fast_learner.train_on_task(task=task_description_1, expected_answer=expected_answer_1)

        # Test on the first task.
        num_successes, num_trials = await evaluator.test_fast_learner(
            fast_learner=fast_learner, task_description=task_description_1, expected_answer=expected_answer_1,
            num_trials=num_final_test_trials, use_memory=True, client=client, page_log=page_log)
        page.add_lines("Task 1 success rate:  {}%".format(round((num_successes / num_trials) * 100)), flush=True)
        total_num_successes_1 += num_successes

        # Test on the second task.
        num_successes, num_trials = await evaluator.test_fast_learner(
            fast_learner=fast_learner, task_description=task_description_2, expected_answer=expected_answer_2,
            num_trials=num_final_test_trials, use_memory=True, client=client, page_log=page_log)
        page.add_lines("Task 2 success rate:  {}%".format(round((num_successes / num_trials) * 100)), flush=True)
        total_num_successes_2 += num_successes

        total_num_trials += num_final_test_trials
        page.add_lines("")

    overall_success_rate_1 = round((total_num_successes_1 / total_num_trials) * 100)
    overall_success_rate_2 = round((total_num_successes_2 / total_num_trials) * 100)
    page.add_lines("\nOverall task 1 success rate (1):  {}%".format(overall_success_rate_1), flush=True)
    page.add_lines("Overall task 2 success rate (2):  {}%".format(overall_success_rate_2), flush=True)

    page_log.finish_page(page)
