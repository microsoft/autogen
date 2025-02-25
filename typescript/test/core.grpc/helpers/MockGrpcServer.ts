import * as grpc from '@grpc/grpc-js';
import { Message } from 'google-protobuf';

/**
 * A mock gRPC server for testing agent communication.
 * Provides a simple test server that can be configured with handlers for different
 * gRPC methods and simulated error conditions.
 * 
 * @example
 * ```typescript
 * const server = new MockGrpcServer();
 * server.addHandler('/test.Service/Method', async (msg) => {
 *   return new TestMessage('response');
 * });
 * await server.start();
 * ```
 */
export class MockGrpcServer {
    private server: grpc.Server;
    private messageHandlers = new Map<string, (message: Message) => Promise<Message>>();

    constructor(private port: number = 50051) {
        this.server = new grpc.Server();
    }

    /**
     * Registers a handler for a specific gRPC method
     */
    addHandler(method: string, handler: (message: Message) => Promise<Message>): void {
        this.messageHandlers.set(method, handler);
    }

    /**
     * Registers a handler that will throw an error for a specific gRPC method.
     * @param method The gRPC method path to handle
     * @param errorMessage The error message to throw
     */
    addErrorHandler(method: string, errorMessage: string): void {
        this.addHandler(method, async () => {
            throw new Error(errorMessage);
        });
    }

    /**
     * Forces the server to shut down, simulating a network error.
     */
    simulateNetworkError(): void {
        this.server.forceShutdown();
    }

    /**
     * Starts the mock server
     */
    async start(): Promise<void> {
        return new Promise((resolve, reject) => {
            this.server.bindAsync(
                `0.0.0.0:${this.port}`,
                grpc.ServerCredentials.createInsecure(),
                (error, port) => {
                    if (error) {
                        reject(error);
                        return;
                    }
                    this.server.start();
                    resolve();
                }
            );
        });
    }

    /**
     * Stops the mock server
     */
    async stop(): Promise<void> {
        return new Promise((resolve) => {
            this.server.tryShutdown(() => resolve());
        });
    }
}
