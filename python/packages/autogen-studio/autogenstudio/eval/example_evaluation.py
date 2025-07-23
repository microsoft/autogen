"""
Comprehensive evaluation examples for AutoGen Studio.

This file demonstrates how to use the evaluation system to:
1. Run simple evaluations with different runners
2. Use the orchestrator for managing complex evaluation workflows
3. Judge results with multiple criteria
4. Test serialization and deserialization

Usage:
    python example_evaluation.py
    
Note: Requires OPENAI_API_KEY environment variable to be set.
"""

import asyncio
from datetime import datetime

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_core import ComponentModel
from autogen_core.models import UserMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient

# Import the evaluation components
from autogenstudio.datamodel.eval import EvalJudgeCriteria, EvalRunResult, EvalRunStatus, EvalScore, EvalTask
from autogenstudio.eval import EvalOrchestrator, LLMEvalJudge, ModelEvalRunner, TeamEvalRunner


async def run_simple_evaluation():
    """Run a simple evaluation of model and team responses."""
    
    print("\n=== Simple Evaluation Example ===\n")

    # Step 1: Create a model client
    model_client = OpenAIChatCompletionClient(
        model="gpt-4o-mini",
        # api_key is loaded from environment variable OPENAI_API_KEY
    )

    # Step 2: Create evaluation tasks
    tasks = [
        EvalTask(
            name="Eiffel Tower Height",
            description="Answer the question about the Eiffel Tower height",
            input="What is the height of the Eiffel Tower?",
        ),
        EvalTask(
            name="Lake Tanganyika Depth",
            description="Answer the question about Lake Tanganyika's depth",
            input="What is the depth of Lake Tanganyika?",
        ),
    ]

    # Step 3: Create evaluation runners

    # 3.1: Model runner (direct model access)
    model_runner = ModelEvalRunner(
        model_client=model_client,
        name="Direct Model Runner",
        description="Evaluates tasks by sending them directly to the model",
    )

    # 3.2: Team runner (using a simple team with one agent)
    # Create an assistant agent for the team
    agent = AssistantAgent(
        name="research_agent", 
        model_client=model_client, 
        system_message="You are a helpful assistant"
    )

    # Create a team with the agent
    team = RoundRobinGroupChat(participants=[agent], max_turns=3)

    # Create a team runner with the team
    team_runner = TeamEvalRunner(
        team=team, 
        name="Team Runner", 
        description="Evaluates tasks using a team of agents"
    )

    # Step 4: Create an LLM judge
    # We use the same model client for simplicity
    judge = LLMEvalJudge(
        model_client=model_client, 
        name="Evaluation Judge", 
        description="Judges the quality of responses"
    )

    # Step 5: Define evaluation criteria
    criteria = [
        EvalJudgeCriteria(
            dimension="accuracy",
            prompt="Evaluate the factual accuracy of the response. Are all facts correct?",
            min_value=0,
            max_value=10,
        ),
        EvalJudgeCriteria(
            dimension="completeness",
            prompt="Evaluate how thoroughly the response addresses the question. Does it provide all relevant information?",
            min_value=0,
            max_value=10,
        ),
    ]

    # Step 6: Run evaluations and judge the results
    print("=== Running Evaluations ===\n")

    # Run model evaluations (batch processing!)
    print("Running model evaluations...")
    print(f"  Evaluating {len(tasks)} tasks in parallel...")
    model_task_results = await model_runner.run(tasks)
    
    model_results = {}
    for task, model_result in zip(tasks, model_task_results):
        model_results[task.task_id] = model_result
        
        # Print model response
        if model_result.status:
            messages = model_result.result.messages if model_result.result else []
            if messages:
                content = getattr(messages[0], 'content', 'No content')
                print(f"  {task.name}: {str(content)[:100]}...")
        else:
            print(f"  {task.name} error: {model_result.error}")

    # Run team evaluations (batch processing!)
    print("\nRunning team evaluations...")
    print(f"  Evaluating {len(tasks)} tasks with isolated teams...")
    team_task_results = await team_runner.run(tasks)
    
    team_results = {}
    for task, team_result in zip(tasks, team_task_results):
        team_results[task.task_id] = team_result
        
        # Print team response
        if team_result.status:
            messages = team_result.result.messages or []
            final_message = messages[-1] if messages else None
            if final_message and hasattr(final_message, 'content'):
                print(f"  {task.name}: {final_message.content[:100]}...")
            else:
                print(f"  {task.name}: No response from team")
        else:
            print(f"  {task.name} error: {team_result.error}")

    # Judge the results
    print("\n=== Judging Results ===\n")

    # Judge model results
    print("Judging model results...")
    model_scores = {}
    for task in tasks:
        if task.task_id in model_results and model_results[task.task_id].status:
            print(f"  Judging task: {task.name}")
            model_score = await judge.judge(task, model_results[task.task_id], criteria)
            model_scores[task.task_id] = model_score

            # Print scores
            print(f"  Overall score: {model_score.overall_score}")
            for dimension_score in model_score.dimension_scores:
                print(f"    {dimension_score.dimension}: {dimension_score.score} - {dimension_score.reason[:50]}...")

    # Judge team results
    print("\nJudging team results...")
    team_scores = {}
    for task in tasks:
        if task.task_id in team_results and team_results[task.task_id].status:
            print(f"  Judging task: {task.name}")
            team_score = await judge.judge(task, team_results[task.task_id], criteria)
            team_scores[task.task_id] = team_score

            # Print scores
            print(f"  Overall score: {team_score.overall_score}")
            for dimension_score in team_score.dimension_scores:
                print(f"    {dimension_score.dimension}: {dimension_score.score} - {dimension_score.reason[:50]}...")

    # Step 7: Test serialization and deserialization
    print("\n=== Testing Serialization and Deserialization ===\n")

    # Serialize model runner
    model_runner_config = model_runner.dump_component()
    print(f"Serialized model runner config created successfully")

    # Deserialize model runner
    deserialized_model_runner = ModelEvalRunner.load_component(model_runner_config)
    print(f"Deserialized model runner: {deserialized_model_runner.name}")

    # Serialize judge
    judge_config = judge.dump_component()
    print(f"Serialized judge config created successfully")

    # Deserialize judge
    deserialized_judge = LLMEvalJudge.load_component(judge_config)
    print(f"Deserialized judge: {deserialized_judge.name}")

    # Close the model client
    await model_client.close()

    return {
        "model_results": model_results,
        "team_results": team_results,
        "model_scores": model_scores,
        "team_scores": team_scores,
    }


