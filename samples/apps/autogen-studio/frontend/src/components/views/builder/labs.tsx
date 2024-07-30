import * as React from "react";
import { BounceLoader, LoadingOverlay } from "../../atoms";
import AgentEvalView from "./agenteval";
import { TrophyIcon } from "@heroicons/react/24/outline";
import { Card } from "antd";

const LabsView = ({}: any) => {
  const [loading, setLoading] = React.useState(false);
  const labList = [{name:"AgentEval", symbol:TrophyIcon}];
  const [selectedLab, setSelectedLab] = React.useState<string>("");

  if (selectedLab === "AgentEval") {
    return <AgentEvalView onBack={() => setSelectedLab("")} />
  }

  const labRows = (labList).map(
    (lab, i: number) => {
      const IconComponent = lab.symbol; 
      return (
        <li key={"labrow" + i} className="block" >
          <Card
            size="small"
            className="block cursor-pointer text-center text-black items-center justify-center w-2/3"
            onClick={() => {
              setSelectedLab(lab.name);
            }}
          >
            <div
              className="break-words my-2"
              aria-hidden="true"
            >
              {lab.name}
            </div>
            <div className="flex-grow flex items-center justify-center">
              <IconComponent className="h-2/3 w-2/3"/>
            </div>
          </Card>
        </li>
      );
    }
  );

  return (
    <div className=" text-primary ">
      <div className="mb-2   relative">
        <div className="     rounded  ">
          <div className="flex mt-2 pb-2 mb-2 border-b">
            <div className="flex-1 font-semibold  mb-2">
              {" "}
              Labs ({labRows.length}){" "}
            </div>
          </div>
          <div className="text-xs mb-2 pb-1">
            {" "}
            List of experimental AutoGen Studio Labs
          </div>
          <div className="w-full relative" >
            <LoadingOverlay loading={loading} />
            <ul className="flex flex-wrap gap-3">{labRows}</ul>
          </div>
          {loading && (
            <div className="  w-full text-center">
              {" "}
              <BounceLoader />{" "}
              <span className="inline-block"> loading .. </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default LabsView;