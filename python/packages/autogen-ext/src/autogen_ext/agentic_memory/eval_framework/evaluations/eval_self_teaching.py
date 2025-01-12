
async def eval_self_teaching(fast_learner, evaluator, client, page_log, settings):
    """An evaluation"""
    page = page_log.begin_page(
        summary="eval_self_teaching",
        details='',
        method_call="eval_self_teaching")

    # Start the test with empty memory.
    fast_learner.reset_memory()

    task_details_list = [
        evaluator.get_task_details_by_name("10_liars"),
        evaluator.get_task_details_by_name("100_vampires")]
    total_num_successes_list = [0 for _ in range(len(task_details_list))]
    total_num_trials = 0
    for i in range(settings["num_loops"]):
        # Train on the first task in the list.
        task_details = task_details_list[0]
        await fast_learner.train_on_task(task=task_details["task_description"],
                                         expected_answer=task_details["expected_answer"])

        # Test on all tasks in the list.
        for j, task_details in enumerate(task_details_list):
            num_successes, num_trials = await evaluator.test_fast_learner(
                fast_learner=fast_learner, task_details=task_details, num_trials=settings["num_final_test_trials"],
                use_memory=True, client=client, page_log=page_log)

            page.add_lines("Success rate ({}):  {}%".format(j, round((num_successes / num_trials) * 100)), flush=True)
            total_num_successes_list[j] += num_successes
        total_num_trials += settings["num_final_test_trials"]
        page.add_lines("")

    for i, total_num_successes in enumerate(total_num_successes_list):
        success_rate = round((total_num_successes / total_num_trials) * 100)
        page.add_lines("\nOverall success rate ({}):  {}%\n".format(i, success_rate), flush=True)

    page_log.finish_page(page)
