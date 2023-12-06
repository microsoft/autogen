import { AdjustmentsVerticalIcon } from "@heroicons/react/24/outline";
import { Modal, Select, Slider } from "antd";
import * as React from "react";
import { ControlRowView, GroupView, ModelSelector } from "../../atoms";
import { IAgentFlowSpec, IFlowConfig, IModelConfig } from "../../types";
import TextArea from "antd/es/input/TextArea";
import { useConfigStore } from "../../../hooks/store";
import debounce from "lodash.debounce";
import { getModels } from "../../utils";

const FlowView = ({
  title,
  flowSpec,
  setFlowSpec,
}: {
  title: string;
  flowSpec: IAgentFlowSpec;
  setFlowSpec: (newFlowSpec: IAgentFlowSpec) => void;
}) => {
  // Local state for the FlowView component
  const [localFlowSpec, setLocalFlowSpec] =
    React.useState<IAgentFlowSpec>(flowSpec);

  // Event handlers for updating local state and propagating changes

  const onControlChange = (value: any, key: string) => {
    const updatedFlowSpec = {
      ...localFlowSpec,
      config: { ...localFlowSpec.config, [key]: value },
    };
    setLocalFlowSpec(updatedFlowSpec);
    setFlowSpec(updatedFlowSpec);
  };

  const onDebouncedControlChange = React.useCallback(
    debounce((value: any, key: string) => {
      onControlChange(value, key);
    }, 3000),
    [onControlChange]
  );
  const modelConfigs = getModels();
  return (
    <>
      <div className="text-accent">{title}</div>
      <GroupView title={flowSpec.config.name} className="mb-4">
        <ControlRowView
          title="Max Consecutive Auto Reply"
          className="mt-4"
          description="Max consecutive auto reply messages before termination."
          value={flowSpec.config.max_consecutive_auto_reply}
          control={
            <Slider
              min={2}
              max={30}
              defaultValue={flowSpec.config.max_consecutive_auto_reply}
              step={1}
              onAfterChange={(value: any) => {
                onControlChange(value, "max_consecutive_auto_reply");
              }}
            />
          }
        />

        <ControlRowView
          title="Human Input Mode"
          description="Defines when to request human input"
          value={flowSpec.config.human_input_mode}
          control={
            <Select
              className="mt-2 w-full"
              defaultValue={flowSpec.config.human_input_mode}
              onChange={(value: any) => {
                onControlChange(value, "human_input_mode");
              }}
              options={
                [
                  { label: "NEVER", value: "NEVER" },
                  { label: "TERMINATE", value: "TERMINATE" },
                  { label: "ALWAYS", value: "ALWAYS" },
                ] as any
              }
            />
          }
        />

        <ControlRowView
          title="System Message"
          className="mt-4"
          description="Free text to control agent behavior"
          value={flowSpec.config.system_message}
          control={
            <TextArea
              className="mt-2 w-full"
              defaultValue={flowSpec.config.system_message}
              rows={3}
              onChange={(e) => {
                onDebouncedControlChange(e.target.value, "system_message");
              }}
            />
          }
        />

        {flowSpec.config.llm_config && (
          <ControlRowView
            title="Model"
            className="mt-4"
            description="Defines which models are used for the agent."
            value={flowSpec.config.llm_config?.config_list?.[0]?.model}
            control={
              <ModelSelector
                className="mt-2 w-full"
                configs={flowSpec.config.llm_config.config_list || []}
                setConfigs={(config_list: IModelConfig[]) => {
                  const llm_config = {
                    ...flowSpec.config.llm_config,
                    config_list,
                  };
                  onControlChange(llm_config, "llm_config");
                }}
              />
            }
          />
        )}
      </GroupView>
    </>
  );
};

