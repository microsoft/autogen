import React, { useCallback, useState, useRef } from "react";
import { Input, Switch, Button, Tooltip, Collapse, InputNumber } from "antd";
import { Edit, HelpCircle, Trash2, PlusCircle, ChevronDown, ChevronRight } from "lucide-react";
import {
  Component,
  ComponentConfig,
  AgentConfig,
  FunctionToolConfig,
  StaticWorkbenchConfig,
  WorkbenchConfig,
} from "../../../../../types/datamodel";
import {
  isAssistantAgent,
  isUserProxyAgent,
  isWebSurferAgent,
  isStaticWorkbench,
  isMcpWorkbench,
} from "../../../../../types/guards";
import DetailGroup from "../detailgroup";

const { TextArea } = Input;

// Helper function to normalize workbench format (handle both single object and array)
const normalizeWorkbenches = (workbench: Component<WorkbenchConfig>[] | Component<WorkbenchConfig> | undefined): Component<WorkbenchConfig>[] => {
  if (!workbench) return [];
  return Array.isArray(workbench) ? workbench : [workbench];
};

interface AgentFieldsProps {
  component: Component<AgentConfig>;
  onChange: (updates: Partial<Component<ComponentConfig>>) => void;
  onNavigate?: (componentType: string, id: string, parentField: string) => void;
  workingCopy?: Component<ComponentConfig> | null;
  setWorkingCopy?: (component: Component<ComponentConfig> | null) => void;
  editPath?: any[];
  updateComponentAtPath?: any;
  getCurrentComponent?: any;
}

const InputWithTooltip: React.FC<{
  label: string;
  tooltip: string;
  required?: boolean;
  children: React.ReactNode;
}> = ({ label, tooltip, required, children }) => (
  <label className="block">
    <div className="flex items-center gap-2 mb-1">
      <span className="text-sm font-medium text-primary">
        {label} {required && <span className="text-red-500">*</span>}
      </span>
      <Tooltip title={tooltip}>
        <HelpCircle className="w-4 h-4 text-secondary" />
      </Tooltip>
    </div>
    {children}
  </label>
);

