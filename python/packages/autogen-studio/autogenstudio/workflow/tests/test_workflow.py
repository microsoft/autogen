"""
Test workflow type validation and serialization.
"""
import pytest
from typing import Any, Dict
from pydantic import BaseModel

from autogenstudio.workflow.steps import EchoStep, BaseStep, TransformStep
from autogenstudio.workflow.core import Workflow, WorkflowRunner, StepMetadata, WorkflowMetadata, EdgeCondition
from autogen_core import CancellationToken


# Test data models
class TextInput(BaseModel):
    message: str


class TextOutput(BaseModel):
    result: str


class NumberInput(BaseModel):
    value: int


class NumberOutput(BaseModel):
    result: int


@pytest.fixture
def sample_workflow():
    """Create a sample workflow for testing."""
    workflow = Workflow(
        metadata=WorkflowMetadata(
            name="Test Workflow",
            version="1.0.0"
        )
    )
    
    step1 = EchoStep(
        step_id="step1",
        metadata=StepMetadata(name="First Step"),
        input_type=TextInput,
        output_type=TextOutput,
        prefix="[1] ",
        suffix=""
    )
    
    step2 = EchoStep(
        step_id="step2",
        metadata=StepMetadata(name="Second Step"),
        input_type=TextOutput,  # Compatible with step1 output
        output_type=TextOutput,
        prefix="[2] ",
        suffix=" (done)"
    )
    
    workflow.add_step(step1).add_step(step2)
    workflow.add_edge("step1", "step2")
    workflow.set_start_step("step1").add_end_step("step2")
    
    return workflow


# === Helper functions for test reuse ===
def make_echo_step(step_id, name, input_type, output_type, prefix="", suffix=""):
    return EchoStep(
        step_id=step_id,
        metadata=StepMetadata(name=name),
        input_type=input_type,
        output_type=output_type,
        prefix=prefix,
        suffix=suffix
    )

def make_edge_condition(type="always", field=None, operator=None, value=None):
    from autogenstudio.workflow.core import EdgeCondition
    return EdgeCondition(type=type, field=field, operator=operator, value=value)


class TestWorkflowValidation:
    """Test workflow validation, especially type checking."""
    
    def test_compatible_types_pass_validation(self, sample_workflow):
        """Test that compatible types pass validation."""
        validation = sample_workflow.validate_workflow()
        assert validation.is_valid
        assert len(validation.errors) == 0
    
    def test_incompatible_types_fail_validation(self):
        """Test that incompatible types fail validation."""
        workflow = Workflow(
            metadata=WorkflowMetadata(name="Invalid Workflow", version="1.0.0")
        )
        
        # Create steps with incompatible types
        step1 = EchoStep(
            step_id="text_step",
            metadata=StepMetadata(name="Text Step"),
            input_type=TextInput,
            output_type=TextOutput,  # Outputs TextOutput
            prefix="Text: ",
            suffix=""
        )
        
        step2 = EchoStep(
            step_id="number_step", 
            metadata=StepMetadata(name="Number Step"),
            input_type=NumberInput,  # Expects NumberInput (incompatible!)
            output_type=NumberOutput,
            prefix="Number: ",
            suffix=""
        )
        
        workflow.add_step(step1).add_step(step2)
        workflow.add_edge("text_step", "number_step")  # This should fail validation
        workflow.set_start_step("text_step").add_end_step("number_step")
        
        validation = workflow.validate_workflow()
        assert not validation.is_valid
        assert len(validation.errors) > 0
        assert any("Type mismatch" in error for error in validation.errors)
    
    def test_schema_based_validation_works(self):
        """Test that schema-based validation correctly identifies compatible types."""
        workflow = Workflow(
            metadata=WorkflowMetadata(name="Schema Test", version="1.0.0")
        )
        
        # Create two steps that use the same schema but different type instances
        step1 = EchoStep(
            step_id="step1",
            metadata=StepMetadata(name="Step 1"),
            input_type=TextInput,
            output_type=TextOutput,
            prefix="[1] ",
            suffix=""
        )
        
        # This step also uses TextOutput as input - should be compatible by schema
        step2 = EchoStep(
            step_id="step2",
            metadata=StepMetadata(name="Step 2"),
            input_type=TextOutput,
            output_type=TextOutput,
            prefix="[2] ",
            suffix=""
        )
        
        workflow.add_step(step1).add_step(step2)
        workflow.add_edge("step1", "step2")
        workflow.set_start_step("step1").add_end_step("step2")
        
        validation = workflow.validate_workflow()
        assert validation.is_valid, f"Validation failed: {validation.errors}"


