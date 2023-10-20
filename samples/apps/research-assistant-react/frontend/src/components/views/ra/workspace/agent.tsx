import {
  ChevronLeftIcon,
  ChevronRightIcon,
  PencilIcon,
} from "@heroicons/react/24/outline";
import * as React from "react";
import ClearDBView from "./cleardb";
import { IStatus } from "../../../types";
import { appContext } from "../../../../hooks/provider";
import { Button, Modal, Select, Switch, message } from "antd";
import { fetchJSON, truncateText } from "../../../utils";
import { LoadBox } from "../../../atoms";
import { set, update } from "lodash";

const AgentView = ({ config }: any) => {
  // console.log("config", config);
  const [profileLoading, setProfileLoading] = React.useState(false);
  const [isOpen, setIsOpen] = React.useState(false);

  const serverUrl = process.env.GATSBY_API_URL;
  const [selectedAgent, setSelectedAgent] = React.useState<number>(0);

  const { user } = React.useContext(appContext);
  const fetchRAUrl = `${serverUrl}/ras`;
  const updateProfileUrl = `${serverUrl}/profile`;

  const [error, setError] = React.useState<IStatus | null>({
    status: true,
    message: "All good",
  });

  const [personalization, setPersonalization] = React.useState(false);

  const [agents, setAgents] = React.useState<any>([]);
  const [textChanged, setTextChanged] = React.useState(false);

  const profileDivRef = React.useRef<HTMLDivElement>(null);

  const fetchRA = () => {
    setError(null);
    setProfileLoading(true);
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
        setAgents(data.data);

        console.log("agents", data);
      } else {
        message.error(data.message);
      }
      setProfileLoading(false);
    };
    const onError = (err: any) => {
      setError(err);

      message.error(err.message);
      setProfileLoading(false);
    };
    fetchJSON(fetchRAUrl, payLoad, onSuccess, onError);
  };

  const raOptions = (agents || []).map((agent: any, i: number) => {
    return {
      value: agent.agent,
      label: agent.title,
      key: i,
    };
  });

  React.useEffect(() => {
    if (user) {
      fetchRA();
    }
  }, []);

  // const minWidth = isOpen ? "200px" : "50px";
  return (
    <div className="">
      <div className="mt-4">
        <hr className="mb-2" />
        <div className="text-sm mb-2 font-semibold">Multi-Agent Workflow</div>
        <div className="text-sm mt-2 mb-2 ">
          Select an multi-agent workflow to use
        </div>
        {agents && agents.length > 0 && (
          <>
            <Select
              labelInValue
              defaultValue={{
                value: agents[selectedAgent].agent,
                label: agents[selectedAgent].title,
                key: selectedAgent,
              }}
              //   style={{ width: 200 }}
              className="w-full"
              onChange={(value: {
                value: string;
                label: React.ReactNode;
                key: any;
              }) => {
                console.log("changed", value.key);
                setSelectedAgent(value.key);
                config.set({ ...config.get, ra: value.value });
              }}
              options={raOptions}
            />

            <div className="text-sm mt-2 text-secondary break-words">
              {agents[selectedAgent].description}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default AgentView;
