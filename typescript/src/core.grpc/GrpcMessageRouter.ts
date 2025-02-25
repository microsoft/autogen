/**
 * @module core.grpc
 */
import { Message } from 'google-protobuf';
import { IAgentMessageSerializer } from './IAgentMessageSerializer';
import { ITypeNameResolver } from './ITypeNameResolver';
import { MessageContext } from '../contracts/MessageContext';

/**
 * Routes messages between TypeScript and protobuf formats.
 * This class handles conversion between native TypeScript objects and Protocol Buffer messages.
 * 
 * @example
 * ```typescript
 * const serializer = new ProtobufMessageSerializer(registry);
 * const typeResolver = new ProtobufTypeNameResolver();
 * const router = new GrpcMessageRouter(serializer, typeResolver);
 * 
 * // Convert to protobuf
 * const [protoMsg, type] = router.toProto(message, context);
 * ```
 */
export class GrpcMessageRouter {
    private readonly serializer: IAgentMessageSerializer;
    private readonly typeResolver: ITypeNameResolver;

    constructor(serializer: IAgentMessageSerializer, typeResolver: ITypeNameResolver) {
        this.serializer = serializer;
        this.typeResolver = typeResolver;
    }

    /**
     * Routes a message from TypeScript format to protobuf format.
     * @param message The message to route
     * @param context The message context
     * @returns A tuple containing the protobuf message and its type
     */
    toProto(message: unknown, context: MessageContext): [Message, string] {
        if (!message) {
            throw new Error('Message cannot be null or undefined');
        }

        try {
            const protoMessage = this.serializer.serialize(message);
            const protoType = this.typeResolver.getProtoTypeName(message.constructor as Function);
            return [protoMessage, protoType];
        } catch (error) {
            throw new Error(`Failed to convert message to proto: ${error instanceof Error ? error.message : String(error)}`);
        }
    }

    /**
     * Routes a message from protobuf format to TypeScript format.
     * @param message The protobuf message to route
     * @param protoType The protobuf message type
     * @returns The deserialized TypeScript message
     */
    fromProto(message: Message, protoType: string): unknown {
        const runtimeType = this.typeResolver.getRuntimeType(protoType);
        if (!runtimeType) {
            throw new Error(`No runtime type found for proto type: ${protoType}`);
        }

        return this.serializer.deserialize(message);
    }
}