async def run_orchestrated_evaluation():
    """Run a comprehensive evaluation using the EvalOrchestrator."""
    
    print("\n=== Orchestrated Evaluation Example ===\n")

    # Step 1: Create a model client
    model_client = OpenAIChatCompletionClient(
        model="gpt-4o-mini",
        # api_key is loaded from environment variable OPENAI_API_KEY
    )

    # Step 2: Create an orchestrator (without DB for this example)
    orchestrator = EvalOrchestrator()

    # Step 3: Create and register tasks
    task_ids = []
    tasks = [
        EvalTask(
            name="Eiffel Tower Height",
            description="Answer the question about the Eiffel Tower height",
            input="What is the height of the Eiffel Tower?",
        ),
        EvalTask(
            name="Lake Tanganyika Depth",
            description="Answer the question about Lake Tanganyika's depth",
            input="What is the depth of Lake Tanganyika?",
        ),
    ]

    print("Creating tasks...")
    for task in tasks:
        task_id = await orchestrator.create_task(task)
        task_ids.append(task_id)
        print(f"  Created task: {task.name} (ID: {task_id})")

    # Step 4: Create and register criteria
    criteria_ids = []
    criteria = [
        EvalJudgeCriteria(
            dimension="accuracy",
            prompt="Evaluate the factual accuracy of the response. Are all facts correct?",
            min_value=0,
            max_value=10,
        ),
        EvalJudgeCriteria(
            dimension="completeness",
            prompt="Evaluate how thoroughly the response addresses the question. Does it provide all relevant information?",
            min_value=0,
            max_value=10,
        ),
    ]

    print("\nCreating criteria...")
    for criterion in criteria:
        criterion_id = await orchestrator.create_criteria(criterion)
        criteria_ids.append(criterion_id)
        print(f"  Created criteria: {criterion.dimension} (ID: {criterion_id})")

    # Step 5: Create runners
    # Model runner
    model_runner = ModelEvalRunner(
        model_client=model_client,
        name="Direct Model Runner",
        description="Evaluates tasks by sending them directly to the model",
    )

    # Team runner
    agent = AssistantAgent(
        name="research_agent", 
        model_client=model_client, 
        system_message="You are a helpful assistant"
    )
    team = RoundRobinGroupChat(participants=[agent], max_turns=3)
    team_runner = TeamEvalRunner(
        team=team, 
        name="Team Runner", 
        description="Evaluates tasks using a team of agents"
    )

    # Step 6: Create a judge
    judge = LLMEvalJudge(
        model_client=model_client, 
        name="Evaluation Judge", 
        description="Judges the quality of responses"
    )

    # Step 7: Create evaluation runs
    model_run_ids = []
    team_run_ids = []

    print("\nCreating evaluation runs...")
    
    # Create model runs
    for i, task_id in enumerate(task_ids):
        run_id = await orchestrator.create_run(
            task=task_id, 
            runner=model_runner, 
            judge=judge, 
            criteria=criteria_ids, 
            name=f"Model Run - Task {i+1}"
        )
        model_run_ids.append(run_id)
        print(f"  Created model run: {run_id}")

    # Create team runs
    for i, task_id in enumerate(task_ids):
        run_id = await orchestrator.create_run(
            task=task_id, 
            runner=team_runner, 
            judge=judge, 
            criteria=criteria_ids, 
            name=f"Team Run - Task {i+1}"
        )
        team_run_ids.append(run_id)
        print(f"  Created team run: {run_id}")

    # Step 8: Execute the runs
    print("\n=== Starting Evaluation Runs ===\n")

    # Start model runs
    print("Starting model runs...")
    for run_id in model_run_ids:
        await orchestrator.start_run(run_id)
        print(f"  Started run: {run_id}")

    # Start team runs
    print("\nStarting team runs...")
    for run_id in team_run_ids:
        await orchestrator.start_run(run_id)
        print(f"  Started run: {run_id}")

    # Step 9: Wait for runs to complete
    print("\n=== Waiting for Runs to Complete ===\n")

    all_runs = model_run_ids + team_run_ids
    completed = {run_id: False for run_id in all_runs}

    while not all(completed.values()):
        for run_id in all_runs:
            if not completed[run_id]:
                status = await orchestrator.get_run_status(run_id)
                if status in [EvalRunStatus.COMPLETED, EvalRunStatus.FAILED, EvalRunStatus.CANCELED]:
                    completed[run_id] = True
                    print(f"Run {run_id} completed with status: {status}")

        await asyncio.sleep(1)

    # Step 10: Get results
    print("\n=== Evaluation Results ===\n")

    # Model results
    print("Model run results:")
    for i, run_id in enumerate(model_run_ids):
        run_result = await orchestrator.get_run_result(run_id)
        score_result = await orchestrator.get_run_score(run_id)

        print(f"\nModel Run {i+1} (ID: {run_id}):")
        if run_result and run_result.status:
            messages = run_result.result.messages if run_result.result else []
            if messages:
                content = getattr(messages[0], 'content', 'No content')
                print(f"  Response: {str(content)[:100]}...")

            if score_result:
                print(f"  Overall score: {score_result.overall_score}")
                for dimension_score in score_result.dimension_scores:
                    print(f"    {dimension_score.dimension}: {dimension_score.score}")
                    print(f"    Reason: {dimension_score.reason[:100]}...")
        else:
            print(f"  Error: {run_result.error if run_result else 'No result'}")

    # Team results
    print("\nTeam run results:")
    for i, run_id in enumerate(team_run_ids):
        run_result = await orchestrator.get_run_result(run_id)
        score_result = await orchestrator.get_run_score(run_id)

        print(f"\nTeam Run {i+1} (ID: {run_id}):")
        if run_result and run_result.status:
            messages = run_result.result.messages or []
            final_message = messages[-1] if messages else None
            if final_message and hasattr(final_message, 'content'):
                print(f"  Response: {final_message.content[:100]}...")

            if score_result:
                print(f"  Overall score: {score_result.overall_score}")
                for dimension_score in score_result.dimension_scores:
                    print(f"    {dimension_score.dimension}: {dimension_score.score}")
                    print(f"    Reason: {dimension_score.reason[:100]}...")
        else:
            print(f"  Error: {run_result.error if run_result else 'No result'}")

    # Step 11: Demonstrate tabulated results
    print("\n=== Tabulated Results ===\n")
    
    all_run_ids = model_run_ids + team_run_ids
    tabulated_results = await orchestrator.tabulate_results(all_run_ids, include_reasons=True)
    
    print(f"Dimensions: {tabulated_results['dimensions']}")
    print(f"Number of runs: {len(tabulated_results['runs'])}")
    
    for run_entry in tabulated_results['runs']:
        print(f"\nRun: {run_entry['name']} ({run_entry['runner_type']})")
        print(f"  Task: {run_entry['task_name']}")
        print(f"  Overall Score: {run_entry['overall_score']}")
        print(f"  Dimension Scores: {run_entry['scores']}")

    # Close the model client
    await model_client.close()

    return {
        "task_ids": task_ids,
        "criteria_ids": criteria_ids,
        "model_run_ids": model_run_ids,
        "team_run_ids": team_run_ids,
        "tabulated_results": tabulated_results,
    }


async def main():
    """Run all evaluation examples."""
    print("🚀 AutoGen Studio Evaluation Examples")
    print("=" * 50)
    
    try:
        # Run simple evaluation
        simple_results = await run_simple_evaluation()
        print(f"\n✅ Simple evaluation completed with {len(simple_results['model_results'])} model results")
        
        # Run orchestrated evaluation  
        orchestrated_results = await run_orchestrated_evaluation()
        print(f"\n✅ Orchestrated evaluation completed with {len(orchestrated_results['model_run_ids'])} model runs and {len(orchestrated_results['team_run_ids'])} team runs")
        
        print("\n🎉 All evaluation examples completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error running evaluations: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())