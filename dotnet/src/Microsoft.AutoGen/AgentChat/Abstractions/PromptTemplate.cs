// Copyright (c) Microsoft Corporation. All rights reserved.
// PromptTemplate.cs

using System.Text;

namespace Microsoft.AutoGen.AgentChat.Abstractions;

/// <summary>
/// A class that represents a message template with named parameters. Similar to an interpolated string, or
/// Python's f-string.
/// </summary>
/// <example>
/// <code>
/// var template = new PromptTemplate("Hello {name}, welcome to {place}!");
/// template.CheckParameters("name", "place"); // returns true
///
/// string name = "Alice";
/// string place = "Wonderland";
/// var parameters = 
/// 
/// string formattedMessage = template.Format(("name", name), ("place", place)).ToString();
/// </code>
/// </example>
public class PromptTemplate
{
    private struct Part
    {
        public bool IsParameter { get; set; }
        public Range Extent { get; set; }

        public ReadOnlySpan<char> Select(ReadOnlySpan<char> templateSpan) => templateSpan[Extent];

        public string Format(ReadOnlySpan<char> templateSpan) => Select(templateSpan).ToString();

        public void Format(StringBuilder target, ReadOnlySpan<char> templateSpan, IDictionary<string, string> parameterValues)
        {
            ReadOnlySpan<char> partSpan = this.Select(templateSpan);
            if (IsParameter)
            {
                string key = partSpan.ToString();
                target.Append(parameterValues[key]);
            }
            else
            {
                target.Append(partSpan);
            }
        }
    }

    private sealed class PartAcumulator
    {
        public List<Part> Parts { get; } = new List<Part>();
        public int ParameterCount { get; private set; }

        private bool? collectingState;
        private int partStart;

        private const bool CollectingFixed = true;
        private const bool CollectingParameter = false;

        public bool IsCollectingParameter => collectingState == CollectingParameter;
        public bool IsCollectingFixed => collectingState == CollectingFixed;

        public void Emit(int finish)
        {
            bool isParameter = collectingState == CollectingParameter;
            if (isParameter)
            {
                ParameterCount++;
            }

            this.Parts.Add(
                new() { IsParameter = isParameter, Extent = new Range(partStart, finish) }
            );

            collectingState = null;
            partStart = finish + 1;
        }

        public void Finish(int finish)
        {
            if (collectingState != null)
            {
                this.Emit(finish);
            }
        }

        public void BeginFixed(int start)
        {
            if (collectingState == CollectingFixed)
            {
                throw new Exception($"Unexpectedly starting Fixed when already collecting Fixed (lastStart: {this.partStart}, newStart: {start})");
            }

            if (collectingState == CollectingParameter)
            {
                throw new Exception($"Unexpectedly starting Fixed when already collecting Parameter (lastStart: {this.partStart}, newStart: {start})");
            }

            this.partStart = start;
            this.collectingState = CollectingFixed;
        }

        public void BeginParameter(int start)
        {
            if (collectingState == CollectingFixed)
            {
                throw new Exception($"Unexpectedly starting Parameter when already collecting Fixed (lastStart: {this.partStart}, newStart: {start})");
            }
            if (collectingState == CollectingParameter)
            {
                throw new Exception($"Unexpectedly starting Parameter when already collecting Parameter (lastStart: {this.partStart}, newStart: {start})");
            }

            this.partStart = start;
            this.collectingState = CollectingParameter;
        }
    }

    private enum EscapeState
    {
        None = 0,
        CandidateLeft = 1, // {|{
        DemandRightEscape = 3
    }

    private string template;
    private List<Part> parts;
    private HashSet<string> parameterKeys;

