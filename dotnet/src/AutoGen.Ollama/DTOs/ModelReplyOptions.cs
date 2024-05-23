// Copyright (c) Microsoft Corporation. All rights reserved.
// ModelReplyOptions.cs

using System.Text.Json.Serialization;

namespace AutoGen.Ollama;

//https://github.com/ollama/ollama/blob/main/docs/modelfile.md#valid-parameters-and-values
public class ModelReplyOptions
{
    /// <summary>
    /// Enable Mirostat sampling for controlling perplexity. (default: 0, 0 = disabled, 1 = Mirostat, 2 = Mirostat 2.0)
    /// </summary>
    [JsonPropertyName("mirostat")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public int? MiroStat { get; set; }

    /// <summary>
    /// Influences how quickly the algorithm responds to feedback from the generated text.
    /// A lower learning rate will result in slower adjustments, while a higher learning rate will make the algorithm more responsive. (Default: 0.1)
    /// </summary>
    [JsonPropertyName("mirostat_eta")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public float? MiroStatEta { get; set; }

    /// <summary>
    /// Controls the balance between coherence and diversity of the output.
    /// A lower value will result in more focused and coherent text. (Default: 5.0)
    /// </summary>
    [JsonPropertyName("mirostat_tau")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public float? MiroStatTau { get; set; }

    /// <summary>
    /// Sets the size of the context window used to generate the next token. (Default: 2048)
    /// </summary>
    [JsonPropertyName("num_ctx")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public int? NumCtx { get; set; }

    /// <summary>
    /// The number of GQA groups in the transformer layer. Required for some models, for example it is 8 for llama2:70b
    /// </summary>
    [JsonPropertyName("num_gqa")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public int? NumGqa { get; set; }

    /// <summary>
    /// The number of layers to send to the GPU(s). On macOS it defaults to 1 to enable metal support, 0 to disable.
    /// </summary>
    [JsonPropertyName("num_gpu")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public int? NumGpu { get; set; }

    /// <summary>
    /// Sets the number of threads to use during computation. By default, Ollama will detect this for optimal performance.
    /// It is recommended to set this value to the number of physical CPU cores your system has (as opposed to the logical number of cores).
    /// </summary>
    [JsonPropertyName("num_thread")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public int? NumThread { get; set; }

    /// <summary>
    /// Sets how far back for the model to look back to prevent repetition. (Default: 64, 0 = disabled, -1 = num_ctx)
    /// </summary>
    [JsonPropertyName("repeat_last_n")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public int? RepeatLastN { get; set; }

    /// <summary>
    /// Sets how strongly to penalize repetitions.
    /// A higher value (e.g., 1.5) will penalize repetitions more strongly, while a lower value (e.g., 0.9) will be more lenient. (Default: 1.1)
    /// </summary>
    [JsonPropertyName("repeat_penalty")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public float? RepeatPenalty { get; set; }

    /// <summary>
    /// The temperature of the model. Increasing the temperature will make the model answer more creatively. (Default: 0.8)
    /// </summary>
    [JsonPropertyName("temperature")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public float? Temperature { get; set; }

    /// <summary>
    /// Sets the random number seed to use for generation.
    /// Setting this to a specific number will make the model generate the same text for the same prompt. (Default: 0)
    /// </summary>
    [JsonPropertyName("seed")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public int? Seed { get; set; }

    /// <summary>
    /// Sets the stop sequences to use. When this pattern is encountered the LLM will stop generating text and return.
    /// Multiple stop patterns may be set by specifying multiple separate stop parameters in a modelfile.
    /// </summary>
    [JsonPropertyName("stop")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Stop { get; set; }

    /// <summary>
    /// Tail free sampling is used to reduce the impact of less probable tokens from the output.
    /// A higher value (e.g., 2.0) will reduce the impact more, while a value of 1.0 disables this setting. (default: 1)
    /// </summary>
    [JsonPropertyName("tfs_z")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public float? TfsZ { get; set; }

    /// <summary>
    /// Maximum number of tokens to predict when generating text. (Default: 128, -1 = infinite generation, -2 = fill context)
    /// </summary>
    [JsonPropertyName("num_predict")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public int? NumPredict { get; set; }

    /// <summary>
    /// Reduces the probability of generating nonsense. A higher value (e.g. 100) will give more diverse answers, while a lower value (e.g. 10) will be more conservative. (Default: 40)
    /// </summary>
    [JsonPropertyName("top_k")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public int? TopK { get; set; }

    /// <summary>
    /// Works together with top-k. A higher value (e.g., 0.95) will lead to more diverse text, while a lower value (e.g., 0.5) will generate more focused and conservative text. (Default: 0.9)
    /// </summary>
    [JsonPropertyName("top_p")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public int? TopP { get; set; }
}
