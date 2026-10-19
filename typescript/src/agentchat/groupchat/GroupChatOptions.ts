import { ITerminationCondition } from "../abstractions/Termination";

/**
 * Represents information about a participant in a group chat.
 */
export class GroupParticipant {
  /**
   * Creates a new group participant.
   * @param topicType The topic type for this participant
   * @param description Description of the participant's capabilities
   */
  constructor(
    public readonly topicType: string,
    public readonly description: string
  ) {}
}

/**
 * Configuration options for a group chat.
 */
export class GroupChatOptions {
  /**
   * Gets the topic type for group chat messages.
   */
  public readonly groupChatTopicType: string;

  /**
   * Gets the topic type for output messages.
   */
  public readonly outputTopicType: string;

  /**
   * Gets or sets the termination condition for the chat.
   */
  public terminationCondition?: ITerminationCondition;

  /**
   * Gets or sets the maximum number of chat turns.
   */
  public maxTurns?: number;

  /**
   * Gets the participants in the chat.
   */
  public readonly participants: Map<string, GroupParticipant> = new Map();

  /**
   * Creates a new instance of GroupChatOptions.
   * @param groupChatTopicType Topic type for group chat messages
   * @param outputTopicType Topic type for output messages
   */
  constructor(groupChatTopicType: string, outputTopicType: string) {
    this.groupChatTopicType = groupChatTopicType;
    this.outputTopicType = outputTopicType;
  }
}
