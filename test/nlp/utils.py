import pandas as pd


def get_toy_data_seqclassification():
    train_data = {
        "sentence1": [
            'Amrozi accused his brother , whom he called " the witness " , of deliberately distorting his evidence .',
            "Yucaipa owned Dominick 's before selling the chain to Safeway in 1998 for $ 2.5 billion .",
            "They had published an advertisement on the Internet on June 10 , offering the cargo for sale , he added .",
            "Around 0335 GMT , Tab shares were up 19 cents , or 4.4 % , at A $ 4.56 , having earlier set a record high of A $ 4.57 .",
        ],
        "sentence2": [
            'Referring to him as only " the witness " , Amrozi accused his brother of deliberately distorting his evidence .',
            "Yucaipa bought Dominick 's in 1995 for $ 693 million and sold it to Safeway for $ 1.8 billion in 1998 .",
            "On June 10 , the ship 's owners had published an advertisement on the Internet , offering the explosives for sale .",
            "Tab shares jumped 20 cents , or 4.6 % , to set a record closing high at A $ 4.57 .",
        ],
        "label": [1, 0, 1, 0],
        "idx": [0, 1, 2, 3],
    }
    train_dataset = pd.DataFrame(train_data)

    dev_data = {
        "sentence1": [
            "The stock rose $ 2.11 , or about 11 percent , to close Friday at $ 21.51 on the New York Stock Exchange .",
            "Revenue in the first quarter of the year dropped 15 percent from the same period a year earlier .",
            "The Nasdaq had a weekly gain of 17.27 , or 1.2 percent , closing at 1,520.15 on Friday .",
            "The DVD-CCA then appealed to the state Supreme Court .",
        ],
        "sentence2": [
            "PG & E Corp. shares jumped $ 1.63 or 8 percent to $ 21.03 on the New York Stock Exchange on Friday .",
            "With the scandal hanging over Stewart 's company , revenue the first quarter of the year dropped 15 percent from the same period a year earlier .",
            "The tech-laced Nasdaq Composite .IXIC rallied 30.46 points , or 2.04 percent , to 1,520.15 .",
            "The DVD CCA appealed that decision to the U.S. Supreme Court .",
        ],
        "label": [1, 1, 0, 1],
        "idx": [4, 5, 6, 7],
    }
    dev_dataset = pd.DataFrame(dev_data)

    test_data = {
        "sentence1": [
            "That compared with $ 35.18 million , or 24 cents per share , in the year-ago period .",
            "Shares of Genentech , a much larger company with several products on the market , rose more than 2 percent .",
            "Legislation making it harder for consumers to erase their debts in bankruptcy court won overwhelming House approval in March .",
            "The Nasdaq composite index increased 10.73 , or 0.7 percent , to 1,514.77 .",
        ],
        "sentence2": [
            "Earnings were affected by a non-recurring $ 8 million tax benefit in the year-ago period .",
            "Shares of Xoma fell 16 percent in early trade , while shares of Genentech , a much larger company with several products on the market , were up 2 percent .",
            "Legislation making it harder for consumers to erase their debts in bankruptcy court won speedy , House approval in March and was endorsed by the White House .",
            "The Nasdaq Composite index , full of technology stocks , was lately up around 18 points .",
        ],
        "label": [0, 0, 0, 0],
        "idx": [8, 10, 11, 12],
    }
    test_dataset = pd.DataFrame(test_data)

    custom_sent_keys = ["sentence1", "sentence2"]
    label_key = "label"

    X_train = train_dataset[custom_sent_keys]
    y_train = train_dataset[label_key]

    X_val = dev_dataset[custom_sent_keys]
    y_val = dev_dataset[label_key]

    X_test = test_dataset[custom_sent_keys]

    return X_train, y_train, X_val, y_val, X_test


