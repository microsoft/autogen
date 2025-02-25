import { ITypeNameResolver } from "./ITypeNameResolver";

/**
 * Default implementation of type name resolution between TypeScript and protobuf.
 */
export class ProtobufTypeNameResolver implements ITypeNameResolver {
    private readonly typeMap = new Map<string, Function>();
    private readonly reverseMap = new Map<Function, string>();

    /**
     * Register a type mapping between protobuf and runtime types.
     * @param protoTypeName Full protobuf type name (e.g., "package.TypeName")
     * @param runtimeType The TypeScript constructor function
     */
    registerType(protoTypeName: string, runtimeType: Function): void {
        if (!protoTypeName || !runtimeType) {
            throw new Error("Proto type name and runtime type must be provided");
        }
        this.typeMap.set(protoTypeName, runtimeType);
        this.reverseMap.set(runtimeType, protoTypeName);
    }

    getProtoTypeName(messageType: Function): string {
        const name = this.reverseMap.get(messageType);
        if (!name) {
            throw new Error(`No protobuf type name registered for type: ${messageType.name}`);
        }
        return name;
    }

    getRuntimeType(protoTypeName: string): Function | undefined {
        return this.typeMap.get(protoTypeName);
    }

    // Add helper method like C# implementation
    clear(): void {
        this.typeMap.clear();
        this.reverseMap.clear();
    }
}
