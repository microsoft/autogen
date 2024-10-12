import React from "react";
import { fetchJSON, getServerUrl, sampleModelConfig } from "../../../utils";
import { Button, Input, message, theme } from "antd";
import {
  CpuChipIcon,
  InformationCircleIcon,
} from "@heroicons/react/24/outline";
import { IModelConfig, IStatus } from "../../../types";
import { Card, ControlRowView } from "../../../atoms";
import TextArea from "antd/es/input/TextArea";
import { appContext } from "../../../../hooks/provider";

const ModelTypeSelector = ({
  model,
  setModel,
}: {
  model: IModelConfig;
  setModel: (newModel: IModelConfig) => void;
}) => {
  const modelTypes = [
    {
      label: "OpenAI",
      value: "open_ai",
      description: "OpenAI or other endpoints that implement the OpenAI API",
      icon: <CpuChipIcon className="h-6 w-6 text-primary" />,
      hint: "In addition to OpenAI models, You can also use OSS models via tools like Ollama, vLLM, LMStudio etc. that provide OpenAI compatible endpoint.",
    },
    {
      label: "Azure OpenAI",
      value: "azure",
      description: "Azure OpenAI endpoint",
      icon: <CpuChipIcon className="h-6 w-6 text-primary" />,
      hint: "Azure OpenAI endpoint",
    },
    {
      label: "Gemini",
      value: "google",
      description: "Gemini",
      icon: <CpuChipIcon className="h-6 w-6 text-primary" />,
      hint: "Gemini",
    },
    {
      label: "Claude",
      value: "anthropic",
      description: "Anthropic Claude",
      icon: <CpuChipIcon className="h-6 w-6 text-primary" />,
      hint: "Anthropic Claude models",
    },
    {
      label: "Mistral",
      value: "mistral",
      description: "Mistral",
      icon: <CpuChipIcon className="h-6 w-6 text-primary" />,
      hint: "Mistral models",
    },
  ];

  const [selectedType, setSelectedType] = React.useState<string | undefined>(
    model?.api_type
  );

  const modelTypeRows = modelTypes.map((modelType: any, i: number) => {
    return (
      <li
        onMouseEnter={() => {
          setSelectedHint(modelType.hint);
        }}
        role="listitem"
        key={"modeltype" + i}
        className="w-36"
      >
        <Card
          active={selectedType === modelType.value}
          className="h-full p-2 cursor-pointer"
          title={<div className="  ">{modelType.label}</div>}
          onClick={() => {
            setSelectedType(modelType.value);
            if (model) {
              const sampleModel = sampleModelConfig(modelType.value);
              setModel(sampleModel);
              //   setAgent(sampleAgent);
            }
          }}
        >
          <div style={{ minHeight: "35px" }} className="my-2   break-words ">
            {" "}
            <div className="mb-2">{modelType.icon}</div>
            <span className="text-secondary  tex-sm">
              {" "}
              {modelType.description}
            </span>
          </div>
        </Card>
      </li>
    );
  });

  const [selectedHint, setSelectedHint] = React.useState<string>("open_ai");

  return (
    <>
      <div className="pb-3">Select Model Type</div>
      <ul className="inline-flex gap-2">{modelTypeRows}</ul>

      <div className="text-xs mt-4">
        <InformationCircleIcon className="h-4 w-4 inline mr-1 -mt-1" />
        {selectedHint}
      </div>
    </>
  );
};

