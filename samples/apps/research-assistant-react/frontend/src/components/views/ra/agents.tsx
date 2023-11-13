import { AdjustmentsVerticalIcon } from "@heroicons/react/24/outline";
import { Modal, Select, Slider } from "antd";
import * as React from "react";
import { GroupView } from "../../atoms";
import {
  IAgentConfig,
  IAgentFlowSpec,
  IFlowConfig,
  ILLMConfig,
} from "../../types";

const AgentsControlView = () => {
  const [isModalVisible, setIsModalVisible] = React.useState(false);

  const ControlRowView = ({
    title,
    description,
    value,
    control,
    className,
  }: any) => {
    return (
      <div className={`${className}`}>
        <div>
          <span className="text-primary inline-block">{title} </span>
          <span className="text-xs ml-1 text-accent -mt-2 inline-block">
            {value}
          </span>
        </div>
        <div className="text-secondary text-xs"> {description} </div>
        {control}
      </div>
    );
  };

  const llm_config: ILLMConfig = {
    seed: 42,
    config_list: [{ model: "gpt-4" }],
    temperature: 0.1,
    use_cache: true,
  };

  const userProxyConfig: IAgentConfig = {
    name: "user_proxy",
    llm_config: llm_config,
    human_input_mode: "NEVER",
    max_consecutive_auto_reply: 10,
    system_message: null,
  };
  const userProxyFlowSpec: IAgentFlowSpec = {
    type: "user_proxy",
    config: userProxyConfig,
  };

  const assistantConfig: IAgentConfig = {
    name: "primary_assistant",
    llm_config: llm_config,
    human_input_mode: "NEVER",
    max_consecutive_auto_reply: 10,
    system_message: null,
  };
  const assistantFlowSpec: IAgentFlowSpec = {
    type: "assistant",
    config: assistantConfig,
  };

  const GeneralFlowConfig: IFlowConfig = {
    name: "General Assistant",
    sender: userProxyFlowSpec,
    receiver: assistantFlowSpec,
    type: "default",
  };
  const GroupChatFlowConfig: IFlowConfig = {
    name: "Group Travel Assistant",
    sender: userProxyFlowSpec,
    receiver: assistantFlowSpec,
    type: "default",
  };

  const [configs, setConfigs] = React.useState([
    GeneralFlowConfig,
    GroupChatFlowConfig,
  ]);
  const [selectedConfig, setSelectedConfig] = React.useState<number>(0);

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
          title="Agent Flow"
          className="mb-4"
          description="The agent flow to use for generation."
          value={configs[selectedConfig].name}
          control={
            <Select
              className="mt-2 w-full"
              defaultValue={configs[selectedConfig].name}
              onChange={(value: any) => {
                console.log(value);
              }}
              options={
                configs.map((config, index) => {
                  return { label: config.name, value: index };
                }) as any
              }
            />
          }
        />

        <div className="flex gap-3 ">
          <div className="w-1/2">
            <div className="">
              <GroupView title={"Sender"} className="mb-4">
                <ControlRowView
                  title="Agent Type"
                  description="Defines agent behavior"
                  value={"userproxy"}
                  control={
                    <Select
                      className="mt-2 w-full"
                      defaultValue={"userproxy"}
                      onChange={(value: any) => {}}
                      options={
                        [
                          { label: "userproxy", value: "userproxy" },
                          { label: "assistant", value: "assistant" },
                        ] as any
                      }
                    />
                  }
                />

                <ControlRowView
                  title="Max Consecutive Auto Reply"
                  className="mt-4"
                  description="Max consecutive auto reply messages before termination."
                  value={10}
                  control={
                    <Slider
                      min={2}
                      max={30}
                      defaultValue={10}
                      step={1}
                      onAfterChange={(value: any) => {}}
                    />
                  }
                />
              </GroupView>
            </div>
          </div>
          <div className="w-1/2">
            <GroupView title={"Receiver"} className="mb-4">
              <ControlRowView
                title="Agent Type"
                description="Defines agent behavior"
                value={"userproxy"}
                control={
                  <Select
                    className="mt-2 w-full"
                    defaultValue={"assistant"}
                    onChange={(value: any) => {}}
                    options={
                      [
                        { label: "userproxy", value: "userproxy" },
                        { label: "assistant", value: "assistant" },
                      ] as any
                    }
                  />
                }
              />

              <ControlRowView
                title="Max Consecutive Auto Reply"
                className="mt-4"
                description="Max consecutive auto reply messages before termination."
                value={10}
                control={
                  <Slider
                    min={2}
                    max={30}
                    defaultValue={10}
                    step={1}
                    onAfterChange={(value: any) => {}}
                  />
                }
              />
            </GroupView>
          </div>
        </div>

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
          console.log("settings clicked");
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
  const handleChange = (value: string) => {
    console.log(`selected ${value}`);
  };

  return (
    <div className="h-full  mb-4 ">
      <div className="font-semibold pb-2 border-b">Agents view</div>
      <div className="text-xs mt-2 mb-2 pb-1  ">
        {" "}
        Select or create an agent workflow.{" "}
      </div>
      <div className="text-xs text-secondary mt-2 flex">
        <div>Default Agent</div>
        <div className="flex-1">
          <AgentsControlView />
        </div>
      </div>

      <Select
        className="mt-2 w-full"
        defaultValue="default"
        onChange={handleChange}
        options={[
          { value: "default", label: "General Assistant" },
          { value: "travelgroupchat", label: "Travel Group Chat" },
        ]}
      />
    </div>
  );
};
export default AgentsView;
