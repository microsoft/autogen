# eval/orchestrator.py
import asyncio
from datetime import datetime
import time
from typing import Dict, List, Optional, Set, Tuple, Union, Any
import uuid

from autogen_core import CancellationToken

from ..datamodel.eval import (
    EvalTask, EvalRunConfig, EvalJudgeCriteria, EvalRunStatus,
    EvalConfigDB, EvalRunDB, EvalResultDB, EvalRunResult,
    EvalScore, EvalRunConfigDB
)
from ..database.db_manager import DatabaseManager
from .judge import BaseEvalJudge
from .runners import BaseEvalRunner


class EvalOrchestrator:
    """Orchestrates evaluation runs across tasks, configs, and judges."""
    
    def __init__(
        self,
        db_manager: DatabaseManager,
        max_concurrent_runs: int = 5
    ):
        self.db_manager = db_manager
        self.max_concurrent_runs = max_concurrent_runs
        self.semaphore = asyncio.Semaphore(max_concurrent_runs)
        self._runner_registry = {}
        self._active_runs = {}  # Tracking active run tasks
        
    def register_runner(self, config_type: str, runner: BaseEvalRunner):
        """Register a runner for a specific config type."""
        self._runner_registry[config_type] = runner
    
    async def create_experiment(
        self,
        name: str,
        tasks: List[EvalTask],
        run_configs: List[EvalRunConfig],
        judge_criteria: List[EvalJudgeCriteria],
        description: str = "",
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> EvalConfigDB:
        """Create a new experiment configuration."""
        # Convert tasks and run_configs to dictionaries for storage
        tasks_dict = {str(task.task_id): task.dict() for task in tasks}
        configs_dict = {str(config.config_id): config.dict() for config in run_configs}
        
        # Create experiment config for DB
        experiment_db = EvalConfigDB(
            name=name,
            description=description,
            tasks=tasks_dict,
            run_configs=configs_dict,
            judge_criteria=[criterion.dict() for criterion in judge_criteria],
            metadata=metadata or {},
            user_id=user_id
        )
        
        # Save to database
        response = self.db_manager.upsert(experiment_db, return_json=False)
        if not response.status:
            raise Exception(f"Failed to create experiment: {response.message}")
        
        return response.data
    
    async def list_experiments(
        self, 
        user_id: Optional[str] = None, 
        limit: int = 100,
        offset: int = 0
    ) -> List[EvalConfigDB]:
        """List all experiments, optionally filtered by user_id."""
        filters = {"user_id": user_id} if user_id else None
        response = self.db_manager.get(
            EvalConfigDB, 
            filters,
            return_json=False
        )
        
        if not response.status:
            raise Exception(f"Failed to list experiments: {response.message}")
        
        return response.data[offset:offset+limit] if response.data else []
    
    async def get_experiment(self, experiment_id: int) -> Optional[EvalConfigDB]:
        """Get details of a specific experiment."""
        response = self.db_manager.get(
            EvalConfigDB,
            {"id": experiment_id},
            return_json=False
        )
        
        if not response.status or not response.data:
            return None
            
        return response.data[0] if response.data else None
    
    async def run_experiment(
        self,
        experiment_id: int,
        judge: BaseEvalJudge,
        run_unfinished_only: bool = False,
        cancellation_token: Optional[CancellationToken] = None
    ) -> EvalRunDB:
        """Run an experiment and judge the results."""
        # Get experiment configuration
        experiment = await self.get_experiment(experiment_id)
        if not experiment:
            raise Exception(f"Experiment with ID {experiment_id} not found")
        
        # Convert stored dicts back to model objects
        tasks = [EvalTask(**task_data) for task_data in experiment.tasks.values()]
        run_configs = [EvalRunConfig(**config_data) for config_data in experiment.run_configs.values()]
        criteria = [EvalJudgeCriteria(**criterion) for criterion in experiment.judge_criteria]
        
        # Create experiment run record
        exp_run = EvalRunDB(
            experiment_id=experiment_id,
            status=EvalRunStatus.PREPARING,
            start_time=datetime.now(),
            user_id=experiment.user_id,
            total_tasks=len(tasks) * len(run_configs),
            completed_tasks=0,
            failed_tasks=0
        )
        
        run_response = self.db_manager.upsert(exp_run, return_json=False)
        if not run_response.status:
            raise Exception(f"Failed to create experiment run: {run_response.message}")
        
        exp_run = run_response.data
        
        try:
            # Check for previously completed evaluations if running unfinished only
            skip_combinations = set()
            if run_unfinished_only:
                skip_combinations = await self._get_completed_combinations(exp_run.id)
            
            # Create all evaluation combinations
            eval_tasks = []
            for task in tasks:
                for config in run_configs:
                    if (str(task.task_id), str(config.config_id)) not in skip_combinations:
                        eval_tasks.append((task, config))
            
            # Update experiment run status
            exp_run.status = EvalRunStatus.RUNNING
            self.db_manager.upsert(exp_run)
            
            # Run evaluations with concurrency control
            self._active_runs[exp_run.id] = []
            async with asyncio.TaskGroup() as tg:
                for task, config in eval_tasks:
                    task_obj = tg.create_task(
                        self._run_and_judge_evaluation(
                            exp_run.id, task, config, judge, criteria, cancellation_token
                        )
                    )
                    self._active_runs[exp_run.id].append(task_obj)
            
            # Check final status
            results_response = self.db_manager.get(
                EvalResultDB,
                {"experiment_run_id": exp_run.id},
                return_json=False
            )
            
            if results_response.status and results_response.data:
                completed = sum(1 for r in results_response.data if r.status == EvalRunStatus.COMPLETED)
                failed = sum(1 for r in results_response.data if r.status == EvalRunStatus.FAILED)
                
                # Update run with final stats
                exp_run.completed_tasks = completed
                exp_run.failed_tasks = failed
                
                # Determine final status
                if failed == 0 and completed == exp_run.total_tasks:
                    exp_run.status = EvalRunStatus.COMPLETED
                elif completed > 0:
                    exp_run.status = EvalRunStatus.PARTIALLY_COMPLETED
                elif failed > 0:
                    exp_run.status = EvalRunStatus.FAILED
            
            exp_run.end_time = datetime.now()
            
        except Exception as e:
            # Update experiment run status in case of error
            exp_run.status = EvalRunStatus.FAILED
            exp_run.end_time = datetime.now()
            exp_run.metadata = {**exp_run.metadata, "error": str(e)}
            raise
        finally:
            # Clean up active runs tracking
            if exp_run.id in self._active_runs:
                del self._active_runs[exp_run.id]
                
            # Save updated experiment run
            self.db_manager.upsert(exp_run)
        
        return exp_run
    
    async def restart_experiment(
        self,
        experiment_run_id: int,
        judge: BaseEvalJudge,
        retry_failed_only: bool = True,
        max_attempts: int = 3,
        cancellation_token: Optional[CancellationToken] = None
    ) -> EvalRunDB:
        """Restart a previous experiment run, optionally only retrying failed evaluations."""
        # Get the run
        run_response = self.db_manager.get(
            EvalRunDB,
            {"id": experiment_run_id},
            return_json=False
        )
        
        if not run_response.status or not run_response.data:
            raise Exception(f"Experiment run with ID {experiment_run_id} not found")
        
        previous_run = run_response.data[0]
        
        # Get the experiment
        experiment = await self.get_experiment(previous_run.experiment_id)
        if not experiment:
            raise Exception(f"Experiment with ID {previous_run.experiment_id} not found")
        
        # Get evaluation results
        results_response = self.db_manager.get(
            EvalResultDB,
            {"experiment_run_id": experiment_run_id},
            return_json=False
        )
        
        if not results_response.status:
            raise Exception(f"Failed to get evaluation results: {results_response.message}")
        
        previous_results = results_response.data or []
        
        # Identify evaluations to retry
        eval_tasks_to_retry = []
        for result in previous_results:
            # Skip if max attempts reached
            if result.attempt >= max_attempts:
                continue
                
            # Skip successful runs if retrying only failed ones
            if retry_failed_only and result.status == EvalRunStatus.COMPLETED:
                continue
                
            # Add to retry list
            task = EvalTask(**result.task)
            config = EvalRunConfig(**result.run_config)
            eval_tasks_to_retry.append((task, config, result.attempt + 1))
        
        if not eval_tasks_to_retry:
            raise Exception(f"No evaluations to retry for run {experiment_run_id}")
        
        # Create new experiment run
        new_run = EvalRunDB(
            experiment_id=previous_run.experiment_id,
            status=EvalRunStatus.PREPARING,
            start_time=datetime.now(),
            user_id=previous_run.user_id,
            total_tasks=len(eval_tasks_to_retry),
            completed_tasks=0,
            failed_tasks=0,
            metadata={
                "restarted_from": experiment_run_id,
                "retry_failed_only": retry_failed_only
            }
        )
        
        run_response = self.db_manager.upsert(new_run, return_json=False)
        if not run_response.status:
            raise Exception(f"Failed to create restart run: {run_response.message}")
        
        new_run = run_response.data
        
        try:
            # Convert judge criteria
            criteria = [EvalJudgeCriteria(**criterion) for criterion in experiment.judge_criteria]
            
            # Update experiment run status
            new_run.status = EvalRunStatus.RUNNING
            self.db_manager.upsert(new_run)
            
            # Run evaluations with concurrency control
            self._active_runs[new_run.id] = []
            async with asyncio.TaskGroup() as tg:
                for task, config, attempt in eval_tasks_to_retry:
                    task_obj = tg.create_task(
                        self._run_and_judge_evaluation(
                            new_run.id, task, config, judge, criteria, 
                            cancellation_token, attempt=attempt
                        )
                    )
                    self._active_runs[new_run.id].append(task_obj)
            
            # Check final status
            results_response = self.db_manager.get(
                EvalResultDB,
                {"experiment_run_id": new_run.id},
                return_json=False
            )
            
            if results_response.status and results_response.data:
                completed = sum(1 for r in results_response.data if r.status == EvalRunStatus.COMPLETED)
                failed = sum(1 for r in results_response.data if r.status == EvalRunStatus.FAILED)
                
                # Update run with final stats
                new_run.completed_tasks = completed
                new_run.failed_tasks = failed
                
                # Determine final status
                if failed == 0 and completed == new_run.total_tasks:
                    new_run.status = EvalRunStatus.COMPLETED
                elif completed > 0:
                    new_run.status = EvalRunStatus.PARTIALLY_COMPLETED
                elif failed > 0:
                    new_run.status = EvalRunStatus.FAILED
            
            new_run.end_time = datetime.now()
            
        except Exception as e:
            # Update experiment run status in case of error
            new_run.status = EvalRunStatus.FAILED
            new_run.end_time = datetime.now()
            new_run.metadata = {**new_run.metadata, "error": str(e)}
            raise
        finally:
            # Clean up active runs tracking
            if new_run.id in self._active_runs:
                del self._active_runs[new_run.id]
                
            # Save updated experiment run
            self.db_manager.upsert(new_run)
        
        return new_run
    
    async def cancel_experiment_run(self, experiment_run_id: int) -> bool:
        """Cancel an active experiment run."""
        # Check if run exists and is active
        run_response = self.db_manager.get(
            EvalRunDB,
            {"id": experiment_run_id},
            return_json=False
        )
        
        if not run_response.status or not run_response.data:
            raise Exception(f"Experiment run with ID {experiment_run_id} not found")
        
        run = run_response.data[0]
        
        # If run is not active, nothing to cancel
        if run.status not in (EvalRunStatus.PREPARING, EvalRunStatus.RUNNING):
            return False
        
        # Cancel active tasks if any
        if experiment_run_id in self._active_runs:
            for task in self._active_runs[experiment_run_id]:
                task.cancel()
            del self._active_runs[experiment_run_id]
        
        # Update run status
        run.status = EvalRunStatus.CANCELED
        run.end_time = datetime.now()
        self.db_manager.upsert(run)
        
        # Update any active evaluation results
        results_response = self.db_manager.get(
            EvalResultDB,
            {"experiment_run_id": experiment_run_id},
            return_json=False
        )
        
        if results_response.status and results_response.data:
            for result in results_response.data:
                if result.status in (EvalRunStatus.PREPARING, EvalRunStatus.RUNNING):
                    result.status = EvalRunStatus.CANCELED
                    result.end_time = datetime.now()
                    self.db_manager.upsert(result)
        
        return True
    
    async def get_experiment_status(self, experiment_run_id: int) -> Dict[str, Any]:
        """Get detailed status of an experiment run."""
        # Get the run
        run_response = self.db_manager.get(
            EvalRunDB,
            {"id": experiment_run_id},
            return_json=False
        )
        
        if not run_response.status or not run_response.data:
            raise Exception(f"Experiment run with ID {experiment_run_id} not found")
        
        run = run_response.data[0]
        
        # Get all evaluation results
        results_response = self.db_manager.get(
            EvalResultDB,
            {"experiment_run_id": experiment_run_id},
            return_json=False
        )
        
        results = results_response.data if results_response.status else []
        
        # Compute stats
        total = run.total_tasks
        completed = run.completed_tasks
        failed = run.failed_tasks
        pending = total - completed - failed
        progress = (completed / total) * 100 if total > 0 else 0
        
        # Get summary metrics if available
        metrics = {}
        if results:
            scores = []
            dimensions = {}
            execution_times = []
            
            for result in results:
                if result.score and result.status == EvalRunStatus.COMPLETED:
                    score_obj = EvalScore(**result.score)
                    
                    # Overall score
                    if score_obj.overall_score is not None:
                        scores.append(score_obj.overall_score)
                    
                    # Dimension scores
                    for dim_score in score_obj.dimension_scores:
                        if dim_score.score is not None:
                            if dim_score.dimension not in dimensions:
                                dimensions[dim_score.dimension] = []
                            dimensions[dim_score.dimension].append(dim_score.score)
                
                # Execution time
                if result.duration_ms:
                    execution_times.append(result.duration_ms)
            
            # Compute averages
            if scores:
                metrics["avg_overall_score"] = sum(scores) / len(scores)
                
            dimension_avgs = {}
            for dim, dim_scores in dimensions.items():
                if dim_scores:
                    dimension_avgs[dim] = sum(dim_scores) / len(dim_scores)
            
            if dimension_avgs:
                metrics["avg_dimension_scores"] = dimension_avgs
                
            if execution_times:
                metrics["avg_execution_time_ms"] = sum(execution_times) / len(execution_times)
        
        # Build status object
        status = {
            "id": run.id,
            "experiment_id": run.experiment_id,
            "status": run.status,
            "start_time": run.start_time.isoformat() if run.start_time else None,
            "end_time": run.end_time.isoformat() if run.end_time else None,
            "total_tasks": total,
            "completed_tasks": completed,
            "failed_tasks": failed,
            "pending_tasks": pending,
            "progress_percentage": progress,
            "metrics": metrics,
            "metadata": run.metadata
        }
        
        return status
    
    async def get_experiment_results(
        self, 
        experiment_run_id: int,
        detailed: bool = False
    ) -> List[Dict[str, Any]]:
        """Get evaluation results for an experiment run."""
        # Get evaluation results
        results_response = self.db_manager.get(
            EvalResultDB,
            {"experiment_run_id": experiment_run_id},
            return_json=False
        )
        
        if not results_response.status:
            raise Exception(f"Failed to get evaluation results: {results_response.message}")
        
        results = results_response.data or []
        
        # Format results
        formatted_results = []
        for result in results:
            # Basic result info
            result_dict = {
                "id": result.id,
                "task_id": result.task_id,
                "run_config_id": result.run_config_id,
                "status": result.status,
                "start_time": result.start_time.isoformat() if result.start_time else None,
                "end_time": result.end_time.isoformat() if result.end_time else None,
                "duration_ms": result.duration_ms,
                "attempt": result.attempt,
                "task_name": result.task.get("name", "Unnamed Task"),
                "config_name": result.run_config.get("name", "Unnamed Config")
            }
            
            # Add score if available
            if result.score:
                score_obj = EvalScore(**result.score)
                result_dict["overall_score"] = score_obj.overall_score
                
                # Add dimension scores
                dimension_scores = {}
                for dim_score in score_obj.dimension_scores:
                    dimension_scores[dim_score.dimension] = {
                        "score": dim_score.score,
                        "reason": dim_score.reason,
                        "max_value": dim_score.max_value
                    }
                
                result_dict["dimension_scores"] = dimension_scores
            
            # Add error if available
            if result.error:
                result_dict["error"] = result.error
            
            # Add detailed info if requested
            if detailed:
                result_dict["task"] = result.task
                result_dict["run_config"] = result.run_config
                
                if result.result:
                    result_dict["result"] = result.result
            
            formatted_results.append(result_dict)
        
        return formatted_results
    
    async def compare_experiment_runs(self, run_ids: List[int]) -> Dict[str, Any]:
        """Compare results across multiple experiment runs."""
        if not run_ids or len(run_ids) < 2:
            raise ValueError("At least two run IDs are required for comparison")
        
        runs = {}
        for run_id in run_ids:
            # Get run info
            run_response = self.db_manager.get(
                EvalRunDB,
                {"id": run_id},
                return_json=False
            )
            
            if not run_response.status or not run_response.data:
                raise Exception(f"Experiment run with ID {run_id} not found")
            
            run = run_response.data[0]
            
            # Get results
            results = await self.get_experiment_results(run_id)
            
            runs[run_id] = {
                "run": run,
                "results": results
            }
        
        # Build comparison metrics
        comparison = {
            "run_ids": run_ids,
            "completion_rates": {},
            "avg_scores": {},
            "dimension_scores": {},
            "execution_times": {}
        }
        
        for run_id, run_data in runs.items():
            run = run_data["run"]
            results = run_data["results"]
            
            total = run.total_tasks
            completed = run.completed_tasks
            
            # Completion rate
            completion_rate = (completed / total) * 100 if total > 0 else 0
            comparison["completion_rates"][run_id] = completion_rate
            
            # Score aggregates
            scores = [r.get("overall_score") for r in results if r.get("overall_score") is not None]
            if scores:
                comparison["avg_scores"][run_id] = sum(scores) / len(scores)
            
            # Dimension scores
            all_dimensions = {}
            for result in results:
                if "dimension_scores" in result:
                    for dim, dim_data in result["dimension_scores"].items():
                        if dim not in all_dimensions:
                            all_dimensions[dim] = {}
                        
                        if run_id not in all_dimensions[dim]:
                            all_dimensions[dim][run_id] = []
                        
                        if dim_data.get("score") is not None:
                            all_dimensions[dim][run_id].append(dim_data["score"])
            
            # Calculate averages for each dimension
            for dim, dim_data in all_dimensions.items():
                if dim not in comparison["dimension_scores"]:
                    comparison["dimension_scores"][dim] = {}
                
                for run_id, scores in dim_data.items():
                    if scores:
                        comparison["dimension_scores"][dim][run_id] = sum(scores) / len(scores)
            
            # Execution times
            times = [r.get("duration_ms") for r in results if r.get("duration_ms") is not None]
            if times:
                comparison["execution_times"][run_id] = sum(times) / len(times)
        
        return comparison
    
    async def _get_completed_combinations(self, experiment_run_id: int) -> Set[Tuple[str, str]]:
        """Get task_id, config_id combinations that were already completed."""
        results_response = self.db_manager.get(
            EvalResultDB, 
            {"experiment_run_id": experiment_run_id}, 
            return_json=False
        )
        
        completed = set()
        if results_response.status and results_response.data:
            for result in results_response.data:
                if result.status == EvalRunStatus.COMPLETED:
                    completed.add((result.task_id, result.run_config_id))
        
        return completed
    
    async def _run_and_judge_evaluation(
        self,
        experiment_run_id: int,
        task: EvalTask,
        config: EvalRunConfig,
        judge: BaseEvalJudge,
        criteria: List[EvalJudgeCriteria],
        cancellation_token: Optional[CancellationToken] = None,
        attempt: int = 1
    ) -> EvalResultDB:
        """Run and judge a single evaluation task."""
        async with self.semaphore:
            # Get the appropriate runner
            runner = self._runner_registry.get(config.config_type)
            if not runner:
                raise ValueError(f"No runner registered for config type: {config.config_type}")
            
            # Create evaluation result record
            eval_result = EvalResultDB(
                experiment_run_id=experiment_run_id,
                task_id=str(task.task_id),
                run_config_id=str(config.config_id),
                status=EvalRunStatus.PENDING,
                task=task.dict(),
                run_config=config.dict(),
                attempt=attempt
            )
            
            # Save initial state
            response = self.db_manager.upsert(eval_result, return_json=False)
            if not response.status:
                raise Exception(f"Failed to create evaluation result: {response.message}")
            
            eval_result = response.data
            
            try:
                # Update status to running
                eval_result.status = EvalRunStatus.RUNNING
                eval_result.start_time = datetime.now()
                self.db_manager.upsert(eval_result)
                
                # Run the evaluation
                start_time = time.time()
                run_result = await runner.run(task, config, cancellation_token)
                end_time = time.time()
                
                # Calculate duration
                duration_ms = (end_time - start_time) * 1000
                
                # Update with run results
                eval_result.result = run_result.dict() if run_result else None
                eval_result.duration_ms = duration_ms
                
                if run_result and run_result.status:
                    eval_result.status = EvalRunStatus.COMPLETED
                    self.db_manager.upsert(eval_result)
                    
                    # Judge the result
                    score = await judge.judge(task, run_result, criteria, cancellation_token)
                    eval_result.score = score.dict() if score else None
                    self.db_manager.upsert(eval_result)
                else:
                    eval_result.status = EvalRunStatus.FAILED
                    eval_result.error = run_result.error if run_result else "No result returned"
                    self.db_manager.upsert(eval_result)
                
                # Update experiment completion counter
                await self._update_experiment_counters(experiment_run_id)
                
            except Exception as e:
                # Update with error
                eval_result.status = EvalRunStatus.FAILED
                eval_result.error = str(e)
                self.db_manager.upsert(eval_result)
                
                # Update experiment failure counter
                await self._update_experiment_counters(experiment_run_id)
                raise
            finally:
                # Ensure end time is set
                eval_result.end_time = datetime.now()
                self.db_manager.upsert(eval_result)
            
            return eval_result
    
    async def _update_experiment_counters(self, experiment_run_id: int):
        """Update the completed and failed task counters for an experiment run."""
        # Get the run
        run_response = self.db_manager.get(
            EvalRunDB,
            {"id": experiment_run_id},
            return_json=False
        )
        
        if not run_response.status or not run_response.data:
            return
        
        run = run_response.data[0]
        
        # Get all results
        results_response = self.db_manager.get(
            EvalResultDB,
            {"experiment_run_id": experiment_run_id},
            return_json=False
        )
        
        if not results_response.status or not results_response.data:
            return
        
        results = results_response.data
        
        # Count completed and failed
        completed = sum(1 for r in results if r.status == EvalRunStatus.COMPLETED)
        failed = sum(1 for r in results if r.status == EvalRunStatus.FAILED)
        
        # Update run
        run.completed_tasks = completed
        run.failed_tasks = failed
        self.db_manager.upsert(run)
    
    async def export_experiment_results(
        self,
        experiment_run_id: int,
        format: str = "json"
    ) -> Dict[str, Any]:
        """Export experiment results in a structured format."""
        # Get run info
        run_response = self.db_manager.get(
            EvalRunDB,
            {"id": experiment_run_id},
            return_json=False
        )
        
        if not run_response.status or not run_response.data:
            raise Exception(f"Experiment run with ID {experiment_run_id} not found")
        
        run = run_response.data[0]
        
        # Get experiment info
        experiment = await self.get_experiment(run.experiment_id)
        if not experiment:
            raise Exception(f"Experiment with ID {run.experiment_id} not found")
        
        # Get results
        results = await self.get_experiment_results(experiment_run_id, detailed=True)
        
        # Build export
        export_data = {
            "experiment": {
                "id": experiment.id,
                "name": experiment.name,
                "description": experiment.description,
                "metadata": experiment.metadata
            },
            "run": {
                "id": run.id,
                "status": run.status,
                "start_time": run.start_time.isoformat() if run.start_time else None,
                "end_time": run.end_time.isoformat() if run.end_time else None,
                "total_tasks": run.total_tasks,
                "completed_tasks": run.completed_tasks,
                "failed_tasks": run.failed_tasks,
                "metadata": run.metadata
            },
            "results": results,
            "export_time": datetime.now().isoformat()
        }
        
        # For now just return JSON, could add CSV or other formats later
        return export_data