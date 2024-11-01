from magentic_one_helper import MagenticOneHelper
import asyncio
import json
import argparse
import os


async def main(task, logs_dir):
    magnetic_one = MagenticOneHelper(logs_dir=logs_dir)
    await magnetic_one.initialize()
    print("MagenticOne initialized.")

    # Create task and log streaming tasks
    task_future = asyncio.create_task(magnetic_one.run_task(task))
    final_answer = None

    # Stream and process logs
    async for log_entry in magnetic_one.stream_logs():
        print(json.dumps(log_entry, indent=2))

    # Wait for task to complete
    await task_future

    # Get the final answer
    final_answer = magnetic_one.get_final_answer()

    if final_answer is not None:
        print(f"Final answer: {final_answer}")
    else:
        print("No final answer found in logs.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a task with MagenticOneHelper.")
    parser.add_argument("task", type=str, help="The task to run")
    parser.add_argument("--logs_dir", type=str, default="./logs", help="Directory to store logs")
    args = parser.parse_args()
    if not os.path.exists(args.logs_dir):
        os.makedirs(args.logs_dir)
    asyncio.run(main(args.task, args.logs_dir))
