import React, { useState, useEffect } from "react";
import {
  Modal,
  Button,
  Form,
  Input,
  Checkbox,
  InputNumber,
  Select,
  Space,
  Typography,
  Alert,
  Card,
} from "antd";
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  MessageSquare,
} from "lucide-react";
import {
  ElicitationRequest,
  ElicitationResponse,
} from "../../../../../../views/mcp/api";

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;

interface ElicitationDialogProps {
  request: ElicitationRequest | null;
  onResponse: (response: ElicitationResponse) => void;
  visible: boolean;
  onCancel: () => void;
}

interface FormFieldProps {
  name: string;
  schema: any;
  value: any;
  onChange: (name: string, value: any) => void;
  required?: boolean;
}

const FormField: React.FC<FormFieldProps> = ({
  name,
  schema,
  value,
  onChange,
  required = false,
}) => {
  const {
    type,
    description,
    minimum,
    maximum,
    enum: enumValues,
  } = schema || {};

  const handleChange = (newValue: any) => {
    onChange(name, newValue);
  };

  const renderField = () => {
    switch (type) {
      case "boolean":
        return (
          <Checkbox
            checked={value || false}
            onChange={(e) => handleChange(e.target.checked)}
          >
            {description || name}
          </Checkbox>
        );

      case "number":
      case "integer":
        return (
          <InputNumber
            value={value}
            onChange={handleChange}
            min={minimum}
            max={maximum}
            placeholder={description || name}
            style={{ width: "100%" }}
            step={type === "integer" ? 1 : 0.1}
          />
        );

      case "string":
        if (enumValues && Array.isArray(enumValues)) {
          return (
            <Select
              value={value}
              onChange={handleChange}
              placeholder={description || name}
              style={{ width: "100%" }}
            >
              {enumValues.map((option: any) => (
                <Option key={option} value={option}>
                  {option}
                </Option>
              ))}
            </Select>
          );
        }
        return (
          <Input
            value={value || ""}
            onChange={(e) => handleChange(e.target.value)}
            placeholder={description || name}
          />
        );

      default:
        return (
          <Input
            value={value || ""}
            onChange={(e) => handleChange(e.target.value)}
            placeholder={description || name}
          />
        );
    }
  };

  return (
    <Form.Item
      label={description || name}
      required={required}
      style={{ marginBottom: 16 }}
    >
      {renderField()}
    </Form.Item>
  );
};

export const ElicitationDialog: React.FC<ElicitationDialogProps> = ({
  request,
  onResponse,
  visible,
  onCancel,
}) => {
  const [formData, setFormData] = useState<Record<string, any>>({});
  const [isFormValid, setIsFormValid] = useState(false);
  const [timeoutWarning, setTimeoutWarning] = useState(false);

  // Reset form data when request changes
  useEffect(() => {
    if (request?.requestedSchema?.properties) {
      const initialData: Record<string, any> = {};
      Object.keys(request.requestedSchema.properties).forEach((key) => {
        const property = request.requestedSchema.properties[key];
        if (property.default !== undefined) {
          initialData[key] = property.default;
        } else if (property.type === "boolean") {
          initialData[key] = false;
        }
      });
      setFormData(initialData);
    } else {
      setFormData({});
    }
    setTimeoutWarning(false);
  }, [request]);

  // Validate form
  useEffect(() => {
    if (!request?.requestedSchema?.properties) {
      setIsFormValid(true);
      return;
    }

    const { properties, required = [] } = request.requestedSchema;
    const isValid = required.every((fieldName: string) => {
      const value = formData[fieldName];
      return value !== undefined && value !== null && value !== "";
    });

    setIsFormValid(isValid);
  }, [formData, request]);

  // Show timeout warning after 25 seconds
  useEffect(() => {
    if (!visible) return;

    const timer = setTimeout(() => {
      setTimeoutWarning(true);
    }, 25000);

    return () => clearTimeout(timer);
  }, [visible]);

  const handleFieldChange = (name: string, value: any) => {
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleAccept = () => {
    if (!request) return;

    const response: ElicitationResponse = {
      type: "elicitation_response",
      request_id: request.request_id,
      action: "accept",
      data: formData,
      session_id: request.session_id,
    };

    console.log("ElicitationDialog: Sending accept response:", response);
    onResponse(response);
  };

  const handleDecline = () => {
    if (!request) return;

    const response: ElicitationResponse = {
      type: "elicitation_response",
      request_id: request.request_id,
      action: "decline",
      session_id: request.session_id,
    };

    onResponse(response);
  };

  const handleCancel = () => {
    if (!request) return;

    const response: ElicitationResponse = {
      type: "elicitation_response",
      request_id: request.request_id,
      action: "cancel",
      session_id: request.session_id,
    };

    onResponse(response);
    onCancel();
  };

  if (!request) return null;

  const { requestedSchema } = request;
  const properties = requestedSchema?.properties || {};
  const required = requestedSchema?.required || [];

  return (
    <Modal
      title={
        <Space>
          <MessageSquare size={20} className="text-blue-600" />
          <span>Tool Request</span>
        </Space>
      }
      open={visible}
      onCancel={handleCancel}
      footer={null}
      width={600}
      maskClosable={false}
      destroyOnHidden
    >
      <Card>
        <Space direction="vertical" style={{ width: "100%" }} size="large">
          {/* Message */}
          <div>
            <Title level={4} style={{ marginBottom: 8 }}>
              Request Details
            </Title>
            <Paragraph>{request.message}</Paragraph>
          </div>

          {/* Timeout Warning */}
          {timeoutWarning && (
            <Alert
              message="Time Limit Warning"
              description="This request will timeout in 5 seconds. Please respond quickly."
              type="warning"
              icon={<AlertTriangle size={16} />}
              showIcon
            />
          )}

          {/* Form Fields */}
          {Object.keys(properties).length > 0 && (
            <div>
              <Title level={5} style={{ marginBottom: 16 }}>
                Required Information
              </Title>
              <Form layout="vertical">
                {Object.entries(properties).map(([fieldName, fieldSchema]) => (
                  <FormField
                    key={fieldName}
                    name={fieldName}
                    schema={fieldSchema}
                    value={formData[fieldName]}
                    onChange={handleFieldChange}
                    required={required.includes(fieldName)}
                  />
                ))}
              </Form>
            </div>
          )}

          {/* Actions */}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
            <Button onClick={handleCancel} size="large">
              Cancel
            </Button>
            <Button
              onClick={handleDecline}
              size="large"
              danger
              icon={<XCircle size={16} />}
            >
              Decline
            </Button>
            <Button
              onClick={handleAccept}
              type="primary"
              size="large"
              disabled={!isFormValid}
              icon={<CheckCircle size={16} />}
            >
              Accept
            </Button>
          </div>
        </Space>
      </Card>
    </Modal>
  );
};

// Elicitation notification badge component
interface ElicitationBadgeProps {
  count: number;
  onClick?: () => void;
}

export const ElicitationBadge: React.FC<ElicitationBadgeProps> = ({
  count,
  onClick,
}) => {
  if (count === 0) return null;

  return (
    <Button
      type="primary"
      size="small"
      onClick={onClick}
      style={{
        backgroundColor: "#f59e0b",
        borderColor: "#f59e0b",
        fontSize: "12px",
        height: "24px",
        padding: "0 8px",
      }}
    >
      {count} pending
    </Button>
  );
};
