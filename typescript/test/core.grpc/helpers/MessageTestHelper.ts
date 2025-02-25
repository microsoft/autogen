import { Message } from 'google-protobuf';
import { ProtobufSerializationRegistry } from '../../../src/core.grpc/ProtobufSerializationRegistry';
import { TestMessage } from './TestMessage';
import { GrpcAgentRuntimeClientOptions } from '../../../src/core.grpc/GrpcAgentRuntimeClientOptions';

/**
 * Helper class for setting up and verifying test messages in gRPC tests.
 * Provides utilities for creating test registries and verifying message content.
 * 
 * @example
 * ```typescript
 * const registry = MessageTestHelper.createTestRegistry();
 * const message = new TestMessage("test");
 * const isValid = MessageTestHelper.verifyMessage(message, "test");
 * ```
 */
export class MessageTestHelper {
    /**
     * Creates a new serialization registry configured with test message types.
     * @returns A registry pre-configured with test message serializers
     */
    static createTestRegistry(): ProtobufSerializationRegistry {
        const registry = new ProtobufSerializationRegistry();
        
        // Register test message type
        registry.registerType(
            'TestMessage',
            new TestMessage(''),
            (bytes: Uint8Array) => new TestMessage(new TextDecoder().decode(bytes))
        );

        return registry;
    }

    /**
     * Verifies that a message matches expected content.
     * @param message The message to verify
     * @param expectedContent The expected content of the message
     * @returns true if the message matches the expected content
     */
    static verifyMessage(message: Message, expectedContent: string): boolean {
        if (!(message instanceof TestMessage)) {
            return false;
        }
        return message.content === expectedContent;
    }
}
