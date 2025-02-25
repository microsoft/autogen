/**
 * Configuration options for the GrpcAgentRuntime client.
 */
export interface GrpcAgentRuntimeClientOptions {
    /**
     * The host address of the gRPC server.
     */
    host: string;

    /**
     * The port number of the gRPC server.
     */
    port: number;

    /**
     * Whether to use TLS/SSL for the connection.
     * Defaults to false.
     */
    useTls?: boolean;
}

/**
 * Creates a new GrpcAgentRuntimeClientOptions with default values.
 * @returns Default configuration for the GrpcAgentRuntime client
 */
export function createDefaultOptions(): GrpcAgentRuntimeClientOptions {
    return {
        host: 'localhost',
        port: 50051,
        useTls: false
    };
}
