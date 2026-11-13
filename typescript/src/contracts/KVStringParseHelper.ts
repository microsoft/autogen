/**
 * Provides helper methods for parsing key-value string representations.
 */
export class KVStringParseHelper {
  /**
   * The regular expression pattern used to match key-value pairs in the format "key/value".
   */
  private static readonly KV_PAIR_PATTERN = /^(?<key>\w+)\/(?<value>\w+)$/;

  /**
   * Parses a string in the format "key/value" into a tuple containing the key and value.
   * @param kvString The input string containing a key-value pair
   * @param keyName The expected name of the key component
   * @param valueName The expected name of the value component
   * @returns A tuple containing the extracted key and value
   * @throws Error if the input string does not match the expected "key/value" format
   * @example
   * ```typescript
   * const input = "agent1/12345";
   * const result = KVStringParseHelper.toKVPair(input, "Type", "Key");
   * console.log(result[0]); // Outputs: agent1
   * console.log(result[1]); // Outputs: 12345
   * ```
   */
  public static toKVPair(kvString: string, keyName: string, valueName: string): [string, string] {
    const match = this.KV_PAIR_PATTERN.exec(kvString);
    if (match?.groups) {
      return [match.groups['key'], match.groups['value']];
    }
    throw new Error(`Invalid key-value pair format: ${kvString}; expecting "${keyName}/${valueName}"`);
  }
}
