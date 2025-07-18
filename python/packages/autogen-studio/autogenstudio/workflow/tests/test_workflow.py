"""
Test workflow type validation and serialization.
"""
import pytest
from typing import Any, Dict
from pydantic import BaseModel

from autogenstudio.workflow.steps import EchoStep
from autogenstudio.workflow.core import Workflow, WorkflowRunner, StepMetadata, WorkflowMetadata


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


if __name__ == "__main__":
    # Allow running as script for quick testing
    pytest.main([__file__, "-v"])
