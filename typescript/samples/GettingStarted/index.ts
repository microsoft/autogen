import "reflect-metadata";
import { AgentsApp, AgentsAppBuilder } from "../../src/core/AgentsApp";
import { CheckerAgent } from "./CheckerAgent"; // Ensure file is named exactly "CheckerAgent.ts"
import { ModifierAgent } from "./ModifierAgent";
import { CountMessage } from "./CountMessage";
import { TypeSubscription } from "../../src/core/TypeSubscription";
import { AgentId, IAgentRuntime } from "../../src/contracts/IAgentRuntime";

export { CountMessage } from "./CountMessage";
export { CountUpdate } from "./CountUpdate";

async function main() {
  // Create and configure the app
  const appBuilder = new AgentsAppBuilder()
    .useInProcessRuntime(false); // Set deliverToSelf to false
  
  const app = await appBuilder.build();

  // Setup shutdown handler
  const shutdown = () => {
    app.shutdown();
  };

  // Register agents
  await app.runtime.registerAgentFactoryAsync("Checker", 
    async (id: AgentId, runtime: IAgentRuntime) => 
      new CheckerAgent(id, runtime));
  
  await app.runtime.registerAgentFactoryAsync("Modifier", 
    async (id: AgentId, runtime: IAgentRuntime) => 
      new ModifierAgent(id, runtime));

  // Add subscriptions
  await app.runtime.addSubscriptionAsync(
    new TypeSubscription("CountTopic", "Modifier")
  );
  await app.runtime.addSubscriptionAsync(
    new TypeSubscription("UpdateTopic", "Checker")
  );

  // Start the app
  await app.start();

  // Send initial message
  await app.publishMessage(
    { count: 10 },
    { type: "CountTopic", source: "start" }
  );

  // Wait for shutdown
  await app.waitForShutdown();
}

// Run the program
main().catch(console.error);
