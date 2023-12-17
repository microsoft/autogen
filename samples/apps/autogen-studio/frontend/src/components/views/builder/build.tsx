import * as React from "react";
import SkillsView from "./skills";
import AgentsView from "./agents";
import WorkflowView from "./workflow";
import { Tabs } from "antd";
import {
  BugAntIcon,
  Square2StackIcon,
  Square3Stack3DIcon,
} from "@heroicons/react/24/outline";

const BuildView = () => {
  return (
    <div className=" ">
      {/* <div className="mb-4 text-2xl">Build </div> */}
      <div className="mb-6 text-sm text-secondary">
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
              label: (
                <div className="w-full  ">
                  {" "}
                  <BugAntIcon className="h-4 w-4 inline-block mr-1" />
                  Skills
                </div>
              ),
              key: "1",
              children: <SkillsView />,
            },
            {
              label: (
                <>
                  <Square2StackIcon className="h-4 w-4 inline-block mr-1" />
                  Agents
                </>
              ),
              key: "2",
              children: <AgentsView />,
            },
            {
              label: (
                <>
                  <Square3Stack3DIcon className="h-4 w-4 inline-block mr-1" />
                  Workflows
                </>
              ),
              key: "3",
              children: <WorkflowView />,
            },
          ]}
        />
      </div>

      <div></div>
    </div>
  );
};

export default BuildView;