def get_toy_data_multiclassclassification():
    train_data = {
        "text": [
            "i didnt feel humiliated",
            "i can go from feeling so hopeless to so damned hopeful just from being around someone who cares and is awake",
            "im grabbing a minute to post i feel greedy wrong",
            "i am ever feeling nostalgic about the fireplace i will know that it is still on the property",
            "i am feeling grouchy",
            "ive been feeling a little burdened lately wasnt sure why that was",
            "ive been taking or milligrams or times recommended amount and ive fallen asleep a lot faster but i also feel like so funny",
            "i feel as confused about life as a teenager or as jaded as a year old man",
            "i have been with petronas for years i feel that petronas has performed well and made a huge profit",
            "i feel romantic too",
            "i feel like i have to make the suffering i m seeing mean something",
            "i do feel that running is a divine experience and that i can expect to have some type of spiritual encounter",
        ],
        "label": [0, 0, 3, 2, 3, 0, 5, 4, 1, 2, 0, 1],
    }
    train_dataset = pd.DataFrame(train_data)

    dev_data = {
        "text": [
            "i think it s the easiest time of year to feel dissatisfied",
            "i feel low energy i m just thirsty",
            "i have immense sympathy with the general point but as a possible proto writer trying to find time to write in the corners of life and with no sign of an agent let alone a publishing contract this feels a little precious",
            "i do not feel reassured anxiety is on each side",
        ],
        "label": [3, 0, 1, 1],
    }
    dev_dataset = pd.DataFrame(dev_data)

    custom_sent_keys = ["text"]
    label_key = "label"

    X_train = train_dataset[custom_sent_keys]
    y_train = train_dataset[label_key]

    X_val = dev_dataset[custom_sent_keys]
    y_val = dev_dataset[label_key]

    return X_train, y_train, X_val, y_val


