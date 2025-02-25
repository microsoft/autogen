import { beforeEach, describe, expect, test } from '@jest/globals';
import { ProtobufMessageSerializer } from '../../src/core.grpc/ProtobufMessageSerializer';
import { ProtobufSerializationRegistry } from '../../src/core.grpc/ProtobufSerializationRegistry';
import { TestMessage } from './helpers/TestMessage';
import { MessageTestHelper } from './helpers/MessageTestHelper';

describe('ProtobufSerializationTests', () => {
    let registry: ProtobufSerializationRegistry;
    let serializer: ProtobufMessageSerializer;

    beforeEach(() => {
        registry = MessageTestHelper.createTestRegistry();
        serializer = new ProtobufMessageSerializer(registry);
    });

    test('Serialize_UnregisteredType_ThrowsError', () => {
        class UnregisteredMessage {
            constructor(public content: string) {}
        }

        expect(() => {
            serializer.serialize(new UnregisteredMessage('test'));
        }).toThrow('No serializer found');
    });

    test('Deserialize_UnregisteredType_ThrowsError', () => {
        const message = new TestMessage('test');
        Object.setPrototypeOf(message, { constructor: { name: 'UnregisteredType' } });

        expect(() => {
            serializer.deserialize(message);
        }).toThrow('No deserializer found');
    });

    test('RegisterType_ThenSerialize_Succeeds', () => {
        const message = new TestMessage('test content');
        const serialized = serializer.serialize(message);
        expect(serialized).toBeDefined();
        expect(serialized instanceof TestMessage).toBe(true);
    });
});
