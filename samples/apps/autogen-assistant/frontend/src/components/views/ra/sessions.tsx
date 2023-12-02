import {
  ClockIcon,
  PlusIcon,
  QueueListIcon,
  TrashIcon,
} from "@heroicons/react/24/outline";
import { Modal, message } from "antd";
import * as React from "react";
import { IChatSession, IStatus } from "../../types";
import { appContext } from "../../../hooks/provider";
import {
  fetchJSON,
  getSampleSkill,
  getServerUrl,
  timeAgo,
  truncateText,
} from "../../utils";
import {
  CodeBlock,
  CollapseBox,
  LaunchButton,
  LoadBox,
  LoadingOverlay,
  MarkdownView,
} from "../../atoms";
import { useConfigStore } from "../../../hooks/store";
import TextArea from "antd/es/input/TextArea";

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
  const flowConfig = useConfigStore((state) => state.flowConfig);
  const setSessions = useConfigStore((state) => state.setSessions);
  // const [session, setSession] =
  //   React.useState<IChatSession | null>(null);
  const session = useConfigStore((state) => state.session);
  const setSession = useConfigStore((state) => state.setSession);

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
      console.log(data);
      if (data && data.status) {
        message.success(data.message);
        console.log("sesssions", data);
        setSessions(data.data);
        if (data.data && data.data.length === 0) {
          createSession();
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
      console.log(data);
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
      setSession(sessions[0]);
    }
  }, [sessions]);

  const createSession = () => {
    setError(null);
    setLoading(true);

    const body = {
      user_id: user?.email,
      session:
        session === null
          ? {
              user_id: user?.email,
              flow_config: flowConfig,
              session_id: null,
            }
          : session,
    };
    // const fetch;
    const payLoad = {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    };

    console.log("payload", body);
    const onSuccess = (data: any) => {
      console.log(data);
      if (data && data.status) {
        message.success(data.message);
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
    fetchJSON(createSessionUrl, payLoad, onSuccess, onError);
  };

  React.useEffect(() => {
    if (user) {
      // console.log("fetching messages", messages);
      fetchSessions();
    }
  }, []);

  const sessionRows = sessions.map((data: IChatSession, index: number) => {
    const isSelected = session?.session_id === data.session_id;
    const rowClass = isSelected
      ? "bg-accent text-white"
      : "bg-secondary text-primary";
    return (
      <div key={"sessionsrow" + index} className="  mb-2 pb-1   ">
        <div
          className={`rounded p-2 cursor-pointer ${rowClass}`}
          role="button"
          onClick={() => {
            setSession(data);
          }}
        >
          <div className="text-xs">{truncateText(data.session_id, 27)}</div>
          <div className="text-xs text-right ">{timeAgo(data.timestamp)} </div>
        </div>
        <div className="flex mt-1 text-secondary">
          <div className="flex-1"></div>

          <div
            role="button"
            onClick={() => {
              console.log("pubish session", data);
              publishSession();
            }}
            className="text-xs px-2  hover:text-accent cursor-pointer"
          >
            {" "}
            publish{" "}
          </div>
        </div>
        {/* <div className="border-b border-dashed mx-2 mt-1"></div> */}
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
      <div className="mb-2 relative">
        <LoadingOverlay loading={loading} />
        <div className="">
          <div className="font-semibold mb-2 pb-1 border-b">Sessions </div>
          <div className="text-xs mb-2 pb-1  ">
            {" "}
            Create a new session or select an existing session to view chat.
          </div>
          <div
            style={{
              maxHeight: "300px",
            }}
            className="mb-4 overflow-y-scroll scroll rounded  "
          >
            {sessionRows}
          </div>
          {(!sessions || sessions.length == 0) && (
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
              createSession();
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
