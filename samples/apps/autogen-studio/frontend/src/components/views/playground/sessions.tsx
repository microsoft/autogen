import {
  ChatBubbleLeftRightIcon,
  CheckIcon,
  GlobeAltIcon,
  PencilIcon,
  PlusIcon,
  Square3Stack3DIcon,
  TrashIcon,
} from "@heroicons/react/24/outline";
import { Button, Dropdown, MenuProps, Modal, message } from "antd";
import * as React from "react";
import { IChatSession, IStatus } from "../../types";
import { appContext } from "../../../hooks/provider";
import { fetchJSON, getServerUrl, timeAgo, truncateText } from "../../utils";
import { LaunchButton, LoadingOverlay } from "../../atoms";
import { useConfigStore } from "../../../hooks/store";
import AgentsWorkflowView from "./workflows";
import { text } from "stream/consumers";

const SessionsView = ({}: any) => {
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<IStatus | null>({
    status: true,
    message: "All good",
  });

  const { user } = React.useContext(appContext);
  const serverUrl = getServerUrl();
  const listSessionUrl = `${serverUrl}/sessions?user_id=${user?.email}`;
  const createSessionUrl = `${serverUrl}/sessions`;
  const renameSessionUrl = `${serverUrl}/sessions/rename?name=`;
  const publishSessionUrl = `${serverUrl}/sessions/publish`;
  const deleteSessionUrl = `${serverUrl}/sessions/delete`;

  const sessions = useConfigStore((state) => state.sessions);
  const workflowConfig = useConfigStore((state) => state.workflowConfig);
  const setSessions = useConfigStore((state) => state.setSessions);
  // const [session, setSession] =
  //   React.useState<IChatSession | null>(null);
  const session = useConfigStore((state) => state.session);
  const setSession = useConfigStore((state) => state.setSession);
  const setWorkflowConfig = useConfigStore((state) => state.setWorkflowConfig);
  const deleteSession = (session: IChatSession) => {
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
        session: session,
      }),
    };

    const onSuccess = (data: any) => {
      if (data && data.status) {
        message.success(data.message);
        setSessions(data.data);
        if (data.data && data.data.length > 0) {
          setSession(data.data[0]);
        }
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
    fetchJSON(deleteSessionUrl, payLoad, onSuccess, onError);
  };

  const [newSessionModalVisible, setNewSessionModalVisible] =
    React.useState(false);

  const fetchSessions = () => {
    setError(null);
    setLoading(true);
    // const fetch;
    const payLoad = {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    };

    const onSuccess = (data: any) => {
      if (data && data.status) {
        // message.success(data.message);
        // console.log("sessions", data);
        setSessions(data.data);
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
    fetchJSON(listSessionUrl, payLoad, onSuccess, onError);
  };

  const publishSession = () => {
    setError(null);
    setLoading(true);

    const body = {
      user_id: user?.email,
      session: session,
      tags: ["published"],
    };
    // const fetch;
    const payLoad = {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    };

    const onSuccess = (data: any) => {
      if (data && data.status) {
        message.success(data.message);
        // setSessions(data.data);
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
    fetchJSON(publishSessionUrl, payLoad, onSuccess, onError);
  };

  React.useEffect(() => {
    if (sessions && sessions.length > 0) {
      const firstSession = sessions[0];
      setSession(firstSession);
      setWorkflowConfig(firstSession?.flow_config);
    } else {
      setSession(null);
    }
  }, [sessions]);

  const createSession = () => {
    setError(null);
    setLoading(true);

    const body = {
      user_id: user?.email,
      session: {
        user_id: user?.email,
        flow_config: workflowConfig,
        session_id: null,
      },
    };
    // const fetch;
    const payLoad = {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    };

    console.log("createSession", payLoad);

    const onSuccess = (data: any) => {
      if (data && data.status) {
        message.success(data.message);
        setSessions(data.data);
        setWorkflowConfig(data.data[0]?.workflow_config);
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
    fetchJSON(createSessionUrl, payLoad, onSuccess, onError);
  };

  const renameSession = (session: IChatSession, name: string) => {
    setError(null);
    setLoading(true);

    const body = {
      user_id: user?.email,
      session: session,
    };
    // const fetch;
    const payLoad = {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    };

    console.log("renameSession to " + name, payLoad);

    const onSuccess = (data: any) => {
      if (data && data.status) {
        message.success(data.message);
        setSessions(data.data);
        setWorkflowConfig(data.data[0]?.workflow_config);
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
    fetchJSON(renameSessionUrl+name, payLoad, onSuccess, onError);
  }

  React.useEffect(() => {
    if (user) {
      // console.log("fetching messages", messages);
      fetchSessions();
    }
  }, []);

  const [renameMenu, setRenameMenu] = React.useState<{[key: string]: {visible: number, nameValue: string}}>({});
  const sessionRows = sessions.map((data: IChatSession, index: number) => {
    const isSelected = session?.id === data.id;
    const rowClass = isSelected
      ? "bg-accent text-white"
      : "bg-secondary text-primary";
    const handleRename = (event: React.ChangeEvent<HTMLInputElement>) => {
      console.log("handleRename", event.target.value);
      setRenameMenu({...renameMenu, [data.id]: {...renameMenu[data.id], nameValue: event.target.value}});
    }
    const submitRename = (event: React.FormEvent<HTMLFormElement>) => {
      const newNameValue = renameMenu[data.id]?.nameValue || '';
      event.preventDefault();
      console.log("submitRename", newNameValue);
      setRenameMenu({...setRenameMenu, [data.id]: 0});
      renameSession(data, newNameValue);
    }

    let items: MenuProps["items"] = [
      {
        label: (
          <div
            onClick={() => {
              console.log("deleting session");
              deleteSession(data);
            }}
          >
            <TrashIcon
              role={"button"}
              title={"Delete"}
              className="h-4 w-4 mr-1 inline-block"
            />
            Delete
          </div>
        ),
        key: "delete",
      },
      {
        label: (
          <div
            onClick={() => {
              console.log("publishing session");
              publishSession();
            }}
          >
            <GlobeAltIcon
              role={"button"}
              title={"Publish"}
              className="h-4 w-4 mr-1 inline-block"
            />
            Publish
          </div>
        ),
        key: "publish",
      },
      {
        label: (
          <div
            onClick={() => {
              console.log("renaming session");
              setRenameMenu({...setRenameMenu, [data.id]: {...renameMenu[data.id], visible: 1}});
            }}
          >
            <PencilIcon
              role={"button"}
              title={"Rename"}
              className="h-4 w-4 mr-1 inline-block"
            />
            Rename
          </div>
        ),
        key: "rename",
      },
    ];

    items.push();
    const menu = (
      <Dropdown menu={{ items }} trigger={["click"]} placement="bottomRight">
        <div
          role="button"
          className={`float-right ml-2 duration-100 hover:bg-secondary font-semibold px-2 pb-1  rounded ${
            isSelected ? "hover:text-accent" : ""
          }`}
        >
          <span className={`block -mt-2 ${isSelected ? "text-white" : ""}`}>
            {" "}
            ...
          </span>
        </div>
      </Dropdown>
    );

    let displayName = data.id;
    if (data.name != null) {
      displayName = data.name
    }
    return (
      <div
        key={"sessionsrow" + index}
        className="group relative  mb-2 pb-1  border-b border-dashed "
      >
        {items.length > 0 && (
          <div className="  absolute right-2 top-2 group-hover:opacity-100 opacity-0 ">
            {menu}
          </div>
        )}
        <div
          className={`rounded p-2 cursor-pointer ${rowClass}`}
          role="button"
          onClick={() => {
            setSession(data);
            setWorkflowConfig(data.flow_config);
          }}
        >
          {(!renameMenu[data.id] || renameMenu[data.id]?.visible == 0) && (<div className="text-xs">{truncateText(displayName, 20)}</div>)}
          {(renameMenu[data.id]?.visible == 1) && (
            <form onSubmit={submitRename}>
              <div style={{display: 'flex', flexDirection: 'row', alignItems: 'center'}}>
                <input id={`renameInputText-${data.id}`} type="text" value={renameMenu[data.id]?.nameValue} onChange={handleRename} style={{color: 'black'}}/>
                <button type="submit"><CheckIcon role={"button"} className="h-5 w-5 ml-1 inline-block"/></button>
              </div>
            </form>
          )}
          <div className="text-xs mt-1">
            <Square3Stack3DIcon className="h-4 w-4 inline-block mr-1" />
            {data.flow_config.name}
          </div>
          <div className="text-xs text-right ">{timeAgo(data.timestamp)}</div>
        </div>
      </div>
    );
  });

  let windowHeight, skillsMaxHeight;
  if (typeof window !== "undefined") {
    windowHeight = window.innerHeight;
    skillsMaxHeight = windowHeight - 400 + "px";
  }

  return (
    <div className="  ">
      <Modal
        title={
          <div className="font-semibold mb-2 pb-1 border-b">
            <Square3Stack3DIcon className="h-5 w-5 inline-block mr-1" />
            New Sessions{" "}
          </div>
        }
        open={newSessionModalVisible}
        footer={[
          <Button
            key="back"
            onClick={() => {
              setNewSessionModalVisible(false);
            }}
          >
            Cancel
          </Button>,
          <Button
            key="submit"
            type="primary"
            disabled={!workflowConfig}
            onClick={() => {
              setNewSessionModalVisible(false);
              createSession();
            }}
          >
            Create
          </Button>,
        ]}
      >
        <AgentsWorkflowView />
      </Modal>
      <div className="mb-2 relative">
        <div className="">
          <div className="font-semibold mb-2 pb-1 border-b">
            <ChatBubbleLeftRightIcon className="h-5 w-5 inline-block mr-1" />
            Sessions{" "}
          </div>
          {sessions && sessions.length > 0 && (
            <div className="text-xs  hidden mb-2 pb-1  ">
              {" "}
              Create a new session or select an existing session to view chat.
            </div>
          )}
          <div
            style={{
              maxHeight: skillsMaxHeight,
            }}
            className="mb-4 overflow-y-auto scroll rounded relative "
          >
            {sessionRows}
            <LoadingOverlay loading={loading} />
          </div>
          {(!sessions || sessions.length == 0) && !loading && (
            <div className="text-xs text-gray-500">
              No sessions found. Create a new session to get started.
            </div>
          )}
        </div>
        <div className="flex gap-x-2">
          <div className="flex-1"></div>
          <LaunchButton
            className="text-sm p-2 px-3"
            onClick={() => {
              if (sessions && sessions.length > 0) {
                setWorkflowConfig(sessions[0]?.flow_config);
              } else {
                setWorkflowConfig(null);
              }
              setNewSessionModalVisible(true);
            }}
          >
            {" "}
            <PlusIcon className="w-5 h-5 inline-block mr-1" />
            New
          </LaunchButton>
        </div>
      </div>
    </div>
  );
};

export default SessionsView;
