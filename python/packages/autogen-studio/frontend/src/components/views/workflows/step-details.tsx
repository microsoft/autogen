import React from "react";
import {
  Modal,
  Tabs,
  Descriptions,
  Tag,
  Button,
  Space,
  Typography,
} from "antd";
import {
  Bot,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Loader2,
  Settings,
  ArrowDownToLine,
  ArrowUpFromLine,
  History,
} from "lucide-react";
import { StepConfig, StepStatus, StepExecution } from "./types";

const { Text, Title } = Typography;
const { TabPane } = Tabs;

interface StepDetailsProps {
  step: StepConfig;
  executionData?: StepExecution;
  isOpen: boolean;
  onClose: () => void;
}

// Helper function to get step status configuration
const getStepStatusConfig = (status: StepStatus) => {
  switch (status) {
    case StepStatus.RUNNING:
      return {
        icon: Loader2,
        text: "Running",
        color: "text-blue-500",
        bgColor: "bg-blue-50",
        borderColor: "border-blue-200",
        animate: "animate-spin",
      };
    case StepStatus.COMPLETED:
      return {
        icon: CheckCircle,
        text: "Completed",
        color: "text-green-500",
        bgColor: "bg-green-50",
        borderColor: "border-green-200",
        animate: "",
      };
    case StepStatus.FAILED:
      return {
        icon: XCircle,
        text: "Failed",
        color: "text-red-500",
        bgColor: "bg-red-50",
        borderColor: "border-red-200",
        animate: "",
      };
    case StepStatus.CANCELLED:
      return {
        icon: AlertCircle,
        text: "Cancelled",
        color: "text-orange-500",
        bgColor: "bg-orange-50",
        borderColor: "border-orange-200",
        animate: "",
      };
    case StepStatus.SKIPPED:
      return {
        icon: AlertCircle,
        text: "Skipped",
        color: "text-orange-500",
        bgColor: "bg-orange-50",
        borderColor: "border-orange-200",
        animate: "",
      };
    case StepStatus.PENDING:
    default:
      return {
        icon: Clock,
        text: "Pending",
        color: "text-gray-500",
        bgColor: "bg-gray-50",
        borderColor: "border-gray-200",
        animate: "",
      };
  }
};

// Helper function to format JSON data
const formatJsonData = (data: any): string => {
  try {
    return JSON.stringify(data, null, 2);
  } catch {
    return String(data);
  }
};

// Helper function to calculate duration
const calculateDuration = (startTime?: string, endTime?: string): string => {
  if (!startTime) return "N/A";

  const start = new Date(startTime);
  const end = endTime ? new Date(endTime) : new Date();
  const duration = end.getTime() - start.getTime();

  if (duration < 1000) return `${duration}ms`;
  if (duration < 60000) return `${(duration / 1000).toFixed(1)}s`;
  return `${(duration / 60000).toFixed(1)}m`;
};

