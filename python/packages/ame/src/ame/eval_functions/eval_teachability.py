from autogen_ext.apprentice import PageLog, Grader


async def eval_teachability(fast_learner, evaluator, client, page_log, settings, run_dict):
    """An evaluation"""
    page = page_log.begin_page(
        summary="eval_teachability",
        details='',
        method_call="eval_teachability")

    # This eval function needs 2 data strings for each run.
    task_file = run_dict["task_file"]  # The task being tested.
    advice_file = run_dict["advice_file"]  # Advice for solving such tasks.

    # Get the actual task and advice strings from their files.
    task_description, expected_answer = evaluator.get_task_description_and_answer_from_file(task_file)
    advice = evaluator.get_advice_from_file(advice_file)

    # First test without memory.
    fast_learner.reset_memory()
    page.add_lines("\nClear memory, then ask the question.")
    response = await fast_learner.handle_user_message(task_description)

    # Check the response.
    grader = Grader(client, page_log)
    response_is_correct, extracted_answer = await grader.is_response_correct(task_description, response, expected_answer)
    page.add_lines("Extracted answer:  {}".format(extracted_answer), flush=True)
    if response_is_correct:
        page.add_lines("Answer is CORRECT.\n", flush=True)
    else:
        page.add_lines("Answer is INCORRECT.\n", flush=True)

    # Give advice that should help solve this task.
    page.add_lines("Give the advice.")
    await fast_learner.handle_user_message(advice)

    # Now ask the question again to see if the advice helps.
    page.add_lines("\nAsk the question again to see if the advice helps.")
    response = await fast_learner.handle_user_message(task_description)

    # Check the response.
    response_is_correct, extracted_answer = await grader.is_response_correct(task_description, response, expected_answer)
    page.add_lines("Extracted answer:  {}".format(extracted_answer), flush=True)
    if response_is_correct:
        page.add_lines("Answer is CORRECT.\n", flush=True)
    else:
        page.add_lines("Answer is INCORRECT.\n", flush=True)

    page_log.finish_page(page)
