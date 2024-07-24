import {
    ArrowDownTrayIcon,
    InformationCircleIcon,
    PlusIcon,
    TrashIcon,
  } from "@heroicons/react/24/outline";
  import { Dropdown, Modal, message } from "antd";
  import * as React from "react";
  import { IStatus } from "../../types";
  import {
    truncateText,
  } from "../../utils";
  import { BounceLoader, Card, CardHoverBar, LoadingOverlay } from "../../atoms";
import AgentEvalView from "./agenteval";
    
  const LabsView = ({}: any) => {
    const [loading, setLoading] = React.useState(false);
    const [error, setError] = React.useState<IStatus | null>({
      status: true,
      message: "All good",
    });

    const labList = ["AgentEval"];
    const [selectedLab, setSelectedLab] = React.useState<string>("");

    if (selectedLab === "AgentEval") {
      return <AgentEvalView onBack={() => setSelectedLab("")} />
    }
  
    const labRows = (labList).map(
      (lab, i: number) => {
        return (
          <li
            key={"labrow" + i}
            className="block   h-full"
            style={{ width: "200px" }}
          >
            <Card
              className="  block p-2 cursor-pointer"
              onClick={() => {
                setSelectedLab(lab);
              }}
            >
              <div
                style={{ minHeight: "65px" }}
                className="break-words  my-2"
                aria-hidden="true"
              >
                {truncateText(lab, 70)}
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
    