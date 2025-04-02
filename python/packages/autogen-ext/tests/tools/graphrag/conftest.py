import pandas as pd
import pytest


@pytest.fixture
def community_df_fixture() -> pd.DataFrame:
    data = {
        "id": ["d572b27c-a7c1-4a4e-a673-4c0efb9fdbd4", "7fa4296f-74d2-4ffb-abe4-3a16ff4b761c"],
        "human_readable_id": [0, 1],
        "community": [0, 1],
        "parent": [-1, -1],
        "level": [0, 0],
        "title": ["Community 0", "Community 1"],
        "entity_ids": [
            [
                "beba48a6-a5a6-458f-ae44-0c07f615e52f",
                "1277ec21-ab15-40e0-96e4-1eda5953a344",
                "195513fe-6e34-4e4f-ad13-e5fa88678a64",
                "3fb5e51a-819e-486e-b17c-d72832621cdd",
                "690a585a-57a9-4abc-b7f5-22051f823b11",
            ],
            [
                "da96b22a-5d6d-4810-bd1d-a6ad71a4cae6",
                "e28d29b0-20ce-4e51-803d-4e3178c59f49",
                "fb396b61-faba-4cb5-bd0c-578ac5df7aa1",
                "d0e85ed0-cb61-4b2a-b271-5dabe5e69c70",
                "b627179c-8354-4c2c-adea-df89f49d4b21",
                "2fcadfbe-61d9-47a7-a259-5c4f9a635a07",
                "d659dbe2-21ba-41fe-9d9d-3e8d800ac444",
                "edc7f87a-0dd6-4db4-9662-6e29aeb1568f",
                "7bb3b3e7-556f-44ce-bd3d-800c7a55d864",
                "fc28a9b5-cf94-4436-92fe-ef733fb3c69d",
            ],
        ],
        "relationship_ids": [
            [
                "224f8223-feff-43f5-9cb2-960d5a650731",
                "6d6dc7ac-cc5a-4a1c-bf37-2cba7b7e7340",
                "8ce25898-f9b3-464a-ac6a-49bd3f898295",
                "bbea05ce-be5e-4970-b8f0-73414284ab84",
            ],
            [
                "13a99b88-aef5-4935-b5c2-e00d24b125ba",
                "4d8a7724-430c-4477-a588-bcecff6fb9d8",
                "6d09a03f-7ecd-4b92-9a78-e8fbf1cea6fd",
                "718ad0a4-861e-496a-921f-62f3106b5e73",
                "73f01531-4563-4836-aad7-b1272c989406",
                "74e81ef6-006f-443d-89e5-e40e491ae874",
                "772ba9c4-19b2-4d13-8666-e08548e0645c",
                "7e494f4c-8692-4794-baa2-aed4f8601a5a",
                "92b4fdab-1e52-4cf5-bd8d-adb47a191875",
                "bd4b2ea4-a9c8-4fa3-aa86-87dcafe0a887",
                "cda6af84-59a6-45d3-b074-8551867bf6a4",
                "f1a16c4b-f673-49d0-be1a-bbb36ae4e5c8",
                "fe26f48b-8152-4a70-a2d5-f13023cbae4c",
            ],
        ],
        "text_unit_ids": [
            [
                "9bcc5581a92c05081bb138322f3dd38589fea781f43c1ef53d208a637a4f37a3f1ee41bd432b20e5257500126b84b62a400befd22dcc92338ebb9d764f59abca"
            ],
            [
                "043185f776c61662fdbc1e50e270edd06f1cc2cdf76158cdff34e8e825ba5bd39453c9e773fc1aca15ab77c837959dc85149e64ef4849c9be0b72512a6fdb00d",
                "60ee542fe71e676b6cc61f19046c27bfa00ff5e086af7101c8aed2bb992436cb17cd192af0389257da9edcee5f67ab8ccd5f52f91102dcb2da2ecedb08a2bb52",
                "9c426c886a92062375501320a4ddf890003d2cc62c5face8356bc4361856c4fbb0f4573865cb9026e99b67bf61837d570251aa0a76acb9e448fb6de84c515a1e",
            ],
        ],
        "period": ["2024-12-16", "2024-12-16"],
        "size": [5, 10],
    }
    return pd.DataFrame(data)


@pytest.fixture
def entity_df_fixture() -> pd.DataFrame:
    data = {
        "id": ["55536111-6a0d-464f-9b72-616ae5d86c2f", "55536111-6a0d-464f-9b72-616ae5d86c2f"],
        "human_readable_id": [0, 0],
        "title": ["PROJECT GUTENBERG", "PROJECT GUTENBERG"],
        "community": [4, 32],
        "level": [0, 1],
        "degree": [11, 11],
        "x": [0, 0],
        "y": [0, 0],
    }
    return pd.DataFrame(data)


