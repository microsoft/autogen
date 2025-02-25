import { Message } from 'google-protobuf';

/**
 * Defines a registry for managing message type serializers.
 */
export interface ISerializationRegistry {
    /**
     * Gets a serializer that can handle the specified message type.
     * @param messageType The message type name to find a serializer for
     * @returns A serializer that can handle the message type, or undefined if none found
     */
    getSerializer(messageType: string): Message | undefined;

    /**
     * Gets a deserializer that can handle the specified protobuf message type.
     * @param messageType The protobuf message type to find a deserializer for
     * @returns A function that can deserialize the message type, or undefined if none found
     */
    getDeserializer(messageType: string): ((bytes: Uint8Array) => unknown) | undefined;

    /**
     * Gets whether the registry can handle a specific message type.
     * @param messageType The message type to check
     * @returns True if the registry can handle the message type
     */
    canHandle(messageType: string): boolean;
}
