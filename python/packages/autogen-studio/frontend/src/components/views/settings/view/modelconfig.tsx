import React, { useState } from "react";
import { Button, Tooltip, Drawer } from "antd";
import { Settings } from "lucide-react";
import { truncateText } from "../../../utils";
import {
  Component,
  ComponentConfig,
  ModelConfig,
} from "../../../types/datamodel";
import { ComponentEditor } from "../../teambuilder/builder/component-editor/component-editor";

interface ModelConfigPanelProps {
  modelComponent: Component<ModelConfig>;
  onModelUpdate: (updatedModel: Component<ComponentConfig>) => Promise<void>;
}

export const ModelConfigPanel: React.FC<ModelConfigPanelProps> = ({
  modelComponent,
  onModelUpdate,
}) => {
  const [isModelEditorOpen, setIsModelEditorOpen] = useState(false);

  const handleOpenModelEditor = () => {
    setIsModelEditorOpen(true);
  };

  const handleCloseModelEditor = () => {
    setIsModelEditorOpen(false);
  };

  const handleModelUpdate = async (
    updatedModel: Component<ComponentConfig>
  ) => {
    await onModelUpdate(updatedModel);
    setIsModelEditorOpen(false);
  };

  return (
    <>
      <div className=" ">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-medium">Default Model Configuration</h3>
          <Tooltip title="Edit Default Model Settings">
            <Button
              type="primary"
              icon={<Settings className="w-4 h-4 mr-1" />}
              onClick={handleOpenModelEditor}
              className="flex items-center"
            >
              Configure Model
            </Button>
          </Tooltip>
        </div>

        <div className="mb-6">
          Configure a default model that will be used for system level tasks.
        </div>
        <div className="bg-secondary p-4 rounded">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm font-medium text-primary">Model</p>
              <p className="text-base">
                {modelComponent.config?.model || "Not set"}
              </p>
              <p className="text-sm">
                {truncateText(modelComponent.label || "", 20) || "Not set"}
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-primary">Model Provider</p>
              <p className="text-base">
                {truncateText(modelComponent.provider || "", 20) || "Not set"}
              </p>
            </div>
            {modelComponent.config?.temperature && (
              <div>
                <p className="text-sm font-medium text-primary">Temperature</p>
                <p className="text-base">
                  {modelComponent.config?.temperature}
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Model Editor Drawer */}
      <Drawer
        title="Edit Default Model Client"
        placement="right"
        size="large"
        onClose={handleCloseModelEditor}
        open={isModelEditorOpen}
        className="component-editor-drawer"
      >
        <ComponentEditor
          component={modelComponent}
          onChange={handleModelUpdate}
          onClose={handleCloseModelEditor}
          navigationDepth={true}
        />
      </Drawer>
    </>
  );
};

export default ModelConfigPanel;
