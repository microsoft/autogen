export class KVStringParseHelper {
  private static readonly KV_PAIR_PATTERN = /^(?<key>\w+)\/(?<value>\w+)$/;

  static toKVPair(kvString: string, keyName: string, valueName: string): [string, string] {
    const match = this.KV_PAIR_PATTERN.exec(kvString);
    if (match?.groups) {
      return [match.groups['key'], match.groups['value']];
    }
    throw new Error(`Invalid key-value pair format: ${kvString}; expecting "${keyName}/${valueName}"`);
  }
}
