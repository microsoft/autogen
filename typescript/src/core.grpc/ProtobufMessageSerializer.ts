/**
 * @module core.grpc
 */
import { Message } from 'google-protobuf';
import { IAgentMessageSerializer } from './IAgentMessageSerializer';
import { ISerializationRegistry } from './ISerializationRegistry';

/**
 * Implements message serialization using Protocol Buffers.
 * This class provides the main interface for converting between native TypeScript objects
 * and Protocol Buffer messages using a registry of serializers.
 * 
 * @example
 * ```typescript
 * const registry = new ProtobufSerializationRegistry();
 * const serializer = new ProtobufMessageSerializer(registry);
 * 
 * // Serialize a message
 * const protoMsg = serializer.serialize(message);
 * ```
 */
export class ProtobufMessageSerializer implements IAgentMessageSerializer {
    constructor(private readonly registry: ISerializationRegistry) {}

    serialize(message: unknown): Message {
        const messageType = this.getProtoMessageType(message);
        const serializer = this.registry.getSerializer(messageType);
        if (!serializer) {
            throw new Error(`No serializer found for message type: ${messageType}`);
        }
        return serializer;
    }

    deserialize(protoMessage: Message): unknown {
        const messageType = protoMessage.constructor.name;
        const deserializer = this.registry.getDeserializer(messageType);
        if (!deserializer) {
            throw new Error(`No deserializer found for message type: ${messageType}`);
        }
        return deserializer(protoMessage.serializeBinary());
    }

    getProtoMessageType(message: unknown): string {
        if (!message) {
            throw new Error('Message cannot be null or undefined');
        }
        return message.constructor.name;
    }

    canHandle(messageType: string): boolean {
        return this.registry.canHandle(messageType);
    }
}
