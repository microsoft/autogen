import {
  InformationCircleIcon,
  PlusIcon,
  TrashIcon,
} from "@heroicons/react/24/outline";
import { Input, Modal, message } from "antd";
import * as React from "react";
import { IAgentFlowSpec, IModelConfig, IStatus } from "../../types";
import { appContext } from "../../../hooks/provider";
import { fetchJSON, getServerUrl, timeAgo, truncateText } from "../../utils";
import {
  AgentFlowSpecView,
  BounceLoader,
  Card,
  LaunchButton,
  LoadBox,
  LoadingOverlay,
} from "../../atoms";
import TextArea from "antd/es/input/TextArea";

const ModelsView = ({}: any) => {
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<IStatus | null>({
    status: true,
    message: "All good",
  });

  const { user } = React.useContext(appContext);
  const serverUrl = getServerUrl();
  const listModelsUrl = `${serverUrl}/models?user_id=${user?.email}`;
  const saveModelsUrl = `${serverUrl}/models`;
  const deleteModelUrl = `${serverUrl}/models/delete`;

  const defaultModel: IModelConfig = {
    model: "gpt-4-1106-preview",
    description: "Sample model",
    user_id: user?.email,
  };

  const [models, setModels] = React.useState<IModelConfig[] | null>([]);
  const [selectedModel, setSelectedModel] = React.useState<IModelConfig | null>(
    null
  );
  const [newModel, setNewModel] = React.useState<IModelConfig | null>(
    defaultModel
  );

  const [showNewModelModal, setShowNewModelModal] = React.useState(false);

  const [showModelModal, setShowModelModal] = React.useState(false);

  const deleteModel = (model: IModelConfig) => {
    setError(null);
    setLoading(true);
    // const fetch;
    const payLoad = {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_id: user?.email,
        model: model,
      }),
    };

    const onSuccess = (data: any) => {
      if (data && data.status) {
        message.success(data.message);
        setModels(data.data);
      } else {
        message.error(data.message);
      }
      setLoading(false);
    };
    const onError = (err: any) => {
      setError(err);
      message.error(err.message);
      setLoading(false);
    };
    fetchJSON(deleteModelUrl, payLoad, onSuccess, onError);
  };

  const fetchModels = () => {
    setError(null);
    setLoading(true);
    const payLoad = {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    };

    const onSuccess = (data: any) => {
      if (data && data.status) {
        setModels(data.data);
      } else {
        message.error(data.message);
      }
      setLoading(false);
    };
    const onError = (err: any) => {
      setError(err);
      message.error(err.message);
      setLoading(false);
    };
    fetchJSON(listModelsUrl, payLoad, onSuccess, onError);
  };

  const saveModel = (model: IModelConfig) => {
    setError(null);
    setLoading(true);

    const payLoad = {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_id: user?.email,
        model: model,
      }),
    };

    const onSuccess = (data: any) => {
      if (data && data.status) {
        message.success(data.message);
        // console.log("models", data.data);
        setModels(data.data);
      } else {
        message.error(data.message);
      }
      setLoading(false);
    };
    const onError = (err: any) => {
      setError(err);
      message.error(err.message);
      setLoading(false);
    };
    fetchJSON(saveModelsUrl, payLoad, onSuccess, onError);
  };

  React.useEffect(() => {
    if (user) {
      // console.log("fetching messages", messages);
      fetchModels();
    }
  }, []);

  React.useEffect(() => {
    if (selectedModel) {
      console.log("selected agent", selectedModel);
    }
  }, [selectedModel]);

  const modelRows = (models || []).map((model: IModelConfig, i: number) => {
    return (
      <div key={"modelrow" + i} className=" " style={{ width: "200px" }}>
        <div className="">
          <Card
            className="h-full p-2 cursor-pointer"
            title={
              <div className="  ">{truncateText(model.model || "", 25)}</div>
            }
            onClick={() => {
              setSelectedModel(model);
              setShowModelModal(true);
            }}
          >
            <div style={{ minHeight: "65px" }} className="my-2   break-words">
              {" "}
              {truncateText(model.description || model.model || "", 70)}
            </div>
            <div className="text-xs">{timeAgo(model.timestamp || "")}</div>
          </Card>
          <div className="text-right mt-2">
            <div
              role="button"
              className="text-accent text-xs inline-block"
              onClick={() => {
                deleteModel(model);
              }}
            >
              <TrashIcon className=" w-5, h-5 cursor-pointer inline-block" />
              <span className="text-xs"> delete</span>
            </div>
          </div>
        </div>
      </div>
    );
  });

  const ModelModal = ({
    model,
    setModel,
    showModelModal,
    setShowModelModal,
    handler,
  }: {
    model: IModelConfig | null;
    setModel: (model: IModelConfig | null) => void;
    showModelModal: boolean;
    setShowModelModal: (show: boolean) => void;
    handler?: (agent: IModelConfig) => void;
  }) => {
    const [localModel, setLocalModel] = React.useState<IModelConfig | null>(
      model
    );

    return (
      <Modal
        title={
          <>
            Model Specification{" "}
            <span className="text-accent font-normal">{model?.model}</span>{" "}
          </>
        }
        width={800}
        open={showModelModal}
        onOk={() => {
          setModel(null);
          setShowModelModal(false);
          if (handler) {
            if (localModel) {
              handler(localModel);
            }
          }
        }}
        onCancel={() => {
          setModel(null);
          setShowModelModal(false);
        }}
      >
        <div className="text-sm my-2">Enter parameters for your model.</div>
        <Input
          placeholder="Model Name"
          value={localModel?.model}
          onChange={(e) => {
            setLocalModel({ ...localModel, model: e.target.value });
          }}
        />
        <Input.Password
          className="mt-2"
          placeholder="API Key"
          value={localModel?.api_key}
          onChange={(e) => {
            if (localModel) {
              setLocalModel({ ...localModel, api_key: e.target.value });
            }
          }}
        />
        <Input
          className="mt-2"
          placeholder="Base URL"
          value={localModel?.base_url}
          onChange={(e) => {
            if (localModel) {
              setLocalModel({ ...localModel, base_url: e.target.value });
            }
          }}
        />
        <Input
          className="mt-2"
          placeholder="API Type (e.g. azure)"
          value={localModel?.api_type}
          onChange={(e) => {
            if (localModel) {
              setLocalModel({ ...localModel, api_type: e.target.value });
            }
          }}
        />
        <Input
          className="mt-2"
          placeholder="API Version (optional)"
          value={localModel?.api_version}
          onChange={(e) => {
            if (localModel) {
              setLocalModel({ ...localModel, api_version: e.target.value });
            }
          }}
        />
        <TextArea
          className="mt-2"
          placeholder="Description"
          value={localModel?.description}
          onChange={(e) => {
            if (localModel) {
              setLocalModel({ ...localModel, description: e.target.value });
            }
          }}
        />

        {localModel?.api_type === "azure" && (
          <div className="mt-4 text-xs">
            Note: For Azure OAI models, you will need to specify all fields.
          </div>
        )}
      </Modal>
    );
  };

  return (
    <div className="text-primary  ">
      <ModelModal
        model={selectedModel}
        setModel={setSelectedModel}
        setShowModelModal={setShowModelModal}
        showModelModal={showModelModal}
        handler={(model: IModelConfig | null) => {
          if (model) {
            saveModel(model);
          }
        }}
      />

      <ModelModal
        model={defaultModel}
        setModel={setNewModel}
        setShowModelModal={setShowNewModelModal}
        showModelModal={showNewModelModal}
        handler={(model: IModelConfig | null) => {
          if (model) {
            saveModel(model);
          }
        }}
      />

      <div className="mb-2   relative">
        <div className="     rounded  ">
          <div className="flex mt-2 pb-2 mb-2 border-b">
            <div className="flex-1 font-semibold mb-2 ">
              {" "}
              Models ({modelRows.length}){" "}
            </div>
            <LaunchButton
              className="text-sm p-2 px-3"
              onClick={() => {
                setShowNewModelModal(true);
              }}
            >
              {" "}
              <PlusIcon className="w-5 h-5 inline-block mr-1" />
              New Model
            </LaunchButton>
          </div>

          <div className="text-xs mb-2 pb-1  ">
            {" "}
            Create model configurations that can be reused in your agents and
            workflows. {selectedModel?.model}
          </div>
          {models && models.length > 0 && (
            <div className="w-full  relative">
              <LoadingOverlay loading={loading} />
              <div className="   flex flex-wrap gap-3">{modelRows}</div>
            </div>
          )}

          {models && models.length === 0 && !loading && (
            <div className="text-sm border mt-4 rounded text-secondary p-2">
              <InformationCircleIcon className="h-4 w-4 inline mr-1" />
              No models found. Please create a new agent.
            </div>
          )}

          {loading && (
            <div className="  w-full text-center">
              {" "}
              <BounceLoader />{" "}
              <span className="inline-block"> loading .. </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ModelsView;
