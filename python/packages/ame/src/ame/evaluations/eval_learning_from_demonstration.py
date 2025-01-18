
async def eval_learning_from_demonstration(fast_learner, evaluator, client, page_log, settings):
    """An evaluation"""
    page = page_log.begin_page(
        summary="eval_learning_from_demonstration",
        details='',
        method_call="eval_learning_from_demonstration")

    task_details = evaluator.get_task_details_by_name("cell_towers")
    num_trials = settings["num_trials"]

    # Start by clearing memory then running a baseline test.
    page.add_lines("To get a baseline, clear memory, then assign the task.")
    fast_learner.reset_memory()
    num_successes, num_trials = await evaluator.test_fast_learner(
        fast_learner=fast_learner, task_details=task_details, num_trials=num_trials,
        use_memory=True, client=client, page_log=page_log)
    success_rate = round((num_successes / num_trials) * 100)
    page.add_lines("\nSuccess rate:  {}%\n".format(success_rate), flush=True)

    # Provide the demonstration.
    page.add_lines("Demonstrate a solution to a similar task.")
    demo_task = "You are a telecommunications engineer who wants to build cell phone towers on a stretch of road. Houses are located at mile markers 17, 20, 19, 10, 11, 12, 3, 6. Each cell phone tower can cover houses located next to the road within a 4-mile radius. Find the minimum number of cell phone towers needed to cover all houses next to the road. Your answer should be a positive numerical integer value."
    demonstration = "Sort the houses by location:  3, 6, 10, 11, 12, 17, 19, 20. Then start at one end and place the towers only where absolutely needed. The house at 3 could be served by a tower as far away as mile marker 7, because 3 + 4 = 7, so place a tower at 7. This obviously covers houses up to mile 7. But a coverage radius of 4 miles (in each direction) means a total coverage of 8 miles. So the tower at mile 7 would reach all the way to mile 11, covering the houses at 10 and 11. The next uncovered house would be at mile 12 (not 10), requiring a second tower. It could go at mile 16 (which is 12 + 4) and this tower would reach up to mile 20 (16 + 4), covering the remaining houses. So 2 towers would be enough."
    await fast_learner.learn_from_demonstration(demo_task, demonstration)

    # Now test again to see if the demonstration (retrieved from memory) helps.
    page.add_lines("Assign the task again to see if the demonstration helps.")
    num_successes, num_trials = await evaluator.test_fast_learner(
        fast_learner=fast_learner, task_details=task_details, num_trials=num_trials,
        use_memory=True, client=client, page_log=page_log)
    success_rate = round((num_successes / num_trials) * 100)
    page.add_lines("\nSuccess rate:  {}%\n".format(success_rate), flush=True)

    page_log.finish_page(page)
