import * as React from "react";
import { BounceLoader } from "../../atoms";
import SkillsView from "./skills";
import AgentsView from "./agents";
import WorkflowView from "./workflow";
import { Tabs } from "antd";

const BuildView = () => {
  const [loading, setLoading] = React.useState(false);

  return (
    <div className=" ">
      <div className="mb-4 text-2xl">Build </div>
      <div className="mb-4 text-secondary">
        {" "}
        Create skills, agents and workflows for building multiagent capabilities{" "}
      </div>

      <div className="mb-4">
        {" "}
        <Tabs
          tabBarStyle={{ paddingLeft: 0, marginLeft: 0 }}
          defaultActiveKey="3"
          tabPosition="left"
          items={[
            {
              label: <div className="w-full  ">Skills</div>,
              key: "1",
              children: <SkillsView />,
            },
            {
              label: "Agents",
              key: "2",
              children: <AgentsView />,
            },
            {
              label: "Workflows",
              key: "3",
              children: <WorkflowView />,
            },
          ]}
        />
      </div>

      <div></div>

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
