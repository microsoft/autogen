import React, { useCallback, useRef, useState } from "react";
import { Input, Switch, Select, Button, Space } from "antd";
import { PlusCircle, MinusCircle } from "lucide-react";
import {
  Component,
  ComponentConfig,
  Import,
} from "../../../../../types/datamodel";
import { isFunctionTool } from "../../../../../types/guards";
import { MonacoEditor } from "../../../../monaco";
import DetailGroup from "../detailgroup";

const { TextArea } = Input;
const { Option } = Select;

interface ToolFieldsProps {
  component: Component<ComponentConfig>;
  onChange: (updates: Partial<Component<ComponentConfig>>) => void;
}

interface ImportState {
  module: string;
  imports: string;
}

export const ToolFields: React.FC<ToolFieldsProps> = ({
  component,
  onChange,
}) => {
  if (!isFunctionTool(component)) return null;

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

  const handleComponentUpdate = useCallback(
    (updates: Partial<Component<ComponentConfig>>) => {
      onChange({
        ...component,
        ...updates,
        config: {
          ...component.config,
          ...(updates.config || {}),
        },
      });
    },
    [component, onChange]
  );

  const formatImport = (imp: Import): string => {
    if (!imp) return "";
    if (typeof imp === "string") {
      return imp;
    }
    return `from ${imp.module} import ${imp.imports.join(", ")}`;
  };

  const handleAddImport = () => {
    const currentImports = [...(component.config.global_imports || [])];

    if (importType === "direct" && directImport) {
      currentImports.push(directImport);
      setDirectImport("");
    } else if (
      importType === "fromModule" &&
      moduleImport.module &&
      moduleImport.imports
    ) {
      currentImports.push({
        module: moduleImport.module,
        imports: moduleImport.imports
          .split(",")
          .map((i) => i.trim())
          .filter((i) => i),
      });
      setModuleImport({ module: "", imports: "" });
    }

    handleComponentUpdate({
      config: {
        ...component.config,
        global_imports: currentImports,
      },
    });
    setShowAddImport(false);
  };

  const handleRemoveImport = (index: number) => {
    const newImports = [...(component.config.global_imports || [])];
    newImports.splice(index, 1);
    handleComponentUpdate({
      config: {
        ...component.config,
        global_imports: newImports,
      },
    });
  };

  return (
    <div className="space-y-6">
      <DetailGroup title="Component Details">
        <div className="space-y-4">
          <label className="block">
            <span className="text-sm font-medium text-gray-700">Name</span>
            <Input
              value={component.label || ""}
              onChange={(e) => handleComponentUpdate({ label: e.target.value })}
              placeholder="Tool name"
              className="mt-1"
            />
          </label>

          <label className="block">
            <span className="text-sm font-medium text-gray-700">
              Description
            </span>
            <TextArea
              value={component.description || ""}
              onChange={(e) =>
                handleComponentUpdate({ description: e.target.value })
              }
              placeholder="Tool description"
              rows={4}
              className="mt-1"
            />
          </label>
        </div>
      </DetailGroup>

      <DetailGroup title="Configuration">
        <div className="space-y-4">
          <label className="block">
            <span className="text-sm font-medium text-gray-700">
              Function Name
            </span>
            <Input
              value={component.config.name || ""}
              onChange={(e) =>
                handleComponentUpdate({
                  config: { ...component.config, name: e.target.value },
                })
              }
              placeholder="Function name"
              className="mt-1"
            />
          </label>

          <div className="space-y-2">
            <span className="text-sm font-medium text-gray-700">
              Global Imports
            </span>
            <div className="flex flex-wrap gap-2 mt-2">
              {(component.config.global_imports || []).map((imp, index) => (
                <div
                  key={index}
                  className="flex items-center gap-2 bg-tertiary rounded px-2 py-1"
                >
                  <span className="text-sm">{formatImport(imp)}</span>
                  <Button
                    type="text"
                    size="small"
                    className="flex items-center justify-center h-6 w-6 p-0"
                    onClick={() => handleRemoveImport(index)}
                    icon={<MinusCircle className="h-4 w-4" />}
                  />
                </div>
              ))}
            </div>

            {showAddImport ? (
              <div className="border rounded p-3 space-y-3">
                <Select
                  value={importType}
                  onChange={setImportType}
                  style={{ width: 200 }}
                >
                  <Option value="direct">Direct Import</Option>
                  <Option value="fromModule">From Module Import</Option>
                </Select>

                {importType === "direct" ? (
                  <Space>
                    <Input
                      placeholder="Package name (e.g., os)"
                      className="w-64"
                      value={directImport}
                      onChange={(e) => setDirectImport(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && directImport) {
                          handleAddImport();
                        }
                      }}
                    />
                    <Button onClick={handleAddImport} disabled={!directImport}>
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
                      />
                      <Button
                        onClick={handleAddImport}
                        disabled={!moduleImport.module || !moduleImport.imports}
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

          <label className="block">
            <span className="text-sm font-medium text-gray-700">
              Source Code
            </span>
            <div className="mt-1 h-96">
              <MonacoEditor
                value={component.config.source_code || ""}
                editorRef={editorRef}
                language="python"
                onChange={(value) =>
                  handleComponentUpdate({
                    config: { ...component.config, source_code: value },
                  })
                }
              />
            </div>
          </label>

          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-700">
              Has Cancellation Support
            </span>
            <Switch
              checked={component.config.has_cancellation_support || false}
              onChange={(checked) =>
                handleComponentUpdate({
                  config: {
                    ...component.config,
                    has_cancellation_support: checked,
                  },
                })
              }
            />
          </div>
        </div>
      </DetailGroup>
    </div>
  );
};

export default React.memo(ToolFields);
