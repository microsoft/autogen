import * as React from "react";
import { IChatSession, IMessage, IStatus } from "../../types";
import { fetchJSON, getServerUrl, setLocalStorage } from "../../utils";
import ChatBox from "./chatbox";
import { appContext } from "../../../hooks/provider";
import { message } from "antd";
import SideBarView from "./sidebar";
import { useConfigStore } from "../../../hooks/store";
import SessionsView from "./sessions";
import AgentsWorkflowView from "./workflows";
import { Square3Stack3DIcon } from "@heroicons/react/24/outline";
import Icon from "../../icons";

const RAView = () => {
  const session: IChatSession | null = useConfigStore((state) => state.session);
  const [loading, setLoading] = React.useState(false);
  const [messages, setMessages] = React.useState<IMessage[] | null>(null);
  const [skillUpdated, setSkillUpdated] = React.useState("default");

  const skillup = {
    get: skillUpdated,
    set: setSkillUpdated,
  };

  const [config, setConfig] = React.useState(null);

  React.useEffect(() => {
    setLocalStorage("ara_config", config);
  }, [config]);

  const [error, setError] = React.useState<IStatus | null>({
    status: true,
    message: "All good",
  });

  const { user } = React.useContext(appContext);
  const serverUrl = getServerUrl();
  const fetchMessagesUrl = `${serverUrl}/messages?user_id=${user?.email}&session_id=${session?.id}`;
  const workflowConfig = useConfigStore((state) => state.workflowConfig);

  const fetchMessages = () => {
    setError(null);
    setLoading(true);
    setMessages(null);
    // const fetch;
    const payLoad = {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    };
    // console.log("payload", payLoad);
    const onSuccess = (data: any) => {
      // console.log(data);
      if (data && data.status) {
        setMessages(data.data);
        // message.success(data.message);
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
    fetchJSON(fetchMessagesUrl, payLoad, onSuccess, onError);
  };

  React.useEffect(() => {
    if (user && session) {
      // console.log("fetching messages", messages);
      fetchMessages();
    }
  }, [session]);

  return (
    <div className="h-full   ">
      <div className="flex h-full   ">
        <div className="  mr-2  rounded">
          <SideBarView />
        </div>
        <div className=" flex-1  ">
          {!session && (
            <div className=" w-full  h-full flex items-center justify-center">
              {/* {JSON.stringify(workflowConfig)} */}
              <div className="w-2/3" id="middle">
                <div className="w-full   text-center">
                  {" "}
                  <img
                    src="/images/svgs/welcome.svg"
                    alt="welcome"
                    className="text-accent inline-block object-cover w-56"
                  />
                </div>
                <SessionsView />
              </div>
            </div>
          )}

          {workflowConfig !== null && session !== null && (
            <ChatBox initMessages={messages} />
          )}
        </div>
      </div>
    </div>
  );
};
export default RAView;