    public PromptTemplate(string template)
    {
        this.template = template;

        const char parameterStart = '{';
        const char parameterEnd = '}';

        int readHead = -1;
        EscapeState state = EscapeState.None;
        PartAcumulator acumulator = new PartAcumulator();

        while (++readHead < template.Length)
        {
            switch (template[readHead])
            {
                case parameterStart:
                    if (acumulator.IsCollectingParameter)
                    {
                        throw new FormatException($"Unexpected '{parameterStart}' at {readHead}; parameter keys cannot contain \'{{\'.");
                    }

                    switch (state)
                    {
                        case EscapeState.None:
                            state = EscapeState.CandidateLeft;
                            break;
                        //case EscapeState.CandidateRight:
                        //    acumulator.Emit(readHead - 2);
                        //    state = EscapeState.CandidateLeft;
                        //    break;
                        case EscapeState.CandidateLeft:
                            // this was an escape sequence, and we're not collecting a paramter
                            state = EscapeState.None;
                            break;
                        case EscapeState.DemandRightEscape:
                            throw new FormatException($"Unexpected '{parameterStart}' at {readHead}; expected to find double '{parameterEnd}' escape sequence.");
                    }

                    break;
                case parameterEnd:
                    switch (state)
                    {
                        case EscapeState.None:
                            if (acumulator.IsCollectingParameter)
                            {
                                acumulator.Emit(readHead - 1);
                                state = EscapeState.None;
                            }
                            else
                            {
                                // we had better expect an escape sequence
                                state = EscapeState.DemandRightEscape;
                            }
                            break;
                        case EscapeState.DemandRightEscape:
                            // this was an escape sequence
                            state = EscapeState.None;
                            break;
                        case EscapeState.CandidateLeft:
                            throw new FormatException($"Invalid parameter at {readHead - 1}; parameter keys must be at least one character long.");
                    }
                    break;
                default:
                    if (!acumulator.IsCollectingFixed && !acumulator.IsCollectingParameter)
                    {
                        acumulator.BeginFixed(readHead);
                    }

                    switch (state)
                    {
                        case EscapeState.CandidateLeft:
                            // start a parameter
                            acumulator.BeginParameter(readHead);
                            break;

                        case EscapeState.DemandRightEscape:
                            throw new FormatException($"Unexpected text at {readHead}; expected to find '{parameterEnd}' to complete an escape sequence.");

                        case EscapeState.None:
                            if (!acumulator.IsCollectingFixed && !acumulator.IsCollectingParameter)
                            {
                                acumulator.BeginFixed(readHead);
                            }
                            break;
                    }
                    break;
            }
        }

        acumulator.Finish(template.Length - 1);

        this.parts = acumulator.Parts;
        this.parameterKeys = new HashSet<string>(acumulator.Parts.Where(p => p.IsParameter).Select(p => p.Format(template)));

    }

    public ISet<string> ParameterKeys => this.parameterKeys;

    public bool CheckParameters(params IEnumerable<string> parameterKeys)
    {
        HashSet<string> inputParameterKeys = [.. parameterKeys];
        return this.parameterKeys.SetEquals(inputParameterKeys);
    }

    public StringBuilder Format(params IEnumerable<(string name, string value)> parameters)
    {
        HashSet<string> inputParameterKeys = new HashSet<string>();
        Dictionary<string, string> parameterValues = new Dictionary<string, string>();
        foreach (var (name, value) in parameters)
        {
            inputParameterKeys.Add(name);
            parameterValues[name] = value;
        }

        return this.FormatInternal(parameterValues, inputParameterKeys);
    }

    public StringBuilder Format(IDictionary<string, string> parameters)
    {
        return this.FormatInternal(parameters, new HashSet<string>(parameters.Keys));
    }

    private StringBuilder FormatInternal(IDictionary<string, string> parameterValues, HashSet<string> inputParameterKeys)
    {
        if (this.parameterKeys.IsSubsetOf(inputParameterKeys))
        {
            StringBuilder result = new StringBuilder();
            foreach (Part part in this.parts)
            {
                part.Format(result, template, parameterValues);
            }
            return result;
        }
        else
        {
            IEnumerable<string> missingParameters = this.parameterKeys.Except(inputParameterKeys);
            throw new InvalidOperationException($"Missing parameters from template in input: {String.Join(", ", missingParameters)}");
        }
    }
}
