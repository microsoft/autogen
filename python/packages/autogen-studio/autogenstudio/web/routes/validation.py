# api/routes/validation.py

from fastapi import APIRouter
from ...validation.validation_service import ValidationService, ValidationRequest, ValidationResponse, ValidationError
from ...validation.component_test_service import ComponentTestService, ComponentTestResult, ComponentTestRequest

router = APIRouter()
 


@router.post("/")
async def validate_component(request: ValidationRequest) -> ValidationResponse:
    """Validate a component configuration"""
    try:
        return ValidationService.validate(request.component)
    except Exception as e:
        print(f"Validation error: {str(e)}")
        return ValidationResponse(
            is_valid=False,
            errors=[ValidationError(field="validation", error=str(e))],
            warnings=[]
        )


@router.post("/test")
async def test_component(request: ComponentTestRequest) -> ComponentTestResult:
    """Test a component functionality with appropriate inputs based on type"""
    # First validate the component configuration
    validation_result = ValidationService.validate(request.component)
    
    # Only proceed with testing if the component is valid
    if not validation_result.is_valid:
        return ComponentTestResult(
            status=False, 
            message="Component validation failed",
            logs=[e.error for e in validation_result.errors]
        )
    
    # If validation passed, run the functional test
    return await ComponentTestService.test_component(
        component=request.component,
        timeout=request.timeout if request.timeout else 60
    )