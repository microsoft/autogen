import * as React from "react";
import {
  IContextItem,
  IGenConfig,
  IMessage,
  IStatus,
  ITextGeneratorConfig,
} from "../../types";
import { fetchJSON, getLocalStorage, setLocalStorage } from "../../utils";
import ChatBox from "./workspace/chatbox";
import MetaDataView from "./workspace/metadata";
import { appContext } from "../../../hooks/provider";
import { message, notification } from "antd";
import SideBarView from "./workspace/sidebar";
import ArtifactBarView from "./workspace/artifactbar";

const RAView = () => {
  const [loading, setLoading] = React.useState(false);
  const [context, setContext] = React.useState<IContextItem | null>(null);
  const [messages, setMessages] = React.useState<IMessage[]>([]);
  const [skillUpdated, setSkillUpdated] = React.useState("default");

  const [api, contextHolder] = notification.useNotification();

  const skillup = {
    get: skillUpdated,
    set: setSkillUpdated,
  };

  const messageFetched = React.useRef(false);

  const initMetaData = {};
  const [metadata, setMetadata] = React.useState(initMetaData);

  const initTextGenerationConfig: ITextGeneratorConfig = {
    temperature: 0,
    n: 1,
    model: "gpt-3.5-turbo-0301",
    max_tokens: 2048,
    messages: [],
  };

  const initMetadata = {
    ranker: "default",
    prompter: "default",
    top_k: 25,
  };

  let confLocalStorage = getLocalStorage("ara_config");

  const initConfig: IGenConfig = {
    metadata: initMetadata,
    textgen_config: initTextGenerationConfig,
    use_cache: false,
    personalize: false,
    ra: "TwoAgents",
  };

  const [config, setConfig] = React.useState(initConfig);

  React.useEffect(() => {
    setLocalStorage("ara_config", config);
  }, [config]);

  const [error, setError] = React.useState<IStatus | null>({
    status: true,
    message: "All good",
  });

  const { user } = React.useContext(appContext);
  const serverUrl = process.env.GATSBY_API_URL;
  const fetchMessagesUrl = `${serverUrl}/messages?user_id=${user?.email}`;

  const fetchMessages = () => {
    setError(null);
    setLoading(true);
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
    if (user) {
      // console.log("fetching messages", messages);
      fetchMessages();
    }
  }, []);

  return (
    <div className="h-full   ">
      {contextHolder}

      {/* <div className="border mt-2 rounded p-2 mb-2">
        <ClearDBView setMessages={setMessages} />
      </div> */}
      <div className="flex h-full   ">
        <div className="border  mr-2 rounded">
          <SideBarView
            setMessages={setMessages}
            skillup={skillup}
            config={{ get: config, set: setConfig }}
            setMetadata={setMetadata}
          />
        </div>
        <div className=" flex-1  ">
          {" "}
          <ChatBox
            context={context}
            config={{ get: config, set: setConfig }}
            setMetadata={setMetadata}
            initMessages={messages}
            skillup={skillup}
          />
        </div>
        <div style={{ maxWidth: "400px" }} className="  rounded     ">
          <div className="h-full w-full ml-2  align-bottom    ">
            <MetaDataView metadata={metadata} setMetadata={setMetadata} />
          </div>
          {/* <ArtifactBarView /> */}
        </div>
      </div>
    </div>
  );
};
export default RAView;