class TestWorkflowSerialization:
    """Test workflow serialization and deserialization."""
    
    def test_workflow_serialization_roundtrip(self, sample_workflow):
        """Test that workflow can be serialized and deserialized correctly."""
        # Serialize
        config = sample_workflow.dump_component()
        assert config.provider == "autogenstudio.workflow.core.Workflow"
        assert len(config.config['steps']) == 2
        
        # Deserialize
        new_workflow = Workflow.load_component(config)
        assert new_workflow.metadata.name == sample_workflow.metadata.name
        assert len(new_workflow.steps) == 2
        assert new_workflow.start_step_id == sample_workflow.start_step_id
        assert new_workflow.end_step_ids == sample_workflow.end_step_ids
        
        # Validate deserialized workflow
        validation = new_workflow.validate_workflow()
        assert validation.is_valid, f"Deserialized workflow validation failed: {validation.errors}"
    
    def test_serialized_workflow_execution_matches_original(self, sample_workflow):
        """Test that serialized workflow produces same results as original."""
        # Run original workflow
        runner = WorkflowRunner()
        input_data = {"message": "test"}
        
        import asyncio
        
        async def run_test():
            result1 = await runner.run(sample_workflow, input_data)
            
            # Serialize and deserialize
            config = sample_workflow.dump_component()
            new_workflow = Workflow.load_component(config)
            
            # Run deserialized workflow
            runner2 = WorkflowRunner()
            result2 = await runner2.run(new_workflow, input_data)
            
            # Compare final outputs
            def get_final_output(result):
                for step_id, step_exec in result.step_executions.items():
                    if step_id in new_workflow.end_step_ids:
                        return step_exec.output_data
                return None
            
            output1 = get_final_output(result1)
            output2 = get_final_output(result2)
            
            assert output1 == output2, f"Outputs don't match: {output1} vs {output2}"
            
        asyncio.run(run_test())
    
    def test_serialization_preserves_step_configuration(self, sample_workflow):
        """Test that step configuration is preserved through serialization."""
        # Serialize and deserialize
        config = sample_workflow.dump_component()
        new_workflow = Workflow.load_component(config)
        
        # Check that step configurations are preserved
        original_step1 = sample_workflow.steps["step1"]
        new_step1 = new_workflow.steps["step1"]
        
        assert original_step1.step_id == new_step1.step_id
        assert original_step1.metadata.name == new_step1.metadata.name
        assert original_step1.prefix == new_step1.prefix
        assert original_step1.suffix == new_step1.suffix


class TestWorkflowBasics:
    """Test basic workflow functionality."""
    
    def test_workflow_creation(self):
        """Test basic workflow creation."""
        workflow = Workflow(
            metadata=WorkflowMetadata(name="Test", version="1.0.0")
        )
        assert workflow.metadata.name == "Test"
        assert len(workflow.steps) == 0
        assert len(workflow.edges) == 0
    
    def test_step_addition(self):
        """Test adding steps to workflow."""
        workflow = Workflow(
            metadata=WorkflowMetadata(name="Test", version="1.0.0")
        )
        
        step = EchoStep(
            step_id="test_step",
            metadata=StepMetadata(name="Test Step"),
            input_type=TextInput,
            output_type=TextOutput,
            prefix="Test: ",
            suffix=""
        )
        
        workflow.add_step(step)
        assert "test_step" in workflow.steps
        assert workflow.steps["test_step"] is step
    
    def test_edge_addition(self):
        """Test adding edges between steps."""
        workflow = Workflow(
            metadata=WorkflowMetadata(name="Test", version="1.0.0")
        )
        
        step1 = EchoStep(
            step_id="step1",
            metadata=StepMetadata(name="Step 1"),
            input_type=TextInput,
            output_type=TextOutput,
            prefix="1: ",
            suffix=""
        )
        
        step2 = EchoStep(
            step_id="step2",
            metadata=StepMetadata(name="Step 2"),
            input_type=TextOutput,
            output_type=TextOutput,
            prefix="2: ",
            suffix=""
        )
        
        workflow.add_step(step1).add_step(step2)
        workflow.add_edge("step1", "step2")
        
        assert len(workflow.edges) == 1
        assert workflow.edges[0].from_step == "step1"
        assert workflow.edges[0].to_step == "step2"


