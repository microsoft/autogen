import { IAgent } from "../../contracts/IAgent";
import { AgentId } from "../../contracts/IAgentRuntime";
import { IAgentRuntime } from "../../contracts/IAgentRuntime";
import { MessageContext } from "../../contracts/MessageContext";
import { BaseAgent } from "../../core/BaseAgent";

/**
 * Base class that adapts an agent for hosting in the runtime system.
 */
export abstract class HostableAgentAdapter extends BaseAgent {
    /**
     * Creates a new instance of the HostableAgentAdapter.
     * @param id The unique identifier for this agent
     * @param runtime The runtime instance this agent will use
     * @param description A brief description of the agent's purpose
     */
    constructor(id: AgentId, runtime: IAgentRuntime, description: string) {
        super(id, runtime, description);
    }

    /**
     * Gets metadata associated with the agent.
     */
    get metadata() {
        return {
            type: this.id.type,
            key: this.id.key,
            description: this.description
        };
    }
}