@pytest.fixture
def report_df_fixture() -> pd.DataFrame:
    data = {
        "id": ["53670ddbd42f4518940333eeabe599ed", "2f129d4030324a7688c14eafab50c81c"],
        "human_readable_id": [105, 106],
        "community": [105, 106],
        "parent": [22, 22],
        "level": [2, 2],
        "title": ["Peterson and the Missing Billycock", "Baker Street and Sherlock Holmes Community"],
        "summary": [
            "The community centers around Peterson, a commissionaire involved in a mystery concerning a lost hat and a goose. His actions are pivotal in the investigation led by Sherlock Holmes, connecting various entities such as the row, the billycock hat, and multiple newspapers where advertisements were placed.",
            "The community centers around Baker Street, the iconic residence of Sherlock Holmes, and its connection to the London Underground. Baker Street serves as a significant landmark associated with the famous detective, while the Underground facilitates access to this notable location.",
        ],
        "full_content": [
            "# Peterson and the Missing Billycock\\n\\nThe community centers around Peterson, a commissionaire involved in a mystery concerning a lost hat and a goose. ...",
            "# Baker Street and Sherlock Holmes Community\\n\\nThe community centers around Baker Street, the iconic residence of Sherlock Holmes, and its connection to the London Underground. Baker...",
        ],
        "rank": [6.5, 6.5],
        "rank_explanation": [
            "The impact severity rating is moderate to high due to the potential implications of the investigation on public interest and media coverage.",
            "The impact severity rating is moderate due to the cultural significance of Baker Street and its association with Sherlock Holmes, which attracts considerable public interest.",
        ],
        "findings": [
            [
                {
                    "explanation": "Peterson is a key figure in the mystery involving the missing blue carbuncle, acting as a commissionaire who aids Sherlock Holmes. His involvement is crucial as he not only discovers the lost billycock hat but also plays a significant role in disseminating information related to the case. This highlights his importance in the narrative and the potential impact of his actions on the investigation's outcome. [Data: Entities (333); Relationships (521, 522)]",
                    "summary": "Peterson's central role in the investigation",
                },
                {
                    "explanation": "The row refers to the altercation that prompted Peterson's intervention, leading to the discovery of the hat. This incident is pivotal as it sets the stage for the entire investigation, illustrating how a seemingly minor event can have far-reaching consequences. The altercation not only affects Peterson but also ties into the larger mystery that Holmes is trying to solve. [Data: Entities (339); Relationships (521)]",
                    "summary": "The significance of the row incident",
                },
                {
                    "explanation": "The billycock hat is not just an accessory but a crucial piece of evidence in the investigation. Its discovery by Peterson links him directly to the case and raises questions about its owner, Henry Baker. The hat's significance is underscored by its role in the narrative, as it is the object around which the mystery revolves. [Data: Entities (340); Relationships (522)]",
                    "summary": "The billycock hat as a central object",
                },
                {
                    "explanation": "Peterson's task of placing advertisements in various evening papers, including the Globe, Star, Pall Mall, and others, indicates the media's role in the investigation. This outreach is essential for gathering information about the hat's owner and demonstrates how public engagement can influence the resolution of the case. The involvement of multiple newspapers suggests a broad interest in the mystery, which could amplify its impact on the community. [Data: Entities (355, 356, 357, 358, 359, 360, 361); Relationships (545, 546, 547, 548, 549, 550, 551)]",
                    "summary": "Media involvement through advertisements",
                },
            ],
            [
                {
                    "explanation": "Baker Street is not only the residence of Sherlock Holmes but also a symbol of his adventures and detective work. Its association with the fictional detective has made it a notable landmark in London, drawing interest from fans and tourists alike. The street's historical and cultural significance contributes to its status as a must-visit location, enhancing its impact on the community. [Data: Entities (4), Relationships (178)]",
                    "summary": "Baker Street as a cultural landmark",
                },
                {
                    "explanation": "Sherlock Holmes is intrinsically linked to Baker Street, as it serves as his residence and the hub for his investigations. This relationship is central to the narrative of his character, making Baker Street a vital part of the Sherlock Holmes lore. The detective's activities at this location have become iconic, further solidifying the street's importance in popular culture. [Data: Entities (4), Relationships (178)]",
                    "summary": "Sherlock Holmes's connection to Baker Street",
                },
                {
                    "explanation": "The London Underground plays a crucial role in facilitating access to Baker Street, making it easier for visitors to reach this iconic location. The connection between the Underground and Baker Street enhances the street's accessibility, contributing to its popularity as a tourist destination. This relationship underscores the importance of public transportation in connecting significant cultural landmarks. [Data: Entities (548), Relationships (862)]",
                    "summary": "The role of the Underground in accessing Baker Street",
                },
                {
                    "explanation": "Baker Street is synonymous with detective work, primarily due to its association with Sherlock Holmes. The street is where many of Holmes's investigations take place, making it a focal point for fans of detective fiction. This connection to crime-solving and mystery adds to the allure of Baker Street, attracting those interested in the genre and its history. [Data: Entities (4), Relationships (178)]",
                    "summary": "Baker Street's association with detective work",
                },
                {
                    "explanation": "The combination of Baker Street's historical significance and its association with Sherlock Holmes has made it a popular tourist destination. Visitors often seek to explore the street and its surroundings, contributing to the local economy and cultural heritage. The public interest in this location highlights the impact of literary figures on real-world places and their ability to draw crowds. [Data: Entities (4), Relationships (178)]",
                    "summary": "Tourism and public interest in Baker Street",
                },
            ],
        ],
        "full_content_json": [
            '{\n    "title": "Peterson and the Missing Billycock",\n    "summary": "The community centers around Peterson, a commissionaire involved in a mystery concerning a lost hat and a goose. His actions are pivotal in the investigation led by Sherlock Holmes, connecting various entities such as the row, the billycock hat, and multiple newspapers where advertisements were placed.",\n    "findings": [\n        {\n            "summary": "Peterson\'s central role in the investigation",\n            "explanation": "Peterson is a key figure in the mystery involving the missing blue carbuncle, acting as a commissionaire who aids Sherlock Holmes. His involvement is crucial as he not only discovers the lost billycock hat but also plays a significant role in disseminating information related to the case. This highlights his importance in the narrative and the potential impact of his actions on the investigation\'s outcome. [Data: Entities (333); Relationships (521, 522)]"\n        },\n        {\n            "summary": "The significance of the row incident",\n            "explanation": "The row refers to the altercation that prompted Peterson\'s intervention, leading to the discovery of the hat. This incident is pivotal as it sets the stage for the entire investigation, illustrating how a seemingly minor event can have far-reaching consequences. The altercation not only affects Peterson but also ties into the larger mystery that Holmes is trying to solve. [Data: Entities (339); Relationships (521)]"\n        },\n        {\n            "summary": "The billycock hat as a central object",\n            "explanation": "The billycock hat is not just an accessory but a crucial piece of evidence in the investigation. Its discovery by Peterson links him directly to the case and raises questions about its owner, Henry Baker. The hat\'s significance is underscored by its role in the narrative, as it is the object around which the mystery revolves. [Data: Entities (340); Relationships (522)]"\n        },\n        {\n            "summary": "Media involvement through advertisements",\n            "explanation": "Peterson\'s task of placing advertisements in various evening papers, including the Globe, Star, Pall Mall, and others, indicates the media\'s role in the investigation. This outreach is essential for gathering information about the hat\'s owner and demonstrates how public engagement can influence the resolution of the case. The involvement of multiple newspapers suggests a broad interest in the mystery, which could amplify its impact on the community. [Data: Entities (355, 356, 357, 358, 359, 360, 361); Relationships (545, 546, 547, 548, 549, 550, 551)]"\n        }\n    ],\n    "rating": 6.5,\n    "rating_explanation": "The impact severity rating is moderate to high due to the potential implications of the investigation on public interest and media coverage.",\n    "extra_attributes": {}\n}',
            '{\n    "title": "Baker Street and Sherlock Holmes Community",\n    "summary": "The community centers around Baker Street, the iconic residence of Sherlock Holmes, and its connection to the London Underground. Baker Street serves as a significant landmark associated with the famous detective, while the Underground facilitates access to this notable location.",\n    "findings": [\n        {\n            "summary": "Baker Street as a cultural landmark",\n            "explanation": "Baker Street is not only the residence of Sherlock Holmes but also a symbol of his adventures and detective work. Its association with the fictional detective has made it a notable landmark in London, drawing interest from fans and tourists alike. The street\'s historical and cultural significance contributes to its status as a must-visit location, enhancing its impact on the community. [Data: Entities (4), Relationships (178)]"\n        },\n        {\n            "summary": "Sherlock Holmes\'s connection to Baker Street",\n            "explanation": "Sherlock Holmes is intrinsically linked to Baker Street, as it serves as his residence and the hub for his investigations. This relationship is central to the narrative of his character, making Baker Street a vital part of the Sherlock Holmes lore. The detective\'s activities at this location have become iconic, further solidifying the street\'s importance in popular culture. [Data: Entities (4), Relationships (178)]"\n        },\n        {\n            "summary": "The role of the Underground in accessing Baker Street",\n            "explanation": "The London Underground plays a crucial role in facilitating access to Baker Street, making it easier for visitors to reach this iconic location. The connection between the Underground and Baker Street enhances the street\'s accessibility, contributing to its popularity as a tourist destination. This relationship underscores the importance of public transportation in connecting significant cultural landmarks. [Data: Entities (548), Relationships (862)]"\n        },\n        {\n            "summary": "Baker Street\'s association with detective work",\n            "explanation": "Baker Street is synonymous with detective work, primarily due to its association with Sherlock Holmes. The street is where many of Holmes\'s investigations take place, making it a focal point for fans of detective fiction. This connection to crime-solving and mystery adds to the allure of Baker Street, attracting those interested in the genre and its history. [Data: Entities (4), Relationships (178)]"\n        },\n        {\n            "summary": "Tourism and public interest in Baker Street",\n            "explanation": "The combination of Baker Street\'s historical significance and its association with Sherlock Holmes has made it a popular tourist destination. Visitors often seek to explore the street and its surroundings, contributing to the local economy and cultural heritage. The public interest in this location highlights the impact of literary figures on real-world places and their ability to draw crowds. [Data: Entities (4), Relationships (178)]"\n        }\n    ],\n    "rating": 6.5,\n    "rating_explanation": "The impact severity rating is moderate due to the cultural significance of Baker Street and its association with Sherlock Holmes, which attracts considerable public interest.",\n    "extra_attributes": {}\n}',
        ],
        "period": ["2024-12-16", "2024-12-16"],
        "size": [10, 2],
    }
    return pd.DataFrame(data)