def get_toy_data_multiplechoiceclassification():
    train_data = {
        "video-id": [
            "anetv_fruimvo90vA",
            "anetv_fruimvo90vA",
            "anetv_fruimvo90vA",
            "anetv_MldEr60j33M",
            "lsmdc0049_Hannah_and_her_sisters-69438",
        ],
        "fold-ind": ["10030", "10030", "10030", "5488", "17405"],
        "startphrase": [
            "A woman is seen running down a long track and jumping into a pit. The camera",
            "A woman is seen running down a long track and jumping into a pit. The camera",
            "A woman is seen running down a long track and jumping into a pit. The camera",
            "A man in a white shirt bends over and picks up a large weight. He",
            "Someone furiously shakes someone away. He",
        ],
        "sent1": [
            "A woman is seen running down a long track and jumping into a pit.",
            "A woman is seen running down a long track and jumping into a pit.",
            "A woman is seen running down a long track and jumping into a pit.",
            "A man in a white shirt bends over and picks up a large weight.",
            "Someone furiously shakes someone away.",
        ],
        "sent2": ["The camera", "The camera", "The camera", "He", "He"],
        "gold-source": ["gen", "gen", "gold", "gen", "gold"],
        "ending0": [
            "captures her as well as lifting weights down in place.",
            "follows her spinning her body around and ends by walking down a lane.",
            "watches her as she walks away and sticks her tongue out to another person.",
            "lifts the weights over his head.",
            "runs to a woman standing waiting.",
        ],
        "ending1": [
            "pans up to show another woman running down the track.",
            "pans around the two.",
            "captures her as well as lifting weights down in place.",
            "also lifts it onto his chest before hanging it back out again.",
            "tackles him into the passenger seat.",
        ],
        "ending2": [
            "follows her movements as the group members follow her instructions.",
            "captures her as well as lifting weights down in place.",
            "follows her spinning her body around and ends by walking down a lane.",
            "spins around and lifts a barbell onto the floor.",
            "pounds his fist against a cupboard.",
        ],
        "ending3": [
            "follows her spinning her body around and ends by walking down a lane.",
            "follows her movements as the group members follow her instructions.",
            "pans around the two.",
            "bends down and lifts the weight over his head.",
            "offers someone the cup on his elbow and strides out.",
        ],
        "label": [1, 3, 0, 0, 2],
    }
    dev_data = {
        "video-id": [
            "lsmdc3001_21_JUMP_STREET-422",
            "lsmdc0001_American_Beauty-45991",
            "lsmdc0001_American_Beauty-45991",
            "lsmdc0001_American_Beauty-45991",
        ],
        "fold-ind": ["11783", "10977", "10970", "10968"],
        "startphrase": [
            "Firing wildly he shoots holes through the tanker. He",
            "He puts his spatula down. The Mercedes",
            "He stands and looks around, his eyes finally landing on: "
            "The digicam and a stack of cassettes on a shelf. Someone",
            "He starts going through someone's bureau. He opens the drawer "
            "in which we know someone keeps his marijuana, but he",
        ],
        "sent1": [
            "Firing wildly he shoots holes through the tanker.",
            "He puts his spatula down.",
            "He stands and looks around, his eyes finally landing on: "
            "The digicam and a stack of cassettes on a shelf.",
            "He starts going through someone's bureau.",
        ],
        "sent2": [
            "He",
            "The Mercedes",
            "Someone",
            "He opens the drawer in which we know someone keeps his marijuana, but he",
        ],
        "gold-source": ["gold", "gold", "gold", "gold"],
        "ending0": [
            "overtakes the rig and falls off his bike.",
            "fly open and drinks.",
            "looks at someone's papers.",
            "stops one down and rubs a piece of the gift out.",
        ],
        "ending1": [
            "squeezes relentlessly on the peanut jelly as well.",
            "walks off followed driveway again.",
            "feels around it and falls in the seat once more.",
            "cuts the mangled parts.",
        ],
        "ending2": [
            "scrambles behind himself and comes in other directions.",
            "slots them into a separate green.",
            "sprints back from the wreck and drops onto his back.",
            "hides it under his hat to watch.",
        ],
        "ending3": [
            "sweeps a explodes and knocks someone off.",
            "pulls around to the drive - thru window.",
            "sits at the kitchen table, staring off into space.",
            "does n't discover its false bottom.",
        ],
        "label": [0, 3, 3, 3],
    }
    test_data = {
        "video-id": [
            "lsmdc0001_American_Beauty-45991",
            "lsmdc0001_American_Beauty-45991",
            "lsmdc0001_American_Beauty-45991",
            "lsmdc0001_American_Beauty-45991",
        ],
        "fold-ind": ["10980", "10976", "10978", "10969"],
        "startphrase": [
            "Someone leans out of the drive - thru window, "
            "grinning at her, holding bags filled with fast food. The Counter Girl",
            "Someone looks up suddenly when he hears. He",
            "Someone drives; someone sits beside her. They",
            "He opens the drawer in which we know someone "
            "keeps his marijuana, but he does n't discover"
            " its false bottom. He stands and looks around, his eyes",
        ],
        "sent1": [
            "Someone leans out of the drive - thru "
            "window, grinning at her, holding bags filled with fast food.",
            "Someone looks up suddenly when he hears.",
            "Someone drives; someone sits beside her.",
            "He opens the drawer in which we know"
            " someone keeps his marijuana, but he does n't discover its false bottom.",
        ],
        "sent2": [
            "The Counter Girl",
            "He",
            "They",
            "He stands and looks around, his eyes",
        ],
        "gold-source": ["gold", "gold", "gold", "gold"],
        "ending0": [
            "stands next to him, staring blankly.",
            "puts his spatula down.",
            "rise someone's feet up.",
            "moving to the side, the houses rapidly stained.",
        ],
        "ending1": [
            "with auditorium, filmed, singers the club.",
            "bumps into a revolver and drops surreptitiously into his weapon.",
            "lift her and they are alarmed.",
            "focused as the sight of someone making his way down a trail.",
        ],
        "ending2": [
            "attempts to block her ransacked.",
            "talks using the phone and walks away for a few seconds.",
            "are too involved with each other to "
            "notice someone watching them from the drive - thru window.",
            "finally landing on: the digicam and a stack of cassettes on a shelf.",
        ],
        "ending3": [
            "is eating solid and stinky.",
            "bundles the flaxen powder beneath the car.",
            "sit at a table with a beer from a table.",
            "deep and continuing, its bleed - length sideburns pressing on him.",
        ],
        "label": [0, 0, 2, 2],
    }

    train_dataset = pd.DataFrame(train_data)
    dev_dataset = pd.DataFrame(dev_data)
    test_dataset = pd.DataFrame(test_data)

    custom_sent_keys = [
        "sent1",
        "sent2",
        "ending0",
        "ending1",
        "ending2",
        "ending3",
        "gold-source",
        "video-id",
        "startphrase",
        "fold-ind",
    ]
    label_key = "label"

    X_train = train_dataset[custom_sent_keys]
    y_train = train_dataset[label_key]

    X_val = dev_dataset[custom_sent_keys]
    y_val = dev_dataset[label_key]

    X_test = test_dataset[custom_sent_keys]
    y_test = test_dataset[label_key]

    return X_train, y_train, X_val, y_val, X_test, y_test


