import React, { useState, useEffect } from 'react';
import { Modal, Form, Input, Select, Checkbox, InputNumber, Button, Alert } from 'antd';
import { PlayCircleOutlined } from '@ant-design/icons';
import { 
  extractWorkflowInputSchema, 
  generateDefaultInputValues, 
  validateInputValues,
  WorkflowInputField 
} from './workflowInputUtils';

interface WorkflowInputFormProps {
  workflow: any;
  visible: boolean;
  onSubmit: (input: Record<string, any>) => void;
  onCancel: () => void;
  loading?: boolean;
}

export const WorkflowInputForm: React.FC<WorkflowInputFormProps> = ({
  workflow,
  visible,
  onSubmit,
  onCancel,
  loading = false
}) => {
  const [form] = Form.useForm();
  const [inputFields, setInputFields] = useState<WorkflowInputField[]>([]);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  // Extract input schema when workflow changes
  useEffect(() => {
    if (workflow) {
      const fields = extractWorkflowInputSchema(workflow);
      setInputFields(fields);
      
      // Set default values
      const defaultValues = generateDefaultInputValues(fields);
      form.setFieldsValue(defaultValues);
    }
  }, [workflow, form]);

  const handleSubmit = () => {
    form.validateFields().then(values => {
      // Additional validation using our schema
      const validation = validateInputValues(inputFields, values);
      
      if (!validation.isValid) {
        setValidationErrors(validation.errors);
        return;
      }

      setValidationErrors([]);
      onSubmit(values);
    }).catch(error => {
      console.error('Form validation failed:', error);
    });
  };

  const renderFormField = (field: WorkflowInputField) => {
    const { name, type, enum: enumValues, description, examples, required, title } = field;
    
    const rules = [
      { required, message: `${title || name} is required` }
    ];

    if (enumValues && enumValues.length > 0) {
      // Dropdown for enum fields (like priority)
      return (
        <Form.Item
          key={name}
          name={name}
          label={title || name.charAt(0).toUpperCase() + name.slice(1)}
          rules={rules}
          tooltip={description}
        >
          <Select
            placeholder={`Select ${title || name}`}
            options={enumValues.map(option => ({
              label: option.charAt(0).toUpperCase() + option.slice(1),
              value: option
            }))}
          />
        </Form.Item>
      );
    }
    
    if (type === 'boolean') {
      // Checkbox for boolean fields (like enable_validation)
      return (
        <Form.Item
          key={name}
          name={name}
          valuePropName="checked"
          label={title || name.charAt(0).toUpperCase() + name.slice(1)}
          tooltip={description}
        >
          <Checkbox>
            {description || `Enable ${title || name}`}
          </Checkbox>
        </Form.Item>
      );
    }
    
    if (type === 'number') {
      // Number input
      return (
        <Form.Item
          key={name}
          name={name}
          label={title || name.charAt(0).toUpperCase() + name.slice(1)}
          rules={[
            ...rules,
            { type: 'number', message: `${title || name} must be a number` }
          ]}
          tooltip={description}
        >
          <InputNumber
            style={{ width: '100%' }}
            placeholder={examples?.[0] || `Enter ${title || name}`}
          />
        </Form.Item>
      );
    }
    
    // Default to text input
    return (
      <Form.Item
        key={name}
        name={name}
        label={title || name.charAt(0).toUpperCase() + name.slice(1)}
        rules={rules}
        tooltip={description}
      >
        <Input
          placeholder={examples?.[0] || `Enter ${title || name}`}
        />
      </Form.Item>
    );
  };

  const workflowName = workflow?.config?.config?.name || 'Workflow';
  const workflowDescription = workflow?.config?.config?.description;

  return (
    <Modal
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <PlayCircleOutlined />
          <span>Run {workflowName}</span>
        </div>
      }
      open={visible}
      onCancel={onCancel}
      footer={[
        <Button key="cancel" onClick={onCancel}>
          Cancel
        </Button>,
        <Button 
          key="submit" 
          type="primary" 
          loading={loading}
          onClick={handleSubmit}
          icon={<PlayCircleOutlined />}
        >
          {loading ? 'Running...' : 'Run Workflow'}
        </Button>
      ]}
      width={600}
      destroyOnClose
    >
      <div style={{ marginBottom: 16 }}>
        {workflowDescription && (
          <p style={{ color: '#666', marginBottom: 16 }}>
            {workflowDescription}
          </p>
        )}
        
        {validationErrors.length > 0 && (
          <Alert
            message="Validation Error"
            description={
              <ul style={{ margin: 0, paddingLeft: 16 }}>
                {validationErrors.map((error, index) => (
                  <li key={index}>{error}</li>
                ))}
              </ul>
            }
            type="error"
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}
      </div>

      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
      >
        {inputFields.map(renderFormField)}
      </Form>
      
      {inputFields.length === 0 && (
        <div style={{ textAlign: 'center', padding: '20px 0', color: '#999' }}>
          No input parameters required for this workflow.
        </div>
      )}
    </Modal>
  );
};

export default WorkflowInputForm;