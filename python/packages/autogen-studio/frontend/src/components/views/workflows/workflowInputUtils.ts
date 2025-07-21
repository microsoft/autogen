/**
 * Utilities for generating dynamic input forms based on workflow schemas
 */

interface WorkflowInputField {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'array';
  required: boolean;
  default?: any;
  enum?: string[];
  description?: string;
  examples?: any[];
  title?: string;
}

/**
 * Extract input schema from a workflow's start step
 */
export function extractWorkflowInputSchema(workflow: any): WorkflowInputField[] {
  try {
    // Handle both backend API response format and direct workflow config
    const config = workflow?.config?.config || workflow?.config;
    if (!config?.steps?.length || !config.start_step_id) {
      console.warn('No steps or start_step_id found, using message fallback');
      return [{
        name: 'message',
        type: 'string',
        required: true,
        description: 'Message to process',
        title: 'Message'
      }];
    }

    // Find the start step - handle both component format and direct config format
    const startStep = config.steps.find((step: any) => {
      // Handle Component<StepConfig> format from backend
      const stepId = step.config?.step_id || step.step_id;
      return stepId === config.start_step_id;
    });

    if (!startStep) {
      console.warn(`Start step '${config.start_step_id}' not found, using message fallback`);
      return [{
        name: 'message',
        type: 'string',
        required: true,
        description: 'Message to process',
        title: 'Message'
      }];
    }

    // Extract input schema - handle both component and direct formats
    const stepConfig = startStep.config || startStep;
    const inputSchema = stepConfig.input_schema;
    
    if (!inputSchema?.properties) {
      console.warn('No input_schema.properties found, using message fallback');
      return [{
        name: 'message',
        type: 'string',
        required: true,
        description: 'Message to process',
        title: 'Message'
      }];
    }

    const properties = inputSchema.properties;
    const required = inputSchema.required || [];

    console.log('Successfully extracted input schema:', { properties, required });
    
    return Object.entries(properties).map(([fieldName, fieldSchema]: [string, any]) => ({
      name: fieldName,
      type: mapJsonTypeToInputType(fieldSchema.type),
      required: required.includes(fieldName),
      default: fieldSchema.default,
      // Use enum if present, otherwise use examples as enum for string fields with limited options
      enum: fieldSchema.enum || (fieldSchema.type === 'string' && fieldSchema.examples?.length ? fieldSchema.examples : undefined),
      description: fieldSchema.description,
      examples: fieldSchema.examples,
      title: fieldSchema.title || fieldName
    }));
  } catch (error) {
    console.warn('Error extracting workflow input schema:', error);
    // Fallback to simple message input
    return [{
      name: 'message',
      type: 'string',
      required: true,
      description: 'Message to process',
      title: 'Message'
    }];
  }
}

/**
 * Map JSON schema types to input field types
 */
function mapJsonTypeToInputType(jsonType: string): 'string' | 'number' | 'boolean' | 'array' {
  switch (jsonType) {
    case 'integer':
    case 'number':
      return 'number';
    case 'boolean':
      return 'boolean';
    case 'array':
      return 'array';
    default:
      return 'string';
  }
}

/**
 * Generate default input values from schema
 */
export function generateDefaultInputValues(inputFields: WorkflowInputField[]): Record<string, any> {
  const defaultValues: Record<string, any> = {};
  
  inputFields.forEach(field => {
    if (field.default !== undefined) {
      defaultValues[field.name] = field.default;
    } else if (field.required) {
      // Provide sensible defaults for required fields
      switch (field.type) {
        case 'string':
          defaultValues[field.name] = field.enum?.[0] || '';
          break;
        case 'number':
          defaultValues[field.name] = 0;
          break;
        case 'boolean':
          defaultValues[field.name] = false;
          break;
        case 'array':
          defaultValues[field.name] = [];
          break;
      }
    }
  });

  return defaultValues;
}

/**
 * Validate input values against schema
 */
export function validateInputValues(
  inputFields: WorkflowInputField[], 
  values: Record<string, any>
): { isValid: boolean; errors: string[] } {
  const errors: string[] = [];

  inputFields.forEach(field => {
    const value = values[field.name];
    
    // Check required fields
    if (field.required && (value === undefined || value === null || value === '')) {
      errors.push(`${field.title || field.name} is required`);
      return;
    }

    // Skip validation for empty optional fields
    if (!field.required && (value === undefined || value === null || value === '')) {
      return;
    }

    // Type validation
    switch (field.type) {
      case 'number':
        if (isNaN(Number(value))) {
          errors.push(`${field.title || field.name} must be a number`);
        }
        break;
      case 'boolean':
        if (typeof value !== 'boolean') {
          errors.push(`${field.title || field.name} must be true or false`);
        }
        break;
      case 'string':
        if (field.enum && !field.enum.includes(value)) {
          errors.push(`${field.title || field.name} must be one of: ${field.enum.join(', ')}`);
        }
        break;
    }
  });

  return {
    isValid: errors.length === 0,
    errors
  };
}

export type { WorkflowInputField };