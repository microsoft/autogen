import { Select, message } from "antd";
import * as React from "react";
import { LoadingOverlay } from "../../../atoms";
import { IWorkflow, IStatus, IMessage, IChatMessage } from "../../../types";
import { fetchJSON, getServerUrl } from "../../../utils";
import { appContext } from "../../../../hooks/provider";
import { Link } from "gatsby";
import RadarMetrics from "./charts/radar";
import BarChart from "@ant-design/plots/es/components/bar";
import BarChartViewer from "./charts/bar";

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
    const profilerUrl = `${serverUrl}/profiler/${messageId}/?user_id=${user?.email}`;
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

  return (
    <div className="   relative">
      <div className="text-sm   ">
        {/* {profile && <RadarMetrics profileData={profile} />} */}
        {profile && <BarChartViewer data={profile} />}
      </div>
    </div>
  );
};
export default ProfilerView;