@pytest.fixture
def entity_embedding_fixture() -> pd.DataFrame:
    data = {
        "id": ["55536111-6a0d-464f-9b72-616ae5d86c2f", "c60946e6-e4ef-499e-b2f2-79aae5471f50"],
        "human_readable_id": [0, 1],
        "title": ["PROJECT GUTENBERG", "ARTHUR CONAN DOYLE"],
        "type": ["ORGANIZATION", "PERSON"],
        "description": [
            "Project Gutenberg is a non-profit digital library that offers free access to a vast collection of eBooks, primarily focusing on works that are in the public domain...",
            "Arthur Conan Doyle is the author of The Adventures of Sherlock Holmes, a famous detective fiction series.",
        ],
        "text_unit_ids": [
            [
                "678a629f6366c004a2f968c2e77c3d05806c71185826352a62f1dfe5a466d4cc8c189dc82b3a43074f9a05ece829f24caf3cbb43c9240ab89936b9d53cc20239",
                "3fcdaf5df6aed13d3916fbfd9c76d9959582122362d62b89079ba1375fea6cc2c4bc7e9acb66820c02e871edbce25acf82169c06599f7643f768f6ec5a79e3fa",
                "98ef7b7dcc2d8472b448144d01d3aae840e1da98dbed56540db3a85f579b04fe15fb9ef441bca80bdd274a369e906359626b32600f56c2697e1bc324367da570",
            ],
            [
                "678a629f6366c004a2f968c2e77c3d05806c71185826352a62f1dfe5a466d4cc8c189dc82b3a43074f9a05ece829f24caf3cbb43c9240ab89936b9d53cc20239"
            ],
        ],
    }
    return pd.DataFrame(data)


