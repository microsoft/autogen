import { ChatMessage, StopMessage, AgentMessage } from "../../src/agentchat/abstractions/Messages";
import { ChatAgentBase } from "../../src/agentchat/agents/ChatAgentBase";
import { RoundRobinGroupChat } from "../../src/agentchat/groupchat/RoundRobinGroupChat";
import { StopMessageTermination } from "../../src/agentchat/terminations/StopMessageTermination";
import { Response } from "../../src/agentchat/abstractions/ChatAgent";
import { HandoffMessage } from "../../src/agentchat/abstractions/Handoff";
import { TaskFrame } from "../../src/agentchat/abstractions/Tasks";
import { GroupParticipant } from "../../src/agentchat/groupchat/GroupChatOptions";

// Update Jest imports
import { describe, expect, test, beforeEach, afterEach } from '@jest/globals';
import { InProcessRuntime } from "../../src/core/InProcessRuntime";
import { ChatAgentRouter } from "../../src/agentchat/groupchat/ChatAgentRouter";
import { TypeSubscription } from "../../src/core/TypeSubscription";

/**
 * An agent that speaks a predefined message.
 */
class SpeakMessageAgent extends ChatAgentBase {
    private readonly content: string;
    
    constructor(name: string, description: string, content: string) {
        super(name, description);
        this.content = content;
    }

    get producedMessageTypes(): Array<Function> {
        return [ChatMessage];  // Change: Produce ChatMessage instead of HandoffMessage
    }

    async handleAsync(messages: ChatMessage[]): Promise<Response> {
        return {
            message: new ChatMessage(this.content, this.name.toString())
        };
    }

    async resetAsync(): Promise<void> {}
}

/**
 * An agent that terminates the conversation.
 */
class TerminatingAgent extends ChatAgentBase {
    public incomingMessages?: ChatMessage[];

    constructor(name: string, description: string) {
        super(name, description);
    }

    get producedMessageTypes(): Array<Function> {
        return [StopMessage];
    }

    async handleAsync(messages: AgentMessage[]): Promise<Response> { // changed from ChatMessage[] to AgentMessage[]
        // Store only ChatMessages for incomingMessages property if needed
        this.incomingMessages = messages.filter(m => m instanceof ChatMessage) as ChatMessage[];

        let content = "Terminating";
        if (messages.length > 0) {
            const lastMessage = messages[messages.length - 1];
            if (isChatMessage(lastMessage)) {
                content = `Terminating; got: ${lastMessage.content}`;
            } else if (isHandoffMessage(lastMessage)) {
                content = `Terminating; got handoff: ${lastMessage.targetAgent}`;
            }
        }

        return {
            message: new StopMessage(content, this.name.toString())
        };
    }

    async resetAsync(): Promise<void> {
        this.incomingMessages = undefined;
    }
}

function isChatMessage(msg: any): msg is ChatMessage {
    return msg instanceof ChatMessage;
}

function isHandoffMessage(msg: any): msg is HandoffMessage {
    return msg instanceof HandoffMessage;
}

describe("AgentChat Smoke Tests", () => {
    let runtime: InProcessRuntime;

    beforeEach(async () => {
        runtime = new InProcessRuntime();
        runtime.deliverToSelf = false;
        await runtime.start();
    });

    afterEach(async () => {
        if (runtime) {
            await runtime.stop();
        }
    });

    test("RoundRobin with SpeakAndTerminating agents", async () => {
        // Create agents with valid names
        const speakAgent = new SpeakMessageAgent("speak", "Speaker", "Hello");
        const terminatingAgent = new TerminatingAgent("terminate", "Terminate");

        // Create chat agent routers
        const speakRouter = new ChatAgentRouter(
            { type: "speak", key: "default" },
            runtime,
            {
                parentTopicType: "test",
                outputTopicType: "speak",
                chatAgent: speakAgent
            }
        );

        const terminateRouter = new ChatAgentRouter(
            { type: "terminate", key: "default" },
            runtime,
            {
                parentTopicType: "test",
                outputTopicType: "terminate",
                chatAgent: terminatingAgent
            }
        );

        // Register agents and subscriptions
        await runtime.registerAgentFactoryAsync("speak", async () => speakRouter);
        await runtime.registerAgentFactoryAsync("terminate", async () => terminateRouter);

        // Add subscriptions to connect topics to agents
        await runtime.addSubscriptionAsync(new TypeSubscription("speak", "speak"));
        await runtime.addSubscriptionAsync(new TypeSubscription("terminate", "terminate")); 
        await runtime.addSubscriptionAsync(new TypeSubscription("test", "speak"));
        await runtime.addSubscriptionAsync(new TypeSubscription("test", "terminate"));

        // Create chat with configuration
        const chat = RoundRobinGroupChat.create(
            "test",
            "output", 
            new StopMessageTermination()
        );

        // Add participants
        chat.addParticipant("speak", new GroupParticipant("speak", "Speaker"));
        chat.addParticipant("terminate", new GroupParticipant("terminate", "Terminate"));

        // Set up message routing
        chat.attachMessagePublishServicer(async (event, topicType) => {
            await runtime.publishMessageAsync(
                event,
                { type: topicType, source: "test" }
            );
            // Give time for message processing
            await new Promise(resolve => setTimeout(resolve, 50));
        });

        // Run the chat
        const frames: TaskFrame[] = [];
        for await (const frame of chat.streamAsync("")) {
            frames.push(frame);
        }

        // Verify results
        expect(frames.length).toBe(1);
        const messages = frames[0].result!.messages;
        expect(messages.length).toBe(3);
        expect((messages[0] as ChatMessage).content).toBe("");
        expect((messages[1] as ChatMessage).content).toBe("Hello");
        expect((messages[2] as StopMessage).content).toBe("Terminating; got: Hello");
    }, 10000);
});
