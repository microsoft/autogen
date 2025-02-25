/**
 * @module core.grpc
 * Constants used throughout the gRPC implementation.
 */
export const Constants = {
    /**
     * The default port used for gRPC communication between agents.
     * This port should be available and not in use by other services.
     */
    DefaultGrpcPort: 50051,

    /**
     * Maximum message size in bytes for gRPC communication.
     * Default is 50MB to accommodate large message payloads.
     */
    MaxMessageSize: 1024 * 1024 * 50, // 50MB

    /**
     * Fully qualified service name for the agent runtime gRPC service.
     * Used when making gRPC calls to identify the service.
     */
    AgentRuntimeService: "agent.Runtime",

    /**
     * Fully qualified service name for the agent runtime gateway gRPC service.
     * Used when making gRPC calls to identify the gateway service.
     */
    AgentRuntimeGatewayService: "agent.RuntimeGateway"
} as const;
