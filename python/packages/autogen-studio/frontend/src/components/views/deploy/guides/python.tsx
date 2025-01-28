import React from "react";
import { Alert } from "antd";
import { CodeSection, copyToClipboard } from "./guides";
import { Download } from "lucide-react";

const PythonGuide: React.FC = () => {
  return (
    <div className="">
      <h1 className="tdext-2xl font-bold mb-6">
        Using AutoGen Studio Teams in Python Code and REST API
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
        class. . In TeamBuilder, select a team configuration and click download.{" "}
        <Download className="h-4 w-4 inline-block" />{" "}
      </div>

      {/* Installation Steps */}
      <div className="space-y-6">
        {/* Basic Usage */}
        <CodeSection
          title="1. Run a Team in Python"
          description="Here's a simple example of using the TeamManager class from AutoGen Studio in your python code."
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

        <CodeSection
          title="2. Serve a Team as a REST API"
          description=<div>
            AutoGen Studio offers a convenience CLI command to serve a team as a
            REST API endpoint.{" "}
          </div>
          code={`
autogenstudio serve --team path/to/team.json --port 8084  
          `}
          onCopy={copyToClipboard}
        />
      </div>
    </div>
  );
};

export default PythonGuide;