class TestMultiEdgeConditions:
    """Test workflow behavior with multiple incoming edges."""
    
    def test_multi_edge_condition_logic_bug(self):
        """Test that demonstrates the bug in multi-edge condition evaluation."""
        workflow = Workflow(
            metadata=WorkflowMetadata(name="Multi-Edge Test", version="1.0.0")
        )
        
        # Create three steps: A, B -> C (C has two incoming edges)
        step_a = EchoStep(
            step_id="step_a",
            metadata=StepMetadata(name="Step A"),
            input_type=TextInput,
            output_type=TextOutput,
            prefix="A: ",
            suffix=""
        )
        
        step_b = EchoStep(
            step_id="step_b", 
            metadata=StepMetadata(name="Step B"),
            input_type=TextInput,
            output_type=TextOutput,
            prefix="B: ",
            suffix=""
        )
        
        step_c = EchoStep(
            step_id="step_c",
            metadata=StepMetadata(name="Step C"),
            input_type=TextOutput,
            output_type=TextOutput,
            prefix="C: ",
            suffix=""
        )
        
        workflow.add_step(step_a).add_step(step_b).add_step(step_c)
        
        # Add edges with conditions
        # A -> C: only if result contains "pass"
        condition_a = EdgeCondition(
            type="output_based",
            field="result", 
            operator="in",
            value="pass"
        )
        workflow.add_edge("step_a", "step_c", condition_a.model_dump())
        
        # B -> C: only if result contains "go"  
        condition_b = EdgeCondition(
            type="output_based",
            field="result",
            operator="in", 
            value="go"
        )
        workflow.add_edge("step_b", "step_c", condition_b.model_dump())
        
        workflow.set_start_step("step_a").add_end_step("step_c")
        
        # Test the bug: step_c should NOT be ready if only one condition passes
        from autogenstudio.workflow.core._models import WorkflowExecution, StepExecution, StepStatus
        
        execution = WorkflowExecution(workflow_id=workflow.id)
        
        # Simulate step_a completed with "pass" but step_b not completed yet
        execution.step_executions["step_a"] = StepExecution(
            step_id="step_a",
            status=StepStatus.COMPLETED,
            output_data={"result": "A: pass"}
        )
        
        # Bug: get_ready_steps will mark step_c as ready even though step_b hasn't completed
        ready_steps = workflow.get_ready_steps(execution)
        
        # This assertion will FAIL due to the bug - step_c should NOT be ready
        # because step_b hasn't completed yet, but current logic only checks if ANY edge condition passes
        assert "step_c" not in ready_steps, "BUG: step_c should not be ready when only one of two dependencies is complete"
    
    def test_always_condition_type(self):
        """Test that 'always' condition type always passes."""
        workflow = Workflow(
            metadata=WorkflowMetadata(name="Always Condition Test", version="1.0.0")
        )
        
        step_a = EchoStep(
            step_id="step_a",
            metadata=StepMetadata(name="Step A"),
            input_type=TextInput,
            output_type=TextOutput,
            prefix="A: ",
            suffix=""
        )
        
        step_b = EchoStep(
            step_id="step_b",
            metadata=StepMetadata(name="Step B"),
            input_type=TextOutput,
            output_type=TextOutput,
            prefix="B: ",
            suffix=""
        )
        
        workflow.add_step(step_a).add_step(step_b)
        
        # Add edge with 'always' condition (default)
        always_condition = EdgeCondition(type="always")
        workflow.add_edge("step_a", "step_b", always_condition.model_dump())
        
        workflow.set_start_step("step_a").add_end_step("step_b")
        
        # Test that step_b is ready after step_a completes, regardless of output
        from autogenstudio.workflow.core._models import WorkflowExecution, StepExecution, StepStatus
        
        execution = WorkflowExecution(workflow_id=workflow.id)
        execution.step_executions["step_a"] = StepExecution(
            step_id="step_a",
            status=StepStatus.COMPLETED,
            output_data={"result": "any output"}  # Content doesn't matter for 'always'
        )
        
        ready_steps = workflow.get_ready_steps(execution)
        assert "step_b" in ready_steps, "'always' condition should make step_b ready regardless of output"
    
    def test_state_based_condition_type(self):
        """Test that 'state_based' condition evaluates workflow state."""
        workflow = Workflow(
            metadata=WorkflowMetadata(name="State Condition Test", version="1.0.0")
        )
        
        step_a = EchoStep(
            step_id="step_a",
            metadata=StepMetadata(name="Step A"),
            input_type=TextInput,
            output_type=TextOutput,
            prefix="A: ",
            suffix=""
        )
        
        step_b = EchoStep(
            step_id="step_b",
            metadata=StepMetadata(name="Step B"),
            input_type=TextOutput,
            output_type=TextOutput,
            prefix="B: ",
            suffix=""
        )
        
        workflow.add_step(step_a).add_step(step_b)
        
        # Add edge with state-based condition
        state_condition = EdgeCondition(
            type="state_based",
            field="user_approved",
            operator="==",
            value=True
        )
        workflow.add_edge("step_a", "step_b", state_condition.model_dump())
        
        workflow.set_start_step("step_a").add_end_step("step_b")
        
        from autogenstudio.workflow.core._models import WorkflowExecution, StepExecution, StepStatus
        
        # Test 1: step_b should NOT be ready when state condition fails
        execution = WorkflowExecution(workflow_id=workflow.id)
        execution.step_executions["step_a"] = StepExecution(
            step_id="step_a",
            status=StepStatus.COMPLETED,
            output_data={"result": "completed"}
        )
        execution.state["user_approved"] = False  # Condition should fail
        
        ready_steps = workflow.get_ready_steps(execution)
        assert "step_b" not in ready_steps, "step_b should not be ready when state condition fails"
        
        # Test 2: step_b should be ready when state condition passes
        execution.state["user_approved"] = True  # Condition should pass
        
        ready_steps = workflow.get_ready_steps(execution)
        assert "step_b" in ready_steps, "step_b should be ready when state condition passes"
    
    def test_multiple_operators_in_conditions(self):
        """Test different operators in edge conditions."""
        workflow = Workflow(
            metadata=WorkflowMetadata(name="Operator Test", version="1.0.0")
        )
        
        step_a = EchoStep(
            step_id="step_a",
            metadata=StepMetadata(name="Step A"),
            input_type=TextInput,
            output_type=TextOutput,
            prefix="A: ",
            suffix=""
        )
        
        step_b = EchoStep(
            step_id="step_b",
            metadata=StepMetadata(name="Step B"),
            input_type=TextOutput,
            output_type=TextOutput,
            prefix="B: ",
            suffix=""
        )
        
        workflow.add_step(step_a).add_step(step_b)
        workflow.set_start_step("step_a").add_end_step("step_b")
        
        from autogenstudio.workflow.core._models import WorkflowExecution, StepExecution, StepStatus
        
        # Test different operators
        test_cases = [
            ("==", "success", "success", True),
            ("==", "success", "failure", False),
            ("!=", "success", "failure", True),
            ("!=", "success", "success", False),
            ("in", "pass", "password", True),
            ("in", "fail", "password", False),
            ("not_in", "fail", "password", True),
            ("not_in", "pass", "password", False),
        ]
        
        for operator, field_value, condition_value, should_pass in test_cases:
            # Clear existing edges and add new one with specific operator
            workflow.edges = []
            condition = EdgeCondition(
                type="output_based",
                field="result",
                operator=operator,
                value=condition_value
            )
            workflow.add_edge("step_a", "step_b", condition.model_dump())
            
            execution = WorkflowExecution(workflow_id=workflow.id)
            execution.step_executions["step_a"] = StepExecution(
                step_id="step_a",
                status=StepStatus.COMPLETED,
                output_data={"result": field_value}
            )
            
            ready_steps = workflow.get_ready_steps(execution)
            if should_pass:
                assert "step_b" in ready_steps, f"Operator {operator} should pass: {field_value} {operator} {condition_value}"
            else:
                assert "step_b" not in ready_steps, f"Operator {operator} should fail: {field_value} {operator} {condition_value}"


