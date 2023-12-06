import * as React from "react";
import { IChatSession, IMessage, IStatus } from "../../types";
import { fetchJSON, getServerUrl, setLocalStorage } from "../../utils";
import ChatBox from "./chatbox";
import { appContext } from "../../../hooks/provider";
import { message } from "antd";
import SideBarView from "./sidebar";
import { useConfigStore } from "../../../hooks/store";

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
  const fetchMessagesUrl = `${serverUrl}/messages?user_id=${user?.email}&session_id=${session?.session_id}`;

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
        console.log("******* messages received ", data);
        setMessages(data.data);
        message.success(data.message);
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
          <SideBarView
            setMessages={setMessages}
            skillup={skillup}
            config={{ get: config, set: setConfig }}
          />
        </div>
        <div className=" flex-1  ">
          {" "}
          <ChatBox
            config={{ get: config, set: setConfig }}
            initMessages={messages}
            skillup={skillup}
          />
        </div>
      </div>
    </div>
  );
};
export default RAView;
