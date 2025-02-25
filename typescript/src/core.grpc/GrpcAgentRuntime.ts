/**
 * @module core.grpc
 */
import * as grpc from '@grpc/grpc-js';
import { IAgentRuntime, AgentId, TopicId } from '../contracts/IAgentRuntime';
import { IAgent } from '../contracts/IAgent';
import { MessageContext } from '../contracts/MessageContext';
import { IAgentMessageSerializer } from './IAgentMessageSerializer';
import { RuntimeGatewayClientOptions } from './RuntimeGatewayClientOptions';
import { Message } from 'google-protobuf';
import { UndeliverableException } from '../contracts/AgentExceptions';
import { GrpcAgentRuntimeClientOptions } from './GrpcAgentRuntimeClientOptions';

/**
 * An implementation of IAgentRuntime that uses gRPC to communicate with agents.
 * This runtime allows agents to communicate over a network using Protocol Buffers
 * for message serialization.
 * 
 * @example
 * ```typescript
 * const options = createDefaultOptions();
 * const registry = new ProtobufSerializationRegistry();
 * const serializer = new ProtobufMessageSerializer(registry);
 * const runtime = new GrpcAgentRuntime(options, serializer);
 * await runtime.start();
 * ```
 */
export class GrpcAgentRuntime implements IAgentRuntime {
    private readonly client: grpc.Client;
    private readonly serializer: IAgentMessageSerializer;
    private isRunning = false;

    constructor(
        options: GrpcAgentRuntimeClientOptions,
        serializer: IAgentMessageSerializer
    ) {
        const credentials = options.useTls 
            ? grpc.credentials.createSsl()
            : grpc.credentials.createInsecure();

        this.client = new grpc.Client(
            `${options.host}:${options.port}`,
            credentials
        );
        this.serializer = serializer;
    }

    async start(): Promise<void> {
        if (this.isRunning) {
            throw new Error("Runtime is already running");
        }
        this.isRunning = true;
    }

    async stop(): Promise<void> {
        if (!this.isRunning) {
            return;
        }
        this.isRunning = false;
        await new Promise<void>((resolve, reject) => {
            this.client.close(() => resolve());
        });
    }

    private async makeGrpcCall<T extends Message>(
        method: string, 
        request: T
    ): Promise<Message> {
        if (!this.isRunning) {
            throw new Error("Runtime not started");
        }

        try {
            return await new Promise((resolve, reject) => {
                this.client.makeUnaryRequest(
                    method,
                    (arg) => arg,
                    (arg) => arg,
                    request,
                    (error, response) => {
                        if (error) {
                            reject(new UndeliverableException(error.message));
                        } else {
                            resolve(response);
                        }
                    }
                );
            });
        } catch (error) {
            if (error instanceof UndeliverableException) {
                throw error;
            }
            throw new UndeliverableException(
                error instanceof Error ? error.message : String(error)
            );
        }
    }

    async publishMessageAsync(
        message: unknown,
        topic: TopicId,
        sender?: AgentId,
        messageId?: string
    ): Promise<void> {
        if (!this.isRunning) {
            throw new Error("Runtime not started");
        }

        const protoMessage = this.serializer.serialize(message);
        const request = {
            message: protoMessage,
            topic,
            sender,
            messageId: messageId ?? crypto.randomUUID()
        };

        await this.makeGrpcCall('/agent.Runtime/PublishMessage', request as Message);
    }

    async sendMessageAsync(
        message: unknown,
        recipient: AgentId,
        sender?: AgentId,
        messageId?: string
    ): Promise<unknown> {
        if (!this.isRunning) {
            throw new Error("Runtime not started");
        }

        const protoMessage = this.serializer.serialize(message);
        const request = {
            message: protoMessage,
            recipient,
            sender,
            messageId: messageId ?? crypto.randomUUID()
        };

        const response = await this.makeGrpcCall('/agent.Runtime/SendMessage', request as Message);
        return this.serializer.deserialize(response);
    }

    // Need to implement these required IAgentRuntime methods:
    async loadAgentStateAsync(agentId: AgentId, state: unknown): Promise<void> {
        const request = { 
            agentId: GrpcExtensions.toProto(agentId),
            state: this.serializer.serialize(state)
        };
        await this.makeGrpcCall('/agent.Runtime/LoadState', request as Message);
    }

    async saveAgentStateAsync(agentId: AgentId): Promise<unknown> {
        const request = { agentId: GrpcExtensions.toProto(agentId) };
        const response = await this.makeGrpcCall('/agent.Runtime/SaveState', request as Message);
        return this.serializer.deserialize(response);
    }

    async getAgentMetadataAsync(agentId: AgentId): Promise<unknown> {
        const request = { agentId: GrpcExtensions.toProto(agentId) };
        const response = await this.makeGrpcCall('/agent.Runtime/GetAgentMetadata', request as Message);
        return this.serializer.deserialize(response);
    }
}