const ModelConfigMainView = ({
  model,
  setModel,
  close,
}: {
  model: IModelConfig;
  setModel: (newModel: IModelConfig) => void;
  close: () => void;
}) => {
  const [loading, setLoading] = React.useState(false);
  const [modelStatus, setModelStatus] = React.useState<IStatus | null>(null);
  const serverUrl = getServerUrl();
  const { user } = React.useContext(appContext);
  const testModelUrl = `${serverUrl}/models/test`;
  const createModelUrl = `${serverUrl}/models`;

  //   const [model, setmodel] = React.useState<IModelConfig | null>(
  //     model
  //   );
  const testModel = (model: IModelConfig) => {
    setModelStatus(null);
    setLoading(true);
    model.user_id = user?.email;
    const payLoad = {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(model),
    };

    const onSuccess = (data: any) => {
      if (data && data.status) {
        message.success(data.message);
        setModelStatus(data.data);
      } else {
        message.error(data.message);
      }
      setLoading(false);
      setModelStatus(data);
    };
    const onError = (err: any) => {
      message.error(err.message);
      setLoading(false);
    };
    fetchJSON(testModelUrl, payLoad, onSuccess, onError);
  };
  const createModel = (model: IModelConfig) => {
    setLoading(true);
    model.user_id = user?.email;
    const payLoad = {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(model),
    };

    const onSuccess = (data: any) => {
      if (data && data.status) {
        message.success(data.message);
        setModel(data.data);
      } else {
        message.error(data.message);
      }
      setLoading(false);
    };
    const onError = (err: any) => {
      message.error(err.message);
      setLoading(false);
    };
    const onFinal = () => {
      setLoading(false);
      setControlChanged(false);
    };
    fetchJSON(createModelUrl, payLoad, onSuccess, onError, onFinal);
  };

  const [controlChanged, setControlChanged] = React.useState<boolean>(false);

  const updateModelConfig = (key: string, value: string) => {
    if (model) {
      const updatedModelConfig = { ...model, [key]: value };
      //   setmodel(updatedModelConfig);
      setModel(updatedModelConfig);
    }
    setControlChanged(true);
  };

  const hasChanged = !controlChanged && model.id !== undefined;

  return (
    <div className="relative ">
      <div className="text-sm my-2">
        Enter parameters for your{" "}
        <span className="mx-1 text-accent">{model.api_type}</span> model.
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <ControlRowView
            title="Model"
            className=""
            description="Model name"
            value={model?.model || ""}
            control={
              <Input
                className="mt-2 w-full"
                value={model?.model}
                onChange={(e) => {
                  updateModelConfig("model", e.target.value);
                }}
              />
            }
          />

          <ControlRowView
            title="Base URL"
            className=""
            description="Base URL for Model Endpoint"
            value={model?.base_url || ""}
            control={
              <Input
                className="mt-2 w-full"
                value={model?.base_url}
                onChange={(e) => {
                  updateModelConfig("base_url", e.target.value);
                }}
              />
            }
          />
        </div>
        <div>
          <ControlRowView
            title="API Key"
            className=""
            description="API Key"
            value={model?.api_key || ""}
            truncateLength={5}
            control={
              <Input.Password
                className="mt-2 w-full"
                value={model?.api_key}
                onChange={(e) => {
                  updateModelConfig("api_key", e.target.value);
                }}
              />
            }
          />
          {model?.api_type == "azure" && (
            <ControlRowView
              title="API Version"
              className=" "
              description="API Version, required by Azure Models"
              value={model?.api_version || ""}
              control={
                <Input
                  className="mt-2 w-full"
                  value={model?.api_version}
                  onChange={(e) => {
                    updateModelConfig("api_version", e.target.value);
                  }}
                />
              }
            />
          )}
        </div>
      </div>

      <ControlRowView
        title="Description"
        className="mt-4"
        description="Description of the model"
        value={model?.description || ""}
        control={
          <TextArea
            className="mt-2 w-full"
            value={model?.description}
            onChange={(e) => {
              updateModelConfig("description", e.target.value);
            }}
          />
        }
      />

      {model?.api_type === "azure" && (
        <div className="mt-4 text-xs">
          Note: For Azure OAI models, you will need to specify all fields.
        </div>
      )}

      {modelStatus && (
        <div
          className={`text-sm border mt-4 rounded text-secondary p-2 ${
            modelStatus.status ? "border-accent" : " border-red-500 "
          }`}
        >
          <InformationCircleIcon className="h-4 w-4 inline mr-1" />
          {modelStatus.message}

          {/* <span className="block"> Note </span> */}
        </div>
      )}

      <div className="w-full mt-4 text-right">
        <Button
          key="test"
          type="primary"
          loading={loading}
          onClick={() => {
            if (model) {
              testModel(model);
            }
          }}
        >
          Test Model
        </Button>

        {!hasChanged && (
          <Button
            className="ml-2"
            key="save"
            type="primary"
            onClick={() => {
              if (model) {
                createModel(model);
                setModel(model);
              }
            }}
          >
            {model?.id ? "Update Model" : "Save Model"}
          </Button>
        )}

        <Button
          className="ml-2"
          key="close"
          type="default"
          onClick={() => {
            close();
          }}
        >
          Close
        </Button>
      </div>
    </div>
  );
};

export const ModelConfigView = ({
  model,
  setModel,
  close,
}: {
  model: IModelConfig;
  setModel: (newModel: IModelConfig) => void;
  close: () => void;
}) => {
  return (
    <div className="text-primary">
      <div>
        {!model?.api_type && (
          <ModelTypeSelector model={model} setModel={setModel} />
        )}

        {model?.api_type && model && (
          <ModelConfigMainView
            model={model}
            setModel={setModel}
            close={close}
          />
        )}
      </div>
    </div>
  );
};
