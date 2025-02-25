import { beforeEach, afterEach, describe, expect, test } from '@jest/globals';
import { InProcessRuntime } from '../../src/core/InProcessRuntime';
import { GrpcAgentRuntime } from '../../src/core.grpc/GrpcAgentRuntime';
import { ProtobufMessageSerializer } from '../../src/core.grpc/ProtobufMessageSerializer';
import { ProtobufSerializationRegistry } from '../../src/core.grpc/ProtobufSerializationRegistry';
import { ChatMessage } from '../../src/agentchat/abstractions/Messages';
import { AgentId } from '../../src/contracts/IAgentRuntime';
import { createDefaultOptions } from '../../src/core.grpc/RuntimeGatewayClientOptions';
import { MockGrpcServer } from './helpers/MockGrpcServer';
import { TestMessage } from './helpers/TestMessage';

describe('AgentGrpcTests', () => {
    let runtime: GrpcAgentRuntime;
    let serializer: ProtobufMessageSerializer;
    let mockServer: MockGrpcServer;

    beforeEach(async () => {
        const registry = new ProtobufSerializationRegistry();
        serializer = new ProtobufMessageSerializer(registry);
        runtime = new GrpcAgentRuntime(createDefaultOptions(), serializer);

        // Set up mock server
        mockServer = new MockGrpcServer();
        mockServer.addHandler('/agent.Runtime/SendMessage', async (message) => {
            return new TestMessage('mock response');
        });
        await mockServer.start();
    });

    afterEach(async () => {
        await mockServer.stop();
    });

    test('SendMessageAsync_BasicMessage_Works', async () => {
        // Arrange
        const message = new ChatMessage('test message');
        const recipient: AgentId = { type: 'test', key: 'agent1' };

        // Act
        await runtime.start();
        try {
            const response = await runtime.sendMessageAsync(message, recipient);

            // Assert
            expect(response).toBeDefined();
            // Add more specific assertions based on expected response
        } finally {
            await runtime.stop();
        }
    });

    test('PublishMessageAsync_BasicMessage_Works', async () => {
        // Arrange
        const message = new ChatMessage('test message');
        const topic = { type: 'test_topic', source: 'test_source' };

        // Act
        await runtime.start();
        try {
            await runtime.publishMessageAsync(message, topic);
            // Assert success (no error thrown)
            expect(true).toBe(true);
        } finally {
            await runtime.stop();
        }
    });

    test('RuntimeNotStarted_ThrowsError', async () => {
        // Arrange
        const message = new ChatMessage('test message');
        const recipient: AgentId = { type: 'test', key: 'agent1' };

        // Act & Assert
        await expect(async () => {
            await runtime.sendMessageAsync(message, recipient);
        }).rejects.toThrow('Runtime not started');
    });

    test('SendMessage_WithMockServer_ReturnsResponse', async () => {
        // Arrange
        const message = new ChatMessage('test message');
        const recipient: AgentId = { type: 'test', key: 'agent1' };

        // Act
        await runtime.start();
        try {
            const response = await runtime.sendMessageAsync(message, recipient);

            // Assert
            expect(response).toBeDefined();
            expect((response as TestMessage).content).toBe('mock response');
        } finally {
            await runtime.stop();
        }
    });

    test('SendMessage_WithError_ThrowsUndeliverableException', async () => {
        // Arrange
        mockServer.addHandler('/agent.Runtime/SendMessage', async () => {
            throw new Error('Simulated error');
        });

        const message = new ChatMessage('test message');
        const recipient: AgentId = { type: 'test', key: 'agent1' };

        // Act & Assert
        await runtime.start();
        try {
            await expect(async () => {
                await runtime.sendMessageAsync(message, recipient);
            }).rejects.toThrow('Simulated error');
        } finally {
            await runtime.stop();
        }
    });

    test('PublishMessage_WithStateTransfer_Works', async () => {
        // Arrange
        const state = { key: 'value' };
        mockServer.addHandler('/agent.Runtime/SaveState', async () => {
            return new TestMessage(JSON.stringify(state));
        });

        // Act
        await runtime.start();
        try {
            const result = await runtime.saveAgentStateAsync({ type: 'test', key: 'agent1' });
            
            // Assert
            expect(result).toBeDefined();
            expect(JSON.parse((result as TestMessage).content)).toEqual(state);
        } finally {
            await runtime.stop();
        }
    });

    test('GetAgentMetadata_ReturnsExpectedData', async () => {
        // Arrange
        const metadata = { type: 'test', key: 'agent1', description: 'Test Agent' };
        mockServer.addHandler('/agent.Runtime/GetAgentMetadata', async () => {
            return new TestMessage(JSON.stringify(metadata));
        });

        // Act
        await runtime.start();
        try {
            const result = await runtime.getAgentMetadataAsync({ type: 'test', key: 'agent1' });
            
            // Assert
            expect(result).toBeDefined();
            expect(JSON.parse((result as TestMessage).content)).toEqual(metadata);
        } finally {
            await runtime.stop();
        }
    });
});
