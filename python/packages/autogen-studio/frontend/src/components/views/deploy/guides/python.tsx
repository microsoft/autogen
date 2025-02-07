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

      {/* Basic Usage */}
      <CodeSection
        title="1. Build Your Team in Python, Export as JSON"
        description="Here is an example of building an Agent Team in python and exporting it as a JSON file."
        code={`
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.conditions import  TextMentionTermination
 
agent = AssistantAgent(
        name="weather_agent",
        model_client=OpenAIChatCompletionClient(
            model="gpt-4o-mini", 
        ), 
    ) 
agent_team = RoundRobinGroupChat([agent], termination_condition=TextMentionTermination("TERMINATE"))
config = agent_team.dump_component()
print(config.model_dump_json())`}
        onCopy={copyToClipboard}
      />

      {/* Installation Steps */}
      <div className="space-y-6">
        {/* Basic Usage */}
        <CodeSection
          title="2. Run a Team in Python"
          description="Here's a simple example of using the TeamManager class from AutoGen Studio in your python code."
          code={`
from autogenstudio.teammanager import TeamManager

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
          title="3. Serve a Team as a REST API"
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
