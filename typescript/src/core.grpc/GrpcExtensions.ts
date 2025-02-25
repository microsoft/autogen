/**
 * @module core.grpc
 */
import { Message } from 'google-protobuf';
import { AgentId, TopicId } from '../contracts/IAgentRuntime';

/**
 * Provides extension methods for converting between domain types and their protobuf representations.
 * This class handles the low-level conversion between TypeScript interfaces and protobuf messages.
 * 
 * @example
 * ```typescript
 * const agentId = { type: "agent1", key: "instance1" };
 * const protoMessage = GrpcExtensions.toProto(agentId);
 * ```
 */
export class GrpcExtensions {
    /**
     * Converts an AgentId to its protobuf representation.
     */
    static toProto(agentId: AgentId): Message {
        return {
            type: agentId.type,
            key: agentId.key
        } as Message;
    }

    /**
     * Converts a TopicId to its protobuf representation.
     */
    static topicToProto(topicId: TopicId): Message {
        return {
            type: topicId.type,
            source: topicId.source
        } as Message;
    }

    /**
     * Converts a protobuf AgentId message to an AgentId.
     */
    static fromProto(proto: any): AgentId {
        return {
            type: proto.type,
            key: proto.key
        };
    }

    /**
     * Converts a protobuf TopicId message to a TopicId.
     */
    static topicFromProto(proto: any): TopicId {
        return {
            type: proto.type,
            source: proto.source
        };
    }
}
