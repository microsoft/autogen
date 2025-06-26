import React, { useState } from "react";
import {
  Modal,
  Form,
  Input,
  Select,
  Button,
  Space,
  Collapse,
  Alert,
} from "antd";
import { Plus, Trash2, Server, PlusCircle, MinusCircle } from "lucide-react";
import type { McpServer } from "./types";
import type {
  McpServerParams,
  StdioServerParams,
  SseServerParams,
  StreamableHttpServerParams,
} from "../../types/datamodel";

const { TextArea } = Input;
const { Option } = Select;
const { Panel } = Collapse;

interface McpServerCreateModalProps {
  open: boolean;
  onCancel: () => void;
  onCreateServer: (server: Omit<McpServer, "id">) => void;
}

export const McpServerCreateModal: React.FC<McpServerCreateModalProps> = ({
  open,
  onCancel,
  onCreateServer,
}) => {
  const [form] = Form.useForm();
  const [serverType, setServerType] = useState<
    "StdioServerParams" | "SseServerParams" | "StreamableHttpServerParams"
  >("StdioServerParams");
  const [args, setArgs] = useState<string[]>([]);
  const [envVars, setEnvVars] = useState<Array<{ key: string; value: string }>>(
    []
  );

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      let serverParams: McpServerParams;

      switch (serverType) {
        case "StdioServerParams":
          serverParams = {
            type: "StdioServerParams",
            command: values.command,
            args: args.length > 0 ? args : undefined,
            env:
              envVars.length > 0
                ? Object.fromEntries(envVars.map((env) => [env.key, env.value]))
                : undefined,
            read_timeout_seconds: values.read_timeout_seconds || 5,
          } as StdioServerParams;
          break;

        case "SseServerParams":
          serverParams = {
            type: "SseServerParams",
            url: values.url,
            timeout: values.timeout || 30,
            sse_read_timeout: values.sse_read_timeout || 300,
            headers: values.headers ? JSON.parse(values.headers) : undefined,
          } as SseServerParams;
          break;

        case "StreamableHttpServerParams":
          serverParams = {
            type: "StreamableHttpServerParams",
            url: values.url,
            timeout: values.timeout || 30,
            sse_read_timeout: values.sse_read_timeout || 300,
            headers: values.headers ? JSON.parse(values.headers) : undefined,
            terminate_on_close: values.terminate_on_close || false,
          } as StreamableHttpServerParams;
          break;

        default:
          throw new Error("Invalid server type");
      }

      const newServer: Omit<McpServer, "id"> = {
        name: values.name,
        description: values.description,
        serverParams,
        isConnected: false,
      };

      onCreateServer(newServer);
      handleReset();
    } catch (error) {
      console.error("Validation failed:", error);
    }
  };

  const handleReset = () => {
    form.resetFields();
    setArgs([]);
    setEnvVars([]);
    setServerType("StdioServerParams");
  };

  const handleCancel = () => {
    handleReset();
    onCancel();
  };

  const addArg = () => {
    setArgs([...args, ""]);
  };

  const removeArg = (index: number) => {
    setArgs(args.filter((_, i) => i !== index));
  };

  const updateArg = (index: number, value: string) => {
    const newArgs = [...args];
    newArgs[index] = value;
    setArgs(newArgs);
  };

  const addEnvVar = () => {
    setEnvVars([...envVars, { key: "", value: "" }]);
  };

  const removeEnvVar = (index: number) => {
    setEnvVars(envVars.filter((_, i) => i !== index));
  };

  const updateEnvVar = (
    index: number,
    field: "key" | "value",
    value: string
  ) => {
    const newEnvVars = [...envVars];
    newEnvVars[index] = { ...newEnvVars[index], [field]: value };
    setEnvVars(newEnvVars);
  };

  return (
    <Modal
      title={
        <div className="flex items-center gap-2">
          <Server className="w-5 h-5 text-accent" />
          <span>Add MCP Server</span>
        </div>
      }
      open={open}
      onCancel={handleCancel}
      footer={[
        <Button key="cancel" onClick={handleCancel}>
          Cancel
        </Button>,
        <Button key="submit" type="primary" onClick={handleSubmit}>
          Add Server
        </Button>,
      ]}
      width={600}
      destroyOnClose
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          read_timeout_seconds: 5,
          timeout: 30,
          sse_read_timeout: 300,
          terminate_on_close: false,
        }}
      >
        {/* Basic Information */}
        <Collapse defaultActiveKey={["basic"]} ghost>
          <Panel header="Basic Information" key="basic">
            <Form.Item
              label="Server Name"
              name="name"
              rules={[
                { required: true, message: "Please enter a server name" },
              ]}
            >
              <Input placeholder="e.g., My MCP Server" />
            </Form.Item>

            <Form.Item label="Description" name="description">
              <TextArea
                rows={2}
                placeholder="Optional description of the server"
              />
            </Form.Item>

            <Form.Item
              label="Server Type"
              name="type"
              rules={[
                { required: true, message: "Please select a server type" },
              ]}
            >
              <Select
                value={serverType}
                onChange={setServerType}
                placeholder="Select server type"
              >
                <Option value="StdioServerParams">
                  <div className="flex items-center gap-2">
                    <span>Standard I/O</span>
                    <small className="text-gray-500">
                      (Local command execution)
                    </small>
                  </div>
                </Option>
                <Option value="SseServerParams">
                  <div className="flex items-center gap-2">
                    <span>Server-Sent Events</span>
                    <small className="text-gray-500">(HTTP SSE)</small>
                  </div>
                </Option>
                <Option value="StreamableHttpServerParams">
                  <div className="flex items-center gap-2">
                    <span>Streamable HTTP</span>
                    <small className="text-gray-500">(HTTP streaming)</small>
                  </div>
                </Option>
              </Select>
            </Form.Item>
          </Panel>
        </Collapse>

        {/* Server Configuration */}
        <Collapse className="mt-4" ghost>
          <Panel header="Server Configuration" key="config">
            {serverType === "StdioServerParams" && (
              <div className="space-y-4">
                <Form.Item
                  label="Command"
                  name="command"
                  rules={[
                    { required: true, message: "Please enter a command" },
                  ]}
                >
                  <Input placeholder="e.g., uvx, python, node" />
                </Form.Item>

                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="block text-sm font-medium">
                      Arguments
                    </label>
                    <Button
                      type="dashed"
                      size="small"
                      icon={<PlusCircle className="w-4 h-4" />}
                      onClick={addArg}
                    >
                      Add Argument
                    </Button>
                  </div>

                  {args.length === 0 ? (
                    <div className="text-sm text-gray-500 italic p-3 border border-dashed rounded">
                      No arguments. Click "Add Argument" to add command line
                      arguments.
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {args.map((arg, index) => (
                        <div key={index} className="flex items-center gap-2">
                          <span className="text-xs text-gray-500 w-8">
                            {index}
                          </span>
                          <Input
                            value={arg}
                            onChange={(e) => updateArg(index, e.target.value)}
                            placeholder={`Argument ${index}`}
                            className="flex-1"
                          />
                          <Button
                            type="text"
                            size="small"
                            icon={<Trash2 className="w-4 h-4" />}
                            onClick={() => removeArg(index)}
                            className="text-red-500 hover:text-red-700"
                          />
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="block text-sm font-medium">
                      Environment Variables
                    </label>
                    <Button
                      type="dashed"
                      size="small"
                      icon={<PlusCircle className="w-4 h-4" />}
                      onClick={addEnvVar}
                    >
                      Add Variable
                    </Button>
                  </div>

                  {envVars.length === 0 ? (
                    <div className="text-sm text-gray-500 italic p-3 border border-dashed rounded">
                      No environment variables. Click "Add Variable" to add
                      environment variables.
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {envVars.map((env, index) => (
                        <div key={index} className="flex items-center gap-2">
                          <Input
                            value={env.key}
                            onChange={(e) =>
                              updateEnvVar(index, "key", e.target.value)
                            }
                            placeholder="Variable name"
                            className="flex-1"
                          />
                          <span>=</span>
                          <Input
                            value={env.value}
                            onChange={(e) =>
                              updateEnvVar(index, "value", e.target.value)
                            }
                            placeholder="Variable value"
                            className="flex-1"
                          />
                          <Button
                            type="text"
                            size="small"
                            icon={<MinusCircle className="w-4 h-4" />}
                            onClick={() => removeEnvVar(index)}
                            className="text-red-500 hover:text-red-700"
                          />
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <Form.Item
                  label="Read Timeout (seconds)"
                  name="read_timeout_seconds"
                >
                  <Input type="number" min={1} />
                </Form.Item>
              </div>
            )}

            {(serverType === "SseServerParams" ||
              serverType === "StreamableHttpServerParams") && (
              <div className="space-y-4">
                <Form.Item
                  label="Server URL"
                  name="url"
                  rules={[
                    { required: true, message: "Please enter a server URL" },
                    { type: "url", message: "Please enter a valid URL" },
                  ]}
                >
                  <Input placeholder="https://your-mcp-server.com" />
                </Form.Item>

                <Form.Item label="Timeout (seconds)" name="timeout">
                  <Input type="number" min={1} />
                </Form.Item>

                <Form.Item
                  label="SSE Read Timeout (seconds)"
                  name="sse_read_timeout"
                >
                  <Input type="number" min={1} />
                </Form.Item>

                <Form.Item label="Headers (JSON)" name="headers">
                  <TextArea
                    rows={3}
                    placeholder='{"Authorization": "Bearer token", "Content-Type": "application/json"}'
                  />
                </Form.Item>

                {serverType === "StreamableHttpServerParams" && (
                  <Form.Item
                    label="Terminate on Close"
                    name="terminate_on_close"
                    valuePropName="checked"
                  >
                    <Input type="checkbox" />
                  </Form.Item>
                )}
              </div>
            )}
          </Panel>
        </Collapse>

        <Alert
          className="mt-4"
          message="Server Configuration"
          description="Configure your MCP server connection parameters. For StdIO servers, specify the command and arguments. For HTTP-based servers, provide the server URL and connection settings."
          type="info"
          showIcon
        />
      </Form>
    </Modal>
  );
};