@pytest.fixture
def relationship_df_fixture() -> pd.DataFrame:
    data = {
        "id": ["00fc026b-236a-4428-b836-06f337e6a89f", "8887b459-34c8-45a1-b821-64a73f518fb6"],
        "human_readable_id": [0, 1],
        "source": ["PROJECT GUTENBERG", "ARTHUR CONAN DOYLE"],
        "target": ["ARTHUR CONAN DOYLE", "SHERLOCK HOLMES"],
        "description": [
            "Project Gutenberg offers free access to the works of Arthur Conan Doyle, including The Adventures of Sherlock Holmes.",
            "Arthur Conan Doyle created the character Sherlock Holmes, who is central to his detective stories.",
        ],
        "weight": [7.0, 10.0],
        "combined_degree": [13, 111],
        "text_unit_ids": [
            [
                "678a629f6366c004a2f968c2e77c3d05806c71185826352a62f1dfe5a466d4cc8c189dc82b3a43074f9a05ece829f24caf3cbb43c9240ab89936b9d53cc20239"
            ],
            [
                "678a629f6366c004a2f968c2e77c3d05806c71185826352a62f1dfe5a466d4cc8c189dc82b3a43074f9a05ece829f24caf3cbb43c9240ab89936b9d53cc20239"
            ],
        ],
    }
    return pd.DataFrame(data)


