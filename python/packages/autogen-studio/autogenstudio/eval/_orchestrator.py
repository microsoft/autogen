import asyncio
import uuid
from datetime import datetime
from pdb import run
from typing import Any, Dict, List, Optional, TypedDict, Union

from loguru import logger
from pydantic import BaseModel

from ..database.db_manager import DatabaseManager
from ..datamodel.db import EvalCriteriaDB, EvalRunDB, EvalTaskDB
from ..datamodel.eval import EvalJudgeCriteria, EvalRunResult, EvalRunStatus, EvalScore, EvalTask
from .judges import BaseEvalJudge
from .runners import BaseEvalRunner


class DimensionScore(TypedDict):
    score: Optional[float]
    reason: Optional[str]


class RunEntry(TypedDict):
    id: str
    name: str
    task_name: str
    runner_type: str
    overall_score: Optional[float]
    scores: List[Optional[float]]
    reasons: Optional[List[Optional[str]]]


class TabulatedResults(TypedDict):
    dimensions: List[str]
    runs: List[RunEntry]


class EvalOrchestrator:
    """
    Orchestrator for evaluation runs.

    This class manages the lifecycle of evaluation tasks, criteria, and runs.
    It can operate with or without a database manager for persistence.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        Initialize the orchestrator.

        Args:
            db_manager: Optional database manager for persistence.
                        If None, data is stored in memory only.
        """
        self._db_manager = db_manager

        # In-memory storage (used when db_manager is None)
        self._tasks: Dict[str, EvalTask] = {}
        self._criteria: Dict[str, EvalJudgeCriteria] = {}
        self._runs: Dict[str, Dict[str, Any]] = {}

        # Active runs tracking
        self._active_runs: Dict[str, asyncio.Task] = {}

    # ----- Task Management -----

    async def create_task(self, task: EvalTask) -> str:
        """
        Create a new evaluation task.

        Args:
            task: The evaluation task to create

        Returns:
            Task ID
        """
        if not task.task_id:
            task.task_id = str(uuid.uuid4())

        if self._db_manager:
            # Store in database
            task_db = EvalTaskDB(name=task.name, description=task.description, config=task)
            response = self._db_manager.upsert(task_db)
            if not response.status:
                logger.error(f"Failed to store task: {response.message}")
                raise RuntimeError(f"Failed to store task: {response.message}")
            task_id = str(response.data.get("id")) if response.data else str(task.task_id)
        else:
            # Store in memory
            task_id = str(task.task_id)
            self._tasks[task_id] = task

        return task_id

    async def get_task(self, task_id: str) -> Optional[EvalTask]:
        """
        Retrieve an evaluation task by ID.

        Args:
            task_id: The ID of the task to retrieve

        Returns:
            The task if found, None otherwise
        """
        if self._db_manager:
            # Retrieve from database
            response = self._db_manager.get(EvalTaskDB, filters={"id": int(task_id) if task_id.isdigit() else task_id})

            if response.status and response.data and len(response.data) > 0:
                task_data = response.data[0]
                return (
                    task_data.get("config")
                    if isinstance(task_data.get("config"), EvalTask)
                    else EvalTask.model_validate(task_data.get("config"))
                )
        else:
            # Retrieve from memory
            return self._tasks.get(task_id)

        return None

    async def list_tasks(self) -> List[EvalTask]:
        """
        List all available evaluation tasks.

        Returns:
            List of evaluation tasks
        """
        if self._db_manager:
            # Retrieve from database
            response = self._db_manager.get(EvalTaskDB)

            tasks = []
            if response.status and response.data:
                for task_data in response.data:
                    config = task_data.get("config")
                    if config:
                        if isinstance(config, EvalTask):
                            tasks.append(config)
                        else:
                            tasks.append(EvalTask.model_validate(config))
            return tasks
        else:
            # Retrieve from memory
            return list(self._tasks.values())

    # ----- Criteria Management -----

    async def create_criteria(self, criteria: EvalJudgeCriteria) -> str:
        """
        Create new evaluation criteria.

        Args:
            criteria: The evaluation criteria to create

        Returns:
            Criteria ID
        """
        criteria_id = str(uuid.uuid4())

        if self._db_manager:
            # Store in database
            criteria_db = EvalCriteriaDB(name=criteria.dimension, description=criteria.prompt, config=criteria)
            response = self._db_manager.upsert(criteria_db)
            if not response.status:
                logger.error(f"Failed to store criteria: {response.message}")
                raise RuntimeError(f"Failed to store criteria: {response.message}")
            criteria_id = str(response.data.get("id")) if response.data else criteria_id
        else:
            # Store in memory
            self._criteria[criteria_id] = criteria

        return criteria_id

    async def get_criteria(self, criteria_id: str) -> Optional[EvalJudgeCriteria]:
        """
        Retrieve evaluation criteria by ID.

        Args:
            criteria_id: The ID of the criteria to retrieve

        Returns:
            The criteria if found, None otherwise
        """
        if self._db_manager:
            # Retrieve from database
            response = self._db_manager.get(
                EvalCriteriaDB, filters={"id": int(criteria_id) if criteria_id.isdigit() else criteria_id}
            )

            if response.status and response.data and len(response.data) > 0:
                criteria_data = response.data[0]
                return (
                    criteria_data.get("config")
                    if isinstance(criteria_data.get("config"), EvalJudgeCriteria)
                    else EvalJudgeCriteria.model_validate(criteria_data.get("config"))
                )
        else:
            # Retrieve from memory
            return self._criteria.get(criteria_id)

        return None

    async def list_criteria(self) -> List[EvalJudgeCriteria]:
        """
        List all available evaluation criteria.

        Returns:
            List of evaluation criteria
        """
        if self._db_manager:
            # Retrieve from database
            response = self._db_manager.get(EvalCriteriaDB)

            criteria_list = []
            if response.status and response.data:
                for criteria_data in response.data:
                    config = criteria_data.get("config")
                    if config:
                        if isinstance(config, EvalJudgeCriteria):
                            criteria_list.append(config)
                        else:
                            criteria_list.append(EvalJudgeCriteria.model_validate(config))
            return criteria_list
        else:
            # Retrieve from memory
            return list(self._criteria.values())

    # ----- Run Management -----

    async def create_run(
        self,
        task: Union[str, EvalTask],
        runner: BaseEvalRunner,
        judge: BaseEvalJudge,
        criteria: List[Union[str, EvalJudgeCriteria]],
        name: str = "",
        description: str = "",
    ) -> str:
        """
        Create a new evaluation run configuration.

        Args:
            task: The task to evaluate (ID or task object)
            runner: The runner to use for evaluation
            judge: The judge to use for evaluation
            criteria: List of criteria to use for evaluation (IDs or criteria objects)
            name: Name for the run
            description: Description for the run

        Returns:
            Run ID
        """
        # Resolve task
        task_obj = None
        if isinstance(task, str):
            task_obj = await self.get_task(task)
            if not task_obj:
                raise ValueError(f"Task not found: {task}")
        else:
            task_obj = task

        # Resolve criteria
        criteria_objs = []
        for criterion in criteria:
            if isinstance(criterion, str):
                criterion_obj = await self.get_criteria(criterion)
                if not criterion_obj:
                    raise ValueError(f"Criteria not found: {criterion}")
                criteria_objs.append(criterion_obj)
            else:
                criteria_objs.append(criterion)

        # Generate run ID
        run_id = str(uuid.uuid4())

        # Create run configuration
        runner_config = runner.dump_component() if hasattr(runner, "dump_component") else runner._to_config()
        judge_config = judge.dump_component() if hasattr(judge, "dump_component") else judge._to_config()

        if self._db_manager:
            # Store in database
            run_db = EvalRunDB(
                name=name or f"Run {run_id}",
                description=description,
                task_id=int(task) if isinstance(task, str) and task.isdigit() else None,
                runner_config=runner_config.model_dump(),
                judge_config=judge_config.model_dump(),
                criteria_configs=criteria_objs,
                status=EvalRunStatus.PENDING,
            )
            response = self._db_manager.upsert(run_db)
            if not response.status:
                logger.error(f"Failed to store run: {response.message}")
                raise RuntimeError(f"Failed to store run: {response.message}")
            run_id = str(response.data.get("id")) if response.data else run_id
        else:
            # Store in memory
            self._runs[run_id] = {
                "task": task_obj,
                "runner_config": runner_config,
                "judge_config": judge_config,
                "criteria_configs": [c.model_dump() for c in criteria_objs],
                "status": EvalRunStatus.PENDING,
                "created_at": datetime.now(),
                "run_result": None,
                "score_result": None,
                "name": name or f"Run {run_id}",
                "description": description,
            }

        return run_id

    async def start_run(self, run_id: str) -> None:
        """
        Start an evaluation run.

        Args:
            run_id: The ID of the run to start
        """
        # Check if run is already active
        if run_id in self._active_runs:
            logger.warning(f"Run {run_id} is already active")
            return

        # Start the run asynchronously
        run_task = asyncio.create_task(self._execute_run(run_id))
        self._active_runs[run_id] = run_task

        # Update run status
        await self._update_run_status(run_id, EvalRunStatus.RUNNING)

    async def _execute_run(self, run_id: str) -> None:
        """
        Execute an evaluation run.

        Args:
            run_id: The ID of the run to execute
        """
        try:
            # Get run configuration
            run_config = await self._get_run_config(run_id)
            if not run_config:
                raise ValueError(f"Run not found: {run_id}")

            # Get task
            task = run_config.get("task")
            if not task:
                raise ValueError(f"Task not found for run: {run_id}")

            # Initialize runner
            runner_config = run_config.get("runner_config")
            runner = BaseEvalRunner.load_component(runner_config) if runner_config else None

            # Initialize judge
            judge_config = run_config.get("judge_config")
            judge = BaseEvalJudge.load_component(judge_config) if judge_config else None

            if not runner or not judge:
                raise ValueError(f"Runner or judge not found for run: {run_id}")

            # Initialize criteria
            criteria_configs = run_config.get("criteria_configs")
            criteria = []
            if criteria_configs:
                criteria = [
                    EvalJudgeCriteria.model_validate(c) if not isinstance(c, EvalJudgeCriteria) else c
                    for c in criteria_configs
                ]

            # Execute runner
            logger.info(f"Starting runner for run {run_id}")
            start_time = datetime.now()
            run_results = await runner.run([task])
            run_result = run_results[0]

            # Update run result
            await self._update_run_result(run_id, run_result)

            if not run_result.status:
                logger.error(f"Runner failed for run {run_id}: {run_result.error}")
                await self._update_run_status(run_id, EvalRunStatus.FAILED)
                return

            # Execute judge
            logger.info(f"Starting judge for run {run_id}")
            score_result = await judge.judge(task, run_result, criteria)

            # Update score result
            await self._update_score_result(run_id, score_result)

            # Update run status
            end_time = datetime.now()
            await self._update_run_completed(run_id, start_time, end_time)

            logger.info(f"Run {run_id} completed successfully")

        except Exception as e:
            logger.exception(f"Error executing run {run_id}: {str(e)}")
            await self._update_run_error(run_id, str(e))
        finally:
            # Remove from active runs
            if run_id in self._active_runs:
                del self._active_runs[run_id]

    async def get_run_status(self, run_id: str) -> Optional[EvalRunStatus]:
        """
        Get the status of an evaluation run.

        Args:
            run_id: The ID of the run

        Returns:
            The run status if found, None otherwise
        """
        run_config = await self._get_run_config(run_id)
        return run_config.get("status") if run_config else None

    async def get_run_result(self, run_id: str) -> Optional[EvalRunResult]:
        """
        Get the result of an evaluation run.

        Args:
            run_id: The ID of the run

        Returns:
            The run result if found, None otherwise
        """
        run_config = await self._get_run_config(run_id)
        if not run_config:
            return None

        run_result = run_config.get("run_result")
        if not run_result:
            return None

        return run_result if isinstance(run_result, EvalRunResult) else EvalRunResult.model_validate(run_result)

    async def get_run_score(self, run_id: str) -> Optional[EvalScore]:
        """
        Get the score of an evaluation run.

        Args:
            run_id: The ID of the run

        Returns:
            The run score if found, None otherwise
        """
        run_config = await self._get_run_config(run_id)
        if not run_config:
            return None

        score_result = run_config.get("score_result")
        if not score_result:
            return None

        return score_result if isinstance(score_result, EvalScore) else EvalScore.model_validate(score_result)

    async def list_runs(self) -> List[Dict[str, Any]]:
        """
        List all available evaluation runs.

        Returns:
            List of run configurations
        """
        if self._db_manager:
            # Retrieve from database
            response = self._db_manager.get(EvalRunDB)

            runs = []
            if response.status and response.data:
                for run_data in response.data:
                    runs.append(
                        {
                            "id": run_data.get("id"),
                            "name": run_data.get("name"),
                            "status": run_data.get("status"),
                            "created_at": run_data.get("created_at"),
                            "updated_at": run_data.get("updated_at"),
                        }
                    )
            return runs
        else:
            # Retrieve from memory
            return [
                {
                    "id": run_id,
                    "name": run_config.get("name"),
                    "status": run_config.get("status"),
                    "created_at": run_config.get("created_at"),
                    "updated_at": run_config.get("updated_at", run_config.get("created_at")),
                }
                for run_id, run_config in self._runs.items()
            ]

    async def cancel_run(self, run_id: str) -> bool:
        """
        Cancel an active evaluation run.

        Args:
            run_id: The ID of the run to cancel

        Returns:
            True if the run was cancelled, False otherwise
        """
        # Check if run is active
        if run_id not in self._active_runs:
            logger.warning(f"Run {run_id} is not active")
            return False

        # Cancel the run task
        try:
            self._active_runs[run_id].cancel()
            await self._update_run_status(run_id, EvalRunStatus.CANCELED)
            del self._active_runs[run_id]
            return True
        except Exception as e:
            logger.error(f"Failed to cancel run {run_id}: {str(e)}")
            return False

    # ----- Helper Methods -----

    async def _get_run_config(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the configuration of an evaluation run.

        Args:
            run_id: The ID of the run

        Returns:
            The run configuration if found, None otherwise
        """
        if self._db_manager:
            # Retrieve from database
            response = self._db_manager.get(EvalRunDB, filters={"id": int(run_id) if run_id.isdigit() else run_id})

            if response.status and response.data and len(response.data) > 0:
                run_data = response.data[0]

                # Get task
                task = None
                if run_data.get("task_id"):
                    task_response = self._db_manager.get(EvalTaskDB, filters={"id": run_data.get("task_id")})
                    if task_response.status and task_response.data and len(task_response.data) > 0:
                        task_data = task_response.data[0]
                        task = (
                            task_data.get("config")
                            if isinstance(task_data.get("config"), EvalTask)
                            else EvalTask.model_validate(task_data.get("config"))
                        )

                return {
                    "task": task,
                    "runner_config": run_data.get("runner_config"),
                    "judge_config": run_data.get("judge_config"),
                    "criteria_configs": run_data.get("criteria_configs"),
                    "status": run_data.get("status"),
                    "run_result": run_data.get("run_result"),
                    "score_result": run_data.get("score_result"),
                    "name": run_data.get("name"),
                    "description": run_data.get("description"),
                    "created_at": run_data.get("created_at"),
                    "updated_at": run_data.get("updated_at"),
                }
        else:
            # Retrieve from memory
            return self._runs.get(run_id)

        return None

    async def _update_run_status(self, run_id: str, status: EvalRunStatus) -> None:
        """
        Update the status of an evaluation run.

        Args:
            run_id: The ID of the run
            status: The new status
        """
        if self._db_manager:
            # Update in database
            response = self._db_manager.get(EvalRunDB, filters={"id": int(run_id) if run_id.isdigit() else run_id})

            if response.status and response.data and len(response.data) > 0:
                run_data = response.data[0]
                run_db = EvalRunDB.model_validate(run_data)
                run_db.status = status
                run_db.updated_at = datetime.now()
                self._db_manager.upsert(run_db)
        else:
            # Update in memory
            if run_id in self._runs:
                self._runs[run_id]["status"] = status
                self._runs[run_id]["updated_at"] = datetime.now()

    async def _update_run_result(self, run_id: str, run_result: EvalRunResult) -> None:
        """
        Update the result of an evaluation run.

        Args:
            run_id: The ID of the run
            run_result: The run result
        """
        if self._db_manager:
            # Update in database
            response = self._db_manager.get(EvalRunDB, filters={"id": int(run_id) if run_id.isdigit() else run_id})

            if response.status and response.data and len(response.data) > 0:
                run_data = response.data[0]
                run_db = EvalRunDB.model_validate(run_data)
                run_db.run_result = run_result
                run_db.updated_at = datetime.now()
                self._db_manager.upsert(run_db)
        else:
            # Update in memory
            if run_id in self._runs:
                self._runs[run_id]["run_result"] = run_result
                self._runs[run_id]["updated_at"] = datetime.now()

    async def _update_score_result(self, run_id: str, score_result: EvalScore) -> None:
        """
        Update the score of an evaluation run.

        Args:
            run_id: The ID of the run
            score_result: The score result
        """
        if self._db_manager:
            # Update in database
            response = self._db_manager.get(EvalRunDB, filters={"id": int(run_id) if run_id.isdigit() else run_id})

            if response.status and response.data and len(response.data) > 0:
                run_data = response.data[0]
                run_db = EvalRunDB.model_validate(run_data)
                run_db.score_result = score_result
                run_db.updated_at = datetime.now()
                self._db_manager.upsert(run_db)
        else:
            # Update in memory
            if run_id in self._runs:
                self._runs[run_id]["score_result"] = score_result
                self._runs[run_id]["updated_at"] = datetime.now()

    async def _update_run_completed(self, run_id: str, start_time: datetime, end_time: datetime) -> None:
        """
        Update a run as completed.

        Args:
            run_id: The ID of the run
            start_time: The start time
            end_time: The end time
        """
        if self._db_manager:
            # Update in database
            response = self._db_manager.get(EvalRunDB, filters={"id": int(run_id) if run_id.isdigit() else run_id})

            if response.status and response.data and len(response.data) > 0:
                run_data = response.data[0]
                run_db = EvalRunDB.model_validate(run_data)
                run_db.status = EvalRunStatus.COMPLETED
                run_db.start_time = start_time
                run_db.end_time = end_time
                run_db.updated_at = datetime.now()
                self._db_manager.upsert(run_db)
        else:
            # Update in memory
            if run_id in self._runs:
                self._runs[run_id]["status"] = EvalRunStatus.COMPLETED
                self._runs[run_id]["start_time"] = start_time
                self._runs[run_id]["end_time"] = end_time
                self._runs[run_id]["updated_at"] = datetime.now()

    async def _update_run_error(self, run_id: str, error_message: str) -> None:
        """
        Update a run with an error.

        Args:
            run_id: The ID of the run
            error_message: The error message
        """
        if self._db_manager:
            # Update in database
            response = self._db_manager.get(EvalRunDB, filters={"id": int(run_id) if run_id.isdigit() else run_id})

            if response.status and response.data and len(response.data) > 0:
                run_data = response.data[0]
                run_db = EvalRunDB.model_validate(run_data)
                run_db.status = EvalRunStatus.FAILED
                run_db.error_message = error_message
                run_db.end_time = datetime.now()
                run_db.updated_at = datetime.now()
                self._db_manager.upsert(run_db)
        else:
            # Update in memory
            if run_id in self._runs:
                self._runs[run_id]["status"] = EvalRunStatus.FAILED
                self._runs[run_id]["error_message"] = error_message
                self._runs[run_id]["end_time"] = datetime.now()
                self._runs[run_id]["updated_at"] = datetime.now()

    async def tabulate_results(self, run_ids: List[str], include_reasons: bool = False) -> TabulatedResults:
        """
        Generate a tabular representation of evaluation results across runs.

        This method collects scores across different runs and organizes them by
        dimension, making it easy to create visualizations like radar charts.

        Args:
            run_ids: List of run IDs to include in the tabulation
            include_reasons: Whether to include scoring reasons in the output

        Returns:
            A dictionary with structured data suitable for visualization
        """
        result: TabulatedResults = {"dimensions": [], "runs": []}

        # Parallelize fetching of run configs and scores
        fetch_tasks = []
        for run_id in run_ids:
            fetch_tasks.append(self._get_run_config(run_id))
            fetch_tasks.append(self.get_run_score(run_id))

        # Wait for all fetches to complete
        fetch_results = await asyncio.gather(*fetch_tasks)

        # Process fetched data
        dimensions_set = set()
        run_data = {}

        for i in range(0, len(fetch_results), 2):
            run_id = run_ids[i // 2]
            run_config = fetch_results[i]
            score = fetch_results[i + 1]

            # Store run data for later processing
            run_data[run_id] = (run_config, score)

            # Collect dimensions
            if score and score.dimension_scores:
                for dim_score in score.dimension_scores:
                    dimensions_set.add(dim_score.dimension)

        # Convert dimensions to sorted list
        result["dimensions"] = sorted(list(dimensions_set))

        # Process each run's data
        for run_id, (run_config, score) in run_data.items():
            if not run_config or not score:
                continue

            # Determine runner type
            runner_type = "unknown"
            if run_config.get("runner_config"):
                runner_config = run_config.get("runner_config")
                if runner_config is not None and "provider" in runner_config:
                    if "ModelEvalRunner" in runner_config["provider"]:
                        runner_type = "model"
                    elif "TeamEvalRunner" in runner_config["provider"]:
                        runner_type = "team"

            # Get task name
            task = run_config.get("task")
            task_name = task.name if task else "Unknown Task"

            # Create run entry
            run_entry: RunEntry = {
                "id": run_id,
                "name": run_config.get("name", f"Run {run_id}"),
                "task_name": task_name,
                "runner_type": runner_type,
                "overall_score": score.overall_score,
                "scores": [],
                "reasons": [] if include_reasons else None,
            }

            # Build dimension lookup map for O(1) access
            dim_map = {ds.dimension: ds for ds in score.dimension_scores}

            # Populate scores aligned with dimensions
            for dim in result["dimensions"]:
                dim_score = dim_map.get(dim)
                if dim_score:
                    run_entry["scores"].append(dim_score.score)
                    if include_reasons:
                        run_entry["reasons"].append(dim_score.reason)  # type: ignore
                else:
                    run_entry["scores"].append(None)
                    if include_reasons:
                        run_entry["reasons"].append(None)  # type: ignore

            result["runs"].append(run_entry)

        return result
