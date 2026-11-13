import { ChatMessage, StopMessage } from "../../src/agentchat/abstractions/Messages";
import { ChatAgentBase } from "../../src/agentchat/agents/ChatAgentBase";
import { RoundRobinGroupChat } from "../../src/agentchat/groupchat/RoundRobinGroupChat";
import { StopMessageTermination } from "../../src/agentchat/terminations/StopMessageTermination";
import { Response } from "../../src/agentchat/abstractions/ChatAgent";
import { describe, expect, test } from '@jest/globals';

class SpeakMessageAgent extends ChatAgentBase {
    constructor() {
        super("speak", "A test agent that says hello");
    }

    get producedMessageTypes(): Array<Function> {
        return [ChatMessage];
    }

    async handleAsync(messages: ChatMessage[]): Promise<Response> {
        // Always respond with "Hello" regardless of input
        return {
            message: new ChatMessage("Hello", this.name.toString())
        };
    }

    async resetAsync(): Promise<void> {}
}

class TerminatingAgent extends ChatAgentBase {
    constructor() {
        super("terminate", "An agent that terminates the conversation");
    }

    get producedMessageTypes(): Array<Function> {
        return [StopMessage];
    }

    async handleAsync(messages: ChatMessage[]): Promise<Response> {
        const lastMessage = messages[messages.length - 1];
        const content = lastMessage instanceof ChatMessage 
            ? `Terminating; got: ${lastMessage.content}`
            : "Terminating";

        return {
            message: new StopMessage(content, this.name.toString())
        };
    }

    async resetAsync(): Promise<void> {}
}

describe("AgentChat Smoke Tests", () => {
    test("Basic Round Robin Chat", async () => {
        // Create chat directly with agents
        const chat = new RoundRobinGroupChat(
            new SpeakMessageAgent(),
            new TerminatingAgent(),
            new StopMessageTermination()
        );

        // Run chat and collect frames
        const frames: Array<any> = []; // Add type annotation here
        for await (const frame of chat.streamAsync("")) {
            frames.push(frame);
        }

        // Verify results
        expect(frames.length).toBe(1);
        const messages = frames[0].result?.messages;
        expect(messages?.length).toBe(3);
        expect((messages?.[0] as ChatMessage).content).toBe("");
        expect((messages?.[1] as ChatMessage).content).toBe("Hello");
        expect((messages?.[2] as StopMessage).content).toBe("Terminating; got: Hello");
    });
});
