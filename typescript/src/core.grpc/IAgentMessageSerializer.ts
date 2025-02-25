import { Message } from 'google-protobuf';

/**
 * Interface for serializing messages between agent runtime and protobuf format.
 */
export interface IAgentMessageSerializer {
    /**
     * Serializes a message to protobuf format.
     * @param message The message to serialize
     * @returns The protobuf message
     */
    serialize(message: unknown): Message;

    /**
     * Deserializes a protobuf message.
     * @param protoMessage The protobuf message to deserialize
     * @returns The deserialized message
     */
    deserialize(protoMessage: Message): unknown;

    /**
     * Gets the protobuf message type for a given message.
     * @param message The message to get type for
     * @returns The protobuf message type name
     */
    getProtoMessageType(message: unknown): string;

    /**
     * Gets whether this serializer can handle a given message type.
     * @param messageType The message type name to check
     * @returns True if this serializer can handle the message type
     */
    canHandle(messageType: string): boolean;
}
