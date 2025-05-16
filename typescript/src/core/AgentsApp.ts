import { IAgentRuntime, AgentId } from "../contracts/IAgentRuntime";
import { IAgent } from "../contracts/IAgent";
import { TopicId } from "../contracts/IAgentRuntime";
import { InProcessRuntime } from "./InProcessRuntime";

/**
 * A builder class for configuring and creating AgentsApp instances.
 */
export class AgentsAppBuilder {
  private agentTypeRegistrations: Array<(app: AgentsApp) => Promise<void>> = [];
  private runtime?: IAgentRuntime;

  /**
   * Configures the application to use the InProcessRuntime.
   * @param deliverToSelf Whether agents should receive their own messages
   * @returns The builder instance for method chaining
   */
  useInProcessRuntime(deliverToSelf = false): AgentsAppBuilder {
    const runtime = new InProcessRuntime();
    runtime.deliverToSelf = deliverToSelf;
    this.runtime = runtime;
    return this;
  }

  /**
   * Builds and initializes the application.
   * @returns A promise resolving to the configured AgentsApp instance
   */
  async build(): Promise<AgentsApp> {
    if (!this.runtime) {
      throw new Error("No runtime configured. Call useInProcessRuntime() first.");
    }
    
    const app = new AgentsApp(this.runtime);
    
    for (const registration of this.agentTypeRegistrations) {
      await registration(app);
    }
    
    return app;
  }
}

/**
 * The main application class that manages agent runtime and lifecycle.
 */
export class AgentsApp {
  private running = false;
  private shutdownCallbacks: Array<() => void> = [];
  
  /**
   * Creates a new instance of AgentsApp.
   * @param runtime The runtime instance to use
   */
  constructor(public readonly runtime: IAgentRuntime) {}

  /**
   * Starts the application and initializes the runtime.
   * @throws Error if the application is already running
   */
  async start(): Promise<void> {
    if (this.running) {
      throw new Error("Application is already running.");
    }
    await this.runtime.start(); // <== Added: start the underlying runtime
    this.running = true;
    // Initialize runtime
  }

  /**
   * Shuts down the application and stops the runtime.
   * @throws Error if the application is not running
   */
  async shutdown(): Promise<void> {
    if (!this.running) {
      throw new Error("Application is already stopped.");
    }
    this.running = false;
    // Cleanup runtime
  }

  /**
   * Publishes a message to all subscribed agents.
   * @param message The message to publish
   * @param topic The topic to publish to
   * @param messageId Optional message identifier
   */
  async publishMessage<T>(
    message: T,
    topic: TopicId,
    messageId?: string
  ): Promise<void> {
    if (!this.running) {
      await this.start();
    }
    await this.runtime.publishMessageAsync(message, topic, undefined, messageId);
  }

  /**
   * Waits for the application to be shut down.
   * @returns A promise that resolves when shutdown is complete
   */
  async waitForShutdown(): Promise<void> {
    // Wait until shutdown is called
    return new Promise((resolve) => {
      if (!this.running) {
        resolve();
      } else {
        const cleanup = () => {
          this.running = false;
          resolve();
        };
        this.shutdownCallbacks.push(cleanup);
      }
    });
  }
}