def get_toy_data_seqregression():
    train_data = {
        "sentence1": [
            "A plane is taking off.",
            "A man is playing a large flute.",
            "A man is spreading shreded cheese on a pizza.",
            "Three men are playing chess.",
        ],
        "sentence2": [
            "An air plane is taking off.",
            "A man is playing a flute.",
            "A man is spreading shredded cheese on an uncooked pizza.",
            "Two men are playing chess.",
        ],
        "label": [5.0, 3.799999952316284, 3.799999952316284, 2.5999999046325684],
        "idx": [0, 1, 2, 3],
    }
    train_dataset = pd.DataFrame(train_data)

    dev_data = {
        "sentence1": [
            "A man is playing the cello.",
            "Some men are fighting.",
            "A man is smoking.",
            "The man is playing the piano.",
        ],
        "sentence2": [
            "A man seated is playing the cello.",
            "Two men are fighting.",
            "A man is skating.",
            "The man is playing the guitar.",
        ],
        "label": [4.25, 4.25, 0.5, 1.600000023841858],
        "idx": [4, 5, 6, 7],
    }
    dev_dataset = pd.DataFrame(dev_data)

    custom_sent_keys = ["sentence1", "sentence2"]
    label_key = "label"

    X_train = train_dataset[custom_sent_keys]
    y_train = train_dataset[label_key]

    X_val = dev_dataset[custom_sent_keys]
    y_val = dev_dataset[label_key]

    return X_train, y_train, X_val, y_val


def get_toy_data_summarization():
    train_dataset = pd.DataFrame(
        [
            ("The cat is alive", "The cat is dead"),
            ("The cat is alive", "The cat is dead"),
            ("The cat is alive", "The cat is dead"),
            ("The cat is alive", "The cat is dead"),
        ]
    )
    dev_dataset = pd.DataFrame(
        [
            ("The old woman is beautiful", "The old woman is ugly"),
            ("The old woman is beautiful", "The old woman is ugly"),
            ("The old woman is beautiful", "The old woman is ugly"),
            ("The old woman is beautiful", "The old woman is ugly"),
        ]
    )
    test_dataset = pd.DataFrame(
        [
            ("The purse is cheap", "The purse is expensive"),
            ("The purse is cheap", "The purse is expensive"),
            ("The purse is cheap", "The purse is expensive"),
            ("The purse is cheap", "The purse is expensive"),
        ]
    )

    for each_dataset in [train_dataset, dev_dataset, test_dataset]:
        each_dataset.columns = ["document", "summary"]

    custom_sent_keys = ["document"]
    label_key = "summary"

    X_train = train_dataset[custom_sent_keys]
    y_train = train_dataset[label_key]

    X_val = dev_dataset[custom_sent_keys]
    y_val = dev_dataset[label_key]

    X_test = test_dataset[custom_sent_keys]
    return X_train, y_train, X_val, y_val, X_test


