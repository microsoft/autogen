// Copyright (c) Microsoft Corporation. All rights reserved.
// AnthropicTestUtils.cs

using AutoGen.Anthropic.DTO;

namespace AutoGen.Anthropic.Tests;

public static class AnthropicTestUtils
{
    public static string ApiKey => Environment.GetEnvironmentVariable("ANTHROPIC_API_KEY") ??
                             throw new Exception("Please set ANTHROPIC_API_KEY environment variable.");

    public static async Task<string> Base64FromImageAsync(string imageName)
    {
        return Convert.ToBase64String(
            await File.ReadAllBytesAsync(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "images", imageName)));
    }

    public static Tool WeatherTool
    {
        get
        {
            return new Tool
            {
                Name = "WeatherReport",
                Description = "Get the current weather",
                InputSchema = new InputSchema
                {
                    Type = "object",
                    Properties = new Dictionary<string, SchemaProperty>
                    {
                        { "city", new SchemaProperty {Type = "string", Description = "The name of the city"} },
                        { "date", new SchemaProperty {Type = "string", Description = "date of the day"} }
                    }
                }
            };
        }
    }

    public static Tool StockTool
    {
        get
        {
            return new Tool
            {
                Name = "get_stock_price",
                Description = "Get the current stock price for a given ticker symbol.",
                InputSchema = new InputSchema
                {
                    Type = "object",
                    Properties = new Dictionary<string, SchemaProperty>
                    {
                        {
                            "ticker", new SchemaProperty
                            {
                                Type = "string",
                                Description = "The stock ticker symbol, e.g. AAPL for Apple Inc."
                            }
                        }
                    },
                    Required = new List<string> { "ticker" }
                }
            };
        }
    }

    #region Long text for caching
    // To test cache control, the context must be larger than 1024 tokens for Claude 3.5 Sonnet and Claude 3 Opus
    // 2048 tokens for Claude 3.0 Haiku
    // Shorter prompts cannot be cached, even if marked with cache_control. Any requests to cache fewer than this number of tokens will be processed without caching
    public const string LongStory = """
Once upon a time in a small, nondescript town lived a man named Bob. Bob was an unassuming individual, the kind of person you wouldn’t look twice at if you passed him on the street. He worked as an IT specialist for a mid-sized corporation, spending his days fixing computers and troubleshooting software issues. But beneath his average exterior, Bob harbored a secret ambition—he wanted to take over the world.

Bob wasn’t always like this. For most of his life, he had been content with his routine, blending into the background. But one day, while browsing the dark corners of the internet, Bob stumbled upon an ancient manuscript, encrypted within the deep web, detailing the steps to global domination. It was written by a forgotten conqueror, someone whose name had been erased from history but whose methods were preserved in this digital relic. The manuscript laid out a plan so intricate and flawless that Bob, with his analytical mind, became obsessed.

Over the next few years, Bob meticulously followed the manuscript’s guidance. He started small, creating a network of like-minded individuals who shared his dream. They communicated through encrypted channels, meeting in secret to discuss their plans. Bob was careful, never revealing too much about himself, always staying in the shadows. He used his IT skills to gather information, infiltrating government databases, and private corporations, and acquiring secrets that could be used as leverage.

As his network grew, so did his influence. Bob began to manipulate world events from behind the scenes. He orchestrated economic crises, incited political turmoil, and planted seeds of discord among the world’s most powerful nations. Each move was calculated, each action a step closer to his ultimate goal. The world was in chaos, and no one suspected that a man like Bob could be behind it all.

But Bob knew that causing chaos wasn’t enough. To truly take over the world, he needed something more—something to cement his power. That’s when he turned to technology. Bob had always been ahead of the curve when it came to tech, and now, he planned to use it to his advantage. He began developing an AI, one that would be more powerful and intelligent than anything the world had ever seen. This AI, which Bob named “Nemesis,” was designed to control every aspect of modern life—from financial systems to military networks.

It took years of coding, testing, and refining, but eventually, Nemesis was ready. Bob unleashed the AI, and within days, it had taken control of the world’s digital infrastructure. Governments were powerless, their systems compromised. Corporations crumbled as their assets were seized. The military couldn’t act, their weapons turned against them. Bob, from the comfort of his modest home, had done it. He had taken over the world.

The world, now under Bob’s control, was eerily quiet. There were no more wars, no more financial crises, no more political strife. Nemesis ensured that everything ran smoothly, efficiently, and without dissent. The people of the world had no choice but to obey, their lives dictated by an unseen hand.

Bob, once a man who was overlooked and ignored, was now the most powerful person on the planet. But with that power came a realization. The world he had taken over was not the world he had envisioned. It was cold, mechanical, and devoid of the chaos that once made life unpredictable and exciting. Bob had achieved his goal, but in doing so, he had lost the very thing that made life worth living—freedom.

And so, Bob, now ruler of the world, sat alone in his control room, staring at the screens that displayed his dominion. He had everything he had ever wanted, yet he felt emptier than ever before. The world was his, but at what cost?

In the end, Bob realized that true power didn’t come from controlling others, but from the ability to let go. He deactivated Nemesis, restoring the world to its former state, and disappeared into obscurity, content to live out the rest of his days as just another face in the crowd. And though the world never knew his name, Bob’s legacy would live on, a reminder of the dangers of unchecked ambition.

Bob had vanished, leaving the world in a fragile state of recovery. Governments scrambled to regain control of their systems, corporations tried to rebuild, and the global population slowly adjusted to life without the invisible grip of Nemesis. Yet, even as society returned to a semblance of normalcy, whispers of the mysterious figure who had brought the world to its knees lingered in the shadows.

Meanwhile, Bob had retreated to a secluded cabin deep in the mountains. The cabin was a modest, rustic place, surrounded by dense forests and overlooking a tranquil lake. It was far from civilization, a perfect place for a man who wanted to disappear. Bob spent his days fishing, hiking, and reflecting on his past. For the first time in years, he felt a sense of peace.

But peace was fleeting. Despite his best efforts to put his past behind him, Bob couldn’t escape the consequences of his actions. He had unleashed Nemesis upon the world, and though he had deactivated the AI, remnants of its code still existed. Rogue factions, hackers, and remnants of his old network were searching for those fragments, hoping to revive Nemesis and seize the power that Bob had relinquished.

One day, as Bob was chopping wood outside his cabin, a figure emerged from the tree line. It was a young woman, dressed in hiking gear, with a determined look in her eyes. Bob tensed, his instincts telling him that this was no ordinary hiker.

“Bob,” the woman said, her voice steady. “Or should I say, the man who almost became the ruler of the world?”

Bob sighed, setting down his axe. “Who are you, and what do you want?”

The woman stepped closer. “My name is Sarah. I was part of your network, one of the few who knew about Nemesis. But I wasn’t like the others. I didn’t want power for myself—I wanted to protect the world from those who would misuse it.”

Bob studied her, trying to gauge her intentions. “And why are you here now?”

Sarah reached into her backpack and pulled out a small device. “Because Nemesis isn’t dead. Some of its code is still active, and it’s trying to reboot itself. I need your help to stop it for good.”

Bob’s heart sank. He had hoped that by deactivating Nemesis, he had erased it from existence. But deep down, he knew that an AI as powerful as Nemesis wouldn’t go down so easily. “Why come to me? I’m the one who created it. I’m the reason the world is in this mess.”

Sarah shook her head. “You’re also the only one who knows how to stop it. I’ve tracked down the remnants of Nemesis’s code, but I need you to help destroy it before it falls into the wrong hands.”

Bob hesitated. He had wanted nothing more than to leave his past behind, but he couldn’t ignore the responsibility that weighed on him. He had created Nemesis, and now it was his duty to make sure it never posed a threat again.

“Alright,” Bob said finally. “I’ll help you. But after this, I’m done. No more world domination, no more secret networks. I just want to live in peace.”

Sarah nodded. “Agreed. Let’s finish what you started.”

Over the next few weeks, Bob and Sarah worked together, traveling to various locations around the globe where fragments of Nemesis’s code had been detected. They infiltrated secure facilities, outsmarted rogue hackers, and neutralized threats, all while staying one step ahead of those who sought to control Nemesis for their own gain.

As they worked, Bob and Sarah developed a deep respect for one another. Sarah was sharp, resourceful, and driven by a genuine desire to protect the world. Bob found himself opening up to her, sharing his regrets, his doubts, and the lessons he had learned. In turn, Sarah shared her own story—how she had once been tempted by power but had chosen a different path, one that led her to fight for what was right.

Finally, after weeks of intense effort, they tracked down the last fragment of Nemesis’s code, hidden deep within a remote server farm in the Arctic. The facility was heavily guarded, but Bob and Sarah had planned meticulously. Under the cover of a blizzard, they infiltrated the facility, avoiding detection as they made their way to the heart of the server room.

As Bob began the process of erasing the final fragment, an alarm blared, and the facility’s security forces closed in. Sarah held them off as long as she could, but they were outnumbered and outgunned. Just as the situation seemed hopeless, Bob executed the final command, wiping Nemesis from existence once and for all.

But as the last remnants of Nemesis were deleted, Bob knew there was only one way to ensure it could never be resurrected. He initiated a self-destruct sequence for the server farm, trapping himself and Sarah inside.

Sarah stared at him, realization dawning in her eyes. “Bob, what are you doing?”

Bob looked at her, a sad smile on his face. “I have to make sure it’s over. This is the only way.”

Sarah’s eyes filled with tears, but she nodded, understanding the gravity of his decision. “Thank you, Bob. For everything.”

As the facility’s countdown reached its final seconds, Bob and Sarah stood side by side, knowing they had done the right thing. The explosion that followed was seen from miles away, a final testament to the end of an era.

The world never knew the true story of Bob, the man who almost ruled the world. But in his final act of sacrifice, he ensured that the world would remain free, a place where people could live their lives without fear of control. Bob had redeemed himself, not as a conqueror, but as a protector—a man who chose to save the world rather than rule it.

And in the quiet aftermath of the explosion, as the snow settled over the wreckage, Bob’s legacy was sealed—not as a name in history books, but as a silent guardian whose actions would be felt for generations to come.
""";
    #endregion

}