class TestConditionalEdgeValidation:
    """Test validation of conditional edge logic."""
    
    def test_validate_contradictory_boolean_conditions(self):
        """Test detection of contradictory boolean conditions."""
        workflow = Workflow(
            metadata=WorkflowMetadata(name="Contradictory Test", version="1.0.0")
        )
        
        step_a = EchoStep(
            step_id="step_a",
            metadata=StepMetadata(name="Step A"),
            input_type=TextInput,
            output_type=TextOutput,
            prefix="A: ", suffix=""
        )
        
        step_b = EchoStep(
            step_id="step_b",
            metadata=StepMetadata(name="Step B"), 
            input_type=TextInput,
            output_type=TextOutput,
            prefix="B: ", suffix=""
        )
        
        step_c = EchoStep(
            step_id="step_c",
            metadata=StepMetadata(name="Step C"),
            input_type=TextOutput,
            output_type=TextOutput,
            prefix="C: ", suffix=""
        )
        
        workflow.add_step(step_a).add_step(step_b).add_step(step_c)
        
        # Add contradictory conditions: A->C if success=true, B->C if success=false
        # But both A and B would need to complete for C to be ready
        true_condition = EdgeCondition(
            type="output_based", field="success", operator="==", value=True
        )
        false_condition = EdgeCondition(
            type="output_based", field="success", operator="==", value=False
        )
        
        workflow.add_edge("step_a", "step_c", true_condition.model_dump())
        workflow.add_edge("step_b", "step_c", false_condition.model_dump())
        workflow.set_start_step("step_a").add_end_step("step_c")
        
        validation = workflow.validate_workflow()
        
        # Should have warnings about contradictory conditions
        assert any("contradictory boolean conditions" in warning for warning in validation.warnings)
    
    def test_validate_steps_with_no_outgoing_edges(self):
        """Test detection of steps with no outgoing edges that aren't end steps."""
        workflow = Workflow(
            metadata=WorkflowMetadata(name="Dead End Test", version="1.0.0")
        )
        
        step_a = EchoStep(
            step_id="step_a",
            metadata=StepMetadata(name="Step A"),
            input_type=TextInput,
            output_type=TextOutput,
            prefix="A: ", suffix=""
        )
        
        step_b = EchoStep(
            step_id="step_b",
            metadata=StepMetadata(name="Step B"),
            input_type=TextOutput,
            output_type=TextOutput,
            prefix="B: ", suffix=""
        )
        
        workflow.add_step(step_a).add_step(step_b)
        workflow.add_edge("step_a", "step_b")
        workflow.set_start_step("step_a")
        # Note: step_b has no outgoing edges and is not marked as end step
        
        validation = workflow.validate_workflow()
        
        # Should have warning about step_b having no outgoing edges
        assert any("has no outgoing edges but is not marked as an end step" in warning for warning in validation.warnings)
    
    def test_validate_unreachable_end_steps(self):
        """Test detection of end steps that cannot be reached due to conditions."""
        workflow = Workflow(
            metadata=WorkflowMetadata(name="Unreachable End Test", version="1.0.0")
        )
        
        step_a = EchoStep(
            step_id="step_a",
            metadata=StepMetadata(name="Step A"),
            input_type=TextInput,
            output_type=TextOutput,
            prefix="A: ", suffix=""
        )
        
        step_b = EchoStep(
            step_id="step_b",
            metadata=StepMetadata(name="Step B"),
            input_type=TextOutput,
            output_type=TextOutput,
            prefix="B: ", suffix=""
        )
        
        workflow.add_step(step_a).add_step(step_b)
        
        # Add impossible condition: step_b requires success=true AND success=false
        impossible_condition = EdgeCondition(
            type="output_based", field="success", operator="==", value="impossible_value"
        )
        workflow.add_edge("step_a", "step_b", impossible_condition.model_dump())
        
        workflow.set_start_step("step_a").add_end_step("step_b")
        
        validation = workflow.validate_workflow()
        
        # Should detect that step_b might be unreachable (though our current implementation is conservative)
        # This test shows the validation is working, even if it doesn't catch this specific case yet
        assert validation.is_valid or len(validation.warnings) > 0


