import { AgentsAppBuilder } from '../core/AgentsApp';
import { GrpcAgentRuntime } from './GrpcAgentRuntime';
import { GrpcAgentRuntimeClientOptions, createDefaultOptions } from './GrpcAgentRuntimeClientOptions';
import { ProtobufMessageSerializer } from './ProtobufMessageSerializer';
import { ProtobufSerializationRegistry } from './ProtobufSerializationRegistry';
import { ProtobufTypeNameResolver } from './ProtobufTypeNameResolver';

/**
 * Extends AgentsAppBuilder with gRPC-specific functionality.
 */
export class GrpcAgentsAppBuilderExtensions {
    /**
     * Configures the application to use gRPC runtime.
     */
    static useGrpcRuntime(
        builder: AgentsAppBuilder,
        options?: Partial<GrpcAgentRuntimeClientOptions>
    ): AgentsAppBuilder {
        const runtimeOptions = {
            ...createDefaultOptions(),
            ...options
        };

        const registry = new ProtobufSerializationRegistry();
        const typeResolver = new ProtobufTypeNameResolver();
        const serializer = new ProtobufMessageSerializer(registry);

        const runtime = new GrpcAgentRuntime(runtimeOptions, serializer);

        // Add runtime to services
        builder['runtime'] = runtime;

        return builder;
    }
}

// Add extension method to AgentsAppBuilder
declare module '../core/AgentsApp' {
    interface AgentsAppBuilder {
        /**
         * Configures the application to use gRPC runtime.
         * @param options Optional configuration for the gRPC runtime
         */
        useGrpcRuntime(options?: Partial<GrpcAgentRuntimeClientOptions>): AgentsAppBuilder;
    }
}

// Implement the extension method
AgentsAppBuilder.prototype.useGrpcRuntime = function(
    options?: Partial<GrpcAgentRuntimeClientOptions>
): AgentsAppBuilder {
    return GrpcAgentsAppBuilderExtensions.useGrpcRuntime(this, options);
};
