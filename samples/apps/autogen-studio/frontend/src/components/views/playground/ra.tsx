import * as React from "react";
import { IChatSession, IMessage, IStatus } from "../../types";
import { fetchJSON, getServerUrl, setLocalStorage } from "../../utils";
import ChatBox from "./chatbox";
import { appContext } from "../../../hooks/provider";
import { message } from "antd";
import SideBarView from "./sidebar";
import { useConfigStore } from "../../../hooks/store";
import SessionsView from "./sessions";

const RAView = () => {
  const session: IChatSession | null = useConfigStore((state) => state.session);
  const [loading, setLoading] = React.useState(false);
  const [messages, setMessages] = React.useState<IMessage[] | null>(null);

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
  const fetchMessagesUrl = `${serverUrl}/sessions/${session?.id}/messages?user_id=${user?.email}`;

  const fetchMessages = () => {
    setError(null);
    setLoading(true);
    setMessages(null);
    const payLoad = {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    };
    const onSuccess = (data: any) => {
      if (data && data.status) {
        setMessages(data.data);
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

          {session !== null && (
            <ChatBox initMessages={messages} session={session} />
          )}
        </div>
      </div>
    </div>
  );
};
export default RAView;
