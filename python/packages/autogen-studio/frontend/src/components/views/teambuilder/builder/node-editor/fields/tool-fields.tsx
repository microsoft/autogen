import React, { useRef, useState } from "react";
import { Form, Input, Switch, Select, Button, Space } from "antd";
import { PlusCircle, MinusCircle } from "lucide-react";
import { Import } from "../../../../../types/datamodel";
import { isFunctionTool } from "../../../../../types/guards";
import { MonacoEditor } from "../../../../monaco";
import { NodeEditorFieldsProps } from "./fields";

const { TextArea } = Input;
const { Option } = Select;

interface ImportState {
  module: string;
  imports: string;
}

export const ToolFields: React.FC<
  Omit<NodeEditorFieldsProps, "onNavigate">
> = ({
  component,
  workingCopy,
  setWorkingCopy,
  editPath,
  updateComponentAtPath,
  getCurrentComponent,
}) => {
  if (!component || !isFunctionTool(component)) return null;

  const editorRef = useRef(null);
  const [showAddImport, setShowAddImport] = useState(false);
  const [importType, setImportType] = useState<"direct" | "fromModule">(
    "direct"
  );
  const [directImport, setDirectImport] = useState("");
  const [moduleImport, setModuleImport] = useState<ImportState>({
    module: "",
    imports: "",
  });

  const formatImport = (imp: Import): string => {
    if (!imp) return "";
    if (typeof imp === "string") {
      return imp;
    }
    return `from ${imp.module} import ${imp.imports.join(", ")}`;
  };

  const handleAddImport = (form: { add: (value: string | Import) => void }) => {
    if (importType === "direct" && directImport) {
      form.add(directImport);
      setDirectImport("");
    } else if (
      importType === "fromModule" &&
      moduleImport.module &&
      moduleImport.imports
    ) {
      form.add({
        module: moduleImport.module,
        imports: moduleImport.imports
          .split(",")
          .map((i) => i.trim())
          .filter((i) => i),
      });
      setModuleImport({ module: "", imports: "" });
    }
    setShowAddImport(false);
  };

  return (
    <>
      <Form.Item
        label="Name"
        name={["config", "name"]}
        rules={[{ required: true }]}
      >
        <Input />
      </Form.Item>

      <Form.Item
        label="Description"
        name={["config", "description"]}
        rules={[{ required: true }]}
      >
        <TextArea rows={4} />
      </Form.Item>

      <Form.Item label="Global Imports">
        <div className="space-y-2">
          <Form.List name={["config", "global_imports"]}>
            {(fields, { add, remove }) => (
              <div className="space-y-2">
                {/* Existing Imports */}
                <div className="flex flex-wrap gap-2">
                  {fields.map((field) => (
                    <div
                      key={field.key}
                      className="flex items-center gap-2 bg-tertiary rounded px-2 py-1"
                    >
                      <Form.Item {...field} noStyle>
                        <Input type="hidden" />
                      </Form.Item>
                      <Form.Item
                        shouldUpdate={(prevValues, curValues) => {
                          const prevImport =
                            prevValues.config?.global_imports?.[field.name];
                          const curImport =
                            curValues.config?.global_imports?.[field.name];
                          return (
                            JSON.stringify(prevImport) !==
                            JSON.stringify(curImport)
                          );
                        }}
                        noStyle
                      >
                        {({ getFieldValue }) => {
                          const imp = getFieldValue([
                            "config",
                            "global_imports",
                            field.name,
                          ]);
                          return (
                            <span className="text-sm">{formatImport(imp)}</span>
                          );
                        }}
                      </Form.Item>
                      <Button
                        type="text"
                        size="small"
                        className="flex items-center justify-center h-6 w-6 p-0"
                        onClick={() => remove(field.name)}
                        icon={<MinusCircle className="h-4 w-4" />}
                      />
                    </div>
                  ))}
                </div>

                {/* Add Import UI */}
                {showAddImport ? (
                  <div className="border rounded p-3 space-y-3">
                    <Form.Item className="mb-2">
                      <Select
                        value={importType}
                        onChange={setImportType}
                        style={{ width: 200 }}
                      >
                        <Option value="direct">Direct Import</Option>
                        <Option value="fromModule">From Module Import</Option>
                      </Select>
                    </Form.Item>

                    {importType === "direct" ? (
                      <Space>
                        <Input
                          placeholder="Package name (e.g., os)"
                          className="w-64"
                          value={directImport}
                          onChange={(e) => setDirectImport(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter" && directImport) {
                              handleAddImport({ add });
                            }
                          }}
                        />
                        <Button
                          onClick={() => handleAddImport({ add })}
                          disabled={!directImport}
                        >
                          Add
                        </Button>
                      </Space>
                    ) : (
                      <Space direction="vertical" className="w-full">
                        <Input
                          placeholder="Module name (e.g., typing)"
                          className="w-64"
                          value={moduleImport.module}
                          onChange={(e) =>
                            setModuleImport((prev) => ({
                              ...prev,
                              module: e.target.value,
                            }))
                          }
                        />
                        <Space className="w-full">
                          <Input
                            placeholder="Import names (comma-separated)"
                            className="w-64"
                            value={moduleImport.imports}
                            onChange={(e) =>
                              setModuleImport((prev) => ({
                                ...prev,
                                imports: e.target.value,
                              }))
                            }
                            onKeyDown={(e) => {
                              if (
                                e.key === "Enter" &&
                                moduleImport.module &&
                                moduleImport.imports
                              ) {
                                handleAddImport({ add });
                              }
                            }}
                          />
                          <Button
                            onClick={() => handleAddImport({ add })}
                            disabled={
                              !moduleImport.module || !moduleImport.imports
                            }
                          >
                            Add
                          </Button>
                        </Space>
                      </Space>
                    )}
                  </div>
                ) : (
                  <Button
                    type="dashed"
                    onClick={() => setShowAddImport(true)}
                    className="w-full"
                  >
                    <PlusCircle className="h-4 w-4 mr-2" />
                    Add Import
                  </Button>
                )}
              </div>
            )}
          </Form.List>
        </div>
      </Form.Item>

      <Form.Item
        label="Source Code"
        name={["config", "source_code"]}
        rules={[{ required: true }]}
      >
        <div className="h-96">
          <Form.Item noStyle shouldUpdate>
            {({ getFieldValue, setFieldValue }) => (
              <MonacoEditor
                value={getFieldValue(["config", "source_code"]) || ""}
                editorRef={editorRef}
                language="python"
                onChange={(value) =>
                  setFieldValue(["config", "source_code"], value)
                }
              />
            )}
          </Form.Item>
        </div>
      </Form.Item>

      <Form.Item
        label="Has Cancellation Support"
        name={["config", "has_cancellation_support"]}
        valuePropName="checked"
      >
        <Switch />
      </Form.Item>
    </>
  );
};

export default ToolFields;
