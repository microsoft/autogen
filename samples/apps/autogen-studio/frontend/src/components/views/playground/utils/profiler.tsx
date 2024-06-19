import { Tooltip, message } from "antd";
import * as React from "react";
import { IStatus, IChatMessage } from "../../../types";
import { fetchJSON, getServerUrl } from "../../../utils";
import { appContext } from "../../../../hooks/provider";
import { InformationCircleIcon } from "@heroicons/react/24/outline";

const BarChartViewer = React.lazy(() => import("./charts/bar"));

const ProfilerView = ({
  agentMessage,
}: {
  agentMessage: IChatMessage | null;
}) => {
  const [error, setError] = React.useState<IStatus | null>({
    status: true,
    message: "All good",
  });

  const [loading, setLoading] = React.useState(false);
  const [profile, setProfile] = React.useState<any | null>(null);

  const { user } = React.useContext(appContext);
  const serverUrl = getServerUrl();

  const fetchProfile = (messageId: number) => {
    const profilerUrl = `${serverUrl}/profiler/${messageId}?user_id=${user?.email}`;
    setError(null);
    setLoading(true);
    const payLoad = {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    };

    const onSuccess = (data: any) => {
      console.log(data);
      if (data && data.status) {
        setProfile(data.data);
        setTimeout(() => {
          // scroll parent to bottom
          const parent = document.getElementById("chatbox");
          if (parent) {
            parent.scrollTop = parent.scrollHeight;
          }
        }, 4000);
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
    fetchJSON(profilerUrl, payLoad, onSuccess, onError);
  };

  React.useEffect(() => {
    if (user && agentMessage && agentMessage.id) {
      fetchProfile(agentMessage.id);
    }
  }, []);

  const UsageViewer = ({ usage }: { usage: any }) => {
    const usageRows = usage.map((usage: any, index: number) => (
      <div key={index} className="  borpder  rounded">
        {(usage.total_cost != 0 || usage.total_tokens != 0) && (
          <>
            <div className="bg-secondary p-2 text-xs rounded-t">
              {usage.agent}
            </div>
            <div className="bg-tertiary p-3 rounded-b inline-flex gap-2 w-full">
              {usage.total_tokens && usage.total_tokens != 0 && (
                <div className="flex flex-col text-center w-full">
                  <div className="w-full  px-2 text-2xl ">
                    {usage.total_tokens}
                  </div>
                  <div className="w-full text-xs">tokens</div>
                </div>
              )}
              {usage.total_cost && usage.total_cost != 0 && (
                <div className="flex flex-col text-center w-full">
                  <div className="w-full px-2  text-2xl ">
                    {usage.total_cost?.toFixed(3)}
                  </div>
                  <div className="w-full text-xs">USD</div>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    ));
    return (
      <div className="inline-flex gap-3  flex-wrap">{usage && usageRows}</div>
    );
  };

  return (
    <div className="   relative">
      <div className="text-sm   ">
        {/* {profile && <RadarMetrics profileData={profile} />} */}
        {profile && <BarChartViewer data={profile} />}

        <div className="mt-4">
          <div className="mt-4  mb-4  txt">
            LLM Costs
            <Tooltip
              title={
                "LLM tokens below based on data returned by the model. Support for exact costs may vary."
              }
            >
              <InformationCircleIcon className="ml-1 text-gray-400 inline-block w-4 h-4" />
            </Tooltip>
          </div>
          {profile && profile.usage && <UsageViewer usage={profile.usage} />}
        </div>
      </div>
    </div>
  );
};
export default ProfilerView;