@pytest.fixture
def text_unit_df_fixture() -> pd.DataFrame:
    data = {
        "id": [
            "678a629f6366c004a2f968c2e77c3d05806c71185826352a62f1dfe5a466d4cc8c189dc82b3a43074f9a05ece829f24caf3cbb43c9240ab89936b9d53cc20239",
            "d4a92a978533a003d4141d5e1f7462af337c1ebc469fc51f1a38961998113dc1d720407d87ae927ab886682859b47a10d485a68ad59fe0895133e8aa1947bf6d",
        ],
        "human_readable_id": [1, 2],
        "text": [
            "The Project Gutenberg eBook of The Adventures of Sherlock Holmes\n    \nThis ebook is for the use of anyone anywhere in the United States and...",
            "Some other text",
        ],
        "n_tokens": [1200, 1200],
        "document_ids": [
            [
                "c91a6627b1ed0d98ab17595f3983d0659ada68f775a9bf2e1da51aa4c8db30702bda39467ad250ba75bdd6c2c323f4bd420dec1dc7907cdc3b4f3ebe77267e08"
            ],
            [
                "c91a6627b1ed0d98ab17595f3983d0659ada68f775a9bf2e1da51aa4c8db30702bda39467ad250ba75bdd6c2c323f4bd420dec1dc7907cdc3b4f3ebe77267e08"
            ],
        ],
        "entity_ids": [
            [
                "55536111-6a0d-464f-9b72-616ae5d86c2f",
                "c60946e6-e4ef-499e-b2f2-79aae5471f50",
                "0724d9bf-5dce-44e0-b093-80d4dd2d10a5",
                "4692443a-158e-4282-a981-c6e631bef664",
                "7fde2ab8-4b80-45ec-9646-cce36134edbe",
                "0519c76d-6e18-4f64-a764-054ef3d433ef",
                "01672ffb-2298-42cd-851e-b2388e317e88",
                "9dc699c9-20bb-4ec6-9288-96882c964576",
                "51574bd9-63d9-4f78-a988-acc3a0719a32",
                "0e78bf0e-4203-4214-9fa8-8e8458442b61",
                "a85078a5-59f7-4a53-a140-e35bd19c82af",
            ],
            [
                "3999222a-aa8a-4910-9cab-596497a7f1fd",
                "86af13ba-3d64-4cef-8511-66b2aaded82e",
                "6fa5215e-5bf8-4023-ba2a-214cfb351eec",
                "937cc7ae-3240-4c4b-ba79-0039205aceb5",
                "f9eac29f-c833-4895-8080-06cf5e714df3",
                "3529ae6b-bb10-4fe5-b241-571ddb1dfa55",
                "c5418966-2204-4278-ace9-8158fff5852a",
                "dde22643-6ac6-4156-ae41-0e841dc688db",
            ],
        ],
        "relationship_ids": [
            [
                "00fc026b-236a-4428-b836-06f337e6a89f",
                "8887b459-34c8-45a1-b821-64a73f518fb6",
                "4f557c1d-dc96-4dbd-9e4c-380955d567c5",
                "2a8843a2-2921-434b-80c2-d5082282e04b",
                "f0242e99-2a49-4813-a363-0c81ae5feaef",
                "7390d425-1908-4a33-8a35-2125e4848896",
                "6111ed8f-7121-49e6-aa9d-05f746bd0b2f",
                "64f93378-0696-4ccc-9877-c1b26482394a",
                "79088678-3cfb-4fd9-8a1e-06d4085da97f",
            ],
            [
                "a91785d7-ae05-4860-b46e-8a565aad7832",
                "ccb8a028-c870-4826-8f93-687aaa5ee23c",
                "4dd46459-f146-48a3-869a-374cfbcc6ec8",
                "489ca036-cc56-4fc5-a239-ece62b98fffb",
                "d0b5c31a-3af2-4ecc-a5b8-e0cba79f94a6",
                "14dfce40-9a4d-4e75-9b7a-eeb7b3c19d78",
                "d048efe6-d7a7-4505-af11-c4b3fc4e25e7",
            ],
        ],
    }
    return pd.DataFrame(data)
