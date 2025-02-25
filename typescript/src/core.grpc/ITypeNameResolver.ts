/**
 * Resolves type names between .NET/TypeScript types and protobuf messages.
 */
export interface ITypeNameResolver {
    /**
     * Gets the protobuf type name for a given message type.
     * @param messageType The runtime type to get protobuf name for
     */
    getProtoTypeName(messageType: Function): string;

    /**
     * Gets the runtime type for a given protobuf type name.
     * @param protoTypeName The protobuf type name to resolve
     */
    getRuntimeType(protoTypeName: string): Function | undefined;
}
