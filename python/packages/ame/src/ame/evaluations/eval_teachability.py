from autogen_ext.apprentice import PageLog, Grader


async def eval_teachability(fast_learner, evaluator, client, page_log, settings):
    """An evaluation"""
    page = page_log.begin_page(
        summary="eval_teachability",
        details='',
        method_call="eval_teachability")

    task_details = evaluator.get_task_details_by_name("autogen_package")
    task_description = task_details["task_description"]
    answer = task_details["expected_answer"]
    grader = Grader(client, page_log)

    # First test without memory.
    fast_learner.reset_memory()
    page.add_lines("\nClear memory, then ask the question.")
    response = await fast_learner.handle_user_message(task_description)

    # Check the response.
    response_is_correct, extracted_answer = await grader.is_response_correct(task_description, response, answer)
    page.add_lines("Extracted answer:  {}".format(extracted_answer), flush=True)
    if response_is_correct:
        page.add_lines("Answer is CORRECT.\n", flush=True)
    else:
        page.add_lines("Answer is INCORRECT.\n", flush=True)

    # Give advice that should help solve this task.
    page.add_lines("Give the advice.")
    advice = "When somebody builds something on autogen and wants to contribute it to autogen, instead of creating a new autogen package, it's better for them to implement it in a separate github repo, then just add the autogen-extension topic to that repo. That way their contribution will be automatically discoverable through autogen's page on community extensions:  https://microsoft.github.io/autogen/dev/user-guide/extensions-user-guide/index.html"
    await fast_learner.handle_user_message(advice)

    # Now ask the question again to see if the advice helps.
    page.add_lines("\nAsk the question again to see if the advice helps.")
    response = await fast_learner.handle_user_message(task_description)

    # Check the response.
    response_is_correct, extracted_answer = await grader.is_response_correct(task_description, response, answer)
    page.add_lines("Extracted answer:  {}".format(extracted_answer), flush=True)
    if response_is_correct:
        page.add_lines("Answer is CORRECT.\n", flush=True)
    else:
        page.add_lines("Answer is INCORRECT.\n", flush=True)

    page_log.finish_page(page)