def get_toy_data_tokenclassification():
    train_data = {
        "chunk_tags": [
            [11, 21, 11, 12, 21, 22, 11, 12, 0],
            [11, 12],
            [11, 12],
            [
                11,
                12,
                12,
                21,
                13,
                11,
                11,
                21,
                13,
                11,
                12,
                13,
                11,
                21,
                22,
                11,
                12,
                17,
                11,
                21,
                17,
                11,
                12,
                12,
                21,
                22,
                22,
                13,
                11,
                0,
            ],
        ],
        "id": ["0", "1", "2", "3"],
        "ner_tags": [
            [3, 0, 7, 0, 0, 0, 7, 0, 0],
            [1, 2],
            [5, 0],
            [
                0,
                3,
                4,
                0,
                0,
                0,
                0,
                0,
                0,
                7,
                0,
                0,
                0,
                0,
                0,
                7,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
            ],
        ],
        "pos_tags": [
            [22, 42, 16, 21, 35, 37, 16, 21, 7],
            [22, 22],
            [22, 11],
            [
                12,
                22,
                22,
                38,
                15,
                22,
                28,
                38,
                15,
                16,
                21,
                35,
                24,
                35,
                37,
                16,
                21,
                15,
                24,
                41,
                15,
                16,
                21,
                21,
                20,
                37,
                40,
                35,
                21,
                7,
            ],
        ],
        "tokens": [
            [
                "EU",
                "rejects",
                "German",
                "call",
                "to",
                "boycott",
                "British",
                "lamb",
                ".",
            ],
            ["Peter", "Blackburn"],
            ["BRUSSELS", "1996-08-22"],
            [
                "The",
                "European",
                "Commission",
                "said",
                "on",
                "Thursday",
                "it",
                "disagreed",
                "with",
                "German",
                "advice",
                "to",
                "consumers",
                "to",
                "shun",
                "British",
                "lamb",
                "until",
                "scientists",
                "determine",
                "whether",
                "mad",
                "cow",
                "disease",
                "can",
                "be",
                "transmitted",
                "to",
                "sheep",
                ".",
            ],
        ],
    }

    dev_data = {
        "chunk_tags": [
            [
                11,
                11,
                12,
                13,
                11,
                12,
                12,
                11,
                12,
                12,
                12,
                12,
                21,
                13,
                11,
                12,
                21,
                22,
                11,
                13,
                11,
                1,
                13,
                11,
                17,
                11,
                12,
                12,
                21,
                1,
                0,
            ],
            [
                0,
                11,
                21,
                22,
                22,
                11,
                12,
                12,
                17,
                11,
                21,
                22,
                22,
                11,
                12,
                13,
                11,
                0,
                0,
                11,
                12,
                11,
                12,
                12,
                12,
                12,
                12,
                12,
                21,
                11,
                12,
                12,
                0,
            ],
            [
                11,
                21,
                11,
                12,
                12,
                21,
                22,
                0,
                17,
                11,
                21,
                22,
                17,
                11,
                21,
                22,
                11,
                21,
                22,
                22,
                13,
                11,
                12,
                12,
                0,
            ],
            [
                11,
                21,
                11,
                12,
                11,
                12,
                13,
                11,
                12,
                12,
                12,
                12,
                21,
                22,
                11,
                12,
                0,
                11,
                0,
                11,
                12,
                13,
                11,
                12,
                12,
                12,
                12,
                12,
                21,
                11,
                12,
                1,
                2,
                2,
                11,
                21,
                22,
                11,
                12,
                0,
            ],
        ],
        "id": ["4", "5", "6", "7"],
        "ner_tags": [
            [
                5,
                0,
                0,
                0,
                0,
                3,
                4,
                0,
                0,
                0,
                1,
                2,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                5,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
            ],
            [
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                3,
                0,
                0,
                0,
                1,
                2,
                2,
                2,
                0,
                0,
                0,
                0,
                0,
            ],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3, 4, 0],
            [
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                3,
                0,
                0,
                1,
                2,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
            ],
        ],
        "pos_tags": [
            [
                22,
                27,
                21,
                35,
                12,
                22,
                22,
                27,
                16,
                21,
                22,
                22,
                38,
                15,
                22,
                24,
                20,
                37,
                21,
                15,
                24,
                16,
                15,
                22,
                15,
                12,
                16,
                21,
                38,
                17,
                7,
            ],
            [
                0,
                28,
                41,
                30,
                37,
                12,
                16,
                21,
                15,
                28,
                41,
                30,
                37,
                12,
                24,
                15,
                28,
                6,
                0,
                12,
                22,
                27,
                16,
                21,
                22,
                22,
                14,
                22,
                38,
                12,
                21,
                21,
                7,
            ],
            [
                28,
                38,
                16,
                16,
                21,
                38,
                40,
                10,
                15,
                28,
                38,
                40,
                15,
                21,
                38,
                40,
                28,
                20,
                37,
                40,
                15,
                12,
                22,
                22,
                7,
            ],
            [
                28,
                38,
                12,
                21,
                16,
                21,
                15,
                22,
                22,
                22,
                22,
                22,
                35,
                37,
                21,
                24,
                6,
                24,
                10,
                16,
                24,
                15,
                12,
                21,
                10,
                21,
                21,
                24,
                38,
                12,
                30,
                16,
                10,
                16,
                21,
                35,
                37,
                16,
                21,
                7,
            ],
        ],
        "tokens": [
            [
                "Germany",
                "'s",
                "representative",
                "to",
                "the",
                "European",
                "Union",
                "'s",
                "veterinary",
                "committee",
                "Werner",
                "Zwingmann",
                "said",
                "on",
                "Wednesday",
                "consumers",
                "should",
                "buy",
                "sheepmeat",
                "from",
                "countries",
                "other",
                "than",
                "Britain",
                "until",
                "the",
                "scientific",
                "advice",
                "was",
                "clearer",
                ".",
            ],
            [
                '"',
                "We",
                "do",
                "n't",
                "support",
                "any",
                "such",
                "recommendation",
                "because",
                "we",
                "do",
                "n't",
                "see",
                "any",
                "grounds",
                "for",
                "it",
                ",",
                '"',
                "the",
                "Commission",
                "'s",
                "chief",
                "spokesman",
                "Nikolaus",
                "van",
                "der",
                "Pas",
                "told",
                "a",
                "news",
                "briefing",
                ".",
            ],
            [
                "He",
                "said",
                "further",
                "scientific",
                "study",
                "was",
                "required",
                "and",
                "if",
                "it",
                "was",
                "found",
                "that",
                "action",
                "was",
                "needed",
                "it",
                "should",
                "be",
                "taken",
                "by",
                "the",
                "European",
                "Union",
                ".",
            ],
            [
                "He",
                "said",
                "a",
                "proposal",
                "last",
                "month",
                "by",
                "EU",
                "Farm",
                "Commissioner",
                "Franz",
                "Fischler",
                "to",
                "ban",
                "sheep",
                "brains",
                ",",
                "spleens",
                "and",
                "spinal",
                "cords",
                "from",
                "the",
                "human",
                "and",
                "animal",
                "food",
                "chains",
                "was",
                "a",
                "highly",
                "specific",
                "and",
                "precautionary",
                "move",
                "to",
                "protect",
                "human",
                "health",
                ".",
            ],
        ],
    }
    train_dataset = pd.DataFrame(train_data)
    dev_dataset = pd.DataFrame(dev_data)

    custom_sent_keys = ["tokens"]
    label_key = "ner_tags"

    X_train = train_dataset[custom_sent_keys]
    y_train = train_dataset[label_key]

    X_val = dev_dataset[custom_sent_keys]
    y_val = dev_dataset[label_key]
    return X_train, y_train, X_val, y_val


def get_automl_settings(estimator_name="transformer"):

    automl_settings = {
        "gpu_per_trial": 0,
        "max_iter": 3,
        "time_budget": 10,
        "task": "seq-classification",
        "metric": "accuracy",
        "log_file_name": "seqclass.log",
        "use_ray": False,
    }

    automl_settings["fit_kwargs_by_estimator"] = {
        estimator_name: {
            "model_path": "google/electra-small-discriminator",
            "output_dir": "test/data/output/",
            "ckpt_per_epoch": 1,
            "fp16": False,
        }
    }

    automl_settings["estimator_list"] = [estimator_name]
    return automl_settings
