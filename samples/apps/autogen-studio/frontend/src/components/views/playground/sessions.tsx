import {
  ChatBubbleLeftRightIcon,
  ExclamationTriangleIcon,
  GlobeAltIcon,
  PencilIcon,
  PlusIcon,
  Square3Stack3DIcon,
  TrashIcon,
} from "@heroicons/react/24/outline";
import { Button, Dropdown, Input, MenuProps, Modal, message } from "antd";
import * as React from "react";
import { IChatSession, IWorkflow, IStatus } from "../../types";
import { appContext } from "../../../hooks/provider";
import { fetchJSON, getServerUrl, timeAgo } from "../../utils";
import { LaunchButton, LoadingOverlay } from "../../atoms";
import { useConfigStore } from "../../../hooks/store";
import WorkflowSelector from "./utils/selectors";

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
  const publishSessionUrl = `${serverUrl}/sessions/publish`;

  const sessions = useConfigStore((state) => state.sessions);

  const setSessions = useConfigStore((state) => state.setSessions);
  const sampleSession: IChatSession = {
    user_id: user?.email || "",
    name:
      "New Session " +
      new Date().toLocaleString("en-US", {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "numeric",
        hour12: true,
      }),
  };
  const [selectedSession, setSelectedSession] =
    React.useState<IChatSession | null>(sampleSession);
  // const [session, setSession] =
  //   React.useState<IChatSession | null>(null);
  const session = useConfigStore((state) => state.session);
  const setSession = useConfigStore((state) => state.setSession);

  const isSessionButtonsDisabled = useConfigStore(
    (state) => state.areSessionButtonsDisabled
  );

  const deleteSession = (session: IChatSession) => {
    setError(null);
    setLoading(true);
    // const fetch;
    const deleteSessionUrl = `${serverUrl}/sessions/delete?user_id=${user?.email}&session_id=${session.id}`;
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
        fetchSessions();
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
    } else {
      setSession(null);
    }
  }, [sessions]);

  const createSession = (session: IChatSession) => {
    setError(null);
    setLoading(true);

    // const fetch;
    const payLoad = {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(session),
    };

    const onSuccess = (data: any) => {
      if (data && data.status) {
        message.success(data.message);
        fetchSessions();
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

  React.useEffect(() => {
    if (user) {
      fetchSessions();
    }
  }, []);

  const sessionRows = sessions.map((data: IChatSession, index: number) => {
    const isSelected = session?.id === data.id;
    const rowClass = isSelected
      ? "bg-accent text-white"
      : "bg-secondary text-primary";

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
              // get current clicked session
              setSelectedSession(data);
              setNewSessionModalVisible(true);
            }}
          >
            <PencilIcon
              role={"button"}
              title={"Edit"}
              className="h-4 w-4 mr-1 inline-block"
            />
            Edit
          </div>
        ),
        key: "edit",
      },
      // {
      //   label: (
      //     <div
      //       onClick={() => {
      //         console.log("publishing session");
      //         publishSession();
      //       }}
      //     >
      //       <GlobeAltIcon
      //         role={"button"}
      //         title={"Publish"}
      //         className="h-4 w-4 mr-1 inline-block"
      //       />
      //       Publish
      //     </div>
      //   ),
      //   key: "publish",
      // },
    ];

    items.push();
    const menu = (
      <Dropdown
        menu={{ items: items }}
        trigger={["click"]}
        placement="bottomRight"
      >
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

    return (
      <div
        key={"sessionsrow" + index}
        className={`group relative  mb-2 pb-1  border-b border-dashed ${
          isSessionButtonsDisabled ? "opacity-50 pointer-events-none" : ""
        }`}
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
            // setWorkflowConfig(data.flow_config);
            if (!isSessionButtonsDisabled) {
              setSession(data);
            }
          }}
        >
          <div className="text-xs mt-1">
            <Square3Stack3DIcon className="h-4 w-4 inline-block mr-1" />
            {data.name}
          </div>
          <div className="text-xs text-right ">
            {timeAgo(data.created_at || "")}
          </div>
        </div>
      </div>
    );
  });

  let windowHeight, skillsMaxHeight;
  if (typeof window !== "undefined") {
    windowHeight = window.innerHeight;
    skillsMaxHeight = windowHeight - 400 + "px";
  }

  const NewSessionModal = ({ session }: { session: IChatSession | null }) => {
    const [workflow, setWorkflow] = React.useState<IWorkflow | null>(null);
    const [localSession, setLocalSession] = React.useState<IChatSession | null>(
      session
    );

    React.useEffect(() => {
      if (workflow && workflow.id && localSession) {
        setLocalSession({ ...localSession, workflow_id: workflow.id });
      }
    }, [workflow]);

    const sessionExists =
      localSession !== null && localSession.id !== undefined;

    return (
      <Modal
        onCancel={() => {
          setNewSessionModalVisible(false);
        }}
        title={
          <div className="font-semibold mb-2 pb-1 border-b">
            <Square3Stack3DIcon className="h-5 w-5 inline-block mr-1" />
            New Session{" "}
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
            disabled={!workflow}
            onClick={() => {
              setNewSessionModalVisible(false);
              if (localSession) {
                createSession(localSession);
              }
            }}
          >
            Create
          </Button>,
        ]}
      >
        <WorkflowSelector
          workflow={workflow}
          setWorkflow={setWorkflow}
          workflow_id={selectedSession?.workflow_id}
          disabled={sessionExists}
        />
        <div className="my-2 text-xs"> Session Name </div>
        <Input
          placeholder="Session Name"
          value={localSession?.name || ""}
          onChange={(event) => {
            if (localSession) {
              setLocalSession({ ...localSession, name: event.target.value });
            }
          }}
        />
        <div className="text-xs mt-4">
          {" "}
          {timeAgo(localSession?.created_at || "", true)}
        </div>
      </Modal>
    );
  };

  return (
    <div className="  ">
      <NewSessionModal session={selectedSession || sampleSession} />
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
            className={`text-sm p-2 px-3 ${isSessionButtonsDisabled ? 'opacity-50 cursor-not-allowed' : ''}`}
            onClick={() => {
              setSelectedSession(sampleSession);
              setNewSessionModalVisible(true);
            }}
          >
            {" "}
            <PlusIcon className="w-5 h-5 inline-block mr-1" />
            New
          </LaunchButton>
        </div>
      </div>

      {error && !error.status && (
        <div className="p-2 border border-orange-500 text-secondary  rounded mt-4   text-sm">
          {" "}
          <ExclamationTriangleIcon className="h-5 text-orange-500 inline-block mr-2" />{" "}
          {error.message}
        </div>
      )}
    </div>
  );
};

export default SessionsView;