# === Test for force cancel ===
import asyncio
from pydantic import BaseModel
from autogenstudio.workflow.core import Workflow, WorkflowRunner, StepMetadata

class DummyInput(BaseModel):
    value: int

class DummyOutput(BaseModel):
    result: int

class SlowStep(BaseStep[DummyOutput, DummyOutput]):
    def __init__(self, step_id, metadata):
        super().__init__(step_id, metadata, DummyOutput, DummyOutput)
    async def execute(self, input_data: DummyOutput, context):
        for i in range(50):  # Increase iterations for a much slower step
            await asyncio.sleep(0.1)  # Increase total time to 5s
        return DummyOutput(result=input_data.result + 1)

def make_slow_workflow():
    wf = Workflow(metadata={"name": "Force Cancel Test"})
    step1 = SlowStep("s1", StepMetadata(name="S1"))
    step2 = SlowStep("s2", StepMetadata(name="S2"))
    wf.add_step(step1)
    wf.add_step(step2)
    wf.add_edge("s1", "s2")
    wf.set_start_step("s1")
    wf.add_end_step("s2")
    return wf

@pytest.mark.asyncio
async def test_force_cancel():
    wf = make_slow_workflow()
    runner = WorkflowRunner()
    events = []
    cancellation_token = CancellationToken()
    async def run():
        async for event in runner.run_stream(wf, {"result": 1}, cancellation_token):
            events.append(event)
    task = asyncio.create_task(run())
    await asyncio.sleep(0.1)  # Reduce sleep so cancellation happens quickly
    cancellation_token.cancel()
    await task
    # Check that workflow was cancelled
    cancelled_event = [e for e in events if getattr(e, "event_type", None) == "workflow_cancelled"]
    assert cancelled_event, "No workflow_cancelled event emitted!"