const AgentsControlView = ({
  flowConfig,
  setFlowConfig,
  selectedConfig,
  setSelectedConfig,
  flowConfigs,
  setFlowConfigs,
}: {
  flowConfig: IFlowConfig;
  setFlowConfig: (newFlowConfig: IFlowConfig) => void;
  selectedConfig: number;
  setSelectedConfig: (index: number) => void;
  flowConfigs: IFlowConfig[];
  setFlowConfigs: (newFlowConfigs: IFlowConfig[]) => void;
}) => {
  const [isModalVisible, setIsModalVisible] = React.useState(false);

  // Function to update a specific flowConfig by index
  const updateFlowConfigs = (index: number, newFlowConfig: IFlowConfig) => {
    const updatedFlowConfigs = [...flowConfigs];
    updatedFlowConfigs[index] = newFlowConfig;
    setFlowConfigs(updatedFlowConfigs);
  };

  React.useEffect(() => {
    updateFlowConfigs(selectedConfig, flowConfig);
  }, [flowConfig]);

  const FlowConfigViewer = ({
    flowConfig,
    setFlowConfig,
  }: {
    flowConfig: IFlowConfig;
    setFlowConfig: (newFlowConfig: IFlowConfig) => void;
  }) => {
    // Local state for sender and receiver FlowSpecs
    const [senderFlowSpec, setSenderFlowSpec] = React.useState<IAgentFlowSpec>(
      flowConfig.sender
    );
    const [receiverFlowSpec, setReceiverFlowSpec] =
      React.useState<IAgentFlowSpec>(flowConfig.receiver);

    // Update the local state and propagate changes to the parent component
    const updateSenderFlowSpec = (newFlowSpec: IAgentFlowSpec) => {
      setSenderFlowSpec(newFlowSpec);
      setFlowConfig({ ...flowConfig, sender: newFlowSpec });
    };

    const updateReceiverFlowSpec = (newFlowSpec: IAgentFlowSpec) => {
      setReceiverFlowSpec(newFlowSpec);
      setFlowConfig({ ...flowConfig, receiver: newFlowSpec });
    };

    return (
      <>
        <div className="mb-2">{flowConfig.name}</div>
        <div className="flex gap-3 ">
          <div className="w-1/2">
            <div className="">
              <FlowView
                title="Sender"
                flowSpec={senderFlowSpec}
                setFlowSpec={updateSenderFlowSpec}
              />
            </div>
          </div>
          <div className="w-1/2">
            <FlowView
              title="Receiver"
              flowSpec={receiverFlowSpec}
              setFlowSpec={updateReceiverFlowSpec}
            />
          </div>
        </div>
      </>
    );
  };

  return (
    <div className="text-secondary rounded p">
      <Modal
        width={800}
        title={
          <span>
            <AdjustmentsVerticalIcon className="h-4 text-accent inline-block mr-2 -mt-1" />
            AutoGen Agent Settings
          </span>
        }
        open={isModalVisible}
        onCancel={() => {
          setIsModalVisible(false);
        }}
        onOk={() => {
          setIsModalVisible(false);
        }}
      >
        <ControlRowView
          title="Agent Flow Specification"
          className="mb-4"
          description="Select the agent flow specification that will be used for your tasks."
          value={flowConfig.name}
          control={
            <Select
              className="mt-2 w-full"
              value={flowConfig.name}
              onChange={(value: any) => {
                setSelectedConfig(value);
                setFlowConfig(flowConfigs[value]);
              }}
              options={
                flowConfigs.map((config, index) => {
                  return { label: config.name, value: index };
                }) as any
              }
            />
          }
        />

        <FlowConfigViewer
          flowConfig={flowConfig}
          setFlowConfig={setFlowConfig}
        />

        <p className="mt-4 text-xs text-secondary">
          {" "}
          Learn more about AutoGen Agent parameters{" "}
          <a
            className="border-b border-accent hover:text-accent "
            target={"_blank"}
            rel={"noopener noreferrer"}
            href={
              "https://microsoft.github.io/autogen/docs/Use-Cases/agent_chat"
            }
          >
            here
          </a>
          .
        </p>
      </Modal>

      <div
        role="button"
        onClick={() => {
          setIsModalVisible(true);
        }}
        className="text-right   flex-1 -mt-1 text-accent"
      >
        <span className="inline-block -mt-2">Settings</span>{" "}
        <AdjustmentsVerticalIcon className="inline-block w-4 h-6  " />
      </div>
    </div>
  );
};

const AgentsView = () => {
  const flowConfigs = useConfigStore((state) => state.flowConfigs);
  const setFlowConfigs = useConfigStore((state) => state.setFlowConfigs);

  const flowConfig = useConfigStore((state) => state.flowConfig);
  const setFlowConfig = useConfigStore((state) => state.setFlowConfig);

  const [selectedConfig, setSelectedConfig] = React.useState<number>(0);
  // const [flowConfig, setFlowConfig] = React.useState<IFlowConfig>(
  //   flowConfigs[selectedConfig]
  // );

  return (
    <div className=" mb-4 ">
      <div className="font-semibold pb-2 border-b">Agents </div>
      <div className="text-xs mt-2 mb-2 pb-1  ">
        {" "}
        Select or create an agent workflow.{" "}
      </div>
      <div className="text-xs text-secondary mt-2 flex">
        <div>Agent Workflow</div>
        <div className="flex-1">
          <AgentsControlView
            flowConfig={flowConfig}
            setFlowConfig={setFlowConfig}
            selectedConfig={selectedConfig}
            setSelectedConfig={setSelectedConfig}
            flowConfigs={flowConfigs}
            setFlowConfigs={setFlowConfigs}
          />
        </div>
      </div>

      <Select
        className="mt-2 w-full"
        value={flowConfigs[selectedConfig].name}
        onChange={(value: any) => {
          setSelectedConfig(value);
          setFlowConfig(flowConfigs[value]);
        }}
        options={
          flowConfigs.map((config, index) => {
            return { label: config.name, value: index };
          }) as any
        }
      />
    </div>
  );
};
export default AgentsView;
