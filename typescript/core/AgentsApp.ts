import { IAgentRuntime, AgentId } from "../contracts/IAgentRuntime";
import { IAgent } from "../contracts/IAgent";
import { TopicId } from "../contracts/IAgentRuntime";
import { InProcessRuntime } from "./InProcessRuntime";

export class AgentsAppBuilder {
  private agentTypeRegistrations: Array<(app: AgentsApp) => Promise<void>> = [];
  private runtime?: IAgentRuntime;

  useInProcessRuntime(deliverToSelf = false): AgentsAppBuilder {
    const runtime = new InProcessRuntime();
    runtime.deliverToSelf = deliverToSelf;
    this.runtime = runtime;
    return this;
  }

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

export class AgentsApp {
  private running = false;
  private shutdownCallbacks: Array<() => void> = [];
  
  constructor(public readonly runtime: IAgentRuntime) {}

  async start(): Promise<void> {
    if (this.running) {
      throw new Error("Application is already running.");
    }
    this.running = true;
    // Initialize runtime
  }

  async shutdown(): Promise<void> {
    if (!this.running) {
      throw new Error("Application is already stopped.");
    }
    this.running = false;
    // Cleanup runtime
  }

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

  async publishMessageAsync<T>(
    message: T,
    topic: TopicId,
    messageId?: string
  ): Promise<void> {
    if (!this.running) {
      await this.start();
    }
    await this.runtime.publishMessageAsync(message, topic, undefined, messageId);
  }

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
