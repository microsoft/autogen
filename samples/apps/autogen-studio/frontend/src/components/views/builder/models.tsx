import {
  ExclamationTriangleIcon,
  InformationCircleIcon,
  PlusIcon,
  TrashIcon,
} from "@heroicons/react/24/outline";
import { Button, Input, Modal, message } from "antd";
import * as React from "react";
import { IModelConfig, IStatus } from "../../types";
import { appContext } from "../../../hooks/provider";
import { fetchJSON, getServerUrl, timeAgo, truncateText } from "../../utils";
import { BounceLoader, Card, LaunchButton, LoadingOverlay } from "../../atoms";
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
  const testModelUrl = `${serverUrl}/models/test`;
  const [modelStatus, setModelStatus] = React.useState<IStatus | null>({
    status: true,
    message: "All good",
  });

  const defaultModel: IModelConfig = {
    model: "gpt-4-1106-preview",
    description: "Sample OpenAI GPT-4 model",
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

  const modelRows = (models || []).map((model: IModelConfig, i: number) => {
    return (
      <div key={"modelrow" + i} className=" " style={{ width: "200px" }}>
        <div className="">
          <Card
            className="h-full p-2 cursor-pointer"
            title={
              <div className="  ">{truncateText(model.model || "", 20)}</div>
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
            <div
              onMouseEnter={(e) => {
                e.stopPropagation();
              }}
              className=" mt-2 text-right opacity-0 group-hover:opacity-100 "
            >
              {" "}
              <div
                role="button"
                className="text-accent text-xs inline-block hover:bg-primary p-2 rounded"
                onClick={(e) => {
                  e.stopPropagation();
                  deleteModel(model);
                }}
              >
                <TrashIcon className=" w-5, h-5 cursor-pointer inline-block" />
                <span className="text-xs hidden"> delete</span>
              </div>
            </div>
          </Card>
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
    const [loadingModelTest, setLoadingModelTest] = React.useState(false);
    const [modelStatus, setModelStatus] = React.useState<IStatus | null>(null);

    const [localModel, setLocalModel] = React.useState<IModelConfig | null>(
      model
    );
    const testModel = (model: IModelConfig) => {
      setModelStatus(null);
      setLoadingModelTest(true);
      const payLoad = {
        method: "POST",
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
          setModelStatus(data.data);
        } else {
          message.error(data.message);
        }
        setLoadingModelTest(false);
        setModelStatus(data);
      };
      const onError = (err: any) => {
        message.error(err.message);
        setLoadingModelTest(false);
      };
      fetchJSON(testModelUrl, payLoad, onSuccess, onError);
    };

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
        footer={[
          <Button
            key="close"
            onClick={() => {
              setModel(null);
              setShowModelModal(false);
            }}
          >
            Close
          </Button>,
          <Button
            key="test"
            type="primary"
            loading={loadingModelTest}
            onClick={() => {
              if (localModel) {
                testModel(localModel);
              }
            }}
          >
            Test Model
          </Button>,
          <Button
            key="save"
            type="primary"
            onClick={() => {
              setModel(null);
              setShowModelModal(false);
              if (handler) {
                if (localModel) {
                  handler(localModel);
                }
              }
            }}
          >
            Save
          </Button>,
        ]}
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
        <div className="relative ">
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
        </div>
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
            {models && models.length > 0 && (
              <span className="block my-2 border rounded border-secondary p-2">
                <ExclamationTriangleIcon className="w-4 h-4 inline-block mr-1" />{" "}
                Note: Changes made to your model do not automatically get
                updated in your workflow. After creating or editing your model,{" "}
                <span className="font-semibold underline">
                  you must also (re-)add
                </span>{" "}
                it to your workflow.
              </span>
            )}
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
              No models found. Please create a new model which can be reused
              with agents.
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