export const AgentFields: React.FC<AgentFieldsProps> = ({
  component,
  onChange,
  onNavigate,
  workingCopy,
  setWorkingCopy,
  editPath,
  updateComponentAtPath,
  getCurrentComponent,
}) => {
  if (!component) return null;

  // State for managing expanded workbenches and tool editing
  const [expandedWorkbenches, setExpandedWorkbenches] = useState<Set<number>>(new Set());
  const [editingTool, setEditingTool] = useState<{ workbenchIndex: number; toolIndex: number } | null>(null);
  const [toolUpdates, setToolUpdates] = useState<{ [key: string]: Partial<FunctionToolConfig> }>({});
  const debounceRefs = useRef<{ [key: string]: NodeJS.Timeout }>({});

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

  const handleConfigUpdate = useCallback(
    (field: string, value: unknown) => {
      handleComponentUpdate({
        config: {
          ...component.config,
          [field]: value,
        },
      });
    },
    [component, handleComponentUpdate]
  );

  // Toggle workbench expansion
  const toggleWorkbenchExpansion = useCallback((workbenchIndex: number) => {
    setExpandedWorkbenches(prev => {
      const newSet = new Set(prev);
      if (newSet.has(workbenchIndex)) {
        newSet.delete(workbenchIndex);
      } else {
        newSet.add(workbenchIndex);
      }
      return newSet;
    });
  }, []);

  // Start editing a tool
  const startEditingTool = useCallback((workbenchIndex: number, toolIndex: number) => {
    setEditingTool({ workbenchIndex, toolIndex });
    setExpandedWorkbenches(prev => new Set(prev).add(workbenchIndex));
  }, []);

  // Cancel tool editing
  const cancelEditingTool = useCallback(() => {
    setEditingTool(null);
    setToolUpdates({});
    // Clear any pending debounced updates
    Object.values(debounceRefs.current).forEach(timeout => clearTimeout(timeout));
    debounceRefs.current = {};
  }, []);

  // Handle tool field updates with debouncing
  const handleToolFieldUpdate = useCallback((
    workbenchIndex: number,
    toolIndex: number,
    field: string,
    value: any
  ) => {
    const key = `${workbenchIndex}-${toolIndex}`;
    
    // Update local state immediately for UI responsiveness
    setToolUpdates(prev => ({
      ...prev,
      [key]: {
        ...prev[key],
        [field]: value,
      },
    }));

    // Clear existing timeout
    if (debounceRefs.current[key]) {
      clearTimeout(debounceRefs.current[key]);
    }

    // Set new debounced update
    debounceRefs.current[key] = setTimeout(() => {
      const updates = toolUpdates[key] || {};
      const finalUpdates = { ...updates, [field]: value };
      
      // Apply updates to the actual component
      if (!isAssistantAgent(component)) return;
      
      let workbenches = normalizeWorkbenches(component.config.workbench);
      if (workbenches[workbenchIndex] && isStaticWorkbench(workbenches[workbenchIndex])) {
        const workbench = workbenches[workbenchIndex];
        const staticConfig = workbench.config as StaticWorkbenchConfig;
        const tools = [...(staticConfig.tools || [])];
        
        if (tools[toolIndex]) {
          tools[toolIndex] = {
            ...tools[toolIndex],
            config: {
              ...tools[toolIndex].config,
              ...finalUpdates,
            },
          };

          const updatedWorkbench = {
            ...workbench,
            config: {
              ...staticConfig,
              tools,
            },
          };

          const updatedWorkbenches = [...workbenches];
          updatedWorkbenches[workbenchIndex] = updatedWorkbench;
          
          handleConfigUpdate("workbench", updatedWorkbenches);
          
          // Clear the pending updates
          setToolUpdates(prev => {
            const newUpdates = { ...prev };
            delete newUpdates[key];
            return newUpdates;
          });
        }
      }
      
      // Clean up the timeout reference
      delete debounceRefs.current[key];
    }, 500); // 500ms debounce
  }, [component, handleConfigUpdate, toolUpdates]);

  // Get current tool value (either from pending updates or component)
  const getToolFieldValue = useCallback((
    workbenchIndex: number,
    toolIndex: number,
    field: string,
    defaultValue: any = ""
  ) => {
    const key = `${workbenchIndex}-${toolIndex}`;
    const pendingUpdate = toolUpdates[key] as any;
    
    if (pendingUpdate && pendingUpdate[field] !== undefined) {
      return pendingUpdate[field];
    }

    if (!isAssistantAgent(component)) return defaultValue;

    const workbenches = normalizeWorkbenches(component.config.workbench);
    const workbench = workbenches[workbenchIndex];
    if (workbench && isStaticWorkbench(workbench)) {
      const staticConfig = workbench.config as StaticWorkbenchConfig;
      const tool = staticConfig.tools?.[toolIndex];
      if (tool) {
        return (tool.config as any)[field] ?? defaultValue;
      }
    }
    
    return defaultValue;
  }, [component, toolUpdates]);

  const handleRemoveTool = useCallback(
    (toolIndex: number) => {
      if (!isAssistantAgent(component)) return;

      // Get workbenches array
      let workbenches = normalizeWorkbenches(component.config.workbench);
      if (workbenches.length === 0) {
        return; // No workbenches to remove tools from
      }

      // Find the first StaticWorkbench (for now, assume single workbench usage)
      const workbenchIndex = workbenches.findIndex(
        (wb) => isStaticWorkbench(wb)
      );
      
      if (workbenchIndex === -1) {
        return; // Can't remove tools if no StaticWorkbench exists
      }

      const workbench = workbenches[workbenchIndex];
      const staticConfig = workbench.config as StaticWorkbenchConfig;
      const newTools = [...(staticConfig.tools || [])];
      newTools.splice(toolIndex, 1);

      // Update workbench config
      const updatedWorkbench = {
        ...workbench,
        config: {
          ...staticConfig,
          tools: newTools,
        },
      };

      // Update the workbenches array
      const updatedWorkbenches = [...workbenches];
      updatedWorkbenches[workbenchIndex] = updatedWorkbench;

      handleConfigUpdate("workbench", updatedWorkbenches);
    },
    [component, handleConfigUpdate]
  );

  const handleAddTool = useCallback(() => {
    if (!isAssistantAgent(component)) return;

    const blankTool: Component<FunctionToolConfig> = {
      provider: "autogen_core.tools.FunctionTool",
      component_type: "tool",
      version: 1,
      component_version: 1,
      description: "Create custom tools by wrapping standard Python functions.",
      label: "New Tool",
      config: {
        source_code: "def new_function():\n    pass",
        name: "new_function",
        description: "Description of the new function",
        global_imports: [],
        has_cancellation_support: false,
      },
    };

    // Get or create workbenches array
    let workbenches = normalizeWorkbenches(component.config.workbench);
    
    // Find existing StaticWorkbench or create one
    let workbenchIndex = workbenches.findIndex(
      (wb) => isStaticWorkbench(wb)
    );
    
    let workbench: Component<StaticWorkbenchConfig>;
    if (workbenchIndex === -1) {
      // Create a new StaticWorkbench
      workbench = {
        provider: "autogen_core.tools.StaticWorkbench",
        component_type: "workbench",
        config: {
          tools: [],
        },
        label: "Static Workbench",
      } as Component<StaticWorkbenchConfig>;
      workbenches = [...workbenches, workbench];
      workbenchIndex = workbenches.length - 1;
    } else {
      workbench = workbenches[workbenchIndex] as Component<StaticWorkbenchConfig>;
    }

    const staticConfig = workbench.config as StaticWorkbenchConfig;
    const currentTools = staticConfig.tools || [];
    const updatedTools = [...currentTools, blankTool];

    // Update workbench config
    const updatedWorkbench = {
      ...workbench,
      config: {
        ...staticConfig,
        tools: updatedTools,
      },
    };

    // Update the workbenches array
    const updatedWorkbenches = [...workbenches];
    updatedWorkbenches[workbenchIndex] = updatedWorkbench;

    handleConfigUpdate("workbench", updatedWorkbenches);

    // If working copy functionality is available, update that too
    if (
      workingCopy &&
      setWorkingCopy &&
      updateComponentAtPath &&
      getCurrentComponent &&
      editPath
    ) {
      const updatedCopy = updateComponentAtPath(workingCopy, editPath, {
        config: {
          ...getCurrentComponent(workingCopy)?.config,
          workbench: updatedWorkbenches,
        },
      });
      setWorkingCopy(updatedCopy);
    }
  }, [
    component,
    handleConfigUpdate,
    workingCopy,
    setWorkingCopy,
    updateComponentAtPath,
    getCurrentComponent,
    editPath,
  ]);

  return (
    <div className="space-y-6">
      <DetailGroup title="Component Details">
        <div className="space-y-4">
          <label className="block">
            <span className="text-sm font-medium text-primary">Name</span>
            <Input
              value={component.label || ""}
              onChange={(e) => handleComponentUpdate({ label: e.target.value })}
              placeholder="Component name"
              className="mt-1"
            />
          </label>

          <label className="block">
            <span className="text-sm font-medium text-primary">
              Description
            </span>
            <TextArea
              value={component.description || ""}
              onChange={(e) =>
                handleComponentUpdate({ description: e.target.value })
              }
              placeholder="Component description"
              rows={4}
              className="mt-1"
            />
          </label>

          <div className="grid grid-cols-2 gap-4">
            <label className="block">
              <span className="text-sm font-medium text-primary">Version</span>
              <InputNumber
                min={1}
                precision={0}
                className="w-full mt-1"
                placeholder="e.g., 1"
                value={component.version || undefined}
                onChange={(value) => handleComponentUpdate({ version: value || undefined })}
              />
            </label>
            <label className="block">
              <span className="text-sm font-medium text-primary">Component Version</span>
              <InputNumber
                min={1}
                precision={0}
                className="w-full mt-1"
                placeholder="e.g., 1"
                value={component.component_version || undefined}
                onChange={(value) => handleComponentUpdate({ component_version: value || undefined })}
              />
            </label>
          </div>
        </div>
      </DetailGroup>

      <DetailGroup title="Configuration">
        <div className="space-y-4">
          {isAssistantAgent(component) && (
            <>
              <InputWithTooltip
                label="Name"
                tooltip="Name of the assistant agent"
                required
              >
                <Input
                  value={component.config.name}
                  onChange={(e) => handleConfigUpdate("name", e.target.value)}
                />
              </InputWithTooltip>

              {/* Model Client Section */}

              <div className="space-y-2">
                <span className="text-sm font-medium text-primary">
                  Model Client
                </span>
                {component.config.model_client ? (
                  <div className="bg-secondary p-1 px-2 rounded-md">
                    <div className="flex items-center justify-between">
                      {" "}
                      <span className="text-sm">
                        {component.config.model_client.config.model}
                      </span>
                      <div className="flex items-center justify-between">
                        {component.config.model_client && onNavigate && (
                          <Button
                            type="text"
                            icon={<Edit className="w-4 h-4" />}
                            onClick={() =>
                              onNavigate(
                                "model",
                                component.config.model_client?.label || "",
                                "model_client"
                              )
                            }
                          >
                            Configure Model
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-sm text-secondary text-center bg-secondary/50 p-4 rounded-md">
                    No model configured
                  </div>
                )}
              </div>

              <InputWithTooltip
                label="System Message"
                tooltip="System message for the agent"
              >
                <TextArea
                  rows={4}
                  value={component.config.system_message}
                  onChange={(e) =>
                    handleConfigUpdate("system_message", e.target.value)
                  }
                />
              </InputWithTooltip>

              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-primary">
                  Reflect on Tool Use
                </span>
                <Switch
                  checked={component.config.reflect_on_tool_use}
                  onChange={(checked) =>
                    handleConfigUpdate("reflect_on_tool_use", checked)
                  }
                />
              </div>

              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-primary">
                  Stream Model Client
                </span>
                <Switch
                  checked={component.config.model_client_stream}
                  onChange={(checked) =>
                    handleConfigUpdate("model_client_stream", checked)
                  }
                />
              </div>

              <InputWithTooltip
                label="Tool Call Summary Format"
                tooltip="Format for tool call summaries"
              >
                <Input
                  value={component.config.tool_call_summary_format}
                  onChange={(e) =>
                    handleConfigUpdate(
                      "tool_call_summary_format",
                      e.target.value
                    )
                  }
                />
              </InputWithTooltip>
            </>
          )}

          {isUserProxyAgent(component) && (
            <InputWithTooltip
              label="Name"
              tooltip="Name of the user proxy agent"
              required
            >
              <Input
                value={component.config.name}
                onChange={(e) => handleConfigUpdate("name", e.target.value)}
              />
            </InputWithTooltip>
          )}

          {isWebSurferAgent(component) && (
            <>
              <InputWithTooltip
                label="Name"
                tooltip="Name of the web surfer agent"
                required
              >
                <Input
                  value={component.config.name}
                  onChange={(e) => handleConfigUpdate("name", e.target.value)}
                />
              </InputWithTooltip>
              <InputWithTooltip
                label="Start Page"
                tooltip="URL to start browsing from"
              >
                <Input
                  value={component.config.start_page || ""}
                  onChange={(e) =>
                    handleConfigUpdate("start_page", e.target.value)
                  }
                />
              </InputWithTooltip>
              <InputWithTooltip
                label="Downloads Folder"
                tooltip="Folder path to save downloads"
              >
                <Input
                  value={component.config.downloads_folder || ""}
                  onChange={(e) =>
                    handleConfigUpdate("downloads_folder", e.target.value)
                  }
                />
              </InputWithTooltip>
              <InputWithTooltip
                label="Debug Directory"
                tooltip="Directory for debugging logs"
              >
                <Input
                  value={component.config.debug_dir || ""}
                  onChange={(e) =>
                    handleConfigUpdate("debug_dir", e.target.value)
                  }
                />
              </InputWithTooltip>

              {/* Added Model Client Section for WebSurferAgent */}
              <div className="space-y-2">
                <span className="text-sm font-medium text-primary">
                  Model Client
                </span>
                {component.config.model_client ? (
                  <div className="bg-secondary p-1 px-2 rounded-md">
                    <div className="flex items-center justify-between">
                      <span className="text-sm">
                        {component.config.model_client.config.model}
                      </span>
                      <div className="flex items-center justify-between">
                        {onNavigate && (
                          <Button
                            type="text"
                            icon={<Edit className="w-4 h-4" />}
                            onClick={() =>
                              onNavigate(
                                "model",
                                component.config.model_client?.label || "",
                                "model_client"
                              )
                            }
                          >
                            Configure Model
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-sm text-secondary text-center bg-secondary/50 p-4 rounded-md">
                    No model configured
                  </div>
                )}
              </div>

              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-primary">
                  Headless
                </span>
                <Switch
                  checked={component.config.headless || false}
                  onChange={(checked) =>
                    handleConfigUpdate("headless", checked)
                  }
                />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-primary">
                  Animate Actions
                </span>
                <Switch
                  checked={component.config.animate_actions || false}
                  onChange={(checked) =>
                    handleConfigUpdate("animate_actions", checked)
                  }
                />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-primary">
                  Save Screenshots
                </span>
                <Switch
                  checked={component.config.to_save_screenshots || false}
                  onChange={(checked) =>
                    handleConfigUpdate("to_save_screenshots", checked)
                  }
                />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-primary">
                  Use OCR
                </span>
                <Switch
                  checked={component.config.use_ocr || false}
                  onChange={(checked) => handleConfigUpdate("use_ocr", checked)}
                />
              </div>
              <InputWithTooltip
                label="Browser Channel"
                tooltip="Channel for the browser (e.g. beta, stable)"
              >
                <Input
                  value={component.config.browser_channel || ""}
                  onChange={(e) =>
                    handleConfigUpdate("browser_channel", e.target.value)
                  }
                />
              </InputWithTooltip>
              <InputWithTooltip
                label="Browser Data Directory"
                tooltip="Directory for browser profile data"
              >
                <Input
                  value={component.config.browser_data_dir || ""}
                  onChange={(e) =>
                    handleConfigUpdate("browser_data_dir", e.target.value)
                  }
                />
              </InputWithTooltip>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-primary">
                  Resize Viewport
                </span>
                <Switch
                  checked={component.config.to_resize_viewport || false}
                  onChange={(checked) =>
                    handleConfigUpdate("to_resize_viewport", checked)
                  }
                />
              </div>
            </>
          )}
        </div>
      </DetailGroup>

      {/* Workbench Management Section - Only for AssistantAgent */}
      {isAssistantAgent(component) && (
        <DetailGroup title="Workbench Management">
          <div className="space-y-4">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
              <p className="text-sm text-blue-800">
                <strong>Modern Tool Management:</strong> Tools are now managed through workbenches for better resource sharing and lifecycle management. 
                StaticWorkbenches contain predefined tools, while MCP workbenches provide dynamic tool collections from external servers.
              </p>
            </div>
            
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-primary">
                Workbenches ({normalizeWorkbenches(component.config.workbench).length})
              </span>
              <div className="flex gap-2">
                <Button
                  type="dashed"
                  size="small"
                  onClick={() => {
                    // Add Static Workbench
                    const normalizedWorkbenches = normalizeWorkbenches(component.config.workbench);
                    const hasStaticWorkbench = normalizedWorkbenches.some(
                      (wb: Component<WorkbenchConfig>) => isStaticWorkbench(wb)
                    );
                  
                    if (!hasStaticWorkbench) {
                      const newWorkbench = {
                        provider: "autogen_core.tools.StaticWorkbench",
                        component_type: "workbench",
                        config: { tools: [] },
                        label: "Static Workbench",
                      };
                      const normalizedWorkbenches = normalizeWorkbenches(component.config.workbench);
                      handleConfigUpdate("workbench", [...normalizedWorkbenches, newWorkbench]);
                    }
                  }}
                  icon={<PlusCircle className="w-4 h-4" />}
                >
                  Add Static Workbench
                </Button>
                {onNavigate && (
                  <Button
                    type="dashed"
                    size="small"
                    onClick={() => onNavigate("workbench", "", "workbench")}
                    icon={<PlusCircle className="w-4 h-4" />}
                  >
                    Add MCP Workbench
                  </Button>
                )}
              </div>
            </div>
            
            <div className="space-y-3">
              {normalizeWorkbenches(component.config.workbench).map((workbench: Component<WorkbenchConfig>, workbenchIndex: number) => {
                const isExpanded = expandedWorkbenches.has(workbenchIndex);
                
                return (
                  <div
                    key={workbenchIndex}
                    className="bg-secondary/30 p-4 rounded-lg border border-gray-200"
                  >
                    {/* Level 1: Workbench Header */}
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <Button
                          type="text"
                          size="small"
                          icon={isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                          onClick={() => toggleWorkbenchExpansion(workbenchIndex)}
                        />
                        <div>
                          <div className="text-sm font-medium">
                            {workbench.label || workbench.provider.split('.').pop()}
                          </div>
                          <div className="text-xs text-gray-500">
                            {workbench.provider}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {onNavigate && (
                          <Button
                            type="text"
                            icon={<Edit className="w-4 h-4" />}
                            onClick={() => {
                              // Navigate to workbench editor for both Static and MCP workbenches
                              onNavigate(
                                "workbench",
                                workbench.label || workbenchIndex.toString(),
                                "workbench"
                              );
                            }}
                          />
                        )}
                        <Button
                          type="text"
                          danger
                          icon={<Trash2 className="w-4 h-4" />}
                          onClick={() => {
                            const normalizedWorkbenches = normalizeWorkbenches(component.config.workbench);
                            const updatedWorkbenches = [...normalizedWorkbenches];
                            updatedWorkbenches.splice(workbenchIndex, 1);
                            handleConfigUpdate("workbench", updatedWorkbenches);
                          }}
                        />
                      </div>
                    </div>
                    
                    {/* Level 2: Expanded Workbench Content */}
                    {isExpanded && (
                      <>
                        {/* StaticWorkbench: Show tools with management capabilities */}
                        {isStaticWorkbench(workbench) && (
                          <div className="space-y-2">
                            <div className="flex items-center justify-between">
                              <span className="text-xs font-medium text-gray-700">
                                Tools ({(workbench.config as StaticWorkbenchConfig).tools?.length || 0})
                              </span>
                              <Button
                                type="dashed"
                                size="small"
                                onClick={handleAddTool}
                                icon={<PlusCircle className="w-3 h-3" />}
                              >
                                Add Tool
                              </Button>
                            </div>
                            
                            <div className="space-y-1">
                              {((workbench.config as StaticWorkbenchConfig).tools || []).map((tool, toolIndex) => {
                                const isEditingThisTool = editingTool?.workbenchIndex === workbenchIndex && editingTool?.toolIndex === toolIndex;
                                
                                return (
                                  <div
                                    key={toolIndex}
                                    className={`bg-white p-3 rounded border ${isEditingThisTool ? 'border-blue-300 shadow-sm' : 'border-gray-100'}`}
                                  >
                                    {/* Level 3: Tool Display/Edit */}
                                    {!isEditingThisTool ? (
                                      // Tool Summary View
                                      <div className="flex items-center justify-between">
                                        <div className="flex-1">
                                          <div className="text-sm font-medium">
                                            {tool.config.name || tool.label || "Unnamed Tool"}
                                          </div>
                                          <div className="text-xs text-gray-500 truncate">
                                            {tool.config.description || "No description"}
                                          </div>
                                        </div>
                                        <div className="flex items-center gap-1">
                                          <Button
                                            type="text"
                                            size="small"
                                            icon={<Edit className="w-3 h-3" />}
                                            onClick={() => startEditingTool(workbenchIndex, toolIndex)}
                                          >
                                            Edit
                                          </Button>
                                          <Button
                                            type="text"
                                            size="small"
                                            danger
                                            icon={<Trash2 className="w-3 h-3" />}
                                            onClick={() => handleRemoveTool(toolIndex)}
                                          />
                                        </div>
                                      </div>
                                    ) : (
                                      // Tool Edit View
                                      <div className="space-y-3">
                                        <div className="flex items-center justify-between mb-2">
                                          <span className="text-sm font-medium text-blue-600">Editing Tool</span>
                                          <div className="flex items-center gap-1">
                                            <Button
                                              type="primary"
                                              size="small"
                                              onClick={cancelEditingTool}
                                            >
                                              Done
                                            </Button>
                                          </div>
                                        </div>
                                        
                                        <div className="grid grid-cols-1 gap-3">
                                          <InputWithTooltip
                                            label="Function Name"
                                            tooltip="The name of the Python function"
                                          >
                                            <Input
                                              size="small"
                                              value={getToolFieldValue(workbenchIndex, toolIndex, "name")}
                                              onChange={(e) => handleToolFieldUpdate(workbenchIndex, toolIndex, "name", e.target.value)}
                                              placeholder="function_name"
                                            />
                                          </InputWithTooltip>
                                          
                                          <InputWithTooltip
                                            label="Description"
                                            tooltip="Description of what this tool does"
                                          >
                                            <Input
                                              size="small"
                                              value={getToolFieldValue(workbenchIndex, toolIndex, "description")}
                                              onChange={(e) => handleToolFieldUpdate(workbenchIndex, toolIndex, "description", e.target.value)}
                                              placeholder="Describe what this function does"
                                            />
                                          </InputWithTooltip>
                                          
                                          <InputWithTooltip
                                            label="Source Code"
                                            tooltip="The Python function implementation"
                                          >
                                            <TextArea
                                              size="small"
                                              rows={6}
                                              value={getToolFieldValue(workbenchIndex, toolIndex, "source_code")}
                                              onChange={(e) => handleToolFieldUpdate(workbenchIndex, toolIndex, "source_code", e.target.value)}
                                              placeholder="def your_function():&#10;    pass"
                                              style={{ fontFamily: 'Monaco, Menlo, "Ubuntu Mono", monospace' }}
                                            />
                                          </InputWithTooltip>
                                          
                                          <InputWithTooltip
                                            label="Global Imports"
                                            tooltip="Comma-separated list of global imports (e.g., os, sys, requests)"
                                          >
                                            <Input
                                              size="small"
                                              value={Array.isArray(getToolFieldValue(workbenchIndex, toolIndex, "global_imports")) 
                                                ? getToolFieldValue(workbenchIndex, toolIndex, "global_imports").join(", ")
                                                : getToolFieldValue(workbenchIndex, toolIndex, "global_imports")
                                              }
                                              onChange={(e) => handleToolFieldUpdate(
                                                workbenchIndex, 
                                                toolIndex, 
                                                "global_imports", 
                                                e.target.value.split(",").map(s => s.trim()).filter(s => s)
                                              )}
                                              placeholder="os, sys, requests"
                                            />
                                          </InputWithTooltip>
                                          
                                          <div className="flex items-center justify-between">
                                            <span className="text-sm font-medium text-primary">
                                              Has Cancellation Support
                                            </span>
                                            <Switch
                                              size="small"
                                              checked={getToolFieldValue(workbenchIndex, toolIndex, "has_cancellation_support", false)}
                                              onChange={(checked) => handleToolFieldUpdate(workbenchIndex, toolIndex, "has_cancellation_support", checked)}
                                            />
                                          </div>
                                        </div>
                                      </div>
                                    )}
                                  </div>
                                );
                              })}
                              
                              {((workbench.config as StaticWorkbenchConfig).tools?.length || 0) === 0 && (
                                <div className="text-xs text-gray-500 text-center p-3 bg-gray-50 rounded">
                                  No tools configured. Click "Add Tool" to get started.
                                </div>
                              )}
                            </div>
                          </div>
                        )}
                        
                        {/* McpWorkbench: Show server info */}
                        {isMcpWorkbench(workbench) && (
                          <div className="text-xs text-gray-600">
                            <div>MCP Server: {(workbench.config as any).server_params?.type || "Not configured"}</div>
                            <div className="text-gray-500 mt-1">Tools are provided dynamically by the MCP server</div>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                );
              })}
              
              {(() => {
                const workbenches = normalizeWorkbenches(component.config.workbench);
                return workbenches.length === 0 && (
                  <div className="text-sm text-secondary text-center bg-secondary/50 p-4 rounded-md">
                    No workbenches configured. Add a workbench to provide tools to this agent.
                  </div>
                );
              })()}
            </div>
          </div>
        </DetailGroup>
      )}
    </div>
  );
};

export default React.memo(AgentFields);