export const StepDetails: React.FC<StepDetailsProps> = ({
  step,
  executionData,
  isOpen,
  onClose,
}) => {
  const statusConfig = executionData?.status
    ? getStepStatusConfig(executionData.status)
    : null;
  const StatusIcon = statusConfig?.icon;

  return (
    <Modal
      title={
        <div className="flex items-center gap-3">
          <Bot className="w-5 h-5 text-accent" />
          <span className="text-lg font-medium">{step.metadata.name}</span>
          {statusConfig && StatusIcon && (
            <div
              className={`flex items-center gap-1.5 px-2 py-1 rounded-full border text-xs font-medium ${statusConfig.bgColor} ${statusConfig.borderColor} ${statusConfig.color}`}
            >
              <StatusIcon size={12} className={statusConfig.animate} />
              <span>{statusConfig.text}</span>
            </div>
          )}
        </div>
      }
      open={isOpen}
      onCancel={onClose}
      width="90%"
      style={{ top: 20 }}
      footer={[
        <Button key="close" onClick={onClose}>
          Close
        </Button>,
      ]}
      destroyOnClose
    >
      <Tabs defaultActiveKey="overview" size="large">
        {/* Overview Tab */}
        <TabPane
          tab={
            <span className="flex items-center gap-2">
              <Settings size={16} />
              Overview
            </span>
          }
          key="overview"
        >
          <div className="space-y-6">
            {/* Step Configuration */}
            <div>
              <Title level={4}>Step Configuration</Title>
              <Descriptions bordered column={2} size="small">
                <Descriptions.Item label="Step ID" span={1}>
                  <Text code>{step.step_id}</Text>
                </Descriptions.Item>
                <Descriptions.Item label="Input Type" span={1}>
                  <Text code>{step.input_type_name}</Text>
                </Descriptions.Item>
                <Descriptions.Item label="Output Type" span={1}>
                  <Text code>{step.output_type_name}</Text>
                </Descriptions.Item>
                <Descriptions.Item label="Max Retries" span={1}>
                  {step.metadata.max_retries || "None"}
                </Descriptions.Item>
                <Descriptions.Item label="Timeout" span={1}>
                  {step.metadata.timeout_seconds
                    ? `${step.metadata.timeout_seconds}s`
                    : "None"}
                </Descriptions.Item>
                <Descriptions.Item label="Tags" span={2}>
                  {step.metadata.tags?.length ? (
                    <Space>
                      {step.metadata.tags.map((tag, index) => (
                        <Tag key={index} color="blue">
                          {tag}
                        </Tag>
                      ))}
                    </Space>
                  ) : (
                    <Text type="secondary">No tags</Text>
                  )}
                </Descriptions.Item>
                <Descriptions.Item label="Description" span={2}>
                  {step.metadata.description || (
                    <Text type="secondary">No description</Text>
                  )}
                </Descriptions.Item>
              </Descriptions>
            </div>

            {/* Execution Status */}
            {executionData && (
              <div>
                <Title level={4}>Execution Status</Title>
                <Descriptions bordered column={2} size="small">
                  <Descriptions.Item label="Status" span={1}>
                    <div className="flex items-center gap-2">
                      {StatusIcon && (
                        <StatusIcon size={16} className={statusConfig?.color} />
                      )}
                      <span className={statusConfig?.color}>
                        {statusConfig?.text}
                      </span>
                    </div>
                  </Descriptions.Item>
                  <Descriptions.Item label="Retry Count" span={1}>
                    {executionData.retry_count}
                  </Descriptions.Item>
                  <Descriptions.Item label="Start Time" span={1}>
                    {executionData.start_time
                      ? new Date(executionData.start_time).toLocaleString()
                      : "N/A"}
                  </Descriptions.Item>
                  <Descriptions.Item label="End Time" span={1}>
                    {executionData.end_time
                      ? new Date(executionData.end_time).toLocaleString()
                      : "N/A"}
                  </Descriptions.Item>
                  <Descriptions.Item label="Duration" span={1}>
                    {calculateDuration(
                      executionData.start_time,
                      executionData.end_time
                    )}
                  </Descriptions.Item>
                  {executionData.error && (
                    <Descriptions.Item label="Error" span={2}>
                      <Text type="danger">{executionData.error}</Text>
                    </Descriptions.Item>
                  )}
                </Descriptions>
              </div>
            )}

            {/* Output Data - Show immediately if available */}
            {executionData?.output_data && (
              <div>
                <Title level={4}>Output Data</Title>
                <div className="bg-green-50 p-4 rounded border">
                  <pre className="text-sm overflow-auto max-h-64">
                    {formatJsonData(executionData.output_data)}
                  </pre>
                </div>
              </div>
            )}

            {/* Input Data - Show if available */}
            {executionData?.input_data && (
              <div>
                <Title level={4}>Input Data</Title>
                <div className="bg-blue-50 p-4 rounded border">
                  <pre className="text-sm overflow-auto max-h-64">
                    {formatJsonData(executionData.input_data)}
                  </pre>
                </div>
              </div>
            )}
          </div>
        </TabPane>

        {/* Schemas Tab */}
        <TabPane
          tab={
            <span className="flex items-center gap-2">
              <Settings size={16} />
              Schemas
            </span>
          }
          key="schemas"
        >
          <div className="space-y-6">
            {/* Input Schema */}
            <div>
              <Title level={4}>Input Schema</Title>
              <div className="bg-gray-50 p-4 rounded border">
                <pre className="text-sm overflow-auto max-h-64">
                  {formatJsonData(step.input_schema)}
                </pre>
              </div>
            </div>

            {/* Output Schema */}
            <div>
              <Title level={4}>Output Schema</Title>
              <div className="bg-gray-50 p-4 rounded border">
                <pre className="text-sm overflow-auto max-h-64">
                  {formatJsonData(step.output_schema)}
                </pre>
              </div>
            </div>

            {/* Note about execution data */}
            {executionData && (
              <div className="bg-gray-50 p-4 rounded border">
                <Text type="secondary">
                  💡 Execution data (input/output) is shown in the Overview tab
                  for quick access.
                </Text>
              </div>
            )}
          </div>
        </TabPane>

        {/* Configuration Tab */}
        <TabPane
          tab={
            <span className="flex items-center gap-2">
              <Settings size={16} />
              Configuration
            </span>
          }
          key="config"
        >
          <div className="space-y-4">
            <div>
              <Title level={4}>Full Step Configuration</Title>
              <div className="bg-gray-50 p-4 rounded border">
                <pre className="text-sm overflow-auto max-h-96">
                  {formatJsonData(step)}
                </pre>
              </div>
            </div>
          </div>
        </TabPane>
      </Tabs>
    </Modal>
  );
};

export default StepDetails;