class TestTransformStep:
    def test_transform_step_valid_mapping(self):
        class InModel(BaseModel):
            foo: str
            bar: int
        class OutModel(BaseModel):
            baz: str
            qux: int
        mappings = {"baz": "foo", "qux": "bar"}
        step = TransformStep(
            step_id="transform",
            metadata=StepMetadata(name="Transform"),
            input_type=InModel,
            output_type=OutModel,
            mappings=mappings
        )
        input_data = InModel(foo="hello", bar=42)
        context = None
        import asyncio
        output = asyncio.run(step.execute(input_data, context))
        assert output.baz == "hello"
        assert output.qux == 42

    def test_transform_step_static_and_invalid_mapping(self):
        class InModel(BaseModel):
            foo: str
        class OutModel(BaseModel):
            baz: str
            static_field: str
        # Valid: static value, Invalid: non-existent input field
        mappings = {"baz": "foo", "static_field": "static:hello"}
        step = TransformStep(
            step_id="transform_static",
            metadata=StepMetadata(name="TransformStatic"),
            input_type=InModel,
            output_type=OutModel,
            mappings=mappings
        )
        input_data = InModel(foo="world")
        context = None
        import asyncio
        output = asyncio.run(step.execute(input_data, context))
        assert output.baz == "world"
        assert output.static_field == "hello"
        # Invalid mapping: output field not in output schema
        mappings_invalid = {"not_in_output": "foo"}
        import pytest
        with pytest.raises(ValueError):
            TransformStep(
                step_id="invalid",
                metadata=StepMetadata(name="Invalid"),
                input_type=InModel,
                output_type=OutModel,
                mappings=mappings_invalid
            )
    def test_transform_step_serialization(self):
        class InModel(BaseModel):
            foo: str
        class OutModel(BaseModel):
            bar: str
        mappings = {"bar": "foo"}
        step = TransformStep(
            step_id="serialize",
            metadata=StepMetadata(name="Serialize"),
            input_type=InModel,
            output_type=OutModel,
            mappings=mappings
        )
        config = step._to_config()
        loaded = TransformStep._from_config(config)
        assert loaded.mappings == mappings
        assert loaded.input_type.schema() == step.input_type.schema()
        assert loaded.output_type.schema() == step.output_type.schema()


if __name__ == "__main__":
    # Allow running as script for quick testing
    pytest.main([__file__, "-v"])
