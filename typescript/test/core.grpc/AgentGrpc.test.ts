import { beforeEach, afterEach, describe, expect, test } from '@jest/globals';
import { GrpcAgentRuntime } from '../../src/core.grpc/GrpcAgentRuntime';
import { createDefaultOptions } from '../../src/core.grpc/GrpcAgentRuntimeClientOptions';
import { ProtobufMessageSerializer } from '../../src/core.grpc/ProtobufMessageSerializer';
import { ProtobufSerializationRegistry } from '../../src/core.grpc/ProtobufSerializationRegistry';
import { MessageTestHelper } from './helpers/MessageTestHelper';
import { TestMessage } from './helpers/TestMessage';
import { MockGrpcServer } from './helpers/MockGrpcServer';
import { UndeliverableException } from '../../src/contracts/AgentExceptions';

describe('AgentGrpcTests', () => {
    let runtime: GrpcAgentRuntime;
    let registry: ProtobufSerializationRegistry;
    let mockServer: MockGrpcServer;

    beforeEach(async () => {
        registry = MessageTestHelper.createTestRegistry();
        const serializer = new ProtobufMessageSerializer(registry);
        runtime = new GrpcAgentRuntime(createDefaultOptions(), serializer);
        mockServer = new MockGrpcServer();
        await mockServer.start();
    });

    afterEach(async () => {
        await runtime.stop();
        await mockServer.stop();
    });

    test('SendUndeliverableMessage_ThrowsError', async () => {
        await runtime.start();
        mockServer.addErrorHandler('/agent.Runtime/SendMessage', 'Undeliverable message');

        await expect(runtime.sendMessageAsync(
            new TestMessage('test'),
            { type: 'test', key: 'agent1' }
        )).rejects.toThrow(UndeliverableException);
    });

    test('PublishUndeliverableMessage_ThrowsError', async () => {
        await runtime.start();
        mockServer.addErrorHandler('/agent.Runtime/PublishMessage', 'Undeliverable message');

        await expect(runtime.publishMessageAsync(
            new TestMessage('test'),
            { type: 'test', source: 'test' }
        )).rejects.toThrow(UndeliverableException);
    });
});
