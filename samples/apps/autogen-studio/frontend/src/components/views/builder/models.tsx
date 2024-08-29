import {
  ArrowDownTrayIcon,
  ArrowUpTrayIcon,
  DocumentDuplicateIcon,
  InformationCircleIcon,
  PlusIcon,
  TrashIcon,
} from "@heroicons/react/24/outline";
import { Dropdown, MenuProps, Modal, message } from "antd";
import * as React from "react";
import { IModelConfig, IStatus } from "../../types";
import { appContext } from "../../../hooks/provider";
import {
  fetchJSON,
  getServerUrl,
  sanitizeConfig,
  timeAgo,
  truncateText,
} from "../../utils";
import { BounceLoader, Card, CardHoverBar, LoadingOverlay } from "../../atoms";
import { ModelConfigView } from "./utils/modelconfig";

const ModelsView = ({}: any) => {
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<IStatus | null>({
    status: true,
    message: "All good",
  });

  const { user } = React.useContext(appContext);
  const serverUrl = getServerUrl();
  const listModelsUrl = `${serverUrl}/models?user_id=${user?.email}`;
  const createModelUrl = `${serverUrl}/models`;
  const testModelUrl = `${serverUrl}/models/test`;

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
    const deleteModelUrl = `${serverUrl}/models/delete?user_id=${user?.email}&model_id=${model.id}`;
    const payLoad = {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
      },
    };

    const onSuccess = (data: any) => {
      if (data && data.status) {
        message.success(data.message);
        fetchModels();
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

  const createModel = (model: IModelConfig) => {
    setError(null);
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
        const updatedModels = [data.data].concat(models || []);
        setModels(updatedModels);
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
    fetchJSON(createModelUrl, payLoad, onSuccess, onError);
  };

  React.useEffect(() => {
    if (user) {
      // console.log("fetching messages", messages);
      fetchModels();
    }
  }, []);

  const modelRows = (models || []).map((model: IModelConfig, i: number) => {
    const cardItems = [
      {
        title: "Download",
        icon: ArrowDownTrayIcon,
        onClick: (e: any) => {
          e.stopPropagation();
          // download workflow as workflow.name.json
          const element = document.createElement("a");
          const sanitizedSkill = sanitizeConfig(model);
          const file = new Blob([JSON.stringify(sanitizedSkill)], {
            type: "application/json",
          });
          element.href = URL.createObjectURL(file);
          element.download = `model_${model.model}.json`;
          document.body.appendChild(element); // Required for this to work in FireFox
          element.click();
        },
        hoverText: "Download",
      },
      {
        title: "Make a Copy",
        icon: DocumentDuplicateIcon,
        onClick: (e: any) => {
          e.stopPropagation();
          let newModel = { ...sanitizeConfig(model) };
          newModel.model = `${model.model}_copy`;
          setNewModel(newModel);
          setShowNewModelModal(true);
        },
        hoverText: "Make a Copy",
      },
      {
        title: "Delete",
        icon: TrashIcon,
        onClick: (e: any) => {
          e.stopPropagation();
          deleteModel(model);
        },
        hoverText: "Delete",
      },
    ];
    return (
      <li
        role="listitem"
        key={"modelrow" + i}
        className=" "
        style={{ width: "200px" }}
      >
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
          <div
            aria-label={`Updated ${timeAgo(model.updated_at || "")} `}
            className="text-xs"
          >
            {timeAgo(model.updated_at || "")}
          </div>
          <CardHoverBar items={cardItems} />
        </Card>
      </li>
    );
  });

  const ModelModal = ({
    model,
    setModel,
    showModelModal,
    setShowModelModal,
    handler,
  }: {
    model: IModelConfig;
    setModel: (model: IModelConfig | null) => void;
    showModelModal: boolean;
    setShowModelModal: (show: boolean) => void;
    handler?: (agent: IModelConfig) => void;
  }) => {
    const [localModel, setLocalModel] = React.useState<IModelConfig>(model);

    const closeModal = () => {
      setModel(null);
      setShowModelModal(false);
      if (handler) {
        handler(model);
      }
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
        footer={[]}
        onOk={() => {
          closeModal();
        }}
        onCancel={() => {
          closeModal();
        }}
      >
        {model && (
          <ModelConfigView
            model={localModel}
            setModel={setLocalModel}
            close={closeModal}
          />
        )}
      </Modal>
    );
  };

  const uploadModel = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".json";
    input.onchange = (e: any) => {
      const file = e.target.files[0];
      const reader = new FileReader();
      reader.onload = (e: any) => {
        const contents = e.target.result;
        if (contents) {
          try {
            const model = JSON.parse(contents);
            if (model) {
              setNewModel(model);
              setShowNewModelModal(true);
            }
          } catch (e) {
            message.error("Invalid model file");
          }
        }
      };
      reader.readAsText(file);
    };
    input.click();
  };

  const modelsMenuItems: MenuProps["items"] = [
    // {
    //   type: "divider",
    // },
    {
      key: "uploadmodel",
      label: (
        <div>
          <ArrowUpTrayIcon className="w-5 h-5 inline-block mr-2" />
          Upload Model
        </div>
      ),
    },
  ];

  const modelsMenuItemOnClick: MenuProps["onClick"] = ({ key }) => {
    if (key === "uploadmodel") {
      uploadModel();
      return;
    }
  };

  return (
    <div className="text-primary  ">
      {selectedModel && (
        <ModelModal
          model={selectedModel}
          setModel={setSelectedModel}
          setShowModelModal={setShowModelModal}
          showModelModal={showModelModal}
          handler={(model: IModelConfig | null) => {
            fetchModels();
          }}
        />
      )}
      <ModelModal
        model={newModel || defaultModel}
        setModel={setNewModel}
        setShowModelModal={setShowNewModelModal}
        showModelModal={showNewModelModal}
        handler={(model: IModelConfig | null) => {
          fetchModels();
        }}
      />

      <div className="mb-2   relative">
        <div className="     rounded  ">
          <div className="flex mt-2 pb-2 mb-2 border-b">
            <div className="flex-1 font-semibold mb-2 ">
              {" "}
              Models ({modelRows.length}){" "}
            </div>
            <div>
              <Dropdown.Button
                type="primary"
                menu={{
                  items: modelsMenuItems,
                  onClick: modelsMenuItemOnClick,
                }}
                placement="bottomRight"
                trigger={["click"]}
                onClick={() => {
                  setShowNewModelModal(true);
                }}
              >
                <PlusIcon className="w-5 h-5 inline-block mr-1" />
                New Model
              </Dropdown.Button>
            </div>
          </div>

          <div className="text-xs mb-2 pb-1  ">
            {" "}
            Create model configurations that can be reused in your agents and
            workflows. {selectedModel?.model}
          </div>
          {models && models.length > 0 && (
            <div className="w-full  relative">
              <LoadingOverlay loading={loading} />
              <ul className="   flex flex-wrap gap-3">{modelRows}</ul>
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
