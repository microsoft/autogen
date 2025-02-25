import { Message } from 'google-protobuf';
import { ISerializationRegistry } from './ISerializationRegistry';

/**
 * Registry for Protocol Buffer message serializers and deserializers.
 */
export class ProtobufSerializationRegistry implements ISerializationRegistry {
    private readonly serializers = new Map<string, Message>();
    private readonly deserializers = new Map<string, (bytes: Uint8Array) => unknown>();

    /**
     * Registers a new message type with its serializer and deserializer.
     * @param messageType The type name of the message
     * @param serializer The protobuf message serializer
     * @param deserializer Function to deserialize the message
     */
    registerType(
        messageType: string, 
        serializer: Message,
        deserializer: (bytes: Uint8Array) => unknown
    ): void {
        this.serializers.set(messageType, serializer);
        this.deserializers.set(messageType, deserializer);
    }

    getSerializer(messageType: string): Message | undefined {
        return this.serializers.get(messageType);
    }

    getDeserializer(messageType: string): ((bytes: Uint8Array) => unknown) | undefined {
        return this.deserializers.get(messageType);
    }

    canHandle(messageType: string): boolean {
        return this.serializers.has(messageType);
    }

    /**
     * Clears all registered type mappings.
     */
    clear(): void {
        this.serializers.clear();
        this.deserializers.clear();
    }

    /**
     * Registers multiple message types at once.
     * @param types Map of message type names to their serializers and deserializers
     */
    registerTypes(types: Map<string, [Message, (bytes: Uint8Array) => unknown]>): void {
        for (const [typeName, [serializer, deserializer]] of types) {
            this.registerType(typeName, serializer, deserializer);
        }
    }
}
