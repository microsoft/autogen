import React from "react";
import { Alert } from "antd";
import { CodeSection, copyToClipboard } from "./guides";
import { Download } from "lucide-react";

const PythonGuide: React.FC = () => {
  return (
    <div className="max-w-4xl">
      <h1 className="tdext-2xl font-bold mb-6">
        Using AutoGen Studio Teams in Python Code
      </h1>

      <Alert
        className="mb-6"
        message="Prerequisites"
        description={
          <ul className="list-disc pl-4 mt-2 space-y-1">
            <li>AutoGen Studio installed</li>
          </ul>
        }
        type="info"
      />

      <div className="my-3 text-sm">
        {" "}
        You can reuse the declarative specifications of agent teams created in
        AutoGen studio in your python application by using the TeamManager
        class.{" "}
      </div>

      {/* Installation Steps */}
      <div className="space-y-6">
        {/* Virtual Environment Setup */}
        <CodeSection
          title="1. Download the team configuration"
          description=<div>
            In AutoGen Studio, select a team configuration and click download.{" "}
            <Download className="h-4 w-4 inline-block" />{" "}
          </div>
          code={``}
          onCopy={copyToClipboard}
        />

        {/* Basic Usage */}
        <CodeSection
          title="2. Run a task with the team configuration"
          description="Here's a simple example of using the TeamManager:"
          code={`from autogenstudio.teammanager import TeamManager

# Initialize the TeamManager
manager = TeamManager()

# Run a task with a specific team configuration
result = await manager.run(
task="What is the weather in New York?",
team_config="team.json"
)
print(result)`}
          onCopy={copyToClipboard}
        />
      </div>
    </div>
  );
};

export default PythonGuide;
