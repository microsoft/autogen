import {
  AdjustmentsVerticalIcon,
  Cog6ToothIcon,
} from "@heroicons/react/24/outline";
import { Button, Checkbox, Input, Modal, Select, Slider } from "antd";
import * as React from "react";
import { SecondaryButton } from "../../atoms";
import { ITextGeneratorConfig, IGenConfig } from "../../types";

const GeneratorControlsView = ({
  config,
}: {
  config: {
    genConfig: IGenConfig;
    setGenConfig: React.Dispatch<React.SetStateAction<IGenConfig>>;
  };
}) => {
  const [isModalVisible, setIsModalVisible] = React.useState(false);

  const { genConfig, setGenConfig } = config;
  const textgen_config = genConfig.textgen_config;

  // console.log("config", genConfig);

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

  return (
    <div className="text-secondary rounded p">
      <Modal
        width={800}
        title={
          <span>
            <AdjustmentsVerticalIcon className="h-4 text-accent inline-block mr-2 -mt-1" />
            Generation Settings
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
        <div className="flex gap-3 ">
          <div className="w-1/2">
            <ControlRowView
              title="Model"
              description="The model to use for generation."
              value={textgen_config.model}
              control={
                <Select
                  className="mt-2 w-full"
                  defaultValue={textgen_config.model}
                  onChange={(value: any) => {
                    setGenConfig({
                      ...genConfig,
                      textgen_config: { ...textgen_config, model: value },
                    });
                  }}
                  options={
                    [
                      { label: "gpt-3.5-turbo", value: "gpt-3.5-turbo-0301" },
                      { label: "gpt-4", value: "gpt-4-0314" },
                    ] as any
                  }
                />
              }
            />

            <ControlRowView
              title="Max Tokens"
              className="mt-4"
              description="Max number of tokens to generate."
              value={textgen_config.max_tokens}
              control={
                <Slider
                  min={128}
                  max={2048}
                  defaultValue={textgen_config.max_tokens}
                  step={64}
                  onAfterChange={(value: any) => {
                    setGenConfig({
                      ...genConfig,
                      textgen_config: { ...textgen_config, max_tokens: value },
                    });
                  }}
                />
              }
            />

            <ControlRowView
              title="Temperature"
              description="The higher the temperature, the more creative the text."
              value={textgen_config.temperature}
              control={
                <Slider
                  min={0.1}
                  max={1.0}
                  defaultValue={textgen_config.temperature}
                  step={0.1}
                  onAfterChange={(value: any) => {
                    setGenConfig({
                      ...genConfig,
                      textgen_config: { ...textgen_config, temperature: value },
                    });
                  }}
                />
              }
            />

            <ControlRowView
              title="Number Messages"
              description="The number of responses to generate."
              value={textgen_config.n}
              control={
                <Slider
                  min={1}
                  max={10}
                  defaultValue={textgen_config.n}
                  step={1}
                  onAfterChange={(value: any) => {
                    setGenConfig({
                      ...genConfig,
                      textgen_config: { ...textgen_config, n: value },
                    });
                  }}
                />
              }
            />

            <ControlRowView
              title="Presence Penalty"
              description="Positive values increases model's likelihood to talk about new topics.[-2.0 to 2.0]"
              value={textgen_config.presence_penalty}
              control={
                <Slider
                  min={-2.0}
                  max={2.0}
                  defaultValue={textgen_config.presence_penalty}
                  step={0.1}
                  onAfterChange={(value: any) => {
                    setGenConfig({
                      ...genConfig,
                      textgen_config: {
                        ...textgen_config,
                        presence_penalty: value,
                      },
                    });
                  }}
                />
              }
            />

            <ControlRowView
              title="Frequency Penalty"
              description="Positive values increases the model's likelihood to talk about new topics. [-2.0 and 2.0]"
              value={textgen_config.frequency_penalty}
              control={
                <Slider
                  min={-2.0}
                  max={2.0}
                  defaultValue={textgen_config.frequency_penalty}
                  step={0.1}
                  onAfterChange={(value: any) => {
                    setGenConfig({
                      ...genConfig,
                      textgen_config: {
                        ...textgen_config,
                        frequency_penalty: value,
                      },
                    });
                  }}
                />
              }
            />
          </div>
          <div className="w-1/2">
            <ControlRowView
              title="Ranker"
              description="Method to use for reranking retrieved passages during generation."
              value={genConfig.metadata.ranker}
              control={
                <Select
                  className="mt-2 w-full"
                  defaultValue={genConfig.metadata.ranker}
                  onChange={(value: any) => {
                    setGenConfig({
                      ...genConfig,
                      metadata: { ...genConfig.metadata, ranker: value },
                    });
                  }}
                  options={
                    [
                      { label: "default", value: "default" },
                      { label: "ancereward", value: "ancereward" },
                    ] as any
                  }
                />
              }
            />

            <ControlRowView
              title="Prompter"
              className="mt-4"
              description="Method for preprocessing the prompt before retrieval."
              value={genConfig.metadata.prompter}
              control={
                <Select
                  className="mt-2 w-full"
                  defaultValue={genConfig.metadata.prompter}
                  onChange={(value: any) => {
                    setGenConfig({
                      ...genConfig,
                      metadata: { ...genConfig.metadata, prompter: value },
                    });
                  }}
                  options={
                    [
                      { label: "default", value: "default" },
                      { label: "hyde", value: "hyde" },
                    ] as any
                  }
                />
              }
            />

            <ControlRowView
              title="Top K Retrieval"
              className="mt-4"
              description="Number of passages to retrieve in search."
              value={genConfig.metadata.top_k}
              control={
                <Slider
                  min={5}
                  max={100}
                  defaultValue={genConfig.metadata.top_k}
                  step={1}
                  onAfterChange={(value: any) => {
                    setGenConfig({
                      ...genConfig,
                      metadata: { ...genConfig.metadata, top_k: value },
                    });
                  }}
                />
              }
            />
          </div>
        </div>

        <p className="mt-4 text-xs text-secondary">
          {" "}
          Learn more about OpenAI model parameters{" "}
          <a
            className="border-b border-accent hover:text-accent "
            target={"_blank"}
            rel={"noopener noreferrer"}
            href={"https://platform.openai.com/docs/api-reference/chat"}
          >
            here
          </a>
          .
        </p>
      </Modal>

      <div className="mb-3 text-secondary md:flex gap-3 grid">
        {" "}
        {/* <div className="mb-4 flex-1">
          <div className="text-xs mb-2">
            {" "}
            Select a visualization library/grammar
          </div>
          <Select
            defaultValue={genConfig.library}
            style={{ width: 220 }}
            onChange={(value: string) => {
              setGenConfig({ ...genConfig, library: value });
            }}
            options={[
              { label: "Altair", value: "altair" },
              { label: "Matplotlib", value: "matplotlib" },
              { label: "Seaborn", value: "seaborn" },
              { label: "GGPlot", value: "ggplot" },
            ]}
          />
        </div> */}
        <div className="  text-right">
          <SecondaryButton
            onClick={() => {
              setIsModalVisible(true);
            }}
          >
            <AdjustmentsVerticalIcon className="h-4 text-accent inline-block mr-2 -mt-1" />
            Generation Settings{" "}
          </SecondaryButton>
          <div className="opacity-80 text-xs mt-2">
            Model: <span className="text-accent"> {textgen_config.model}</span>,
            n:
            <span className="text-accent"> {textgen_config.n}</span>,
            Temperature:{" "}
            <span className="text-accent"> {textgen_config.temperature}</span>{" "}
            ...
          </div>
        </div>
      </div>
    </div>
  );
};
export default GeneratorControlsView;
