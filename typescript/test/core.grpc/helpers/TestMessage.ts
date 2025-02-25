import { Message } from 'google-protobuf';

/**
 * A test message implementation for verifying serialization in gRPC tests.
 * This class provides a simple implementation of the protobuf Message interface
 * that can be used to test serialization and deserialization.
 * 
 * @example
 * ```typescript
 * const message = new TestMessage("test content");
 * const binary = message.serializeBinary();
 * ```
 */
export class TestMessage implements Message {
    constructor(public content: string) {}

    serializeBinary(): Uint8Array {
        return new TextEncoder().encode(this.content);
    }

    toObject(): { [k: string]: any } {
        return { content: this.content };
    }
}
