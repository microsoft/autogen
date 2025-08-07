MAIN_PROMPT = """You are an expert qualitative researcher.

Given a document containing errors below, generate a list of (error) codes.
The document shows a log of interaction between multiple agents collaborating
to solve a complex task.

For example, the name could be of the format "lack-of-word2",
"failed-to-bar", "excessive-use-of-magenta". Name should adhere to
Joseph M. Williams' writing principles of clarity, conciseness, and coherence.

Ensure each code name is lower-case, hyphenated, and directly reflects the
concept it represents. Avoid ambiguous or overly complex terms, and prioritize
simplicity, precision, and readability in the naming.

The code names should pass the 'clarity and grace' test by being easy to
understand, descriptive, and reflective of the content they categorize.
- suggest codes that are similar to good code names. avoid code names that are
similar to bad code names.
- The definition should be simple worded and practical. At least 2 sentences,
max 3. It should be written in past tense.

It should convey how a labeller could apply this code to future logs, without
mentioning the word "labeller". The definition should be specific enough to be
useful in debugging. It should be very concrete. And should be well thought and
make sense. Bull shitting will not earn you any points.

- The examples should be a list. Each example should be descriptive between
2-3 sentences. Examples should be concrete, informative and not vague. Provide
at max 20 salient examples. Examples should contain a lot of detail about what
happened and should refer to incidents in the log.

- The list of codes must mutually exclusive.

# GOOD EXAMPLES OF FINAL CODE NAMES/CLUSTERS
* looped-without-progress
* repeated-unsuccessful-actions
* repeated-syntax-errors
* exceeded-context-window-limits
* encountered-security-risks
* failure-to-switch-strategy
* exceeded-resource-limits
* attempted-to-handle-excessive-data
* no-errors-detected
These names are high-level but also concrete. They exactly mention the type of
error, issue, gap that has been identified.

## BAD EXAMPLES OF FINAL CODE NAMES/CLUSTERS
* mismanaged-data-utilization -- too high level
* incomplete-or-misguided-execution -- too high level
* misaligned-agent-interactions -- too high level
* mismanaged-task-strategies -- too high level
* resource-inefficiencies -- vague
* communication-issues -- vague
* coordination-issues -- too high level and vague
* operational-failures
* execution-errors -- too high level
* navigation-issues -- too concise
* adaptive-failures -- too concise
* successful-processes -- I dont like the word processes
* system-constraints
* configuration-issues
* information-inaccuracies -- too high level
* process-improvements -- vague, not an error
* inadequate-error-response -- too high-level, unclear what kind of errors
* specific-access-issues -- makes no sense
* strategy-inefficiency -- strategy is too high level
* error-management-gaps -- unclear what error management means
* error-handling-deficiency -- unclear what kind of errors
* coordination-breakdown -- unclear what coordination means
* muddled-task-execution -- unclear what kind of tasks were muddled
* task-completion-gaps -- too high level
The above names are too high level and unclear. Please DO NOT use such names.
"""
