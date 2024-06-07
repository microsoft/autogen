import { Bar, Line } from "@ant-design/plots";
import * as React from "react";
import { IStatus } from "../../../../types";

const BarChartViewer = ({ data }: { data: any | null }) => {
  const [error, setError] = React.useState<IStatus | null>({
    status: true,
    message: "All good",
  });

  const [loading, setLoading] = React.useState(false);

  const config = {
    data: data.bar,
    xField: "agent",
    yField: "message",
    colorField: "tool_call",
    stack: true,
    axis: {
      y: { labelFormatter: "" },
      x: {
        labelSpacing: 4,
      },
    },
    style: {
      radiusTopLeft: 10,
      radiusTopRight: 10,
    },
    height: 60 * data.agents.length,
  };

  const config_code_exec = Object.assign({}, config);
  config_code_exec.colorField = "code_execution";

  return (
    <div className="bg-white  rounded relative">
      <div>
        <div className="grid grid-cols-2">
          <div>
            <div className=" text-gray-700  border-b border-dashed p-4">
              {" "}
              Tool Call
            </div>
            <Bar {...config} />
          </div>
          <div className=" ">
            <div className=" text-gray-700  border-b border-dashed p-4">
              {" "}
              Code Execution Status
            </div>
            <Bar {...config_code_exec} />
          </div>
        </div>
      </div>
    </div>
  );
};
export default BarChartViewer;
