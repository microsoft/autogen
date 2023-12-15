import * as React from "react";
import { BounceLoader } from "../../atoms";
import SkillsView from "./skills";
import AgentsView from "./agents";
import WorkflowView from "./workflow";

const BuildView = () => {
  const [loading, setLoading] = React.useState(false);

  return (
    <div className=" ">
      <div className="mb-4 text-2xl">Build </div>
      <div className="mb-4 text-secondary">
        {" "}
        Create skills, agents and workflows for building multiagent capabilities{" "}
      </div>

      <div>
        <SkillsView />
        <AgentsView />
        <WorkflowView />
      </div>

      {loading && (
        <div className="w-full text-center boder mt-4">
          <div>
            {" "}
            <BounceLoader />
          </div>
          loading gallery
        </div>
      )}
    </div>
  );
};

export default BuildView;
