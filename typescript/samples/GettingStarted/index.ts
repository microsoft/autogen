import "reflect-metadata";
import { AgentsApp, AgentsAppBuilder } from "../../src/core/AgentsApp";
import { Checker } from "./Checker";
import { Modifier } from "./Modifier";
import { CountMessage } from "./CountMessage";
import { TypeSubscription } from "../../src/core/TypeSubscription";
import { AgentId, IAgentRuntime } from "../../src/contracts/IAgentRuntime";

async function main() {
  // Define the modification and termination functions
  const modifyFunc = (x: number) => x - 1;
  const runUntilFunc = (x: number) => x <= 1;

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
      new Checker(id, runtime, runUntilFunc, shutdown));
  
  await app.runtime.registerAgentFactoryAsync("Modifier", 
    async (id: AgentId, runtime: IAgentRuntime) => 
      new Modifier(id, runtime, modifyFunc));

  // Add subscriptions
  await app.runtime.addSubscriptionAsync(
    new TypeSubscription("default")
  );
  // Start the app
  await app.start();

  // Send initial message
  await app.publishMessageAsync<CountMessage>(
    { content: 10 },
    { type: "default", source: "main" }
  );

  // Wait for shutdown
  await app.waitForShutdown();
}

// Run the program
main().catch(console.error);
