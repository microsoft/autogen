import * as React from "react";
import SkillsView from "./skills";
import ModelsView from "./models";
import AgentsView from "./agents";
import WorkflowView from "./workflow";
import LabsView from "./labs";
import { Tabs } from "antd";
import {
  BugAntIcon,
  CpuChipIcon,
  Square2StackIcon,
  Square3Stack3DIcon,
} from "@heroicons/react/24/outline";


const BuildView = () => {
  return (
    <div className=" ">
      {/* <div className="mb-4 text-2xl">Build </div> */}
      <div className="mb-6 text-sm hidden text-secondary">
        {" "}
        Create skills, agents and workflows for building multiagent capabilities{" "}
      </div>

      <div className="mb-4 text-primary">
        {" "}
        <Tabs
          tabBarStyle={{ paddingLeft: 0, marginLeft: 0 }}
          defaultActiveKey="5" // TODO: revert back to 4
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
                <div className="w-full  ">
                  {" "}
                  <CpuChipIcon className="h-4 w-4 inline-block mr-1" />
                  Models
                </div>
              ),
              key: "2",
              children: <ModelsView />,
            },
            {
              label: (
                <>
                  <Square2StackIcon className="h-4 w-4 inline-block mr-1" />
                  Agents
                </>
              ),
              key: "3",
              children: <AgentsView />,
            },
            {
              label: (
                <>
                  <Square3Stack3DIcon className="h-4 w-4 inline-block mr-1" />
                  Workflows
                </>
              ),
              key: "4",
              children: <WorkflowView />,
            },
            {
              label: (
                <>
                  <Square3Stack3DIcon className="h-4 w-4 inline-block mr-1" />
                  Labs
                </>
              ),
              key: "5",
              children: <LabsView />,
            },
          ]}
        />
      </div>

      <div></div>
    </div>
  );
};

export default BuildView;
