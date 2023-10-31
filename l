[33mcommit 56944862721a67ec9fb4ba8886e15a6cee05f981[m[33m ([m[1;36mHEAD -> [m[1;32mmain[m[33m, [m[1;31morigin/main[m[33m, [m[1;31morigin/HEAD[m[33m)[m
Author: gagb <gagb@users.noreply.github.com>
Date:   Fri Oct 27 22:51:28 2023 -0700

    Update Installation.md (#456)
    
    * Update Installation.md
    
    Replace autogen->pyautogen in env setup to avoid confusion
    
    Related issue: #211
    
    * Update Installation.md
    
    Add deactivation instructions
    
    * Update website/docs/Installation.md
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    ---------
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit dd90756bdb05479cea035db718f6473ce3e1859f[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Fri Oct 27 17:24:04 2023 -0700

    bump version to 0.1.14 (#400)
    
    * bump version to 0.1.14
    
    * endpoint
    
    * test
    
    * test
    
    * add ipython to retrievechat dependency
    
    * constraints
    
    * target

[33mcommit 12150179fbfbbe8292af41dfb7df3c54f84664c1[m
Author: rajpal <codingdrone@gmail.com>
Date:   Fri Oct 27 19:06:06 2023 +0530

    spelling fix for Update math_user_proxy_agent.py (#431)
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 8c3401dd6af2c954dc2bbcee42493326885db885[m
Author: Yiran Wu <32823396+kevin666aa@users.noreply.github.com>
Date:   Fri Oct 27 08:57:35 2023 -0400

    Add token_count_util (#421)
    
    * add token_count_util
    
    * remove token_count from retrieval util
    
    * format
    
    * update dependency
    
    * update test

[33mcommit cde99e05c58166ac1fa4e27385222b3ecdda84c3[m
Author: Aaron <aaronlaptop12@hotmail.com>
Date:   Fri Oct 27 13:52:26 2023 +0100

    Update FAQ section in documentation (#390)
    
    * UPDATE - FAQ section in documentation
    
    * FIX - formatting test failure
    
    * FIX - added disclaimer
    
    * pre-commit
    
    * Update website/docs/FAQ.md
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update website/docs/FAQ.md
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update website/docs/FAQ.md
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * UPDATE - notebook and FAQ information for config_list_from_models
    
    ---------
    
    Co-authored-by: Ward <award40@LAMU0CLP74YXVX6.uhc.com>
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    Co-authored-by: Li Jiang <bnujli@gmail.com>

[33mcommit 37deabefcf567415564bf036e523d3b48f741f56[m
Author: Craig Presti <146438+craigomatic@users.noreply.github.com>
Date:   Fri Oct 27 23:19:41 2023 +1030

    Adds jupyter as a vscode extension, fix validation errors in devcontainer.json (#433)
    
    * Adds jupyter as a vscode extension, fix validation errors in vscode (see https://containers.dev/supporting#visual-studio-code)
    
    * Trim trailing whitespace
    
    * Add newline to end of file
    
    ---------
    
    Co-authored-by: Li Jiang <bnujli@gmail.com>

[33mcommit 09bf41a1ed189bc45a0be3c4b5498aba89a2d3ca[m
Author: Ricky Loynd <riloynd@microsoft.com>
Date:   Fri Oct 27 05:49:21 2023 -0700

    TeachableAgent blog post (#436)
    
    * Authors
    
    * initial checkin
    
    * completed blog post
    
    * trim trailing whitespace
    
    * date
    
    * Address reviewer feedback.

[33mcommit 27e619e46e3abac5ba6a025698137d9f635c4dd8[m
Author: Li Jiang <bnujli@gmail.com>
Date:   Fri Oct 27 10:52:38 2023 +0800

    [Blocking Issue] Add tests dependencies for qdrant and fix chromadb errors (#435)
    
    * Add tests dependencies for qdrant
    
    * Update chromadb API
    
    * Update chromadb API version
    
    * Fix typehint
    
    * Add py 3.9 condition
    
    * Fix client creation error

[33mcommit 50ac5476377c1b41330589a6cfc5c4e65b93079f[m
Author: Anush <anushshetty90@gmail.com>
Date:   Wed Oct 25 10:38:43 2023 +0530

    feat: Qdrant vector store support (#303)
    
    * feat: QdrantRetrieveUserProxyAgent
    
    * fix: QdrantRetrieveUserProxyAgent docstring
    
    * chore: batch of 500 all CPU cores
    
    * chore: conditional import for tests
    
    * chore: config parallel, batch 100
    
    * chore: collection creation params
    
    * chore: conditonal payload indexing
    fastembed import check
    
    * docs: notebook for QdrantRetrieveUserProxyAgent
    
    * docs: update docs link
    
    * docs: notebook examples update
    
    * chore: hnsw, payload index reference
    
    * docs: notebook docs_path update
    
    * Update test/agentchat/test_qdrant_retrievechat.py
    
    Co-authored-by: Li Jiang <bnujli@gmail.com>
    
    * chore: update notebook output
    
    * Fix format
    
    ---------
    
    Co-authored-by: Li Jiang <bnujli@gmail.com>

[33mcommit 80954e4b8d0752fd4772f339dee419fbf1debc6f[m
Author: Li Jiang <bnujli@gmail.com>
Date:   Wed Oct 25 00:09:25 2023 +0800

    Fix tmp dir not exists (#401)
    
    * Fix tmp dir not exists
    
    * Update tests to make it more clear
    
    * Add check if save path is not None

[33mcommit 3991f860e4b62b1848bf67ed810335be989d68bc[m
Author: Ragy Abraham <52903382+ragyabraham@users.noreply.github.com>
Date:   Wed Oct 25 00:29:14 2023 +1000

    using thread safe timeout to allow code execution to be compatible with multi-threading/multi-processing (#224)
    
    Co-authored-by: Li Jiang <lijiang1@microsoft.com>
    Co-authored-by: Victor Dibia <chuvidi2003@gmail.com>
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 99329457654675cac2baabec9035829d0a374eae[m
Author: Beibin Li <BeibinLi@users.noreply.github.com>
Date:   Mon Oct 23 22:26:41 2023 -0700

    Supporting MultiModal Models: an example with LLaVA Notebook (#286)
    
    * LMM notebook
    
    * Use "register_reply" instead.
    
    * Loop check LLaVA non-empty response
    
    * Run notebook
    
    * Make the llava_call function more flexible
    
    * Include API for LLaVA from Replicate
    
    * LLaVA data format update x2
    1. prompt formater function
    2. conversation format with SEP
    
    * Coding example added
    
    * Rename "ImageAgent" -> "LLaVAAgent"
    
    * Docstring and comments updates
    
    * Debug notebook: Remote LLaVA tested
    
    * Example 1: remove system message
    
    * MultimodalConversableAgent added
    
    * Add gpt4v_formatter
    
    * LLaVA: update example 1
    
    * LLaVA: Add link to "Table of Content"

[33mcommit 9ed6c8e5d0ccb052dc529e2d3e5675871c45049a[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Mon Oct 23 20:54:45 2023 -0700

    config list for test (#395)

[33mcommit f9acb69aeabee8516acd3743454ca99798765d0e[m
Author: Li Jiang <bnujli@gmail.com>
Date:   Tue Oct 24 06:28:38 2023 +0800

    Update docs in RetrieveChat notebook and Installation (#379)
    
    * Update comments to make it more clear
    
    * Update Installation

[33mcommit 6438625063b36b1940312e865775edb0890a2604[m
Author: Sheetali Maity <74114936+smty2018@users.noreply.github.com>
Date:   Mon Oct 23 21:46:53 2023 +0530

    Add link to OptiGuide #371 (#376)
    
    * OptiGuide Link
    
    * Update AutoGen-AgentChat.md
    
    * fixes

[33mcommit 6e74e2d51a23331d3d1055ec8480a25440975844[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Mon Oct 23 08:34:32 2023 -0700

    headsup about dependency change (#378)
    
    * headsup about dependency change
    
    * more change

[33mcommit a8da3854c00cf8a4517d2572668a8b45077c63bc[m
Author: Shruti Patel <shruti222patel@users.noreply.github.com>
Date:   Sun Oct 22 00:58:01 2023 -0400

    Update agentchat_langchain.ipynb (#355)
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit b43d2649cd9c5e7efb1773011dab7deb9877d8d5[m
Author: Shruti Patel <shruti222patel@users.noreply.github.com>
Date:   Sun Oct 22 00:57:57 2023 -0400

    Fix the grammar and spelling in agentchat_human_feedback.ipynb (#354)
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 22635af48248d5d9841d70851f87325c9bb1cf3b[m
Author: Shruti Patel <shruti222patel@users.noreply.github.com>
Date:   Sun Oct 22 00:56:53 2023 -0400

    Fix grammar and spelling in agentchat_planning.ipynb (#356)
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 4c8d4b0b53ec22c2d01aef65a54d73fd7a075e75[m
Author: Shruti Patel <shruti222patel@users.noreply.github.com>
Date:   Sun Oct 22 00:49:49 2023 -0400

    Fix grammar in agentchat_stream.ipynb (#357)
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 1c7fbe5acfd69f59b9294087aa8ade8523fec80f[m
Author: Shruti Patel <shruti222patel@users.noreply.github.com>
Date:   Sun Oct 22 00:46:07 2023 -0400

    Improve readability for agentchat_two_users.ipynb (#361)
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 5c2cd99ce84bbdd03dce664051258ad0fbe8076f[m
Author: Shruti Patel <shruti222patel@users.noreply.github.com>
Date:   Sun Oct 22 00:35:29 2023 -0400

    Fix grammar for agentchat_web_info.ipynb (#362)
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit a2aa9116474c723e88416ea66eb3287b8d7ae415[m
Author: Shruti Patel <shruti222patel@users.noreply.github.com>
Date:   Sun Oct 22 00:28:35 2023 -0400

    Improve readability in oai_completion.ipynb (#364)
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit da88d6379cfb50d772b51318ea43d7762ca9cbb2[m
Author: Shruti Patel <shruti222patel@users.noreply.github.com>
Date:   Sun Oct 22 00:20:04 2023 -0400

    Improve readability in oai_openai_utils.ipynb (#365)

[33mcommit c2e0ddf667078228a14b2216ae8c6c5142f133f3[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Sun Oct 22 00:08:59 2023 -0400

    format (#358)

[33mcommit 61ac64081f1de3cd051a7277c5ff916258b181ed[m
Author: Shruti Patel <shruti222patel@users.noreply.github.com>
Date:   Sat Oct 21 20:46:04 2023 -0400

    Improve readability in agentchat_groupchat_research.ipynb (#350)
    
    * Improve readability in agentchat_groupchat_research.ipynb
    
    * Undo updates to system message.

[33mcommit ec423ddf072a5a267a157db25095084d6ab62767[m
Author: Shruti Patel <shruti222patel@users.noreply.github.com>
Date:   Sat Oct 21 20:26:34 2023 -0400

    Improve readability for agentchat_function_call.ipynb (#347)

[33mcommit 15ff52a52cd8288fe2674a90168fd28462d05afa[m
Author: Shruti Patel <shruti222patel@users.noreply.github.com>
Date:   Sat Oct 21 20:22:25 2023 -0400

    Fix grammar and spelling in agentchat_chess.ipynb (#346)

[33mcommit ca2e0b889e13a13e3d4c4c737fc5899c4919ff62[m
Author: Shruti Patel <shruti222patel@users.noreply.github.com>
Date:   Sat Oct 21 19:56:46 2023 -0400

    Update agentchat_MathChat.ipynb (#341)

[33mcommit 58b8c52851e7c8f2f39f5ebc5f8a3642eeba6bbc[m
Author: Shruti Patel <shruti222patel@users.noreply.github.com>
Date:   Sat Oct 21 19:56:01 2023 -0400

    Update agentchat_auto_feedback_from_code_execution.ipynb (#342)
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit ec52087c95ee1252b9c9dd7a8b9cdf9fbaa53154[m
Author: Ansh Babbar <31804810+rabbabansh@users.noreply.github.com>
Date:   Sun Oct 22 04:30:50 2023 +0530

    Updating Examples to follow new categorical structure. #273 (#327)
    
    * Updating Examples to follow new categorical structure. #273
    
    Addressing the remaining task for #273, I have copied over the changes from /Usecases to /Examples to follow the new categorical example notebooks structure.
    
    * Add the new example notebook
    
    ---------
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit 5c4edcd8bc24ba4cb5c2eccead9241e685ff48d2[m
Author: Ishita Pathak <75848598+IshitaPathak@users.noreply.github.com>
Date:   Sun Oct 22 00:44:46 2023 +0530

    Update README.md (#321)
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit df4882524fcb79f0f6db1a472550c26c9759d992[m
Author: Sean Connelly <47223469+2good4hisowngood@users.noreply.github.com>
Date:   Sat Oct 21 14:46:14 2023 -0400

    Resolves Typo Correction #336 (#338)
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 15d85aa1ad5bc7746c270b1503a5ecc160440d9b[m
Author: Gourav <herculeswarrior.in@gmail.com>
Date:   Sat Oct 21 23:05:31 2023 +0530

    Added Roadmap to Getting-Started.md (#324)

[33mcommit fc59da5113896314af8173bbd60d516a145812e1[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Fri Oct 20 21:58:45 2023 -0700

    add downloads stats in readme (#334)

[33mcommit 176987f6e99dc5b7efe8eda444cda56c7dd132a1[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Fri Oct 20 21:58:27 2023 -0700

    bump version to 0.1.13 (#333)

[33mcommit d22b6b20064d645c3ebda724b136b1b7e0a6e01c[m
Author: Ricky Loynd <riloynd@microsoft.com>
Date:   Fri Oct 20 19:27:10 2023 -0700

    TeachableAgent (#278)
    
    * Initial commit.
    
    * Disable LLM response caching.
    
    * Add teachability option to setup.py
    
    * Modify test to use OAI_CONFIG_LIST as suggested in the docs.
    
    * Expand unit test.
    
    * Complete unit test.
    
    * Add filter_dict
    
    * details
    
    * AnalysisAgent
    
    * details
    
    * More documentation and debug output.
    
    * Support retrieval of any number of relevant memos, including zero.
    
    * More robust analysis separator.
    
    * cleanup
    
    * teach_config
    
    * refactoring
    
    * For robustness, allow more flexibility on memo storage and retrieval.
    
    * de-dupe the retrieved memos.
    
    * Simplify AnalysisAgent. The unit tests now pass with gpt-3.5
    
    * comments
    
    * Add a verbosity level to control analyzer messages.
    
    * refactoring
    
    * comments
    
    * Persist memory on disk.
    
    * cleanup
    
    * Use markdown to format retrieved memos.
    
    * Use markdown in TextAnalyzerAgent
    
    * Add another verbosity level.
    
    * clean up logging
    
    * notebook
    
    * minor edits
    
    * cleanup
    
    * linter fixes
    
    * Skip tests that fail to import openai
    
    * Address reviewer feedback.
    
    * lint
    
    * refactoring
    
    * Improve wording
    
    * Improve code coverage.
    
    * lint
    
    * Use llm_config to control caching.
    
    * lowercase notebook name
    
    * Sort out the parameters passed through to ConversableAgent, and supply full docstrings for the others.
    
    * lint
    
    * Allow TextAnalyzerAgent to be given a different llm_config than TeachableAgent.
    
    * documentation
    
    * Modifications to run openai workflow.
    
    * Test on just python 3.10.
    Replace agent with agent teachable_agent as recommended.
    
    * Test on python 3.9 instead of 3.10.
    
    * Remove space from name -> teachableagent
    
    ---------
    
    Co-authored-by: Li Jiang <bnujli@gmail.com>
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit b1e1f416b019aa6d80f6f915b2cd31c2a76bae62[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Fri Oct 20 16:50:18 2023 -0700

    guidance for contribution (#320)

[33mcommit 26ff2ce0c12126ccb4b08c768e2fca4b99f87d08[m
Author: Yiran Wu <32823396+kevin666aa@users.noreply.github.com>
Date:   Fri Oct 20 13:27:14 2023 -0400

    update oai models (#316)

[33mcommit a456b512d5a933ce9707ce51c465ea35a9dd180c[m
Author: Li Jiang <bnujli@gmail.com>
Date:   Fri Oct 20 10:23:29 2023 +0800

    Fix format and links in documentations (#310)
    
    * Fix format and links
    
    * Update title
    
    * Sync title
    
    * Add examples to installation

[33mcommit e20ecfd259cb28abdf5838d9269f575228baf3e9[m
Author: Haseeb Ansari <47222685+haseeb-xd@users.noreply.github.com>
Date:   Fri Oct 20 07:23:03 2023 +0500

    doc: Update FAQ.md (#282)
    
    Isssue #277

[33mcommit 67157ab44f049b6e309497c87aa02bc9c7a70a43[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Thu Oct 19 11:58:57 2023 -0700

    bump version to 0.1.12 (#301)
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit 4de81d02bbbb76f393013d0fe62f3e68c57811ad[m
Author: gagb <gagb@users.noreply.github.com>
Date:   Thu Oct 19 11:58:49 2023 -0700

    Update README.md with Roadmap. (#304)
    
    also removed ugly periods. fixes: https://github.com/microsoft/autogen/issues/289#issuecomment-1771140811
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit 749757aca3349b1240a4529d263eb5492063b4e3[m
Author: Li Jiang <bnujli@gmail.com>
Date:   Fri Oct 20 01:51:49 2023 +0800

    Update docs (#297)
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit af879bdcda9e040793e4dcd6531bb646cb5b9974[m
Author: Victor Dibia <chuvidi2003@gmail.com>
Date:   Thu Oct 19 08:54:54 2023 -0700

    Organize notebooks into logical groups #273 (#288)
    
    * Organize notebooks into logical groups #273
    
    * update multiagent group to mention >3 agents

[33mcommit 19835755207f5b1c5ab2959fb20d37358593eab3[m
Author: Surav Shrestha <148448735+suravkshrestha@users.noreply.github.com>
Date:   Thu Oct 19 21:16:24 2023 +0545

    fix typo in website/blog/2023-05-18-GPT-adaptive-humaneval/index.mdx (#299)
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit 8d4afe42635bf040ace461e0279d50e0ef768f30[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Thu Oct 19 07:43:36 2023 -0700

    function call filter in group chat (#294)
    
    * function call filter in group chat
    
    * find agents with function_map

[33mcommit bed85a332fc319244cff35022a1faaed1b8d8c95[m
Author: Li Jiang <bnujli@gmail.com>
Date:   Thu Oct 19 04:26:42 2023 +0800

    Add a blog for RAG agents (#284)
    
    * Init blog
    
    * Update blog
    
    * Add more contents
    
    * Restore notebook

[33mcommit 9e876abf235532e944a18637b10e23a66ca4bcf0[m
Author: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>
Date:   Wed Oct 18 12:47:21 2023 -0400

    Bump @babel/traverse from 7.20.1 to 7.23.2 in /website (#283)
    
    Bumps [@babel/traverse](https://github.com/babel/babel/tree/HEAD/packages/babel-traverse) from 7.20.1 to 7.23.2.
    - [Release notes](https://github.com/babel/babel/releases)
    - [Changelog](https://github.com/babel/babel/blob/main/CHANGELOG.md)
    - [Commits](https://github.com/babel/babel/commits/v7.23.2/packages/babel-traverse)
    
    ---
    updated-dependencies:
    - dependency-name: "@babel/traverse"
      dependency-type: indirect
    ...
    
    Signed-off-by: dependabot[bot] <support@github.com>
    Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

[33mcommit 47df9d53be9ba28da460c7344e3c8a37bdbbc24b[m
Author: Maxim Saplin <smaxmail@gmail.com>
Date:   Wed Oct 18 05:43:01 2023 +0300

    Update Getting-Started.md (#275)
    
    Co-authored-by: Li Jiang <bnujli@gmail.com>
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit 45677e3e085335cc3acadbf98df4847b98a2cc2f[m
Author: Ayush Kumar Pandit <31253617+Ayushpanditmoto@users.noreply.github.com>
Date:   Wed Oct 18 05:21:24 2023 +0530

    docs: added virtual environment setup process (#249)
    
    * docs: added virtual environment setup process
    
    * Update website/docs/Installation.md
    
    ---------
    
    Co-authored-by: Li Jiang <bnujli@gmail.com>
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 88ebb77048607eeb6d33e826ba2a2000c18a6f0a[m
Author: Li Jiang <bnujli@gmail.com>
Date:   Wed Oct 18 04:31:27 2023 +0800

    Add group chat and retrieve agent example (#227)
    
    * Add group chat and retrieve agent example
    
    * Fix link and models
    
    * Support call rag in a group chat and not init with rag
    
    * Fix n_results logic
    
    * Update notebook
    
    * Fix format
    
    * Improve wording
    
    * Update variable name
    
    * Revert to main
    
    * Update function call
    
    * Update keys
    
    * Update contents
    
    * Update contents

[33mcommit f594333f7238386ef2069cfb5e6c667c36d95170[m
Author: Maxim Saplin <smaxmail@gmail.com>
Date:   Tue Oct 17 17:57:31 2023 +0300

    Update FAQ.md, elaborate on how to customise docker image and pick 'python:3' to solve typical errors (#269)
    
    * Update FAQ.md
    
    * Update website/docs/FAQ.md
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>
    
    * Update website/docs/FAQ.md
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>
    
    * Update website/docs/FAQ.md
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>
    
    ---------
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit f2d7553cdcfed076a4dd793aec0ffd349b6fbdd0[m
Author: Li Jiang <bnujli@gmail.com>
Date:   Tue Oct 17 22:53:40 2023 +0800

    Add support to custom text spliter (#270)
    
    * Add support to custom text spliter function and a list of files or urls
    
    * Add parameter to retrieve_config, add tests
    
    * Fix tests
    
    * Fix tests

[33mcommit 294e006ac9a35975bce896b4a525c732f7aee159[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Mon Oct 16 16:23:27 2023 -0700

    Lancgain tool bridge (#262) (#263)
    
    * Added a LangChain tooling bridge example
    
    * Updated Doco
    
    * Update agentchat_langchain.ipynb
    
    remove key
    
    ---------
    
    Co-authored-by: Elliot Wood <gigaflare_elliot@hotmail.com>
    Co-authored-by: Li Jiang <lijiang1@microsoft.com>

[33mcommit 4fb2f1f449a23efe57e0a573cb592188123484c2[m
Author: Sheetali Maity <74114936+smty2018@users.noreply.github.com>
Date:   Mon Oct 16 22:50:53 2023 +0530

    Added figure to notebook (#246)
    
    Co-authored-by: Li Jiang <lijiang1@microsoft.com>

[33mcommit 356f6e599ffa6efb5bc6822733650d76778b12cd[m
Author: Olaoluwa Ademola Salami <olaoluwaasalami@gmail.com>
Date:   Mon Oct 16 17:41:51 2023 +0100

    document retrieve chat (#258)
    
    * document retrieve chat
    
    * Ran pre commit hook

[33mcommit ea8dec7ea967e7115986d4472a1b4eb7a6aa2edd[m
Author: Gourav <herculeswarrior.in@gmail.com>
Date:   Mon Oct 16 09:45:03 2023 +0530

     docstr updated for `use_docker` in `execute_code ` (#233)
    
    * docstr updated
    
    * fixed line 245
    
    * Fixed line 246
    
    * space_traling error Fix_01
    
    * Revert space in '-'
    
    * Fixed line 245 FIX_02
    
    ---------
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit 1394e293266b1833a3a72daf8f2e34b3cb538dfe[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sun Oct 15 08:01:05 2023 -0700

    bump version to 0.1.11 (#242)
    
    * bump version to 0.1.11
    
    * fix format issue

[33mcommit 6156faaa0a0495e0410e8e0d23d4410b6f772913[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Fri Oct 13 18:07:17 2023 -0400

    Typo (#234)
    
    * fix typo
    
    * wording
    
    * typo

[33mcommit c46f8e54f13f26c3d8313cf79b18c5d583e1c517[m
Author: Shruti Patel <shruti222patel@users.noreply.github.com>
Date:   Fri Oct 13 17:34:15 2023 -0400

    Spelling fixes. (#220)
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit e69916d445b81951b0185fbd01aec4394129a3ad[m
Author: Hitesh Bansal <83907989+05hiteshbansal@users.noreply.github.com>
Date:   Sat Oct 14 01:42:17 2023 +0530

    Update Installation.md-with detailed explanation on add a period or newline #219  (#231)
    
    * Update Installation.md
    
    Usage and importance of Docker is explained in more precise and to the point
    
    * Update website/docs/Installation.md
    
    ---------
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit 3eda9ed74d6f36a19f197702199fbceb51b1bf5e[m
Author: James Tsang <wtzeng1@gmail.com>
Date:   Fri Oct 13 14:46:50 2023 -0500

    fix: be compatible with custom model without full response (#222)
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit 04319c968a34a56f81bd8a0d047e41364010ee76[m
Author: Sheetali Maity <74114936+smty2018@users.noreply.github.com>
Date:   Fri Oct 13 21:19:47 2023 +0530

    Added comment about config_list in the README example #216 (#218)
    
    * Update README.md
    
    * Update README.md

[33mcommit fbf8faeac10cfcaf15761c3751a4387051590904[m
Author: Javid Jamae <javidjamae@gmail.com>
Date:   Thu Oct 12 11:06:31 2023 -0500

    Update Getting-Started.md (#213)
    
    Fixed minor typo
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit b61aeb6cce65ea45027c88669e8d3ff5e53148ff[m
Author: Yiran Wu <32823396+kevin666aa@users.noreply.github.com>
Date:   Thu Oct 12 10:31:52 2023 -0400

    Improving logging in oai.completion to show token_count (#179)
    
    * update
    
    * update doc
    
    ---------
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit 6b14bd6609a30c25b71c598e7a2f27152a200f77[m
Author: afourney <adamfo@microsoft.com>
Date:   Thu Oct 12 05:58:36 2023 -0700

    Addresses issue #199 (#200)
    
    * Addresses issue #199
    
    * Fixed comment to align with new behavior.
    
    ---------
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit 09854e4704c9c9270897bfcd2dccd1eda766d592[m
Author: Gaëtan H <gaetanhus@gmail.com>
Date:   Thu Oct 12 06:52:30 2023 +0200

    Icons not centered in the "autogen_agentchat.png" (#169)
    
    * Delete website/static/img/autogen_agentchat.png
    
    * Add files via upload

[33mcommit 98ca5bcc80417280266a24dfdf57bcf406e87634[m
Author: Deepanshu <91846266+creator0131@users.noreply.github.com>
Date:   Thu Oct 12 09:17:04 2023 +0530

    Fix typo in README.md (#193)

[33mcommit c7dd6ce1f783057a610f359b7770276963a6dc29[m
Author: gagb <gagb@users.noreply.github.com>
Date:   Wed Oct 11 20:27:55 2023 -0700

    Add md for faqs (#194)
    
    * Add md for faq; Update readme
    
    * Update TRANSPARENCY_FAQS.md
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update TRANSPARENCY_FAQS.md
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Remove trailing space
    
    * Fix trailing space issue
    
    ---------
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit d481aebb9bfcf677bf3a7038d88bb3df2109647b[m
Author: Manuel Saelices <msaelices@gmail.com>
Date:   Wed Oct 11 19:27:54 2023 +0200

    Fix edge cases extracting code when the message's content is None (#205)

[33mcommit 0a1214f875aedfc4ff1bc0c7cb690b32499e4f45[m
Author: wayliums <wayliums@users.noreply.github.com>
Date:   Tue Oct 10 18:20:04 2023 -0700

    Make getting started a little easier (#180)
    
    * Update README.md
    
    add codespace quick start
    
    * add codespace
    
    * update path
    
    ---------
    
    Co-authored-by: Li Jiang <lijiang1@microsoft.com>

[33mcommit 688cf44d0e2bae339a9753c261fc9eb6714a0c3a[m
Author: Ikko Eltociear Ashimine <eltociear@gmail.com>
Date:   Wed Oct 11 02:43:55 2023 +0900

    Fix typo in agentchat_MathChat.ipynb (#191)
    
    requries -> requires

[33mcommit fa6e2a52c00a28756b9cf30e85bc336d4c5da055[m
Author: Li Jiang <lijiang1@microsoft.com>
Date:   Tue Oct 10 20:53:18 2023 +0800

    Add support to customized vectordb and embedding functions (#161)
    
    * Add custom embedding function
    
    * Add support to custom vector db
    
    * Improve docstring
    
    * Improve docstring
    
    * Improve docstring
    
    * Add support to customized is_termination_msg fucntion
    
    * Add a test for customize vector db with lancedb
    
    * Fix tests
    
    * Add test for embedding_function
    
    * Update docstring

[33mcommit 37a07a83c3c3c938e54b837329c885d815d0cd0f[m
Author: Li Jiang <lijiang1@microsoft.com>
Date:   Tue Oct 10 13:21:56 2023 +0800

    Bump version to 0.1.10 (#181)

[33mcommit afdff3ea14c53b69253072258d96e49eacdbf263[m
Author: afourney <adamfo@microsoft.com>
Date:   Mon Oct 9 17:17:36 2023 -0700

    Warn if oai.Completion is provided with an empty config_list (#178)
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit 72239a6d5d00f4d0d94a337a966ee8cd2235ce80[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Mon Oct 9 17:08:08 2023 -0700

    bump version to 0.1.9 (#177)
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit 9571b7fbe753c91f4a7460d6a7c16ce13f33b98f[m
Author: afourney <adam.fourney@gmail.com>
Date:   Mon Oct 9 16:27:54 2023 -0700

    Display a warning if use_docker evlauates to True but the python docker package is not available. (#172)
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit 4522900487b65766d0f89dd30b10b6021b45e313[m
Author: afourney <adam.fourney@gmail.com>
Date:   Mon Oct 9 14:30:20 2023 -0700

    Warn if GroupChat is underpopulatd. (#170)

[33mcommit d8ebf6c8c63a48cd5046fd5918192c176248c81d[m
Author: afourney <adam.fourney@gmail.com>
Date:   Mon Oct 9 13:15:39 2023 -0700

    Output a warning if attempting to load the OAI_CONFIG_LIST from a file, but the file is not found. (#174)

[33mcommit fbe82da2085361bf13a4fb9f285b5f0428a110dc[m
Author: Allen Shi <33379392+AllenJShi@users.noreply.github.com>
Date:   Mon Oct 9 06:30:04 2023 -0400

    fix: replace gpt-35-turbo in model name to gpt-3.5-turbo so the name … (#138)
    
    * fix: replace gpt-35-turbo in model name to gpt-3.5-turbo so the name string is in the current chat_model list
    
    * ref: reformatted with black
    
    ---------
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit 71ac774cd0dcbee4314c6fe906c0adf0d09178ff[m
Author: Vidhula <58629266+vidhula17@users.noreply.github.com>
Date:   Mon Oct 9 15:43:25 2023 +0530

    Added twitter link to the contributing section (#162)
    
    Co-authored-by: vidhula17 <catchvidhula@gmail.com>

[33mcommit 95e4c5851547294e6ffb5b77239b3200e988d3fe[m
Author: Li Jiang <bnujli@gmail.com>
Date:   Mon Oct 9 11:50:29 2023 +0800

    Update termination logic (#155)

[33mcommit 46ab5b8c68330a81c4c567ba3f5de81b62f703ec[m
Author: Olaoluwa Ademola Salami <olaoluwaasalami@gmail.com>
Date:   Mon Oct 9 04:40:12 2023 +0100

    add twitter account to start page (#159)

[33mcommit 19f8711c1beccbff83da69bad581c4a7c4bdaaa8[m
Author: Li Jiang <bnujli@gmail.com>
Date:   Mon Oct 9 10:30:11 2023 +0800

    Update num tokens from text (#149)
    
    * Improve num_tokens_from_text
    
    * Format
    
    * Update comments
    
    * Improve docstrings

[33mcommit ae497a0323e592a080e67cf301866daffeb2ac9f[m
Author: Olaoluwa Ademola Salami <oyomafia@gmail.com>
Date:   Mon Oct 9 00:34:24 2023 +0100

    add twitter account to website (#150)
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 24adfb0c05922a7033bf8c405f0d9964d68c4fa7[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Sun Oct 8 12:20:55 2023 -0400

    bump version to 0.1.8

[33mcommit 50d6d9e0b8fc74ee022a1b98d20c07fa3882687a[m
Author: Manish Kumar <51908018+manish7017@users.noreply.github.com>
Date:   Sun Oct 8 20:15:54 2023 +0530

    move citation before contributing (#154)

[33mcommit 5ff85a3febe2ecdd494fe3c6e788fff3ab4371ba[m
Author: mrauter1 <marcelorauter@gmail.com>
Date:   Sat Oct 7 10:29:52 2023 -0300

    Title: Adjust shell language switch in execute_code for Docker usage (#139)
    
    Description:
    This commit modifies the conditional check in execute_code to ensure the switch to PowerShell on Windows only occurs when Docker is not being used. This keeps shell script execution consistent within a Docker container across all platforms, aligning with the function's intended behavior.
    
    Co-authored-by: Xiaoyun Zhang <bigmiao.zhang@gmail.com>

[33mcommit 5510e87c0a5386976e558d78f5bfeabd1dab4de4[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Oct 7 02:18:04 2023 -0700

    bump version to 0.1.7 (#141)

[33mcommit 09c9dbe944e9a353e6666df96ebb5e2ae79f6817[m
Author: Sagar Desai <60027013+SDcodehub@users.noreply.github.com>
Date:   Sat Oct 7 10:05:48 2023 +0530

    typo fixed (#127)
    
    Co-authored-by: Sagar Desai <60027013+sagardesai-ml-mlops@users.noreply.github.com>
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit f863e97b94b3057a6ad7153933945364363291e8[m
Author: Tristan Murphy <72839119+HyperCodec@users.noreply.github.com>
Date:   Sat Oct 7 00:32:05 2023 -0400

    fix doc typo (#123)
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit a087347d1942124ff9a8d0c4e590a55adaed9ddc[m
Author: Hyung-Taik Choi <htc.refactor@gmail.com>
Date:   Sat Oct 7 13:16:29 2023 +0900

    Fix broken link in README.md (#134)
    
    The link to the documentation's FAQ#code-execution was broken because the 'docs' directory was missing in the original URL.
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit 62b635729451f5dcb372cb79df413f0d53be1379[m
Author: lars.gersmann <lars.gersmann@gmail.com>
Date:   Sat Oct 7 06:04:22 2023 +0200

    docs: typo fixed (#129)

[33mcommit 20d77a1039a167139da60e0eed4713039de76956[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Thu Oct 5 12:48:24 2023 -0700

    document about docker (#119)
    
    * document about docker
    
    * clarify
    
    * dev container

[33mcommit 5c2a268d95e08e3203f6dfa72f5c9b51b972dd10[m
Author: Aaron <aaronlaptop12@hotmail.com>
Date:   Thu Oct 5 05:45:11 2023 +0100

    openai_utils.py - functionality for instantiating config_list with a .env file (#68)
    
    * FORMATTING
    
    * UPDATE - OAI __init__.py
    
    * ruff
    
    * ADD - notebook covering oai API configuration options and their different purposes
    
    * ADD openai util updates so that the function just assumes the same environment variable name for all models, also added functionality for adding API configurations like api_base etc.
    
    * ADD - updates to config_list_from_dotenv and tests for openai_util testing, update example notebook
    
    * UPDATE - added working config_list_from_dotenv() with passing tests, and updated notebook
    
    * UPDATE - code and tests to potentially get around the window build permission error, used different method of producing temporary files
    
    ---------
    
    Co-authored-by: Ward <award40@LAMU0CLP74YXVX6.uhc.com>

[33mcommit dc70b804ad6bcb74be5d02a806a53c990dc8fee8[m
Author: Ujjwal gupta <guptarickey3@gmail.com>
Date:   Wed Oct 4 05:20:42 2023 +0530

    Docs: fixed typos and grammar (#94)

[33mcommit 305dffebca98de70afa936b03e612480b640feb3[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Oct 3 16:45:55 2023 -0700

    show github stars (#92)

[33mcommit 6ef012425167f601f001f393134a552a742e9f5b[m
Author: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>
Date:   Tue Oct 3 16:43:26 2023 -0700

    Bump postcss from 8.4.18 to 8.4.31 in /website (#93)
    
    Bumps [postcss](https://github.com/postcss/postcss) from 8.4.18 to 8.4.31.
    - [Release notes](https://github.com/postcss/postcss/releases)
    - [Changelog](https://github.com/postcss/postcss/blob/main/CHANGELOG.md)
    - [Commits](https://github.com/postcss/postcss/compare/8.4.18...8.4.31)
    
    ---
    updated-dependencies:
    - dependency-name: postcss
      dependency-type: indirect
    ...
    
    Signed-off-by: dependabot[bot] <support@github.com>
    Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

[33mcommit a3547f82c4eb17bdc0da47a2f6a80f89b8df2dd4[m
Author: Mohamed Attia <mu.attiyah@gmail.com>
Date:   Tue Oct 3 19:52:50 2023 +0200

    Replace the use of `assert` in non-test code (#80)
    
    * Replace `assert`s in the `conversable_agent` module with `if-log-raise`.
    
    * Use a `logger` object in the `code_utils` module.
    
    * Replace use of `assert` with `if-log-raise` in the `code_utils` module.
    
    * Replace use of `assert` in the `math_utils` module with `if-not-raise`.
    
    * Replace `assert` with `if` in the `oai.completion` module.
    
    * Replace `assert` in the `retrieve_utils` module with an if statement.
    
    * Add missing `not`.
    
    * Blacken `completion.py`.
    
    * Test `generate_reply` and `a_generate_reply` raise an assertion error
    when there are neither `messages` nor a `sender`.
    
    * Test `execute_code` raises an `AssertionError` when neither code nor
    filename is provided.
    
    * Test `split_text_to_chunks` raises when passed an invalid chunk mode.
    
    * * Add `tiktoken` and `chromadb` to test dependencies as they're used in
    the `test_retrieve_utils` module.
    
    * Sort the test requirements alphabetically.

[33mcommit 39c145dd53d3f631b4b04493daa31e489cb5295d[m
Author: Al-Ekram Elahee Hridoy <aliqramalaheehridoy@gmail.com>
Date:   Mon Oct 2 20:36:23 2023 -0600

    Format issue (#69)
    
    * Fixed formating issue in the README
    
    * Fixed the formating issue in the README
    
    * Updated formatting as per review comments
    
    * Refactor README.md to highlight use cases and features
    
    * Updated README as per feedback
    
    * Updated README as per feedback
    
    ---------
    
    Co-authored-by: Al-Iqram Elahee <hridoy@Al-Iqrams-MacBook-Pro.local>
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit 1131943a5d39455f007c01377af8d22fc0181ceb[m
Author: Shaurya Rohatgi <shauryr@gmail.com>
Date:   Mon Oct 2 21:32:13 2023 -0500

    spelling error (#84)

[33mcommit 50cb53cfe66c8445063f830b4f0ab7656b998a06[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Mon Oct 2 19:16:30 2023 -0700

    bump version to 0.1.6 (#85)

[33mcommit 3b5e6277466dc25cd468a7f7e5d00a63c794b85c[m
Author: Xiaoyun Zhang <bigmiao.zhang@gmail.com>
Date:   Mon Oct 2 12:46:46 2023 -0700

    enable openai workflow on fork branch (#82)
    
    * update
    
    * update
    
    * Update openai.yml

[33mcommit 4d85f4db0aeccb1f2cc89f39b248b882e0b86c4e[m
Author: Yiran Wu <32823396+kevin666aa@users.noreply.github.com>
Date:   Mon Oct 2 14:52:38 2023 -0400

    fix append_oai_message (#47)
    
    * fix append_oai_message
    
    * add testcase for groupchat
    
    * add test_oai to openai workflow
    
    * code formate
    
    * update
    
    * formate
    
    * update

[33mcommit 0481483faa03b337faaa4e8c7b3b4a9d51e7db29[m
Author: Hiftie <127197446+hiftielabs@users.noreply.github.com>
Date:   Mon Oct 2 18:31:14 2023 +0530

    Fixed MD Issue (#72)

[33mcommit b642f69005121301d715c1d8bd28a3b1c5f6425e[m
Author: Xiaoyun Zhang <bigmiao.zhang@gmail.com>
Date:   Mon Oct 2 05:15:25 2023 -0700

    minor fix (#31)
    
    * minor fix for stablility
    
    * fix format
    
    * fix format
    
    * update run_code logic
    
    * format
    
    * Update conversable_agent.py
    
    * fix format
    
    * Update conversable_agent.py
    
    * add tests
    
    * fix format
    
    * revert changes

[33mcommit 49ad771052a027e731137cd8e1b33b100000261d[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sun Oct 1 18:34:59 2023 -0700

    expand faq (#66)
    
    * expand faq
    
    * models
    
    * fix format error

[33mcommit bf65b59b7986cf16caa80b1f7f70f5956e097745[m
Author: Priyanshu Yashwant Deshmukh <69320370+priyansh4320@users.noreply.github.com>
Date:   Mon Oct 2 02:48:55 2023 +0530

    Updated readme.md : seprated AutoGen and EcoOptGen also removed bibtex (#43)
    
    * Updated README.md added required changes to previous pull
    
    new changes :
    1. A section containing citation to AutoGen and EcoOptiGen
    2. Another section contain citation to MathChat
    ## Citation
    [AutoGen](https://arxiv.org/abs/2308.08155).
    AND  [EcoOptiGen](https://arxiv.org/abs/2303.04673).
    ```
    bibtex
    @inproceedings{wu2023autogen,
          title={AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation Framework},
          author={Qingyun Wu and Gagan Bansal and Jieyu Zhang and Yiran Wu and Shaokun Zhang and Erkang Zhu and Beibin Li and Li Jiang and Xiaoyun Zhang and Chi Wang},
          year={2023},
          eprint={2308.08155},
          archivePrefix={arXiv},
          primaryClass={cs.AI}
    }
    
    bibtex
    @inproceedings{wang2023EcoOptiGen,
        title={Cost-Effective Hyperparameter Optimization for Large Language Model Generation Inference},
        author={Chi Wang and Susan Xueqing Liu and Ahmed H. Awadallah},
        year={2023},
        booktitle={AutoML'23},
    }
    ```
    
     [MathChat](https://arxiv.org/abs/2306.01337).
    
    ```
    bibtex
    @inproceedings{wu2023empirical,
        title={An Empirical Study on Challenging Math Problem Solving with GPT-4},
        author={Yiran Wu and Feiran Jia and Shaokun Zhang and Hangyu Li and Erkang Zhu and Yue Wang and Yin Tat Lee and Richard Peng and Qingyun Wu and Chi Wang},
        year={2023},
        booktitle={ArXiv preprint arXiv:2306.01337},
    }
    ```
    
    * Seperated AutoGen and EcoOptGen and removed 'bibtex'
    
    ## Citation
    [AutoGen](https://arxiv.org/abs/2308.08155).
    ```
    @inproceedings{wu2023autogen,
          title={AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation Framework},
          author={Qingyun Wu and Gagan Bansal and Jieyu Zhang and Yiran Wu and Shaokun Zhang and Erkang Zhu and Beibin Li and Li Jiang and Xiaoyun Zhang and Chi Wang},
          year={2023},
          eprint={2308.08155},
          archivePrefix={arXiv},
          primaryClass={cs.AI}
    }
    ```
    
    [EcoOptiGen](https://arxiv.org/abs/2303.04673).
    ```
    @inproceedings{wang2023EcoOptiGen,
        title={Cost-Effective Hyperparameter Optimization for Large Language Model Generation Inference},
        author={Chi Wang and Susan Xueqing Liu and Ahmed H. Awadallah},
        year={2023},
        booktitle={AutoML'23},
    }
    ```

[33mcommit c39bfcaa6ed283e84b017cdeaa947f4eedff0023[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sun Oct 1 04:57:21 2023 -0700

    typing & docstr update (#59)
    
    * typing & docstr update
    
    * bump version to 0.1.5

[33mcommit e4eb7aed97dddbe7cfae87b770441da56955f2ac[m
Author: Li Jiang <bnujli@gmail.com>
Date:   Sun Oct 1 19:56:49 2023 +0800

    Bump version to 0.1.5 (#60)

[33mcommit 4adbffa94be0c1984f0ab76c0dbe854004dc04b9[m
Author: Aaron <aaronlaptop12@hotmail.com>
Date:   Sun Oct 1 11:22:58 2023 +0100

    retrieve_utils.py - Updated.py to have the ability to parse text from PDF Files (#50)
    
    * UPDATE - Updated retrieve_utils.py to have the ability to parse text from pdf files
    
    * UNDO - change to recursive condition
    
    * UPDATE - updated agentchat_RetrieveChat.ipynb to clarify which file types are accepted to be in the docs path
    
    * ADD - missing import
    
    * UPDATE - setup.py to have PyPDF2 in retrievechat
    
    * RE-ADD - urls
    
    * ADD - tests for retrieve utils, and removed deprecated PyPdf2
    
    * Update agentchat_RetrieveChat.ipynb
    
    * Update retrieve_utils.py
    
    Fix format
    
    * Update retrieve_utils.py
    
    Replace print with logger
    
    * UPDATE - added more specific exception to PDF decryption try/catch
    
    * FIX - typo, return statement at wrong indentation in extract_text_from_pdf
    
    ---------
    
    Co-authored-by: Ward <award40@LAMU0CLP74YXVX6.uhc.com>
    Co-authored-by: Li Jiang <bnujli@gmail.com>

[33mcommit 7112da6b7a07f4d001ef4ba90faa65f0ff9cca5b[m
Author: Ali Eren SALKIM <129160641+AlyrenN@users.noreply.github.com>
Date:   Sun Oct 1 05:17:58 2023 +0300

    Update README.md (#54)
    
    README update for my profile <3

[33mcommit b06919bb76e73ecb9ca3c8724328a535051f5b20[m
Author: Li Jiang <bnujli@gmail.com>
Date:   Sun Oct 1 10:00:00 2023 +0800

    Update no_update_context, fix upsert docs (#52)
    
    * Update no_update_context, fix upsert docs
    
    * Recreate only once
    
    * Add comments to get_or_create
    
    ---------
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 904b293aa47c0e87e27e127254ce4f17a391048c[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Sep 30 09:21:07 2023 -0700

    make retry_time configurable, add doc (#53)
    
    * make retry_time configurable, add doc
    
    * in seconds
    
    * retry_wait_time
    
    * bump version to 0.1.4
    
    * remove .json
    
    * rename
    
    * time

[33mcommit d802b7ae0409fae9ed611ffb52d38b8349e34456[m
Author: Juanma Cuevas <jumacuca@gmail.com>
Date:   Fri Sep 29 19:59:30 2023 +0200

    Improves clarity and fixes punctuation in README and Multi-agent documentation (#40)
    
    * Improves clarity and fixes punctuation in README and Multi-agent documentation
    
    * fix broken colab link to agentchat_groupchat_research.ipynb (others are fine)
    
    * fix typos, improves readability

[33mcommit 5550803ed68fb46324b0526bc3b76640869d201e[m
Author: Ikko Eltociear Ashimine <eltociear@gmail.com>
Date:   Fri Sep 29 05:18:57 2023 +0900

    Fix typo in README.md (#37)
    
    functionalites -> functionalities

[33mcommit 402c5bf8d1761d4cdac87eaf2faafce2a4943865[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Thu Sep 28 13:14:36 2023 -0700

    Fix bug for windows and improve sample code (#38)
    
    * fix bug for windows
    
    * fix bug for windows
    
    * more clear example
    
    * link to example
    
    * add test
    
    * format
    
    * comment
    
    * fix assertion error
    
    * fix test error and links
    
    ---------
    
    Co-authored-by: Chi Wang (MSR) <chiw@microsoft.com>

[33mcommit d3d5dca15973127c29097d29629d1e4fdfb55e7d[m
Author: Danizord <daniel@gimenes.dev>
Date:   Thu Sep 28 11:54:15 2023 -0300

    Remove duplicated sentence (#35)

[33mcommit 0dff1237c17505d9d072940a500f3e93c515e60e[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Wed Sep 27 21:14:21 2023 +0000

    cleanup

[33mcommit e549fc4f80fc3cc649c0741c4ac2db28e984a68c[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Wed Sep 27 21:01:09 2023 +0000

    cleanup

[33mcommit 38639fcf12df303884019e9e1d03e99e84f8406a[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Wed Sep 27 17:54:32 2023 +0000

    cleanup

[33mcommit 5c86bfaf359de215e061273acd8982346c4e8395[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Wed Sep 27 17:43:27 2023 +0000

    cleanup

[33mcommit 8fbfa8b1c2b77127ab09b581e9b3be772a4f8e10[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Wed Sep 27 17:00:53 2023 +0000

    cleanup

[33mcommit ddf10044a1184153e532e9a7ef7129a647ffdde7[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Wed Sep 27 16:29:12 2023 +0000

    cleanup

[33mcommit eef911d39ba8b8fb0de641d6342bb159793bbfb3[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Wed Sep 27 12:57:39 2023 +0000

    cleanup

[33mcommit 8e9cda716ec741ddcfcc0f552e7bb09ee2e21f57[m
Merge: 0dca217 1108818
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Wed Sep 27 04:22:54 2023 +0000

    Merge branch 'main' of https://github.com/microsoft/autogen

[33mcommit 0dca217f4d7dcdeea30f8d2e45f9d0886833f11c[m
Merge: 5d209d0 9f3af1e
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Wed Sep 27 04:20:37 2023 +0000

    Merge branch 'cleanup'

[33mcommit 9f3af1ef802d27d193cca3ba431ea4ab0068c452[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Wed Sep 27 04:20:22 2023 +0000

    cleanup

[33mcommit 11088181b631330dfaa58ac638621f621b6079fd[m
Author: Li Jiang <bnujli@gmail.com>
Date:   Wed Sep 27 09:22:50 2023 +0800

    Improve RetrieveChat (#6)
    
    * Upsert in batch
    
    * Improve update context, support customized answer prefix
    
    * Update tests
    
    * Update intermediate answer
    
    * Fix duplicate intermediate answer, add example 6 to notebook
    
    * Add notebook results
    
    * Works better without intermediate answers in the context
    
    * Bump version to 0.1.2
    
    * Remove commented code and add descriptions to _generate_retrieve_user_reply
    
    ---------
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit f619eccda3fe7cd0c72c14365f18b41636ed2816[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Tue Sep 26 14:32:50 2023 -0400

    update link (#20)

[33mcommit 5d209d0f7d56824e21ecdf4a654f122772f83e83[m
Merge: 2eddcf8 23ceac0
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Mon Sep 25 21:42:33 2023 +0000

    Merge branch 'cleanup'

[33mcommit 23ceac0fe0d43c6ff2e7e5fec6d9f7db1fe07b3f[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Mon Sep 25 21:42:24 2023 +0000

    cleanup

[33mcommit 2eddcf80df13fbd4c979e1aff955281990224646[m
Merge: 3627ca4 552c30f
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Sep 23 22:07:03 2023 +0000

    Merge branch 'cleanup'

[33mcommit 552c30f4c05c066694b4903b8c992bdb6ec202e8[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Sep 23 22:06:52 2023 +0000

    cleanup

[33mcommit 3627ca4f2c77795e36cd903896b8a9bc1040a819[m
Author: Beibin Li <BeibinLi@users.noreply.github.com>
Date:   Thu Sep 21 09:50:44 2023 -0700

    Extact_code can detect single-line code now (#2)
    
    * Extact_code can detect single-line code now
    
    * Add comments for RE
    
    * Add test case and adjust UNKNOWN behavior
    
    * Remove tmp test files
    
    * Update autogen/code_utils.py
    
    ---------
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 8a43c3bab11e89922ae59b394cd84bdcf0cc91ac[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Thu Sep 21 15:58:42 2023 +0000

    cleanup

[33mcommit efa8213d9d555cf6943ea34ebf7b572fa21caa32[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Thu Sep 21 15:40:14 2023 +0000

    cleanup

[33mcommit 23633ae744f2dd39f765279dd9d3ece805bcdf40[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Thu Sep 21 15:39:52 2023 +0000

    cleanup

[33mcommit 7dd9831857226b50d1dfb5db96616938e4a3dad2[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Thu Sep 21 15:20:10 2023 +0000

    cleanup

[33mcommit c8cdb2a75248fd752fa6407f0f48a35105ee1ca8[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Thu Sep 21 15:19:06 2023 +0000

    cleanup

[33mcommit 6f54631707875dff1ce2b573b5afc6cb380222b6[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Thu Sep 21 02:48:20 2023 +0000

    cleanup

[33mcommit 0a1f8a1e61011a4f7881690c0b10a040ee1acf0a[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Thu Sep 21 02:42:38 2023 +0000

    cleanup

[33mcommit 0fbf1a0b4626c582f60a7573dae1fd2549423dbf[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Thu Sep 21 02:30:53 2023 +0000

    cleanup

[33mcommit cf4d46f31d8caf28267ed3807c3eb7183074a5e6[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Sep 19 20:34:01 2023 +0000

    cleanup

[33mcommit 012faa60e2934b8a999649d1e4a7f63cfeca258b[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Sep 19 18:26:50 2023 +0000

    cleanup

[33mcommit a3efd9cecd405920b7325a05231c61ff839cd80c[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Sep 19 18:14:54 2023 +0000

    cleanup

[33mcommit b6ef985d4fbc0a4dfff3ba2300d237dc0196ec5d[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Sep 19 17:50:43 2023 +0000

    cleanup

[33mcommit b2cbf508fbda806ff8863857231122a0935a2fe2[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Sep 19 15:29:30 2023 +0000

    cleanup

[33mcommit 255ac0ea2f5f2f65cf026bd3cff41da6c2fb3886[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Sep 19 14:26:38 2023 +0000

    cleanup

[33mcommit abf886d4486ed0241cf41f6b7da402ec574b83e5[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Sep 19 14:24:18 2023 +0000

    cleanup

[33mcommit eb7b26a8ec6851562fb3c6c3d09ea08dfcf965cc[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Sep 19 14:21:04 2023 +0000

    cleanup

[33mcommit 41074d127fd1391ee268269420ffbf051cd10c71[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Sep 19 13:52:31 2023 +0000

    cleanup

[33mcommit a75225919287b339a3ef8c0529cb76189f0d9017[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Sep 19 13:44:41 2023 +0000

    cleanup

[33mcommit 804472519dc8b8c259a903f89cdcf7327d3d5e7b[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Sep 19 13:29:52 2023 +0000

    cleanup

[33mcommit 7647fca5e998e166b76dd5e1e87c188f22116ad4[m
Merge: 3f44a3a 4c4f622
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Sep 19 06:14:32 2023 -0700

    Merge pull request #1 from microsoft/add_links_retrievechat
    
    Add links to RetrieveChat notebook

[33mcommit 3f44a3a1576439f9eb9cf10d9d1d68e047d8d73f[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Sep 19 13:09:57 2023 +0000

    cleanup

[33mcommit 4c4f622d731274418f28378519cdc0f6abedf935[m
Author: Li Jiang <bnujli@gmail.com>
Date:   Tue Sep 19 20:58:08 2023 +0800

    Add links to RetrieveChat notebook

[33mcommit c42b68b889446d5e753afef5150a78d990c39c54[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Sep 19 12:44:59 2023 +0000

    cleanup

[33mcommit 5be9e6700a7aac3cafbfbc979f365828e1bee1c1[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Sep 19 12:38:26 2023 +0000

    cleanup

[33mcommit 1048dae60257fb0949ca2ff51d5daabdf453a9c3[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Sep 19 12:22:09 2023 +0000

    cleanup

[33mcommit 3a5bea95a947e638769003acc478350fc8055ff7[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Sep 19 12:21:07 2023 +0000

    cleanup

[33mcommit ec85b4984d86e3fe667f387e1878c2bb9f8b22c8[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Sep 19 02:26:57 2023 +0000

    cleanup

[33mcommit 1e4781acd25637e9b7cebe3737208c4588388109[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sun Sep 17 21:04:04 2023 +0000

    cleanup

[33mcommit bc5e91e5aa2de3ffb0c24e9e164f0a846630ac6a[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sun Sep 17 20:18:13 2023 +0000

    cleanup

[33mcommit 188ddc19a53853780c42eb198834032c209ae1f6[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Sep 16 21:11:42 2023 +0000

    cleanup

[33mcommit 836a771ee74739567df656efbd6f3919900ccce7[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Sep 16 21:06:05 2023 +0000

    cleanup

[33mcommit 78b79aa03692da5de6a298ee1f251de3f1ea083a[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Sep 16 20:58:17 2023 +0000

    cleanup

[33mcommit 0c60bc51118d8978308ee37b0a61638f582e35a7[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Sep 16 20:41:27 2023 +0000

    cleanup

[33mcommit 45ddfa2dd01065c2c49e3b25b0835bfcf004ff94[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Sep 16 19:03:53 2023 +0000

    cleanup

[33mcommit 1517105c3aa2db2a0c1e180c18f7c29aa40aacdc[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Sep 16 16:41:15 2023 +0000

    cleanup

[33mcommit a4b9297719e19c27c8f7043b834db2847d5e9d2f[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Sep 16 16:34:16 2023 +0000

    cleanup

[33mcommit 99f2f82fa36f2744c89bbbec9ca7890fe36fe8eb[m
Merge: 812db59 3bfc5f2
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Sep 16 16:34:04 2023 +0000

    Merge remote-tracking branch 'upstream/autogen-links' into code

[33mcommit 812db59d33acc23da78cc64be322d3840be99e67[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Sep 16 15:30:28 2023 +0000

    cleanup

[33mcommit bc4473fe8a392198ab631bd7242efb99f60d7155[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Sep 16 10:57:57 2023 +0000

    cleanup

[33mcommit 4f8e30786c7dac03c552d1618e023f6409457e9c[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Sep 16 10:15:41 2023 +0000

    restore license

[33mcommit 4685f27d02ec765cfee6f0685acf11eccb6966b5[m
Merge: 95db977 4886cb5
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Sep 16 10:13:38 2023 +0000

    Merge remote-tracking branch 'upstream/main' into code

[33mcommit 4886cb56891af6ccf3e6d694bd97f571623fa6f8[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Mon Sep 11 17:07:35 2023 -0700

    Rename Responsive -> Conversable (#1202)
    
    * responsive -> conversable
    
    * preview
    
    * rename
    
    * register reply
    
    * rename and version
    
    * bump version to 2.1.0
    
    * notebook
    
    * bug fix

[33mcommit 95db977718f9a5a8bf7958bd64ce80fdc13de3e6[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Mon Sep 11 10:35:46 2023 -0400

    update fig

[33mcommit 599731cb22ad1515f8d29995e5fb8cbbd953804f[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Mon Sep 11 07:33:47 2023 -0700

    rename human to user_proxy (#1215)
    
    * rename human to user_proxy
    
    * notebook update and bug fix

[33mcommit 9233bf077f26c9213cef2db88072de725ee3ef30[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Mon Sep 11 10:30:24 2023 -0400

    reply func renaming

[33mcommit 409fec0dfb3732099411525104731b329d91e784[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Mon Sep 11 09:50:07 2023 -0400

    agent renaming

[33mcommit 3bfc5f21d216440f019441d66fc7e072dc59437f[m
Merge: 2f814e2 0cb79df
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Mon Sep 11 09:39:55 2023 -0400

    Merge remote-tracking branch 'origin/main' into autogen-links

[33mcommit 0cb79dfdffbbbddccfb1220ca9b6f5563e8402bb[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sun Sep 10 16:20:45 2023 -0700

    group chat for visualization (#1213)
    
    * group chat for visualization
    
    * show figure
    
    * webpage update
    
    * link update
    
    * example 2
    
    * example 2
    
    ---------
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit 90e086a5a6715d55a4e28d08a3dcebf4b84e61b7[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Sun Sep 10 16:09:14 2023 -0400

    update group chat links

[33mcommit 2f814e2b3fe7afa3e582e3d80508c4afb5cbc9b8[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Sat Sep 9 12:12:39 2023 -0400

    wording

[33mcommit 82ac1a1d3ac65e0cdc52ef1a9810212d1daa396a[m
Merge: fe38fae f70df31
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Sat Sep 9 12:10:08 2023 -0400

    Merge remote-tracking branch 'origin/main' into autogen-links

[33mcommit f70df312f442cad2cd4696956fc97868c5650046[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Fri Sep 8 20:08:24 2023 -0400

    Migration headsup (#1204)
    
    * add readme
    
    * migration headsup
    
    * remove move date
    
    * Update README.md
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    ---------
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit fe38faeec2359b0cbb9d9a86d58363f1e39bfe07[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Fri Sep 8 11:14:06 2023 -0400

    update autogen doc link

[33mcommit faee51ca9c29a92df9deed102de8e11257dc2a33[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Fri Sep 8 10:07:19 2023 -0400

    update links

[33mcommit 2837e22f3a20589d6fefdfccf692dc4e01e4a5cd[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Fri Sep 8 09:42:55 2023 -0400

    fix typo

[33mcommit 93b9e091663e1fc7c7827638a25a2fbc4944ea46[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Wed Sep 6 19:17:53 2023 -0700

    admin takeover in group chat (#1209)
    
    * admin takeover in group chat
    
    * comments
    
    * add comments

[33mcommit a27b9bc9e182b45786c9d9b331b514f7b9d7f8c6[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Tue Sep 5 20:34:59 2023 -0400

    add group chat link

[33mcommit eebe5af4249616cf7c9b66dd26c47585beb8edb7[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Tue Sep 5 18:37:47 2023 -0400

    typo

[33mcommit 3c6e191044035e0741383f6457cf7e2009f3d883[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Tue Sep 5 15:02:48 2023 -0400

    fix typo (#1210)

[33mcommit a104556a83d41ce03e294c757ad5816a0585f6db[m
Merge: e4ba349 1e0a515
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Mon Sep 4 23:04:18 2023 -0400

    Merge branch 'main' of https://github.com/microsoft/autogen

[33mcommit e4ba3491427f8dcd0aaa2e4a3b3f868093dcfb7b[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Mon Sep 4 23:03:20 2023 -0400

    add SKD

[33mcommit 1e0a515a03299af29adb1975bef810091457e5ca[m
Author: “skzhang1” <“shaokunzhang529@gmail.com”>
Date:   Mon Sep 4 21:37:56 2023 -0400

    change base url

[33mcommit a21a635502f8f60ab4f4988fd4d0023d0fbd940b[m
Author: “skzhang1” <“shaokunzhang529@gmail.com”>
Date:   Mon Sep 4 21:18:19 2023 -0400

    update action

[33mcommit 18278c9faeeac62d4d425e8723759a79e84209d2[m
Author: “skzhang1” <“shaokunzhang529@gmail.com”>
Date:   Mon Sep 4 20:48:18 2023 -0400

    add action

[33mcommit da6ed2ac624c150bee379e6b4a30d71ef0542e44[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Mon Sep 4 11:16:30 2023 -0400

    update wording

[33mcommit f00314f046cd1e9803b739677f7346a4a055eaf9[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Mon Sep 4 10:45:06 2023 -0400

    update fig

[33mcommit 1a073cfc872b4316af8398a4715c279d24ef6b62[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Mon Sep 4 10:17:29 2023 -0400

    update figs and wording

[33mcommit ec9e8c403df65910ea50f63d63892f230c6feefb[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Sun Sep 3 23:51:34 2023 -0400

    update links

[33mcommit 5f9b514be72f0e38bc5b716171a21dd408b9a315[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sun Sep 3 19:32:51 2023 -0700

    suffix in model name (#1206)
    
    * suffix in model name
    
    * bump version to 2.0.3

[33mcommit 549eee830f507115a29a292b2a89246d3fb7ebc0[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Sun Sep 3 15:42:36 2023 -0400

    revise key features

[33mcommit 2a69be7fe3fa17a94578934e46bd2d1ad2c8ef26[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Sat Sep 2 21:58:13 2023 -0400

    update conversation pattern

[33mcommit 65c14e2332b1c3a991b80dc772a14984ef98a0f4[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Sat Sep 2 20:37:51 2023 -0400

    add figures

[33mcommit 45b3f1d80d499efb29c1842ba19adc1b784975fe[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Sat Sep 2 14:46:20 2023 -0400

    change back name to flaml

[33mcommit 2eab9a358eec681a7b85d16c8e49965617992b94[m
Author: “skzhang1” <“shaokunzhang529@gmail.com”>
Date:   Sat Sep 2 12:15:54 2023 -0400

    update

[33mcommit 87f76f837cd427fd181ee7c30252f230e8a30c32[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Fri Sep 1 19:57:09 2023 -0400

    wording

[33mcommit 1a51ab57b7998a2d81c8c3e357decc0b82ebe027[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Fri Sep 1 17:55:32 2023 -0400

    update main page

[33mcommit d835f4863284f79dab76e314ca2fe7dcf2e17375[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Thu Aug 31 15:37:45 2023 +0000

    doc update

[33mcommit 5d8ba794b36573809f7e1ce17d3341c9c68f412b[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Thu Aug 31 04:12:20 2023 +0000

    .gitignore

[33mcommit e8dc1999d54a305378aa09eb48550e8c45e92235[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Thu Aug 31 04:10:10 2023 +0000

    discord link

[33mcommit 8b74d7a698b35942b8cce46bd71e934e87c70fd1[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Wed Aug 30 17:48:31 2023 -0400

    wording

[33mcommit f687a6c57d1c289ba716823439abf731ed360de7[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Wed Aug 30 17:27:35 2023 -0400

    naming

[33mcommit 95dcd39b081442397a46219114ea8ff2e667ef69[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Wed Aug 30 17:14:48 2023 -0400

    add autogen documentation

[33mcommit f750e0037f300e5e144c72d87c1d4efe4ae8e273[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Wed Aug 30 16:50:59 2023 -0400

    add documentation files

[33mcommit c5fc2fed824d4be3e933d7ba04c20bf5266a7c31[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Wed Aug 30 12:03:49 2023 -0400

    add a tentitive autogen log

[33mcommit 44932712c45050cebeb6b64df8bda8e1fc0f6915[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Aug 29 17:54:09 2023 -0700

    Prompt improvement (#1203)
    
    * prompt improvement
    
    * image None for unsupported lang
    
    * notebook update
    
    * prompt improvement

[33mcommit f0731e2240251cdf4da97c8a87997de3f9fe1927[m
Author: Li Jiang <bnujli@gmail.com>
Date:   Tue Aug 29 21:52:33 2023 +0800

    Update readme and AutoGen docs (#1183)
    
    * Update readme and AutoGen docs
    
    * Update Autogen#notebook-examples, Add link to AutoGen arxiv
    
    * Update website/docs/Use-Cases/Autogen.md
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update link
    
    ---------
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit 3a3e11535f6d4d0b06f76a09c88987f6a02a111a[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sun Aug 27 20:01:41 2023 -0700

    document response fields (#1199)

[33mcommit 9cfe8c6268ecc4b28e6628c6b84a8af6d2a772e3[m
Author: “skzhang1” <“shaokunzhang529@gmail.com”>
Date:   Sun Aug 27 21:32:15 2023 -0400

    update readme

[33mcommit 6f5ef68fec0f409286120a23c7ef2a60bad29077[m
Author: “skzhang1” <“shaokunzhang529@gmail.com”>
Date:   Sun Aug 27 21:30:54 2023 -0400

    web-template

[33mcommit 57a2bea95a36409e7f895a6d420a26307eebc97a[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sun Aug 27 15:16:52 2023 -0700

    prompt improvement (#1188)
    
    * test
    
    * chart
    
    * plan
    
    * separate
    
    * bump version to 2.0.1
    
    * explain plan and code/lang
    
    * notebook update
    
    * notebook update
    
    * typo
    
    * plan
    
    * match can be None

[33mcommit 87c2361040968b9f0914abe3c92387e00b164391[m
Author: Yiran Wu <32823396+kevin666aa@users.noreply.github.com>
Date:   Fri Aug 25 06:50:22 2023 -0400

    fix generate_reply when sender is None. (#1186)
    
    * fix generate_reply
    
    * code format
    
    * add test case
    
    * update
    
    * update
    
    * Update test/autogen/agentchat/test_responsive_agent.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update test/autogen/agentchat/test_responsive_agent.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update flaml/autogen/agentchat/responsive_agent.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    ---------
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 07b97eb469efa33529c9761a6d8b9971c3cd110c[m
Author: Yiran Wu <32823396+kevin666aa@users.noreply.github.com>
Date:   Sun Aug 20 01:28:29 2023 -0400

    cover function calls with no arguments (#1185)

[33mcommit d179357881da9f36b41c8d604f9c058c7f3aa815[m
Author: Microsoft Open Source <microsoftopensource@users.noreply.github.com>
Date:   Fri Aug 18 04:43:50 2023 -0700

    README.md committed

[33mcommit a5f2118764d0983245c21ecfa56c895887b4947b[m
Author: Microsoft Open Source <microsoftopensource@users.noreply.github.com>
Date:   Fri Aug 18 04:43:50 2023 -0700

    SECURITY.md committed

[33mcommit 67e5956dcb1520b4abe74c3366e053c1f71f9dae[m
Author: Microsoft Open Source <microsoftopensource@users.noreply.github.com>
Date:   Fri Aug 18 04:43:49 2023 -0700

    LICENSE committed

[33mcommit 6bb9ef477c779dfa996638e520f0a5fe2edbdbe3[m
Author: Microsoft Open Source <microsoftopensource@users.noreply.github.com>
Date:   Fri Aug 18 04:43:49 2023 -0700

    LICENSE-CODE committed

[33mcommit 6feef45b00561063a82497b7e9a11ab77f1ac413[m
Author: Microsoft Open Source <microsoftopensource@users.noreply.github.com>
Date:   Fri Aug 18 04:43:48 2023 -0700

    CODE_OF_CONDUCT.md committed

[33mcommit 7ab4d114d76f624ce8be95362305b76cde3337b6[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Mon Aug 14 00:09:45 2023 -0700

    silent; code_execution_config; exit; version (#1179)
    
    * silent; code_execution_config; exit; version
    
    * url
    
    * url
    
    * readme
    
    * preview
    
    * doc
    
    * url
    
    * endpoints
    
    * timeout
    
    * chess
    
    * Fix retrieve chat
    
    * config
    
    * mathchat
    
    ---------
    
    Co-authored-by: Li Jiang <bnujli@gmail.com>

[33mcommit 700ff05874fa02261cbe063023445c4c0053d5c5[m
Author: Li Jiang <bnujli@gmail.com>
Date:   Sun Aug 13 20:51:54 2023 +0800

    Add RetrieveChat (#1158)
    
    * Add RetrieveChat notebook, RetrieveAssistantAgent and RetrieveUserProxyAgent
    
    * Update according to comments
    
    * Add output
    
    * Add tests, merge main, address comments
    
    * Fix tests
    
    * Merge main
    
    * Remove unnecessary code
    
    * Update test
    
    * Update notebook, some functions
    
    * Fix print issue
    
    * Update notebook
    
    * Update notebook
    
    * Update notebook
    
    * Improve retrieve utils and update notebook
    
    * Update vector db creation method
    
    * Update notebook
    
    * Update notebook
    
    * Add terminate if no more context
    
    * Update prompt and notebook, add example for update context
    
    * Update results
    
    * Update results
    
    * Update results of update context
    
    * Fix typo
    
    * Add table of contents
    
    * Update table of contents

[33mcommit 55d2ebb289985a20c25f3d54c823019ebcfc553c[m
Author: Sayan Roy <sayan98.roy@gmail.com>
Date:   Sat Aug 12 10:42:22 2023 +0530

    Update README.md (#1180)
    
    Updated Readme with installation link

[33mcommit c44d2f4a012e9ecb5f6b3f1d5d87edd223d2e8ee[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Mon Aug 7 18:34:47 2023 -0700

    support async in agents (#1178)
    
    * Make auto reply method pluggable
    
    * support async
    
    * async
    
    * allow richer trigger types
    
    * test list
    
    * rename key

[33mcommit a603e6dddce44e1f9cc10dc34f275e156f9e047b[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Mon Aug 7 11:41:58 2023 -0700

    Make auto reply method pluggable (#1177)
    
    * Make auto reply method pluggable
    
    * allow richer trigger types
    
    * test list

[33mcommit 2208dfb79e1a1f44328628fd5de8666c7e8c11bc[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Fri Aug 4 07:26:58 2023 -0700

    Improve auto reply registration (#1170)
    
    * Improve auto reply registration
    
    * object key
    
    * fix test error
    
    * bug fix in math user proxy agent
    
    * allow send/receive without reply
    
    * reset -> stop

[33mcommit 45b7d908e4281f3156e96a61076cdeb4d4ce0b10[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Thu Aug 3 02:17:20 2023 -0700

    consecutive auto reply, history, template, group chat, class-specific reply (#1165)
    
    * max consecutive auto reply
    
    * chess notebook
    
    * link to notebook
    
    * clear history
    
    * filter
    
    * **context -> context
    
    * format str template
    
    * groupchat
    
    * register class specific reply
    
    * groupchat notebook
    
    * move human reply into generate_reply
    
    * arg in config
    
    * colab link
    
    * remove room
    
    * rename

[33mcommit c48babd02fa9b3252cf49100599fb99c70794591[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Mon Jul 31 19:22:30 2023 -0700

    raise error when msg is invalid; fix docstr; improve ResponsiveAgent; update doc and packaging; capture ipython output; find code blocks with llm when regex fails. (#1154)
    
    * autogen.agent -> autogen.agentchat
    
    * bug fix in portfolio
    
    * notebook
    
    * timeout
    
    * timeout
    
    * infer lang; close #1150
    
    * timeout
    
    * message context
    
    * context handling
    
    * add sender to generate_reply
    
    * clean up the receive function
    
    * move mathchat to contrib
    
    * contrib
    
    * last_message
    
    * Add OptiGuide: agent and notebook
    
    * Optiguide notebook: add figures and URL
    1. figures and code points to remote URL
    2. simplify the prompt for the interpreter, because
    all information is already in the chat history.
    
    * Update name: Agent -> GenericAgent
    
    * Update notebook
    
    * Rename: GenericAgent -> ResponsiveAgent
    
    * Rebase to autogen.agentchat
    
    * OptiGuide: Comment, sytle, and notebook updates
    
    * simplify optiguide
    
    * raise error when msg is invalid; fix docstr
    
    * allow return None for generate_reply()
    
    * update_system_message
    
    * test update_system_message
    
    * simplify optiguide
    
    * simplify optiguide
    
    * simplify optiguide
    
    * simplify optiguide
    
    * move test
    
    * add test and fix bug
    
    * doc update
    
    * doc update
    
    * doc update
    
    * color
    
    * optiguide
    
    * prompt
    
    * test danger case
    
    * packaging
    
    * docker
    
    * remove path in traceback
    
    * capture ipython output
    
    * simplify
    
    * find code blocks with llm
    
    * find code with llm
    
    * order
    
    * order
    
    * fix bug in context handling
    
    * print executing msg
    
    * print executing msg
    
    * test find code
    
    * test find code
    
    * disable find_code
    
    * default_auto_reply
    
    * default auto reply
    
    * remove optiguide
    
    * remove -e
    
    ---------
    
    Co-authored-by: Beibin Li <beibin79@gmail.com>

[33mcommit da92238ffebc7c92ca6a4ba52c0cafaad8f532fb[m
Author: minghao <howt51@gmail.com>
Date:   Tue Aug 1 09:58:30 2023 +0800

    Commenting use_label_encoder - xgboost (#1122)
    
    * Commenting use_label_encoder - xgboost
    
    * format change
    
    * moving the import xgboost version to the head
    
    * Shfit params for use_label to outside maxdept
    
    * Keep the original logic
    
    ---------
    
    Co-authored-by: Shaokun <shaokunzhang529@gmail.com>
    Co-authored-by: Li Jiang <bnujli@gmail.com>

[33mcommit 9d857d988b1a6db6ca5df2ad2969be9a794b4f5f[m
Author: Yiran Wu <32823396+kevin666aa@users.noreply.github.com>
Date:   Sat Jul 29 21:13:43 2023 +0800

    MathChat blog post (#1096)
    
    * mathchat blog
    
    * Update website/blog/2023-06-28-MathChat/index.mdx
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update website/blog/2023-06-28-MathChat/index.mdx
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update website/blog/2023-06-28-MathChat/index.mdx
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update website/blog/2023-06-28-MathChat/index.mdx
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>
    
    * Update website/blog/2023-06-28-MathChat/index.mdx
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>
    
    * Update website/blog/2023-06-28-MathChat/index.mdx
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>
    
    * update
    
    * forrmat
    
    * update
    
    * delete image
    
    * change link
    
    ---------
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit 7ddb171cd9d80175d32658a75ad4280802707f63[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Fri Jul 28 21:17:51 2023 -0700

    autogen.agent -> autogen.agentchat (#1148)
    
    * autogen.agent -> autogen.agentchat
    
    * bug fix in portfolio
    
    * notebook
    
    * timeout
    
    * timeout
    
    * infer lang; close #1150
    
    * timeout
    
    * message context
    
    * context handling
    
    * add sender to generate_reply
    
    * clean up the receive function
    
    * move mathchat to contrib
    
    * contrib
    
    * last_message

[33mcommit c0580a835bbc8fd36dc48df76fd33f605ac0209f[m
Author: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>
Date:   Thu Jul 27 13:57:07 2023 -0400

    Bump semver from 5.7.1 to 5.7.2 in /website (#1119)
    
    Bumps [semver](https://github.com/npm/node-semver) from 5.7.1 to 5.7.2.
    - [Release notes](https://github.com/npm/node-semver/releases)
    - [Changelog](https://github.com/npm/node-semver/blob/v5.7.2/CHANGELOG.md)
    - [Commits](https://github.com/npm/node-semver/compare/v5.7.1...v5.7.2)
    
    ---
    updated-dependencies:
    - dependency-name: semver
      dependency-type: indirect
    ...
    
    Signed-off-by: dependabot[bot] <support@github.com>
    Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>
    Co-authored-by: Shaokun <shaokunzhang529@gmail.com>
    Co-authored-by: Li Jiang <bnujli@gmail.com>

[33mcommit ecf51f41bbccc99a7ec302bbf7434a900966ca2c[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Jul 25 22:22:25 2023 -0700

    rename GenericAgent -> ResponsiveAgent (#1146)
    
    * rename GenericAgent -> ResponsiveAgent
    
    * always

[33mcommit 3e7aac6e8b0e6d93219d7eccabc49b9af6ae686c[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Jul 25 16:46:11 2023 -0700

    unify auto_reply; bug fix in UserProxyAgent; reorg agent hierarchy (#1142)
    
    * simplify the initiation of chat
    
    * version update
    
    * include openai
    
    * completion
    
    * load config list from json
    
    * initiate_chat
    
    * oai config list
    
    * oai config list
    
    * config list
    
    * config_list
    
    * raise_error
    
    * retry_time
    
    * raise condition
    
    * oai config list
    
    * catch file not found
    
    * catch openml error
    
    * handle openml error
    
    * handle openml error
    
    * handle openml error
    
    * handle openml error
    
    * handle openml error
    
    * handle openml error
    
    * close #1139
    
    * use property
    
    * termination msg
    
    * AIUserProxyAgent
    
    * smaller dev container
    
    * update notebooks
    
    * match
    
    * document code execution and AIUserProxyAgent
    
    * gpt 3.5 config list
    
    * rate limit
    
    * variable visibility
    
    * remove unnecessary import
    
    * quote
    
    * notebook comments
    
    * remove mathchat from init import
    
    * two users
    
    * import location
    
    * expose config
    
    * return str not tuple
    
    * rate limit
    
    * ipython user proxy
    
    * message
    
    * None result
    
    * rate limit
    
    * rate limit
    
    * rate limit
    
    * rate limit
    
    * make auto_reply a common method for all agents
    
    * abs path
    
    * refactor and doc
    
    * set mathchat_termination
    
    * code format
    
    * modified
    
    * emove import
    
    * code quality
    
    * sender -> messages
    
    * system message
    
    * clean agent hierarchy
    
    * dict check
    
    * invalid oai msg
    
    * return
    
    * openml error
    
    * docstr
    
    ---------
    
    Co-authored-by: kevin666aa <yrwu000627@gmail.com>

[33mcommit 2406e694963c3290ce869d55b313c69bdde6cff1[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sun Jul 23 06:23:09 2023 -0700

    Json config list, agent refactoring and new notebooks (#1133)
    
    * simplify the initiation of chat
    
    * version update
    
    * include openai
    
    * completion
    
    * load config list from json
    
    * initiate_chat
    
    * oai config list
    
    * oai config list
    
    * config list
    
    * config_list
    
    * raise_error
    
    * retry_time
    
    * raise condition
    
    * oai config list
    
    * catch file not found
    
    * catch openml error
    
    * handle openml error
    
    * handle openml error
    
    * handle openml error
    
    * handle openml error
    
    * handle openml error
    
    * handle openml error
    
    * close #1139
    
    * use property
    
    * termination msg
    
    * AIUserProxyAgent
    
    * smaller dev container
    
    * update notebooks
    
    * match
    
    * document code execution and AIUserProxyAgent
    
    * gpt 3.5 config list
    
    * rate limit
    
    * variable visibility
    
    * remove unnecessary import
    
    * quote
    
    * notebook comments
    
    * remove mathchat from init import
    
    * two users
    
    * import location
    
    * expose config
    
    * return str not tuple
    
    * rate limit
    
    * ipython user proxy
    
    * message
    
    * None result
    
    * rate limit
    
    * rate limit
    
    * rate limit
    
    * rate limit

[33mcommit 559fcb4879256b144e9ab489200a50dfe5819d65[m
Author: LeoLjl <3110503618@qq.com>
Date:   Sat Jul 22 00:12:49 2023 +0800

    Update docs on how to interact with local LLM (#1128)
    
    * Update docstring for oai.completion.
    
    Specify the details of how **config is used in Completion.
    
    * Update docs about how to interact with local LLMs
    
    * Update docs about how to interact with local LLMs
    
    * Reformat file.
    
    * Fix issues.
    
    * Update website/blog/2023-07-14-Local-LLMs/index.mdx
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update website/blog/2023-07-14-Local-LLMs/index.mdx
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update website/docs/Use-Cases/Auto-Generation.md
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Add documents about multiple workers.
    
    * Update user instructions.
    
    * Label big fix as optional
    
    * Update website/blog/2023-07-14-Local-LLMs/index.mdx
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    ---------
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 16f0fcd6f8fac9d392cd52a95facc0a52daabc1b[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Mon Jul 17 20:40:41 2023 -0700

    simplify the initiation of chat (#1131)
    
    * simplify the initiation of chat
    
    * version update
    
    * include openai
    
    * completion

[33mcommit 7665f73e4b2b225b1a1b2c2a2f9da4b1eef73bde[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Mon Jul 17 08:18:39 2023 -0700

    change price ratio (#1130)

[33mcommit eae65ac22b7e6fb4028d97599ffc38e332a3fa25[m
Author: Xiaobo Xia <56142822+xiaoboxia@users.noreply.github.com>
Date:   Mon Jul 17 09:02:10 2023 -0400

    suppress printing data split type (#1126)
    
    * first commit
    
    * second update
    
    * third update
    
    ---------
    
    Co-authored-by: “xiaoboxia” <“xiaoboxia.uni@gmail.com”>
    Co-authored-by: Shaokun <shaokunzhang529@gmail.com>
    Co-authored-by: “skzhang1” <“shaokunzhang529@gmail.com”>

[33mcommit 297a1ea9e0ef2a1a4bf0fa903ff63b2d46838944[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Fri Jul 14 15:52:45 2023 -0700

    Update assistant agent (#1121)
    
    * update colab link
    
    * typo
    
    * upload file instruction
    
    * update system message and notebooks
    
    * update notebooks
    
    * notebook test
    
    * aoai api version and exclusion
    
    * gpt-3.5-turbo
    
    * dict check
    
    * change model for test
    
    * endpoints, cache_path and func description update
    
    * model list
    
    * gitter -> discord

[33mcommit 8ac9a393b8a9cc7690db7d0263a47ee7af56cb78[m
Author: Li Jiang <bnujli@gmail.com>
Date:   Thu Jul 13 20:54:39 2023 +0800

    Add log metric (#1125)
    
    * Add original metric to mlflow logging
    
    * Update metric

[33mcommit ac7c4138e78c1bffa4d29013298da5972560ae28[m
Author: Yiran Wu <32823396+kevin666aa@users.noreply.github.com>
Date:   Thu Jul 13 09:10:22 2023 +0800

    fix mathproxyagent bug (#1124)

[33mcommit 3527e8a14ddfd8ed2680992edd99d8f80f37ac75[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Jul 11 10:45:04 2023 -0700

    update colab link (#1118)
    
    * update colab link
    
    * typo
    
    * upload file instruction

[33mcommit 784c4c4f86e8b0c6abeb411f06b3a1b78a74980b[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Mon Jul 10 09:07:48 2023 -0700

    Try to prevent the default AssistantAgent from asking users to modify the code (#1114)
    
    * inform assistant agent:
    user proxy agent can't modify code
    
    * update notebooks
    
    * configure timeout in UserProxyAgent
    
    ---------
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit 45c37b51490f6c7c79e7e8ddef4b47bfa74d7441[m
Author: LeoLjl <3110503618@qq.com>
Date:   Mon Jul 10 18:59:54 2023 +0800

    Update docstring for oai.completion. (#1113)
    
    Specify the details of how **config is used in Completion.

[33mcommit 255faf97e2b96a8ca05fe0e6ca3399a7f30f6ae7[m
Author: Yiran Wu <32823396+kevin666aa@users.noreply.github.com>
Date:   Mon Jul 10 12:56:07 2023 +0800

    Add Funccall notebook and document (#1110)
    
    * add funccall example and doc
    
    * revise to comments
    
    * Update website/docs/Use-Cases/Auto-Generation.md
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * revise
    
    * update
    
    * minor update
    
    * add test notebook
    
    * update
    
    ---------
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 5eece5c748e263e9f47fa0671d555737028bcbce[m
Author: levscaut <57213911+levscaut@users.noreply.github.com>
Date:   Mon Jul 10 12:44:01 2023 +0800

    Enhance Integration with Spark (#1097)
    
    * add doc for spark
    
    * labelCol equals to label by default
    
    * change title and reformat
    
    * reference about default index type
    
    * fix doc build
    
    * Update website/docs/Examples/Integrate - Spark.md
    
    * update doc
    
    * Added more references
    
    * remove exception case when `y_train.name` is None
    
    * fix broken link
    
    ---------
    
    Co-authored-by: Wendong Li <v-wendongli@microsoft.com>
    Co-authored-by: Li Jiang <bnujli@gmail.com>

[33mcommit 9c09090bf947b16524b700d089db96c11f37e721[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Jul 8 22:25:43 2023 -0700

    update notebook with new models (#1112)
    
    * rerun notebook with new models
    
    * planning agent
    
    * link to notebook

[33mcommit ca10b286cc8fb5965724e660c8a0654c293b035e[m
Author: Yiran Wu <32823396+kevin666aa@users.noreply.github.com>
Date:   Thu Jul 6 06:08:44 2023 +0800

    Support function_call in `autogen/agent` (#1091)
    
    * update funccall
    
    * code format
    
    * update to comments
    
    * update notebook
    
    * remove test for py3.7
    
    * allow funccall to class functions
    
    * add test and clean up notebook
    
    * revise notebook and test
    
    * update
    
    * update mathagent
    
    * Update flaml/autogen/agent/agent.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update flaml/autogen/agent/user_proxy_agent.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * revise to comments
    
    * revise function call design, notebook and test. add doc
    
    * code format
    
    * ad message_to_dict function
    
    * update mathproxyagent
    
    * revise docstr
    
    * update
    
    * Update flaml/autogen/agent/math_user_proxy_agent.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update flaml/autogen/agent/math_user_proxy_agent.py
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>
    
    * Update flaml/autogen/agent/user_proxy_agent.py
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>
    
    * simply funccall in userproxyagent, rewind auto-gen.md, revise to comments
    
    * code format
    
    * update
    
    * remove notebook for another pr
    
    * revise oai_conversation part  in agent, revise function exec in user_proxy_agent
    
    * update test_funccall
    
    * update
    
    * update
    
    * fix pydantic version
    
    * Update test/autogen/test_agent.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * fix bug
    
    * fix bug
    
    * update
    
    * update is_termination_msg to accept dict
    
    ---------
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>
    Co-authored-by: Li Jiang <bnujli@gmail.com>

[33mcommit dd9202bb0131d78b0ecd45fd11413548759fd90f[m
Author: Shaokun <shaokunzhang529@gmail.com>
Date:   Wed Jul 5 11:14:02 2023 +0800

    Update OptunaSearch  (#1106)
    
    * update optuna
    
    * update setup
    
    * fix dependencies
    
    * fix bugs in test
    
    * fix bugs, web format
    
    ---------
    
    Co-authored-by: “skzhang1” <“shaokunzhang529@gmail.com”>
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit 4f1dfe6676cfd7bdfc373d552d19103d4ebe1b0f[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Jul 4 13:29:32 2023 -0700

    doc update (#1089)
    
    * doc update
    
    * add link to mathchat notebook
    
    * use_docker property
    
    * function name
    
    * version update
    
    ---------
    
    Co-authored-by: kevin666aa <yrwu000627@gmail.com>
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit 8236533fafe97297be7dac7c069377ea57f66929[m
Author: Yiran Wu <32823396+kevin666aa@users.noreply.github.com>
Date:   Sun Jul 2 23:26:30 2023 +0800

    update math notebook (#1095)
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 7a641486760170ad52805adaf4e7759822aaf48e[m
Author: Shaokun <shaokunzhang529@gmail.com>
Date:   Sat Jul 1 11:01:14 2023 +0800

    support string alg in tune (#1093)
    
    * support string alg in tune
    
    * add test, enforce string feasible, support lexico in set_search_priorities in CFO
    
    * fix bug
    
    * fix bug
    
    * fix bug
    
    * fix bug
    
    * fix bugs
    
    * fix yiran
    
    ---------
    
    Co-authored-by: “skzhang1” <“shaokunzhang529@gmail.com”>

[33mcommit aa05434c87d7ef675d4810364f5b08a3c866635a[m
Author: Li Jiang <bnujli@gmail.com>
Date:   Fri Jun 30 22:17:55 2023 +0800

    temp solution for joblib 1.3.0 issue (#1100)
    
    * temp solution for joblib 1.3.0 issue, no need once https://github.com/joblib/joblib-spark/pull/48 is merged
    
    * update option

[33mcommit e3ca95bf8a5cc9c86638dab8ef0eb44bc1f3ee6f[m
Author: Yiran Wu <32823396+kevin666aa@users.noreply.github.com>
Date:   Sun Jun 25 21:49:34 2023 +0800

    An agent implementation of MathChat (#1090)
    
    * mathcaht implementation
    
    * code forrmat
    
    * update readme
    
    * update openai.yml
    
    * update openai.yml
    
    * update openai.yml

[33mcommit 5245efbd2c213caf657888efb1d85f0ea008ac20[m
Author: EgorKraevTransferwise <62890791+EgorKraevTransferwise@users.noreply.github.com>
Date:   Mon Jun 19 12:20:32 2023 +0100

    Factor out time series-related functionality into a time series Task object (#989)
    
    * Refactor into automl subpackage
    
    Moved some of the packages into an automl subpackage to tidy before the
    task-based refactor. This is in response to discussions with the group
    and a comment on the first task-based PR.
    
    Only changes here are moving subpackages and modules into the new
    automl, fixing imports to work with this structure and fixing some
    dependencies in setup.py.
    
    * Fix doc building post automl subpackage refactor
    
    * Fix broken links in website post automl subpackage refactor
    
    * Fix broken links in website post automl subpackage refactor
    
    * Remove vw from test deps as this is breaking the build
    
    * Move default back to the top-level
    
    I'd moved this to automl as that's where it's used internally, but had
    missed that this is actually part of the public interface so makes sense
    to live where it was.
    
    * Re-add top level modules with deprecation warnings
    
    flaml.data, flaml.ml and flaml.model are re-added to the top level,
    being re-exported from flaml.automl for backwards compatability. Adding
    a deprecation warning so that we can have a planned removal later.
    
    * Fix model.py line-endings
    
    * WIP
    
    * WIP - Notes below
    
    Got to the point where the methods from AutoML are pulled to
    GenericTask. Started removing private markers and removing the passing
    of automl to these methods. Done with decide_split_type, started on
    prepare_data. Need to do the others after
    
    * Re-add generic_task
    
    * Most of the merge done, test_forecast_automl fit succeeds, fails at predict()
    
    * Remaining fixes - test_forecast.py passes
    
    * Comment out holidays-related code as it's not currently used
    
    * Further holidays cleanup
    
    * Fix imports in a test
    
    * tidy up validate_data in time series task
    
    * Test fixes
    
    * Fix tests: add Task.__str__
    
    * Fix tests: test for ray.ObjectRef
    
    * Hotwire TS_Sklearn wrapper to fix test fail
    
    * Attempt at test fix
    
    * Fix test where val_pred_y is a list
    
    * Attempt to fix remaining tests
    
    * Push to retrigger tests
    
    * Push to retrigger tests
    
    * Push to retrigger tests
    
    * Push to retrigger tests
    
    * Remove plots from automl/test_forecast
    
    * Remove unused data size field from Task
    
    * Fix import for CLASSIFICATION in notebook
    
    * Monkey patch TFT to avoid plotting, to fix tests on MacOS
    
    * Monkey patch TFT to avoid plotting v2, to fix tests on MacOS
    
    * Monkey patch TFT to avoid plotting v2, to fix tests on MacOS
    
    * Fix circular import
    
    * remove redundant code in task.py post-merge
    
    * Fix test: set svd_solver="full" in PCA
    
    * Update flaml/automl/data.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Fix review comments
    
    * Fix task -> str in custom learner constructor
    
    * Remove unused CLASSIFICATION imports
    
    * Hotwire TS_Sklearn wrapper to fix test fail by setting
    optimizer_for_horizon == False
    
    * Revert changes to the automl_classification and pin FLAML version
    
    * Fix imports in reverted notebook
    
    * Fix FLAML version in automl notebooks
    
    * Fix ml.py line endings
    
    * Fix CLASSIFICATION task import in automl_classification notebook
    
    * Uncomment pip install in notebook and revert import
    
    Not convinced this will work because of installing an older version of
    the package into the environment in which we're running the tests, but
    let's see.
    
    * Revert c6a5dd1a0
    
    * Fix get_classification_objective import in suggest.py
    
    * Remove hcrystallball docs reference in TS_Sklearn
    
    * Merge markharley:extract-task-class-from-automl into this
    
    * Fix import, remove smooth.py
    
    * Fix dependencies to fix TFT fail on Windows Python 3.8 and 3.9
    
    * Add tensorboardX dependency to fix TFT fail on Windows Python 3.8 and 3.9
    
    * Set pytorch-lightning==1.9.0 to fix  TFT fail on Windows Python 3.8 and 3.9
    
    * Set pytorch-lightning==1.9.0 to fix  TFT fail on Windows Python 3.8 and 3.9
    
    * Disable PCA reduction of lagged features for now, to fix svd convervence fail
    
    * Merge flaml/main into time_series_task
    
    * Attempt to fix formatting
    
    * Attempt to fix formatting
    
    * tentatively implement holt-winters-no covariates
    
    * fix forecast method, clean class
    
    * checking external regressors too
    
    * update test forecast
    
    * remove duplicated test file, re-add sarimax, search space cleanup
    
    * Update flaml/automl/model.py
    
    removed links. Most important one probably was: https://robjhyndman.com/hyndsight/ets-regressors/
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * prevent short series
    
    * add docs
    
    * First attempt at merging Holt-Winters
    
    * Linter fix
    
    * Add holt-winters to TimeSeriesTask.estimators
    
    * Fix spark test fail
    
    * Attempt to fix another spark test fail
    
    * Attempt to fix another spark test fail
    
    * Change Black max line length to 127
    
    * Change Black max line length to 120
    
    * Add logging for ARIMA params, clean up time series models inheritance
    
    * Add more logging for missing ARIMA params
    
    * Remove a meaningless test causing a fail, add stricter check on ARIMA params
    
    * Fix a bug in HoltWinters
    
    * A pointless change to hopefully trigger the on and off KeyError in ARIMA.fit()
    
    * Fix formatting
    
    * Attempt to fix formatting
    
    * Attempt to fix formatting
    
    * Attempt to fix formatting
    
    * Attempt to fix formatting
    
    * Add type annotations to _train_with_config() in state.py
    
    * Add type annotations to prepare_sample_train_data() in state.py
    
    * Add docstring for time_col argument of AutoML.fit()
    
    * Address @sonichi's comments on PR
    
    * Fix formatting
    
    * Fix formatting
    
    * Reduce test time budget
    
    * Reduce test time budget
    
    * Increase time budget for the test to pass
    
    * Remove redundant imports
    
    * Remove more redundant imports
    
    * Minor fixes of points raised by Qingyun
    
    * Try to fix pandas import fail
    
    * Try to fix pandas import fail, again
    
    * Try to fix pandas import fail, again
    
    * Try to fix pandas import fail, again
    
    * Try to fix pandas import fail, again
    
    * Try to fix pandas import fail, again
    
    * Try to fix pandas import fail, again
    
    * Try to fix pandas import fail, again
    
    * Try to fix pandas import fail, again
    
    * Try to fix pandas import fail, again
    
    * Try to fix pandas import fail, again
    
    * Formatting fixes
    
    * More formatting fixes
    
    * Added test that loops over TS models to ensure coverage
    
    * Fix formatting issues
    
    * Fix more formatting issues
    
    * Fix random fail in check
    
    * Put back in tests for ARIMA predict without fit
    
    * Put back in tests for lgbm
    
    * Update test/test_model.py
    
    cover dedup
    
    * Match target length to X length in missing test
    
    ---------
    
    Co-authored-by: Mark Harley <mark.harley@transferwise.com>
    Co-authored-by: Mark Harley <mharley.code@gmail.com>
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    Co-authored-by: Andrea W <a.ruggerini@ammagamma.com>
    Co-authored-by: Andrea Ruggerini <nescio.adv@gmail.com>
    Co-authored-by: Egor Kraev <Egor.Kraev@tw.com>
    Co-authored-by: Li Jiang <bnujli@gmail.com>

[33mcommit 87606313494754761f0f7e826498bcf6f871d076[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Jun 17 06:11:22 2023 -0700

    string to array (#1086)
    
    * string to array
    
    * exclude aoai

[33mcommit e1da7f7d68a5c94bc2c733ab1ab25e5277a4aa57[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Thu Jun 15 17:58:44 2023 -0700

    update openai model support (#1082)
    
    * update openai model support
    
    * new gpt3.5
    
    * docstr
    
    * function_call and content may co-exist
    
    * test function call
    
    ---------
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit 0b739b8c93fc2ba9abaa32458977691bea92d11b[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Thu Jun 15 02:56:24 2023 -0700

    Links to papers (#1084)
    
    * Links to papers
    
    * Update website/docs/Use-Cases/Auto-Generation.md
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>
    
    ---------
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit 0c7082c7bfa49d45e3151f5583b610c178baffec[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Wed Jun 14 19:56:13 2023 -0400

    Docmentation for agents (#1057)
    
    * add agent notebook and documentation
    
    * fix bug
    
    * set flush to True when printing msg in agent
    
    * add a math problem in agent notebook
    
    * remove
    
    * header
    
    * improve notebook doc
    
    * notebook update
    
    * improve notebook example
    
    * improve doc
    
    * improve notebook doc
    
    * improve print
    
    * doc
    
    * human_input_mode
    
    * human_input_mode str
    
    * indent
    
    * indent
    
    * Update flaml/autogen/agent/user_proxy_agent.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update notebook/autogen_agent.ipynb
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update notebook/autogen_agent.ipynb
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update notebook/autogen_agent.ipynb
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * add agent doc
    
    * del old files
    
    * remove chat
    
    * agent doc
    
    * remove chat_agent
    
    * naming
    
    * improve documentation
    
    * wording
    
    * improve agent doc
    
    * wording
    
    * general auto reply
    
    * update agent doc
    
    * human input mode
    
    * add agent figure
    
    * update agent figure
    
    * update agent example figure
    
    * update code example
    
    * extensibility of UserProxyAgent
    
    ---------
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 3874a429cf464766a5941535f2b6ad9f4786cb7b[m
Author: Li Jiang <lijiang1@microsoft.com>
Date:   Wed Jun 14 14:44:30 2023 +0800

    fix workflow (#1071)

[33mcommit 9356a92ba5e5fe48dd075be43f51ca715e8d0b1f[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Tue Jun 13 04:25:41 2023 -0400

    add pands requirement in benchmark option (#1070)
    
    Co-authored-by: Li Jiang <bnujli@gmail.com>

[33mcommit c5dfb03f0ee0e2010d1728993c2add827b907a6a[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Mon Jun 12 11:07:14 2023 -0700

    encode timeout msg in bytes (#1078)
    
    * encode timeout msg in bytes
    
    * fix msg and test

[33mcommit a30d1985304396d7afb969d657d7af1ffb29dd96[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Jun 10 18:03:49 2023 -0700

    Fix documentation (#1075)
    
    * Fix indentation in documentation
    
    * newline
    
    * version

[33mcommit 5387a0a60786726412545dd3c56b9671dd1b5b71[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Fri Jun 9 11:40:04 2023 -0700

    Agent notebook example with human feedback; Support shell command and multiple code blocks; Improve the system message for assistant agent; Improve utility functions for config lists; reuse docker image  (#1056)
    
    * add agent notebook and documentation
    
    * fix bug
    
    * set flush to True when printing msg in agent
    
    * add a math problem in agent notebook
    
    * remove
    
    * header
    
    * improve notebook doc
    
    * notebook update
    
    * improve notebook example
    
    * improve doc
    
    * agent notebook example with user feedback
    
    * log
    
    * log
    
    * improve notebook doc
    
    * improve print
    
    * doc
    
    * human_input_mode
    
    * human_input_mode str
    
    * indent
    
    * indent
    
    * Update flaml/autogen/agent/user_proxy_agent.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * shell command and multiple code blocks
    
    * Update notebook/autogen_agent.ipynb
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update notebook/autogen_agent.ipynb
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update notebook/autogen_agent.ipynb
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * coding agent
    
    * math notebook
    
    * renaming and doc format
    
    * typo
    
    * infer lang
    
    * sh
    
    * docker
    
    * docker
    
    * reset consecutive autoreply counter
    
    * fix explanation
    
    * paper talk
    
    * human feedback
    
    * web info
    
    * rename test
    
    * config list explanation
    
    * link to blogpost
    
    * installation
    
    * homepage features
    
    * features
    
    * features
    
    * rename agent
    
    * remove notebook
    
    * notebook test
    
    * docker command
    
    * notebook update
    
    * lang -> cmd
    
    * notebook
    
    * make it work for gpt-3.5
    
    * return full log
    
    * quote
    
    * docker
    
    * docker
    
    * docker
    
    * docker
    
    * docker
    
    * docker image list
    
    * notebook
    
    * notebook
    
    * use_docker
    
    * use_docker
    
    * use_docker
    
    * doc
    
    * agent
    
    * doc
    
    * abs path
    
    * pandas
    
    * docker
    
    * reuse docker image
    
    * context window
    
    * news
    
    * print format
    
    * pyspark version in py3.8
    
    * pyspark in py3.8
    
    * pyspark and ray
    
    * quote
    
    * pyspark
    
    * pyspark
    
    * pyspark
    
    ---------
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit d36b2afe7fedfc24126e5c2588f53e4b53f8eeb7[m
Author: Li Jiang <bnujli@gmail.com>
Date:   Fri Jun 2 00:04:01 2023 +0800

    suppress warning message of pandas_on_spark to_spark (#1058)

[33mcommit b975df81da48fc244969bce8f949302bf343db75[m
Author: Li Jiang <bnujli@gmail.com>
Date:   Wed May 31 20:07:57 2023 +0800

    Support more azure openai api_type (#1059)

[33mcommit fed28e700b3010790b7a7b4cf457fbc046f4ca1c[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Sat May 27 23:17:23 2023 -0400

    add agent notebook and documentation (#1052)
    
    * add agent notebook and documentation
    
    * fix bug
    
    * set flush to True when printing msg in agent
    
    * add a math problem in agent notebook
    
    * remove
    
    * header
    
    * improve notebook doc
    
    * notebook update
    
    * improve notebook example
    
    * improve doc
    
    * improve notebook doc
    
    * improve print
    
    * doc
    
    * human_input_mode
    
    * human_input_mode str
    
    * indent
    
    * indent
    
    * Update flaml/autogen/agent/user_proxy_agent.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update notebook/autogen_agent.ipynb
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update notebook/autogen_agent.ipynb
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update notebook/autogen_agent.ipynb
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * renaming and doc format
    
    * typo
    
    ---------
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 3e6e834bbbb5bc2d6c5a4d07ba9d6c0cdb96d804[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Fri May 26 22:59:51 2023 -0400

    remove redundant doc and add tutorial (#1004)
    
    * remove redundant doc and add tutorial
    
    * add demos for pydata2023
    
    * Update pydata23 docs
    
    * remove redundant notebooks
    
    * Move tutorial notebooks to notebook folder
    
    * update readme and notebook links
    
    * update notebook links
    
    * update links
    
    * update readme
    
    ---------
    
    Co-authored-by: Li Jiang <lijiang1@microsoft.com>
    Co-authored-by: Li Jiang <bnujli@gmail.com>

[33mcommit b90e9ee283907f70c1aaa218af551a03742e2878[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Fri May 26 13:24:30 2023 -0700

    doc and test update (#1053)
    
    * doc and test update
    
    * docker update

[33mcommit 9e2eb200dfd33ec8fc24f7b1f4bf3f1d45aee38e[m
Author: badjouras <47984759+badjouras@users.noreply.github.com>
Date:   Thu May 25 03:23:54 2023 +0100

    docs: 📝 Fix link to installation section in Task-Oriented-AutoML.md (#1051)
    
    Co-authored-by: rcardoso <ricardo.cardoso@anova.com>
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit a0b318b12ee8288db54b674904655307f9e201c2[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Wed May 24 16:55:04 2023 -0700

    create an automl option to remove unnecessary dependency for autogen and tune (#1007)
    
    * version update post release v1.2.2
    
    * automl option
    
    * import pandas
    
    * remove automl.utils
    
    * default
    
    * test
    
    * type hint and version update
    
    * dependency update
    
    * link to open in colab
    
    * use packging.version to close #725
    
    ---------
    
    Co-authored-by: Li Jiang <lijiang1@microsoft.com>
    Co-authored-by: Li Jiang <bnujli@gmail.com>

[33mcommit e9fdbc6e02ffec9acd9e137e10fae8b1db33a7d8[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Wed May 24 14:28:52 2023 -0700

    Improve messaging in documentation (#1050)
    
    * Improve messaging in documentation
    
    * doc
    
    * improve wording in blogpost
    
    ---------
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit 9977a7aae1d5d2bb7e6c09c23ec93802a95f6bd8[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Mon May 22 21:22:15 2023 -0700

    Blogpost for adaptation in HumanEval (#1048)
    
    * Blogpost for adaptation in HumanEval
    
    * doc
    
    * fix link
    
    * fix link
    
    * explain
    
    * model
    
    * interface
    
    * link
    
    * typo
    
    * doc

[33mcommit e463146cb815fbd1e8ddc90afe7a467604c56cdc[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sun May 21 15:22:29 2023 -0700

    response filter (#1039)
    
    * response filter
    
    * rewrite implement based on the filter
    
    * multi responses
    
    * abs path
    
    * code handling
    
    * option to not use docker
    
    * context
    
    * eval_only -> raise_error
    
    * notebook
    
    * utils
    
    * utils
    
    * separate tests
    
    * test
    
    * test
    
    * test
    
    * test
    
    * test
    
    * test
    
    * test
    
    * test
    
    * **config in test()
    
    * test
    
    * test
    
    * filename

[33mcommit 7de4eb347d2fb7d69117aae4bb921fa620fdf234[m
Author: Li Jiang <bnujli@gmail.com>
Date:   Sat May 20 04:05:14 2023 +0800

    Fix PULL_REQUEST_TEMPLATE and improve test by removing unnecessary environment variable (#1043)
    
    * Improve test by removing unnecessary environment variable
    
    * Fix PULL_REQUEST_TEMPLATE
    
    * Hide pre-commit check
    
    * remove the checkbox for pre-commit
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    ---------
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 683f6befd2d1411c710e838c72018ad061512767[m
Author: Pratyay Roy <pratyayroy18@gmail.com>
Date:   Thu May 18 04:06:41 2023 +0530

    updated search space (#1044)
    
    Co-authored-by: Pratyay Roy <63900765+pratyay-roy@users.noreply.github.com>

[33mcommit a1f51d1d23ad449ec12fc63bd693e0c9583e8ac1[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Tue May 16 23:49:19 2023 -0400

    Blogpost (#1026)
    
    * add 1m milestone blogpost
    
    * format issues
    
    * update subsection title
    
    * acknowledgement
    
    * Update website/blog/2023-05-07-1M-milestone/index.mdx
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update website/blog/2023-05-07-1M-milestone/index.mdx
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * update blogpost
    
    * collaborators
    
    * wording
    
    * Azure Data to Azure Synapse
    
    * name
    
    * Azure Synapse Analytics
    
    * tasks and search space
    
    * Update website/blog/2023-05-07-1M-milestone/index.mdx
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    ---------
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    Co-authored-by: Li Jiang <bnujli@gmail.com>

[33mcommit 0e2dbd53782b5534ba5b58e9acef926f2a30d0ff[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Mon May 15 23:18:33 2023 -0700

    fix of website link (#1042)

[33mcommit 2e43509690988e306206ebff6a9063e3bb2cddb3[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Mon May 15 20:37:38 2023 -0400

    Human agent (#1025)
    
    * add human agent and chat agent
    
    * feedback msg
    
    * clean print
    
    * remove redundant import
    
    * make coding agent work
    
    * import check
    
    * terminate condition
    
    * rename
    
    * add docstr
    
    * exitcode to str
    
    * print
    
    * save and execute code
    
    * add max_turn_num
    
    * add max_turn_num in test_agent.py
    
    * reduce max_turn_num in the test
    
    * change max_turn_num to max_consecutive_auto_reply
    
    * update human proxy agent
    
    * remove execution agent and dated docstr
    
    * clean doc
    
    * add back work_dir
    
    * add is_termination_msg when mode is NEVER
    
    * revise stop condition
    
    * remove work_dir in coding agent
    
    * human_proxy_agent docstr
    
    * auto_reply
    
    * clean auto_reply
    
    ---------
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit f01acb67f634ff936066618bc1d3c19c3296d1e3[m
Author: Susan Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Tue May 9 20:48:22 2023 -0400

    update model of text summarization (#1030)

[33mcommit 59e882e5cc03afd9bf2280c084438378af4ceab1[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue May 9 13:39:46 2023 -0700

    chat completion check (#1024)
    
    * chat completion check
    
    * add test
    
    * doc
    
    * timeout
    
    * bump version to 1.2.4

[33mcommit 51c8768bcf8c90cfc4307a6ddb23d07eb169d611[m
Author: Beibin Li <BeibinLi@users.noreply.github.com>
Date:   Sat May 6 04:16:50 2023 -0700

    Catch AuthenticationError trying different configs (#1023)
    
    * Catch AuthenticationError trying different configs
    While trying different openai `config_list`, some
    configs might be outdated (e.g., an API key is expired).
    In these cases, we don't want the program to crash.
    Instead, we might want to try other configs.
    
    * Lint whitespace

[33mcommit b3fba9734ebf7ce504b180fac1783442389b85bf[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Thu May 4 19:48:31 2023 -0700

    Mark experimental classes; doc; multi-config trial (#1021)
    
    * Mark experimental classes
    
    * template
    
    * multi model
    
    * test
    
    * multi-config doc
    
    * doc
    
    * doc
    
    * test
    
    ---------
    
    Co-authored-by: Li Jiang <bnujli@gmail.com>

[33mcommit 8b2411b2197bbe0640c9707cd4b5293664c8873b[m
Author: Li Jiang <bnujli@gmail.com>
Date:   Wed May 3 17:59:29 2023 +0800

    update spark session in spark tests (#1006)
    
    * add mlflow and spark integration tests
    
    * remove unused params
    
    * remove mlflow tests

[33mcommit fd1f36597b23f117b60358566678c8379bf6c3c0[m
Author: Li Jiang <bnujli@gmail.com>
Date:   Wed May 3 17:16:32 2023 +0800

    update max_spark_parallelism to fit in auto-scale spark cluster (#1008)
    
    * update max_spark_parallelism to fit in auto-scale spark cluster
    
    * update test

[33mcommit 00c30a398e6bdcb4a7790adfafdb295d13f390b5[m
Author: Susan Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Wed May 3 01:50:28 2023 -0400

    fix NLP zero division error (#1009)
    
    * fix NLP zero division error
    
    * set predictions to None
    
    * set predictions to None
    
    * set predictions to None
    
    * refactor
    
    * refactor
    
    ---------
    
    Co-authored-by: Li Jiang <lijiang1@microsoft.com>
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    Co-authored-by: Li Jiang <bnujli@gmail.com>

[33mcommit 31864d2d777be8f53a4b97d8a585dbbe42f28d8b[m
Author: garar <krystiankichewko@gmail.com>
Date:   Wed May 3 05:09:04 2023 +0200

    Add mlflow_logging param (#1015)
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 19aee67f55901a0b805dd215bc5ec77649521a80[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue May 2 13:38:23 2023 -0700

    coding agent; logging (#1011)
    
    * coding agent
    
    * tsp
    
    * tsp
    
    * aoai
    
    * logging
    
    * compact
    
    * Handle Import Error
    
    * cost function
    
    * reset counter; doc
    
    * reset_counter
    
    * home page update
    
    * use case
    
    * catboost in linux
    
    * catboost
    
    * catboost
    
    * catboost
    
    * doc
    
    * intro
    
    * catboost

[33mcommit 39b9a9a417b80dac768465d695b809bce5116e04[m
Author: Li Jiang <bnujli@gmail.com>
Date:   Tue May 2 22:19:56 2023 +0800

    Fix catboost failure in mac-os python<3.9 (#1020)

[33mcommit 6d7fb3d78685effce8086960e93552b12394f45a[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Apr 29 11:46:28 2023 -0700

    raise content_filter error (#1018)
    
    * raise content_filter error
    
    * import error handling

[33mcommit 06cd3f52e508f9381caa7bad4b824094e9438bd0[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Fri Apr 28 02:38:09 2023 -0400

    update readme (#1014)
    
    Co-authored-by: Li Jiang <lijiang1@microsoft.com>

[33mcommit 73bb6e7667a6be3ad55f8423639cc3101ce22d34[m
Author: Jirka Borovec <6035284+Borda@users.noreply.github.com>
Date:   Fri Apr 28 03:54:55 2023 +0200

    pyproject.toml & switch to Ruff (#976)
    
    * unify config to pyproject.toml
    replace flake8 with Ruff
    
    * drop configs
    
    * update
    
    * fixing
    
    * Apply suggestions from code review
    
    Co-authored-by: Zvi Baratz <z.baratz@gmail.com>
    
    * setup
    
    * ci
    
    * pr template
    
    * reword
    
    ---------
    
    Co-authored-by: Zvi Baratz <z.baratz@gmail.com>
    Co-authored-by: Li Jiang <lijiang1@microsoft.com>

[33mcommit a8752b6aa0eaf93a031882b4f23d15a56555cc67[m
Author: Anupam <35479077+luckyklyist@users.noreply.github.com>
Date:   Wed Apr 26 20:52:33 2023 +0545

    fixed sentence misplace #998 (#1010)

[33mcommit e9cd6a058c043550947ce265f177ff958465b1bf[m
Author: Sayan Roy <sayan98.roy@gmail.com>
Date:   Wed Apr 26 11:18:09 2023 +0530

    fixing the typo #990 (#994)
    
    * fixing the typo #990
    
    * Update website/docs/Use-Cases/Auto-Generation.md
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * removing extra space : Update website/docs/Use-Cases/Auto-Generation.md
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update website/docs/Use-Cases/Auto-Generation.md
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update website/docs/Use-Cases/Auto-Generation.md
    
    ---------
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit f097c20f860c42fbce3a13a2f39f591e71fad4bf[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Mon Apr 24 21:48:17 2023 -0700

    version update post release v1.2.2 (#1005)

[33mcommit fa5ccea86253fdb2e4e17531749d7d228c98d76c[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sun Apr 23 04:50:29 2023 -0700

    extract code from text; solve_problem; request_timeout in config; improve code (#999)
    
    * extract code from text
    
    * solve_problem; request_timeout in config
    
    * improve
    
    * move import statement
    
    * improve code
    
    * generate assertions
    
    * constant
    
    * configs for implement; voting
    
    * doc
    
    * execute code in docker
    
    * success indicator of code executation in docker
    
    * success indicator
    
    * execute code
    
    * strip n
    
    * add cost in generate_code
    
    * add docstr
    
    * filename
    
    * bytes
    
    * check docker version
    
    * print log
    
    * python test
    
    * remove api key address
    
    * rename exit code
    
    * success exit code
    
    * datasets
    
    * exit code
    
    * recover openai tests
    
    * cache and pattern match
    
    * wait
    
    * wait
    
    * cache and test
    
    * timeout test
    
    * python image name and skip macos
    
    * windows image
    
    * docker images
    
    * volume path and yaml
    
    * win path -> posix
    
    * extensions
    
    * path
    
    * path
    
    * path
    
    * path
    
    * path
    
    * path
    
    * path
    
    * path
    
    * path
    
    * path
    
    * path
    
    * skip windows
    
    * path
    
    * timeout in windows
    
    * use_docker
    
    * use_docker
    
    * hot fix from #1000
    
    ---------
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit 7114b8f7425ccca0ee539c8a3d8f97f4d43272e3[m
Author: Susan Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Sat Apr 22 23:55:51 2023 -0400

    fix zerodivision (#1000)
    
    * fix zerodivision
    
    * update
    
    * remove final
    
    ---------
    
    Co-authored-by: Li Jiang <lijiang1@microsoft.com>

[33mcommit da0d8c05e10cae9b60cac3b3a734a78c4935ad53[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Fri Apr 21 21:41:16 2023 -0700

    Blog post for LLM tuning (#986)
    
    * outline
    
    * revision
    
    * eval function signature
    
    * first draft
    
    * link
    
    * format
    
    * example
    
    * cleanup
    
    * average
    
    * move figure
    
    * tldr
    
    * bold
    
    * bold
    
    * tag

[33mcommit 99bb0a8425a58a537ae34347c867b4bc05310471[m
Author: Susan Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Mon Apr 17 13:29:36 2023 -0400

    update nlp notebook (#940)
    
    * update nlp notebook
    
    * rerun
    
    * rerun
    
    * removing redundant in notebook
    
    * remove redundant content in nlp notebook
    
    * update notebook
    
    * update plot
    
    * update plot
    
    * update plot
    
    ---------
    
    Co-authored-by: Li Jiang <lijiang1@microsoft.com>

[33mcommit d4070e24c1b9fbdab15fe31013792445bdebbd6d[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sun Apr 16 14:18:32 2023 -0700

    make context optional; improve error handling and doc (#997)
    
    * make context optional
    
    * better error handling and doc
    
    * skip instantiation if no context
    
    * skip test

[33mcommit b235fe009866ad9bd098430db088149367cb309d[m
Author: Jane Illarionova <illariojane@gmail.com>
Date:   Sat Apr 15 12:06:47 2023 -0700

    Expose feature and label transformer in automl.py (#993)
    
    * expose label and feature transformer
    
    * linter apply
    
    * avoid undefined attribute in flaml/automl/automl.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * avoid undefined attribute in flaml/automl/automl.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * retrigger checks
    
    * retrigger checks
    
    ---------
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit c9fc622af1024990a944d8ff1c3bcf998723f5ce[m
Author: Li Jiang <lijiang1@microsoft.com>
Date:   Sat Apr 15 22:52:40 2023 +0800

    fix tests failure caused by version incompatibility (#995)

[33mcommit c780d79004cc8fc3790c6ddd71962856e6f1a557[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Mon Apr 10 13:46:28 2023 -0700

    Post release update (#985)
    
    * news update
    
    * doc update
    
    * avoid KeyError
    
    * bump version to 1.2.1
    
    * handle empty responses
    
    * typo
    
    * eval function

[33mcommit a701cd82f871249923d3c92c74c557fbff64ffd1[m
Author: Jirka Borovec <6035284+Borda@users.noreply.github.com>
Date:   Mon Apr 10 21:50:40 2023 +0200

    set black with 120 line length (#975)
    
    * set black with 120 line length
    
    * apply pre-commit
    
    * apply black

[33mcommit ef5a17cd830cc996bb07e72d07a1d2f3fc0c74c6[m
Author: Susan Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Sun Apr 9 12:53:30 2023 -0400

    handling nlp divide by zero (#926)
    
    * handling nlp divide by zero
    
    * catching zerodivisionerror
    
    * catching zerodivisionerror
    
    * catching zerodivisionerror
    
    * addressing comments
    
    * addressing comments
    
    * updating test case
    
    * update
    
    * add blank to last line
    
    * update nlp notebook
    
    * rerun
    
    * rerun
    
    * sync with main
    
    * add model selection for nlg
    
    * addressing keyerror
    
    * add raise exception
    
    * update
    
    * fix bug
    
    * revert
    
    * updating automl_nlp
    
    * Update flaml/automl/model.py
    
    Co-authored-by: Zvi Baratz <z.baratz@gmail.com>
    
    * address comments
    
    * address comments
    
    ---------
    
    Co-authored-by: Li Jiang <lijiang1@microsoft.com>
    Co-authored-by: Zvi Baratz <z.baratz@gmail.com>

[33mcommit 82f0a4309d2fe3f8445fcf48dca21eadc226e826[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Fri Apr 7 20:04:01 2023 -0700

    autogen subpackage (#968)
    
    * math utils in autogen
    
    * cleanup
    
    * code utils
    
    * remove check function from code response
    
    * comment out test
    
    * GPT-4
    
    * increase request timeout
    
    * name
    
    * logging and error handling
    
    * better doc
    
    * doc
    
    * codegen optimized
    
    * GPT series
    
    * text
    
    * no demo example
    
    * math
    
    * import openai
    
    * import openai
    
    * azure model name
    
    * azure model name
    
    * openai version
    
    * generate assertion if necessary
    
    * condition to generate assertions
    
    * init region key
    
    * rename
    
    * comments about budget
    
    * prompt
    
    ---------
    
    Co-authored-by: Susan Xueqing Liu <liususan091219@users.noreply.github.com>

[33mcommit 7f9402b8fd64f25e8f95d342fefc8eea1c006f2a[m
Author: Andrea Ruggerini <nescio.adv@gmail.com>
Date:   Tue Apr 4 19:29:54 2023 +0200

    Add Holt-Winters exponential smoothing (#962)
    
    * tentatively implement holt-winters-no covariates
    
    * fix forecast method, clean class
    
    * checking external regressors too
    
    * update test forecast
    
    * remove duplicated test file, re-add sarimax, search space cleanup
    
    * Update flaml/automl/model.py
    
    removed links. Most important one probably was: https://robjhyndman.com/hyndsight/ets-regressors/
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * prevent short series
    
    * add docs
    
    ---------
    
    Co-authored-by: Andrea W <a.ruggerini@ammagamma.com>
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 4c20c85dfd261a5f8231f0bbe3808d55240bc2a0[m
Author: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>
Date:   Tue Apr 4 09:00:46 2023 -0400

    Bump eta from 1.12.3 to 2.0.0 in /website (#941)
    
    Bumps [eta](https://github.com/eta-dev/eta) from 1.12.3 to 2.0.0.
    - [Release notes](https://github.com/eta-dev/eta/releases)
    - [Commits](https://github.com/eta-dev/eta/compare/v1.12.3...v2.0.0)
    
    ---
    updated-dependencies:
    - dependency-name: eta
      dependency-type: indirect
    ...
    
    Signed-off-by: dependabot[bot] <support@github.com>
    Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>
    Co-authored-by: Shaokun <shaokunzhang529@gmail.com>

[33mcommit 61d2a445f7aace61db446fa06db59a6633a21bc7[m
Author: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>
Date:   Tue Apr 4 12:59:39 2023 +0000

    Bump @sideway/formula from 3.0.0 to 3.0.1 in /website (#963)
    
    Bumps [@sideway/formula](https://github.com/sideway/formula) from 3.0.0 to 3.0.1.
    - [Release notes](https://github.com/sideway/formula/releases)
    - [Commits](https://github.com/sideway/formula/compare/v3.0.0...v3.0.1)
    
    ---
    updated-dependencies:
    - dependency-name: "@sideway/formula"
      dependency-type: indirect
    ...
    
    Signed-off-by: dependabot[bot] <support@github.com>
    Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>
    Co-authored-by: Shaokun <shaokunzhang529@gmail.com>

[33mcommit 185cdff005c6fb55638151fecf06672fd145b3b8[m
Author: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>
Date:   Tue Apr 4 08:59:01 2023 -0400

    Bump webpack from 5.74.0 to 5.76.1 in /website (#952)
    
    Bumps [webpack](https://github.com/webpack/webpack) from 5.74.0 to 5.76.1.
    - [Release notes](https://github.com/webpack/webpack/releases)
    - [Commits](https://github.com/webpack/webpack/compare/v5.74.0...v5.76.1)
    
    ---
    updated-dependencies:
    - dependency-name: webpack
      dependency-type: indirect
    ...
    
    Signed-off-by: dependabot[bot] <support@github.com>
    Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>
    Co-authored-by: Shaokun <shaokunzhang529@gmail.com>

[33mcommit f404b66a4c20d421c9cee465a6796ca76a0a8992[m
Author: Jirka Borovec <6035284+Borda@users.noreply.github.com>
Date:   Tue Apr 4 06:44:23 2023 +0200

    ci: concurrency (#931)
    
    * ci: concurrency
    
    * no fail-fast
    
    * Apply suggestions from code review
    
    ---------
    
    Co-authored-by: Shaokun <shaokunzhang529@gmail.com>

[33mcommit 904b5ea7cdc15d7268767d5bf53abeb49635682e[m
Author: Li Jiang <bnujli@gmail.com>
Date:   Mon Apr 3 12:58:34 2023 +0800

    add timeout to openai create (#973)

[33mcommit 5616ce0a540003eefcc4a65bc7c9fb2557cdd974[m
Author: Ayesh Vininda <61907771+AyeshGK@users.noreply.github.com>
Date:   Mon Apr 3 07:20:44 2023 +0530

    Noctus contribute (#961)
    
    * indentation space #884 changing indentation of python code blocks
    
    * indentation space #884 changing indentation of python code blocks 2

[33mcommit 45641000c048a37e34ef1d39b94926d6a7eba960[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Sun Apr 2 12:14:11 2023 -0400

    Adding a test function for OpenAI completion in flaml  (#951)
    
    * improve max_valid_n and doc
    
    * Update README.md
    
    Co-authored-by: Li Jiang <lijiang1@microsoft.com>
    
    * add support for chatgpt
    
    * notebook
    
    * newline at end of file
    
    * chatgpt notebook
    
    * ChatGPT in Azure
    
    * doc
    
    * math
    
    * warning, timeout, log file name
    
    * handle import error
    
    * doc update; default value
    
    * paper
    
    * doc
    
    * docstr
    
    * eval_func
    
    * add a test func in completion
    
    * update notebook
    
    * update math notebook
    
    * improve notebok
    
    * lint and handle exception
    
    * flake8
    
    * exception in test
    
    * add agg_method
    
    * NameError
    
    * refactor
    
    * Update flaml/integrations/oai/completion.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update flaml/integrations/oai/completion.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * add example
    
    * merge files from oai_eval_test
    
    * Revert "merge files from oai_eval_test"
    This reverts commit 1e6a550f913bb94df6e9680934ccb7175d00702e.
    
    * merge
    
    * save results to notebook_output
    
    * update version and cache
    
    * update doc
    
    * save nb cell results to file
    
    * fix typo in model name
    
    * code improvements
    
    * improve docstr
    
    * docstr
    
    * docstr on the Returns of test
    
    ---------
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    Co-authored-by: Li Jiang <lijiang1@microsoft.com>
    Co-authored-by: Susan Xueqing Liu <liususan091219@users.noreply.github.com>

[33mcommit 05c5f8f426b348e8527a45619b0883848d71213d[m
Author: levscaut <57213911+levscaut@users.noreply.github.com>
Date:   Mon Mar 27 12:12:50 2023 +0800

    more tolerant time limit for test_overtime (#960)
    
    * more tolerant time limit for test_overtime
    
    * Cancel assertion becasue github VM sometimes is super slow
    
    ---------
    
    Co-authored-by: Li Jiang <lijiang1@microsoft.com>

[33mcommit 595f5a8025b74bab8627cce2a3ca34bbcbd29afb[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sun Mar 26 10:13:06 2023 -0700

    gpt-4 support; openai workflow fix; model str; timeout; voting (#958)
    
    * workflow; model str; timeout
    
    * voting
    
    * notebook
    
    * pull request
    
    * recover workflow
    
    * voted answer
    
    * aoai
    
    * ignore None answer
    
    * default config
    
    * note
    
    * gpt-4
    
    * n=5
    
    * cleanup
    
    * config name
    
    * introduction
    
    * readme
    
    * avoid None
    
    * add output/ to gitignore
    
    * openai version
    
    * invalid var
    
    * comment long running cells

[33mcommit 50334f2c52b8bc1d3f079dfe1be29958ec5b4fb8[m
Author: Li Jiang <lijiang1@microsoft.com>
Date:   Sun Mar 26 03:59:46 2023 +0800

    Support spark dataframe as input dataset and spark models as estimators (#934)
    
    * add basic support to Spark dataframe
    
    add support to SynapseML LightGBM model
    
    update to pyspark>=3.2.0 to leverage pandas_on_Spark API
    
    * clean code, add TODOs
    
    * add sample_train_data for pyspark.pandas dataframe, fix bugs
    
    * improve some functions, fix bugs
    
    * fix dict change size during iteration
    
    * update model predict
    
    * update LightGBM model, update test
    
    * update SynapseML LightGBM params
    
    * update synapseML and tests
    
    * update TODOs
    
    * Added support to roc_auc for spark models
    
    * Added support to score of spark estimator
    
    * Added test for automl score of spark estimator
    
    * Added cv support to pyspark.pandas dataframe
    
    * Update test, fix bugs
    
    * Added tests
    
    * Updated docs, tests, added a notebook
    
    * Fix bugs in non-spark env
    
    * Fix bugs and improve tests
    
    * Fix uninstall pyspark
    
    * Fix tests error
    
    * Fix java.lang.OutOfMemoryError: Java heap space
    
    * Fix test_performance
    
    * Update test_sparkml to test_0sparkml to use the expected spark conf
    
    * Remove unnecessary widgets in notebook
    
    * Fix iloc java.lang.StackOverflowError
    
    * fix pre-commit
    
    * Added params check for spark dataframes
    
    * Refactor code for train_test_split to a function
    
    * Update train_test_split_pyspark
    
    * Refactor if-else, remove unnecessary code
    
    * Remove y from predict, remove mem control from n_iter compute
    
    * Update workflow
    
    * Improve _split_pyspark
    
    * Fix test failure of too short training time
    
    * Fix typos, improve docstrings
    
    * Fix index errors of pandas_on_spark, add spark loss metric
    
    * Fix typo of ndcgAtK
    
    * Update NDCG metrics and tests
    
    * Remove unuseful logger
    
    * Use cache and count to ensure consistent indexes
    
    * refactor for merge maain
    
    * fix errors of refactor
    
    * Updated SparkLightGBMEstimator and cache
    
    * Updated config2params
    
    * Remove unused import
    
    * Fix unknown parameters
    
    * Update default_estimator_list
    
    * Add unit tests for spark metrics

[33mcommit a3e770eac53de3f6c24bd0090668a095a6f2ab64[m
Author: Susan Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Mon Mar 13 23:19:58 2023 -0400

    fix delete (#950)

[33mcommit 27b271201680051eb94ed1e32f922929ef95db51[m
Author: Mark Harley <mharley.code@gmail.com>
Date:   Sat Mar 11 02:39:08 2023 +0000

    Extract task class from automl (#857)
    
    * Refactor into automl subpackage
    
    Moved some of the packages into an automl subpackage to tidy before the
    task-based refactor. This is in response to discussions with the group
    and a comment on the first task-based PR.
    
    Only changes here are moving subpackages and modules into the new
    automl, fixing imports to work with this structure and fixing some
    dependencies in setup.py.
    
    * Fix doc building post automl subpackage refactor
    
    * Fix broken links in website post automl subpackage refactor
    
    * Fix broken links in website post automl subpackage refactor
    
    * Remove vw from test deps as this is breaking the build
    
    * Move default back to the top-level
    
    I'd moved this to automl as that's where it's used internally, but had
    missed that this is actually part of the public interface so makes sense
    to live where it was.
    
    * Re-add top level modules with deprecation warnings
    
    flaml.data, flaml.ml and flaml.model are re-added to the top level,
    being re-exported from flaml.automl for backwards compatability. Adding
    a deprecation warning so that we can have a planned removal later.
    
    * Fix model.py line-endings
    
    * WIP
    
    * WIP - Notes below
    
    Got to the point where the methods from AutoML are pulled to
    GenericTask. Started removing private markers and removing the passing
    of automl to these methods. Done with decide_split_type, started on
    prepare_data. Need to do the others after
    
    * Re-add generic_task
    
    * Fix tests: add Task.__str__
    
    * Fix tests: test for ray.ObjectRef
    
    * Hotwire TS_Sklearn wrapper to fix test fail
    
    * Remove unused data size field from Task
    
    * Fix import for CLASSIFICATION in notebook
    
    * Update flaml/automl/data.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Fix review comments
    
    * Fix task -> str in custom learner constructor
    
    * Remove unused CLASSIFICATION imports
    
    * Hotwire TS_Sklearn wrapper to fix test fail by setting
    optimizer_for_horizon == False
    
    * Revert changes to the automl_classification and pin FLAML version
    
    * Fix imports in reverted notebook
    
    * Fix FLAML version in automl notebooks
    
    * Fix ml.py line endings
    
    * Fix CLASSIFICATION task import in automl_classification notebook
    
    * Uncomment pip install in notebook and revert import
    
    Not convinced this will work because of installing an older version of
    the package into the environment in which we're running the tests, but
    let's see.
    
    * Revert c6a5dd1a0
    
    * Revert "Revert c6a5dd1a0"
    
    This reverts commit e55e35adea03993de87b23f092b14c6af623d487.
    
    * Black format model.py
    
    * Bump version to 1.1.2 in automl_xgboost
    
    * Add docstrings to the Task ABC
    
    * Fix import in custom_learner
    
    * fix 'optimize_for_horizon' for ts_sklearn
    
    * remove debugging print statements
    
    * Check for is_forecast() before is_classification() in decide_split_type
    
    * Attempt to fix formatting fail
    
    * Another attempt to fix formatting fail
    
    * And another attempt to fix formatting fail
    
    * Add type annotations for task arg in signatures and docstrings
    
    * Fix formatting
    
    * Fix linting
    
    ---------
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>
    Co-authored-by: EgorKraevTransferwise <egor.kraev@transferwise.com>
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    Co-authored-by: Kevin Chen <chenkevin.8787@gmail.com>

[33mcommit 169012f3e732cee7206c4a844481c811bf37330d[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Fri Mar 10 11:35:36 2023 -0800

    ChatGPT support (#942)
    
    * improve max_valid_n and doc
    
    * Update README.md
    
    Co-authored-by: Li Jiang <lijiang1@microsoft.com>
    
    * add support for chatgpt
    
    * notebook
    
    * newline at end of file
    
    * chatgpt notebook
    
    * ChatGPT in Azure
    
    * doc
    
    * math
    
    * warning, timeout, log file name
    
    * handle import error
    
    * doc update; default value
    
    * paper
    
    * doc
    
    * docstr
    
    * eval_func
    
    * prompt and messages
    
    * remove confusing words
    
    * notebook name
    
    ---------
    
    Co-authored-by: Li Jiang <lijiang1@microsoft.com>
    Co-authored-by: Susan Xueqing Liu <liususan091219@users.noreply.github.com>

[33mcommit 3a606930d1394069a30ff7d5f7e388f4fd84c1bb[m
Author: Shaokun <shaokunzhang529@gmail.com>
Date:   Fri Mar 10 08:54:48 2023 -0500

    Update doc and notebook (#946)
    
    * update
    
    * update doc
    
    ---------
    
    Co-authored-by: “skzhang1” <“shaokunzhang529@gmail.com”>

[33mcommit 1ec77b58b4ccbf88fb06688dfd1e0cec793da0bf[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sun Mar 5 08:40:57 2023 -0800

    improve max_valid_n and doc (#933)
    
    * improve max_valid_n and doc
    
    * Update README.md
    
    Co-authored-by: Li Jiang <lijiang1@microsoft.com>
    
    * newline at end of file
    
    * doc
    
    ---------
    
    Co-authored-by: Li Jiang <lijiang1@microsoft.com>
    Co-authored-by: Susan Xueqing Liu <liususan091219@users.noreply.github.com>
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit 97928609baae78e84bb78bdbfb2eb21579a687ac[m
Author: Susan Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Sat Mar 4 20:15:49 2023 -0500

    adding openai documentation (#938)
    
    * adding openai documentation
    
    * adding openai documentation
    
    * Update website/docs/Examples/Integrate - OpenAI.md
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update website/docs/Examples/Integrate - OpenAI.md
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>
    
    * Update website/docs/Examples/Integrate - OpenAI.md
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update website/docs/Examples/Integrate - OpenAI.md
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update website/docs/Examples/Integrate - OpenAI.md
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * addressing comments
    
    * Update website/docs/Examples/Integrate - OpenAI.md
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update website/docs/Examples/Integrate - OpenAI.md
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * adding Azure
    
    * rerun
    
    * addressing comments about Azure
    
    ---------
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit 0b5a637f9aa17fa28e28f3c4d2a7d0502cb26722[m
Author: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>
Date:   Tue Feb 28 22:09:18 2023 -0500

    Bump http-cache-semantics from 4.1.0 to 4.1.1 in /website (#913)
    
    Bumps [http-cache-semantics](https://github.com/kornelski/http-cache-semantics) from 4.1.0 to 4.1.1.
    - [Release notes](https://github.com/kornelski/http-cache-semantics/releases)
    - [Commits](https://github.com/kornelski/http-cache-semantics/compare/v4.1.0...v4.1.1)
    
    ---
    updated-dependencies:
    - dependency-name: http-cache-semantics
      dependency-type: indirect
    ...
    
    Signed-off-by: dependabot[bot] <support@github.com>
    Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>
    Co-authored-by: Shaokun <shaokunzhang529@gmail.com>
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit a3409194584a6d2b5ec5de73947207caf3579778[m
Author: Jirka Borovec <6035284+Borda@users.noreply.github.com>
Date:   Tue Feb 28 17:29:07 2023 +0100

    adding precommit check (#930)
    
    * adding precommit check
    
    * run precommit
    
    * Apply suggestions from code review
    
    Co-authored-by: Zvi Baratz <z.baratz@gmail.com>
    
    * apply precommit
    
    ---------
    
    Co-authored-by: Zvi Baratz <z.baratz@gmail.com>

[33mcommit 2ff1035733af0f8465d8b0a0b43a1704ddece6e4[m
Author: Jirka Borovec <6035284+Borda@users.noreply.github.com>
Date:   Tue Feb 28 17:27:14 2023 +0100

    precommit: end-of-file-fixer (#929)
    
    * precommit: end-of-file-fixer
    
    * exclude .gitignore
    
    * apply
    
    ---------
    
    Co-authored-by: Shaokun <shaokunzhang529@gmail.com>

[33mcommit a3e368d2ca0bb1c449bbdbdf11c978510581d91d[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Fri Feb 24 02:43:18 2023 -0800

    minor change to notebook (#928)

[33mcommit c6a24403481368da8fe4ee5263850ec233af8b9a[m
Author: levscaut <57213911+levscaut@users.noreply.github.com>
Date:   Fri Feb 24 16:07:00 2023 +0800

    add PySparkOvertimeMonitor to avoid exceeding time budget (#923)
    
    * merging
    
    * clean commit
    
    * Delete mylearner.py
    
    This file is not needed.
    
    * fix py4j import error
    
    * more tolerant cancelling time
    
    * fix problems following suggestions
    
    * Update flaml/tune/spark/utils.py
    
    Co-authored-by: Li Jiang <bnujli@gmail.com>
    
    * remove redundant model
    
    * Update test/spark/custom_mylearner.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * add docstr
    
    * reverse change in gitignore
    
    * Update test/spark/custom_mylearner.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    ---------
    
    Co-authored-by: Li Jiang <bnujli@gmail.com>
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 4118c8e27f2cce00de4ae435213a9598e45e375c[m
Author: Xiaoyun Zhang <bigmiao.zhang@gmail.com>
Date:   Thu Feb 23 20:31:46 2023 -0800

    fix #493 (#932)
    
    * add custom meta feature function
    
    * Update flaml/default/suggest.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    ---------
    
    Co-authored-by: littlelittlecloud <g2260578356@gmail.com>
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 7c0340fde6971b3e812fe78b28d21780f47b7bd6[m
Author: Li Jiang <lijiang1@microsoft.com>
Date:   Thu Feb 23 13:23:24 2023 +0800

    Updated dict type args default value to None (#927)

[33mcommit 8e447562c70686f9433e4c245d6d691df40c9c5f[m
Author: Andrea Ruggerini <nescio.adv@gmail.com>
Date:   Wed Feb 22 03:49:56 2023 +0100

    Improve annotations in automl and ml modules (#919)
    
    * begin annotation in automl.py and ml.py
    
    * EstimatorSubclass + annotate metric
    
    * review: fixes + setting fit_kwargs as proper Optional
    
    * import from flaml.automl.model (import from flaml.model is deprecated)
    
    * comment n_jobs in train_estimator as well
    
    * better annotation in _compute_with_config_base
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>
    
    ---------
    
    Co-authored-by: Andrea W <a.ruggerini@ammagamma.com>
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit 6aa1d16ebc9973be7c52cb81b1ce644807b8e9ac[m
Author: Jirka Borovec <6035284+Borda@users.noreply.github.com>
Date:   Wed Feb 22 01:49:38 2023 +0100

    pre-commit: update config (#925)
    
    * update config
    
    * apply precommit

[33mcommit c18dd456c78231c7ba5f9dd1f808fe668c139f67[m
Author: Shaokun <shaokunzhang529@gmail.com>
Date:   Mon Feb 20 18:45:49 2023 -0500

    Fix Dependabot alerts (#922)
    
    * fix_alerts
    
    * clean up
    
    ---------
    
    Co-authored-by: “skzhang1” <“shaokunzhang529@gmail.com”>

[33mcommit 0eaac7d0185b622e3a8bde383fd0a0803f8012f8[m
Author: Animaholic <48635315+Animaholic@users.noreply.github.com>
Date:   Sat Feb 18 18:56:58 2023 -0500

    added a documentation about small time budget (#914)
    
    * added documentation about small time budget
    
    * small change for better clarity
    
    * Update website/docs/Use-Cases/Task-Oriented-AutoML.md
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    ---------
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 501a0b8eb89bda9f7d036729da0b033127fa184a[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Feb 18 08:07:27 2023 -0800

    bump version to 1.1.3; workflow trigger (#924)

[33mcommit 2273937e68b4ed6c5daec71b7d568cdb25217996[m
Author: Susan Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Fri Feb 17 18:52:36 2023 -0500

    Update hf version (#918)
    
    * update hf version
    
    * adding transformers version
    
    ---------
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 138eb78dbcc89fffa3f60d1a5c7ecff3c356e7bc[m
Author: Li Jiang <lijiang1@microsoft.com>
Date:   Sat Feb 18 00:38:55 2023 +0800

    Added extras for synapse (#916)
    
    * Added extras for synapse
    
    * Update Installation doc

[33mcommit 35ce9b79e8cc0670f0ad051460df1922f5f51add[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Thu Feb 16 15:38:50 2023 -0800

    azure oai (#920)
    
    * azure oai
    
    * price update in notebook
    
    * text Davinci
    
    * pytorch-lightning version
    
    * trigger action in merge queue
    
    * types
    
    * doc check in mege group

[33mcommit 671146146ad87a4cc5eadcee85f021c42ed511b6[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Wed Feb 8 20:47:07 2023 -0800

    workflow path->paths (#915)
    
    * workflow path->paths
    
    * Apply suggestions from code review
    
    Co-authored-by: Li Jiang <bnujli@gmail.com>
    
    ---------
    
    Co-authored-by: Li Jiang <bnujli@gmail.com>

[33mcommit 63d350d4c8cae5f5bdd686a97e737013fbd9641d[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sun Feb 5 20:13:08 2023 -0800

    Openai (#905)
    
    * add cost budget; move loc of make_dir
    
    * support openai completion
    
    * install pytest in workflow
    
    * skip openai test
    
    * test openai
    
    * path for docs rebuild
    
    * install datasets
    
    * signal
    
    * notebook
    
    * notebook in workflow
    
    * optional arguments and special params
    
    * key -> k
    
    * improve readability
    
    * assumption
    
    * optimize for model selection
    
    * larger range of max_tokens
    
    * notebook
    
    * python package workflow
    
    * skip on win

[33mcommit bcc6a197fd201bd8fe3f95e9608e28b991850880[m
Author: Animaholic <48635315+Animaholic@users.noreply.github.com>
Date:   Sun Feb 5 20:48:07 2023 -0500

    Add bibtex entries for research publications (#904)
    
    * Update Research.md
    
    * Update website/docs/Research.md
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update website/docs/Research.md
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update website/docs/Research.md
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update website/docs/Research.md
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update website/docs/Research.md
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update website/docs/Research.md
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update website/docs/Research.md
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    ---------
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit 3b6bfc2876e632d8334d19ebaa6a128d8f5c2d35[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sun Feb 5 16:34:59 2023 -0800

    add cost budget; move loc of make_dir (#888)
    
    * add cost budget; move loc of make_dir
    
    * remove None in return
    
    ---------
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit fbea1d06dd5cce3c42b4f5713f182452f52a33cc[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sun Feb 5 15:26:14 2023 -0800

    stratified group kfold splitter (#899)
    
    * stratified group kfold splitter
    
    * exclude catboost
    
    ---------
    
    Co-authored-by: Shaokun <shaokunzhang529@gmail.com>
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit cb3378d621270a154f6538be1f8e79e778f89b6f[m
Merge: 50a7b62 d0f7b30
Author: Shaokun <shaokunzhang529@gmail.com>
Date:   Sat Feb 4 09:18:05 2023 -0500

    Merge pull request #912 from microsoft/tutorial-updates
    
    update doc for research papers

[33mcommit d0f7b30b61c992a2ce00b332cfe484b339148e18[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Fri Feb 3 16:57:16 2023 -0800

    update doc for research papers

[33mcommit 50a7b624d15fdfea41ef0e0a5e5b8c742af6b7fa[m
Merge: 871f377 c6f8e00
Author: Shaokun <shaokunzhang529@gmail.com>
Date:   Tue Jan 31 15:19:53 2023 -0500

    Merge pull request #894 from coffepowered/first_contribution
    
    Document how to use the group k-fold

[33mcommit c6f8e004e78cf1d728e898a0011284c1dfb4b41a[m
Author: skzhang1 <shaokunzhang529@gmail.com>
Date:   Mon Jan 30 06:01:20 2023 -0800

    fix link

[33mcommit 58ac6b61c46080ac901a828d74f2ad96bbd83c09[m
Merge: 3e6247a df5efa5
Author: Andrea W <a.ruggerini@ammagamma.com>
Date:   Mon Jan 30 11:21:43 2023 +0000

    Merge branch 'first_contribution' of https://github.com/coffepowered/FLAML into first_contribution

[33mcommit 3e6247ae590b681a884282662fb68fce62ae6a1a[m
Author: Andrea W <a.ruggerini@ammagamma.com>
Date:   Mon Jan 30 11:17:27 2023 +0000

    add link to notebook showing group cv

[33mcommit df5efa5c2d9d91fb75c723b2f87e39ace81de79d[m
Merge: 7644265 871f377
Author: Shaokun <shaokunzhang529@gmail.com>
Date:   Sun Jan 29 22:56:45 2023 -0500

    Merge branch 'main' into first_contribution

[33mcommit 871f3776f3fd3d88c59ea40290be08db8767d715[m
Merge: d46532e b342337
Author: Shaokun <shaokunzhang529@gmail.com>
Date:   Sun Jan 29 14:08:46 2023 -0500

    Merge pull request #875 from skzhang1/support_percentages
    
    Support percentage tolerance for lexicographic optimization

[33mcommit 7644265d1f0f9b8f2f0eadfc73baa36ce441d048[m
Merge: 2f93736 d46532e
Author: Shaokun <shaokunzhang529@gmail.com>
Date:   Sun Jan 29 10:48:16 2023 -0500

    Merge branch 'main' into first_contribution

[33mcommit b342337875833a462cbbc2a6afd144bfd25b38e1[m
Merge: 175a2ea d46532e
Author: Shaokun <shaokunzhang529@gmail.com>
Date:   Sun Jan 29 10:39:41 2023 -0500

    Merge branch 'main' into support_percentages

[33mcommit d46532efda14f7b2567c12729c406f207d317454[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Jan 28 15:42:49 2023 -0800

    display data head in notebook; exclude None (#885)

[33mcommit 175a2eaaf6981170940810117533db8545310d47[m
Merge: b8982f7 dbd48c5
Author: Shaokun <shaokunzhang529@gmail.com>
Date:   Sat Jan 28 10:00:57 2023 -0500

    Merge branch 'main' into support_percentages

[33mcommit b8982f7cf2a1d95489bf99fae2c622b9838fcab8[m
Author: skzhang1 <shaokunzhang529@gmail.com>
Date:   Sat Jan 28 06:58:58 2023 -0800

    update

[33mcommit 184251a2a72ebe568040051ba88a4a3141660d7f[m
Author: skzhang1 <shaokunzhang529@gmail.com>
Date:   Sat Jan 28 06:53:37 2023 -0800

    update

[33mcommit dbd48c555fcfea4a92753bfc6d5f755222b65107[m
Merge: cdc4201 b740d79
Author: Shaokun <shaokunzhang529@gmail.com>
Date:   Fri Jan 27 21:25:44 2023 -0500

    Merge pull request #900 from microsoft/dependabot/npm_and_yarn/website/ua-parser-js-0.7.33
    
    Bump ua-parser-js from 0.7.32 to 0.7.33 in /website

[33mcommit b740d79369f7b933c34fb1fd08d58851282df366[m
Author: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>
Date:   Fri Jan 27 17:35:14 2023 +0000

    Bump ua-parser-js from 0.7.32 to 0.7.33 in /website
    
    Bumps [ua-parser-js](https://github.com/faisalman/ua-parser-js) from 0.7.32 to 0.7.33.
    - [Release notes](https://github.com/faisalman/ua-parser-js/releases)
    - [Changelog](https://github.com/faisalman/ua-parser-js/blob/master/changelog.md)
    - [Commits](https://github.com/faisalman/ua-parser-js/compare/0.7.32...0.7.33)
    
    ---
    updated-dependencies:
    - dependency-name: ua-parser-js
      dependency-type: indirect
    ...
    
    Signed-off-by: dependabot[bot] <support@github.com>

[33mcommit 2f93736740a27ad5a1a7d994858e9da697ccce0f[m
Author: Andrea W <a.ruggerini@ammagamma.com>
Date:   Fri Jan 27 10:00:16 2023 +0000

    remove postponed eval of annotations from automl.py

[33mcommit bdbba6e3bc49ae40f43b24afb7bcc57c6bfe5539[m
Author: Andrea W <a.ruggerini@ammagamma.com>
Date:   Thu Jan 26 14:31:54 2023 +0000

    modify doc

[33mcommit 297fc5ad7c2dc2268496c249db8698b7e1c562b4[m
Author: Andrea W <a.ruggerini@ammagamma.com>
Date:   Thu Jan 26 14:18:55 2023 +0000

    annotate state, add cv notebook

[33mcommit cdc4201188565e74507c026f86abe540ade4cb72[m
Author: Shaokun <shaokunzhang529@gmail.com>
Date:   Wed Jan 18 14:35:57 2023 -0500

    update (#883)

[33mcommit 60a3e85b98e03a565b5e5ef41fe4531fc5e2da07[m
Merge: 3a68da8 100bfe2
Author: Shaokun <shaokunzhang529@gmail.com>
Date:   Tue Jan 17 10:06:51 2023 -0500

    Merge branch 'main' into support_percentages

[33mcommit 3a68da87742c040bbd1321bf435c57d4ccd3be43[m
Author: skzhang1 <shaokunzhang529@gmail.com>
Date:   Tue Jan 17 06:49:59 2023 -0800

    update

[33mcommit 100bfe2d43c640517f23c796417ea2375b59b314[m
Author: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>
Date:   Tue Jan 10 09:39:29 2023 -0800

    Bump json5 from 2.2.1 to 2.2.3 in /website (#877)
    
    Bumps [json5](https://github.com/json5/json5) from 2.2.1 to 2.2.3.
    - [Release notes](https://github.com/json5/json5/releases)
    - [Changelog](https://github.com/json5/json5/blob/main/CHANGELOG.md)
    - [Commits](https://github.com/json5/json5/compare/v2.2.1...v2.2.3)
    
    ---
    updated-dependencies:
    - dependency-name: json5
      dependency-type: indirect
    ...
    
    Signed-off-by: dependabot[bot] <support@github.com>
    
    Signed-off-by: dependabot[bot] <support@github.com>
    Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>
    Co-authored-by: Shaokun <shaokunzhang529@gmail.com>

[33mcommit 7b07b9778df4bc05d1d3b0efbb664c081875b457[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Jan 10 07:04:28 2023 -0800

    handle num_samples=-1 (#879)
    
    * handle num_samples=-1
    
    * comment on num_samples=0

[33mcommit 75e3454120fbc3be1778ce01375852607ea29b30[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Jan 7 18:39:29 2023 -0800

    notebook test; spark warning message; reproducibility bug; sequential tuning stop condition (#869)
    
    * notebook test
    
    * add ipykernel, remove except
    
    * only create dir if not empty
    
    * Stop sequential tuning when result is None
    
    * fix reproducibility of global search
    
    * save gs seed
    
    * use get to avoid KeyError
    
    * test

[33mcommit b7c0c242697a13a4cceae8cde9eb5156188ebc29[m
Author: skzhang1 <shaokunzhang529@gmail.com>
Date:   Sat Jan 7 11:41:24 2023 -0800

    support percentage tolerance for lexicographic

[33mcommit 9fde27e536438b82e15fcee0317136c4457d8d38[m
Author: Li Jiang <bnujli@gmail.com>
Date:   Sat Jan 7 23:41:35 2023 +0800

    fix #871: call check_spark only when necessary (#872)
    
    Co-authored-by: Li Jiang <lijiang1@microsoft.com>

[33mcommit 5f67c0ab8af693eb42d0a82bc2db3243c93f350d[m
Author: Antoni Baum <antoni.baum@protonmail.com>
Date:   Fri Jan 6 03:00:05 2023 +0100

    Do not persist entire AutoMLState in Searcher (#870)
    
    * Do not persist entire AutoMLState in Searcher
    
    Signed-off-by: Antoni Baum <antoni.baum@protonmail.com>
    
    * Fix tests
    
    Signed-off-by: Antoni Baum <antoni.baum@protonmail.com>
    
    Signed-off-by: Antoni Baum <antoni.baum@protonmail.com>

[33mcommit 90aea9c28b6100faf86f2c204e53a68e87f10c66[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Fri Dec 30 10:21:30 2022 -0800

    create dir for log file name (#867)

[33mcommit b78d0b57c498ab852aec7f8d30bc782d7914ff69[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sun Dec 25 11:43:22 2022 -0800

    Info and naming (#864)
    
    * remove __class__
    
    * var name

[33mcommit da2cd7ca890c467562cdf93ac160e40e1144b8b8[m
Author: Li Jiang <bnujli@gmail.com>
Date:   Sat Dec 24 00:18:49 2022 +0800

    Add supporting using Spark as the backend of parallel training (#846)
    
    * Added spark support for parallel training.
    
    * Added tests and fixed a bug
    
    * Added more tests and updated docs
    
    * Updated setup.py and docs
    
    * Added customize_learner and tests
    
    * Update spark tests and setup.py
    
    * Update docs and verbose
    
    * Update logging, fix issue in cloud notebook
    
    * Update github workflow for spark tests
    
    * Update github workflow
    
    * Remove hack of handling _choice_
    
    * Allow for failures
    
    * Fix tests, update docs
    
    * Update setup.py
    
    * Update Dockerfile for Spark
    
    * Update tests, remove some warnings
    
    * Add test for notebooks, update utils
    
    * Add performance test for Spark
    
    * Fix lru_cache maxsize
    
    * Fix test failures on some platforms
    
    * Fix coverage report failure
    
    * resovle PR comments
    
    * resovle PR comments 2nd round
    
    * resovle PR comments 3rd round
    
    * fix lint and rename test class
    
    * resovle PR comments 4th round
    
    * refactor customize_learner to broadcast_code

[33mcommit 4140fc90225816b28d5b9dc9eb5b7ff8063b81b7[m
Author: Shaokun <shaokunzhang529@gmail.com>
Date:   Thu Dec 22 22:36:34 2022 -0500

    Format errors on the web. (#855)
    
    * fix_doc
    
    * update
    
    * fix lint
    
    * fix lint
    
    * reformat
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit f98b7555e96599924d12a23c827f80c910bb6894[m
Merge: b2d51b6 91ec8e9
Author: Shaokun <shaokunzhang529@gmail.com>
Date:   Mon Dec 19 16:38:19 2022 -0500

    Merge pull request #853 from jingdong00/jingdong00-patch-1
    
    Fix example tune-pytorch where the checkpoint path may be named differently

[33mcommit 91ec8e9355f558f0d06dc3dd2acad1f0ce676190[m
Merge: 3a194d0 b2d51b6
Author: Shaokun <shaokunzhang529@gmail.com>
Date:   Mon Dec 19 12:40:58 2022 -0500

    Merge branch 'main' into jingdong00-patch-1

[33mcommit 3a194d047bae043fbdc79dfd3cde05be8687dc49[m
Author: Jing Dong <jindong@umich.edu>
Date:   Mon Dec 19 09:22:16 2022 -0800

    fix checkpoint.value in the notebook and test

[33mcommit b2d51b648c7a9bfdda3c07989656101474877867[m
Author: Jing Dong <35925336+jingdong00@users.noreply.github.com>
Date:   Mon Dec 19 01:49:00 2022 +0800

    Added an info reminding user that if no time_budget and no max_iter is specified, then effectively zero-shot AutoML is used (#850)
    
    * Added an info reminding user that if no time_budget and no max_iter is specified, then effectively zero-shot AutoML is used
    
    * moved message to line 2818
    
    * Update flaml/automl/automl.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update flaml/automl/automl.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit 7e4e4c7901897983bc45d5546ac869c83edf702f[m
Author: skzhang1 <shaokunzhang529@gmail.com>
Date:   Sat Dec 17 13:34:11 2022 -0500

    clean up

[33mcommit 68886053881336142809673a8afb93a7b6d89009[m
Author: skzhang1 <shaokunzhang529@gmail.com>
Date:   Sat Dec 17 13:31:52 2022 -0500

    remove

[33mcommit 5778227a714396815502cfed0f2d5a9900ee105f[m
Author: Jing Dong <35925336+jingdong00@users.noreply.github.com>
Date:   Fri Dec 16 14:41:33 2022 +0800

    Fix checkpoint path issue
    
    checkpoint path may be named dir_or_data instead of value

[33mcommit c1872861b671dd98c272d6deabf49ad3c7ea27e7[m
Merge: f6aa8ee 2b203ca
Author: Jing Dong <35925336+jingdong00@users.noreply.github.com>
Date:   Fri Dec 16 14:31:08 2022 +0800

    Merge branch 'microsoft:main' into main

[33mcommit 2b203ca69406ef8e2188693eb91a555fc7943700[m
Author: Luis Quintanilla <46974588+luisquintanilla@users.noreply.github.com>
Date:   Tue Dec 13 22:56:45 2022 -0500

    Update .NET documentation links (#847)
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit 23384319903632609be629c8a5327c21aaa635eb[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Dec 13 15:09:50 2022 -0800

    FAQ about OOM (#849)
    
    * FAQ about OOM
    
    * reduce -> resolve

[33mcommit f6aa8eed3f30ac3c0207efa9c07fd15a2a76da44[m
Author: Jing Dong <jindong@umich.edu>
Date:   Tue Dec 13 14:19:09 2022 -0800

    Added an info reminding user that if no time_budget and no max_iter is specified, then effectively zero-shot AutoML is used

[33mcommit 232c356a4bfd6e67d9a3ca92af8200680d7eb22e[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Dec 13 12:48:32 2022 -0800

    fix bug related to _choice_ (#848)
    
    * fix bug related to _choice_
    
    * remove py 3.6
    
    * sanitize config
    
    * optimize test

[33mcommit f50415305fd444bb6611589a297e4912b32ff18c[m
Merge: dbc2e2d 24eb0e9
Author: Shaokun <shaokunzhang529@gmail.com>
Date:   Wed Dec 7 15:54:52 2022 -0500

    Merge pull request #843 from skzhang1/update_doc
    
    Update doc

[33mcommit 24eb0e9227bda007f97858c708a4786c7fb075d3[m
Merge: 1030385 dbc2e2d
Author: Shaokun <shaokunzhang529@gmail.com>
Date:   Wed Dec 7 13:05:00 2022 -0500

    Merge branch 'main' into update_doc

[33mcommit 10303854e273c74e3e7e813db4bf94e84bcf01f6[m
Author: Shaokun <shaokun.zhang@psu.edu>
Date:   Wed Dec 7 13:04:55 2022 -0500

    Update website/docs/Examples/Tune-Lexicographic-objectives.md
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 28c7626e99a285c1b0e4e47213b255b966b156c6[m
Author: Shaokun <shaokun.zhang@psu.edu>
Date:   Wed Dec 7 10:57:33 2022 -0500

    Update Tune-Lexicographic-objectives.md

[33mcommit dbc2e2d7963c36ec6111c22a79476ad522dd04ec[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Dec 6 22:23:45 2022 -0800

    Use get to avoid KeyError (#824)
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>
    Co-authored-by: Kevin Chen <74878789+int-chaos@users.noreply.github.com>

[33mcommit 2a4d9d3eccd9039498928dab9064ec404dfbecb1[m
Merge: 5adce62 f8fa525
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Tue Dec 6 21:41:07 2022 -0500

    Merge branch 'main' into update_doc

[33mcommit f8fa5258e1a846d7627472806c9c111fc4706f5e[m
Author: HangHouCheong <89648965+HangHouCheong@users.noreply.github.com>
Date:   Wed Dec 7 10:27:15 2022 +0800

    Edit the announcement of AAAI-23 tutorial and the KDD tutorial announcement. (#820)
    
    * AAAI
    
    * KDD
    
    * Update README.md
    
    Co-authored-by: Kevin Chen <74878789+int-chaos@users.noreply.github.com>
    
    * Update README.md
    
    Co-authored-by: Kevin Chen <74878789+int-chaos@users.noreply.github.com>
    
    * revise
    
    * Update README.md
    
    * Update README.md
    
    * Update README.md
    
    * Update README.md
    
    * Update README.md
    
    * Exchange_order
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>
    Co-authored-by: Kevin Chen <74878789+int-chaos@users.noreply.github.com>

[33mcommit 5adce62857e7dc3f9d4547e5e9ad7bf21be09603[m
Author: skzhang1 <shaokunzhang529@gmail.com>
Date:   Tue Dec 6 20:42:06 2022 -0500

    update

[33mcommit 44ddf9e1046581748341c5f0762277bd735de9ba[m
Author: Mark Harley <mharley.code@gmail.com>
Date:   Tue Dec 6 20:46:08 2022 +0000

    Refactor into automl subpackage (#809)
    
    * Refactor into automl subpackage
    
    Moved some of the packages into an automl subpackage to tidy before the
    task-based refactor. This is in response to discussions with the group
    and a comment on the first task-based PR.
    
    Only changes here are moving subpackages and modules into the new
    automl, fixing imports to work with this structure and fixing some
    dependencies in setup.py.
    
    * Fix doc building post automl subpackage refactor
    
    * Fix broken links in website post automl subpackage refactor
    
    * Fix broken links in website post automl subpackage refactor
    
    * Remove vw from test deps as this is breaking the build
    
    * Move default back to the top-level
    
    I'd moved this to automl as that's where it's used internally, but had
    missed that this is actually part of the public interface so makes sense
    to live where it was.
    
    * Re-add top level modules with deprecation warnings
    
    flaml.data, flaml.ml and flaml.model are re-added to the top level,
    being re-exported from flaml.automl for backwards compatability. Adding
    a deprecation warning so that we can have a planned removal later.
    
    * Fix model.py line-endings
    
    * Pin pytorch-lightning to less than 1.8.0
    
    We're seeing strange lightning related bugs from pytorch-forecasting
    since the release of lightning 1.8.0. Going to try constraining this to
    see if we have a fix.
    
    * Fix the lightning version pin
    
    Was optimistic with setting it in the 1.7.x range, but that isn't
    compatible with python 3.6
    
    * Remove lightning version pin
    
    * Revert dependency version changes
    
    * Minor change to retrigger the build
    
    * Fix line endings in ml.py and model.py
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>
    Co-authored-by: EgorKraevTransferwise <egor.kraev@transferwise.com>

[33mcommit 92b79221b67cad7e7d4f7fc7c622d3f58c513a7e[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Dec 6 10:13:39 2022 -0800

    make performance test reproducible (#837)
    
    * make performance test reproducible
    
    * fix test error
    
    * Doc update and disable logging
    
    * document random_state and version
    
    * remove hardcoded budget
    
    * fix test error and dependency; close #777
    
    * iloc

[33mcommit 3b3b0bfa8e5cc6d8ffabc191b0ee574621547e72[m
Author: Shreyas <53392583+shreyas36@users.noreply.github.com>
Date:   Sat Dec 3 08:57:32 2022 +0530

    roc_auc_weighted metric addition (#827)
    
    * Pending changes exported from your codespace
    
    * Update flaml/automl.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update flaml/automl.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update flaml/ml.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update flaml/ml.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update website/docs/Examples/Integrate - Scikit-learn Pipeline.md
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * added documentation for new metric
    
    * Update flaml/ml.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * minor notebook changes
    
    * Update Integrate - Scikit-learn Pipeline.md
    
    * Update notebook/automl_classification.ipynb
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update integrate_azureml.ipynb
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit d213ae8f396166a4720e2bb2ed27eb7d1b753394[m
Author: Kevin Chen <74878789+int-chaos@users.noreply.github.com>
Date:   Fri Dec 2 16:56:59 2022 -0500

    catch TFT logger bugs (#833)
    
    * catch logger bugs
    
    * indentations issues
    
    * fix logger issues
    
    * specify exception
    
    * document reason for exception
    
    * update exceptions
    
    * disable callbacks when `logger=False`
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit 2501b86444f321efedee34eb7ecf130f7f33f9ed[m
Author: Li Jiang <bnujli@gmail.com>
Date:   Thu Dec 1 09:04:29 2022 +0800

    fix typo of output directory (#828)
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 70d86942f4afe9bad1659bb71355417246d1b095[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Nov 29 13:10:35 2022 -0800

    skip test in py 3.6 (#832)

[33mcommit 595af7a04f98e664b1f5dc0ba5b7cfefe26546cc[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sun Nov 27 11:22:54 2022 -0800

    install editable package in codespace (#826)
    
    * install editable package in codespace
    
    * fix test error in test_forecast
    
    * fix test error in test_space
    
    * openml version
    
    * break tests; pre-commit
    
    * skip on py10+win32
    
    * install mlflow in test
    
    * install mlflow in [test]
    
    * skip test in windows
    
    * import
    
    * handle PermissionError
    
    * skip test in windows
    
    * skip test in windows
    
    * skip test in windows
    
    * skip test in windows
    
    * remove ts_forecast_panel from doc

[33mcommit 586afe0d6b15d64361440820a22014abd3462c63[m
Author: Shaokun Zhang <shaokunzhang529@gmail.com>
Date:   Tue Nov 22 11:58:02 2022 -0500

    fix typo (#823)

[33mcommit 54220d675291d640275b4a1e6997d07812ba4762[m
Merge: beea11a fda42fb
Author: Shaokun Zhang <shaokunzhang529@gmail.com>
Date:   Wed Nov 16 16:35:13 2022 -0500

    Merge pull request #818 from skzhang1/fix_alert
    
    fix dependably alert

[33mcommit fda42fb576550fd3174474d740572811f9843f92[m
Author: skzhang1 <shaokunzhang529@gmail.com>
Date:   Wed Nov 16 14:58:41 2022 -0500

    upgrade

[33mcommit beea11adebb6e23b963fe3d6e8491dfbdf585d79[m
Merge: 5eb9927 3466e38
Author: Shaokun Zhang <shaokunzhang529@gmail.com>
Date:   Tue Nov 15 21:20:23 2022 -0500

    Merge pull request #699 from microsoft/dependabot/github_actions/actions/checkout-3
    
    Bump actions/checkout from 2 to 3

[33mcommit 3466e38549be87492e56c6ba97237f28440a7e86[m
Merge: e90ea72 5eb9927
Author: Shaokun Zhang <shaokunzhang529@gmail.com>
Date:   Tue Nov 15 15:10:40 2022 -0500

    Merge branch 'main' into dependabot/github_actions/actions/checkout-3

[33mcommit 5eb99276423f8ac88b7fe38c37d9b7f37fafe4fb[m
Author: Anonymous-submission-repo <79179917+Anonymous-submission-repo@users.noreply.github.com>
Date:   Tue Nov 15 10:44:53 2022 -0500

    Add performance test for LexiFlow  (#812)
    
    * add test
    
    * fix
    
    * change test name

[33mcommit cb3402052fe1f6e7f67425d89784c09938b75793[m
Author: shreyas36 <53392583+shreyas36@users.noreply.github.com>
Date:   Tue Nov 15 01:59:36 2022 +0530

    added the models used for forecasting in documentation (#811)

[33mcommit 30e200985c171e6a4dd7606a064084aaee19cce6[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sun Nov 13 12:47:59 2022 -0800

    Fix issues related to zero-shot automl (#783)
    
    * skip in-search-space check for small max iter
    
    * resolve Pickle Transformer #730
    
    * resolve default config unrecognized #784
    
    * Change definition of init_config
    
    * copy points_to_evaluate
    
    * make test pass
    
    * check learner selector

[33mcommit 9a7a9ef1c63f33bd05de532f40232b39fc654534[m
Author: Jing Dong <35925336+jingdong00@users.noreply.github.com>
Date:   Sun Nov 13 10:36:06 2022 +0800

    Added a link to documentation webpage in notebook time_series_forcast (#791)
    
    * added a link to documentation webpage in notebook time_series_forcast
    
    * added a link to documentation webpage in notebook time_series_forcast
    
    * Update notebook/automl_time_series_forecast.ipynb
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * complete output
    
    * added all cell output
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    Co-authored-by: zsk <shaokunzhang529@gmail.com>
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit 2531980dc3a77379e832ab7d670644c6445efb55[m
Merge: d2bc168 7d11e3c
Author: Shaokun Zhang <shaokunzhang529@gmail.com>
Date:   Tue Nov 8 22:26:33 2022 -0500

    Merge pull request #802 from royninja/main
    
    Documentation about classification/regression task #753

[33mcommit 7d11e3cf40365ef4acc73d7535124fe634bc3050[m
Merge: 289f4d6 d2bc168
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Mon Nov 7 08:07:33 2022 -0500

    Merge branch 'main' into main

[33mcommit e90ea72dd6e8c04d98f48d62070e7bc6bf4673db[m
Merge: 0ecfe60 d2bc168
Author: zsk <shaokunzhang529@gmail.com>
Date:   Sun Nov 6 18:28:17 2022 -0500

    Merge branch 'main' into dependabot/github_actions/actions/checkout-3

[33mcommit d2bc168f3692ac41c8f13e1464a078879aa38a45[m
Merge: 1ed3426 6779584
Author: zsk <shaokunzhang529@gmail.com>
Date:   Sun Nov 6 18:27:40 2022 -0500

    Merge pull request #799 from skzhang1/fix_alert
    
    fix_alerts

[33mcommit 289f4d61d300853011ea38f7bd20ed6b2ecc3c92[m
Merge: f1d4adf 1ed3426
Author: Sayan Roy <sayan98.roy@gmail.com>
Date:   Mon Nov 7 01:34:15 2022 +0530

    Merge branch 'microsoft:main' into main

[33mcommit f1d4adf4ff82ded977874a419b11f380e71bde66[m
Author: Sayan Roy <sayan98.roy@gmail.com>
Date:   Mon Nov 7 01:29:12 2022 +0530

    limiting the scope to tabular data.
    
    limiting the scope to tabular data.

[33mcommit 67795848045d6fbd271c3f2e2fe8676b81373ed1[m
Author: skzhang1 <shaokunzhang529@gmail.com>
Date:   Sat Nov 5 15:21:32 2022 -0400

    fix_alerts

[33mcommit 0ecfe60196755453b1f8392a4c7aea5fb12e5a35[m
Merge: b58151b 1ed3426
Author: zsk <shaokunzhang529@gmail.com>
Date:   Sat Nov 5 11:17:34 2022 -0400

    Merge branch 'main' into dependabot/github_actions/actions/checkout-3

[33mcommit 1ed342617ebeefee84431fa8996b99827a99d518[m
Merge: 53d8d62 9584321
Author: zsk <shaokunzhang529@gmail.com>
Date:   Sat Nov 5 09:48:26 2022 -0400

    Merge pull request #797 from ElinaAndreeva/main
    
    Fixed typo

[33mcommit 958432190f2eb8594bbe70526d66d391d63f2f88[m
Merge: 723662c 53d8d62
Author: zsk <shaokunzhang529@gmail.com>
Date:   Fri Nov 4 23:07:13 2022 -0400

    Merge branch 'main' into main

[33mcommit b58151b3faf35a9489da500b7b7743c88edcfc0c[m
Author: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>
Date:   Fri Nov 4 23:23:27 2022 +0000

    Bump actions/checkout from 2 to 3
    
    Bumps [actions/checkout](https://github.com/actions/checkout) from 2 to 3.
    - [Release notes](https://github.com/actions/checkout/releases)
    - [Changelog](https://github.com/actions/checkout/blob/main/CHANGELOG.md)
    - [Commits](https://github.com/actions/checkout/compare/v2...v3)
    
    ---
    updated-dependencies:
    - dependency-name: actions/checkout
      dependency-type: direct:production
      update-type: version-update:semver-major
    ...
    
    Signed-off-by: dependabot[bot] <support@github.com>

[33mcommit 53d8d62348920d7af6b9b3f07fdb50e0ec1b0fcb[m
Merge: d25330c 8856fff
Author: zsk <shaokunzhang529@gmail.com>
Date:   Fri Nov 4 19:22:50 2022 -0400

    Merge pull request #793 from skzhang1/fix_alert
    
    fix_alert

[33mcommit 8856fff44a4202a213f8d984e8acad7d90a42fd8[m
Merge: 944e560 d25330c
Author: zsk <shaokunzhang529@gmail.com>
Date:   Fri Nov 4 16:05:40 2022 -0400

    Merge branch 'main' into fix_alert

[33mcommit 944e56028b9d80d3f9e4fe50c75df6f7b9c0f545[m
Author: skzhang1 <shaokunzhang529@gmail.com>
Date:   Fri Nov 4 11:20:21 2022 -0400

    fix

[33mcommit d25330c497ed5fd4ca9be2d05fa9da225b69537d[m
Merge: d3f83d8 ddebfae
Author: zsk <shaokunzhang529@gmail.com>
Date:   Fri Nov 4 09:16:21 2022 -0400

    Merge pull request #790 from satya-vinay/issue-775
    
    Removed extra | in documentation

[33mcommit 723662c5025747dd67d57ce56ea23ad1daeb838b[m
Author: ElinaAndreeva <lolaclouds@yandex.ru>
Date:   Fri Nov 4 12:06:07 2022 +0400

    Fixed typo

[33mcommit 7b1fad4e5f2d836d812b383a976a2264c82584fd[m
Author: skzhang1 <shaokunzhang529@gmail.com>
Date:   Thu Nov 3 11:23:15 2022 -0400

    update yarn.lock

[33mcommit 991eaa8be8095adcc0a9f45f7cc9336daab6fa9f[m
Author: skzhang1 <shaokunzhang529@gmail.com>
Date:   Thu Nov 3 10:02:23 2022 -0400

    fix_alert

[33mcommit ddebfaea1cf925874831581bad2eeb3f705315ac[m
Author: satya-vinay <satyavinay2@gmail.com>
Date:   Thu Nov 3 13:30:42 2022 +0530

    Removed extra | in documentation

[33mcommit d3f83d8b48d6da445199caa38b3614ea86048264[m
Merge: af586e3 d6fd89a
Author: zsk <shaokunzhang529@gmail.com>
Date:   Tue Nov 1 21:33:01 2022 -0400

    Merge pull request #697 from microsoft/dependabot/github_actions/codecov/codecov-action-3
    
    Bump codecov/codecov-action from 1 to 3

[33mcommit d6fd89a80a9ca2675c01d30e1781e72cda4ab668[m
Merge: 0d6714c af586e3
Author: zsk <shaokunzhang529@gmail.com>
Date:   Tue Nov 1 20:13:22 2022 -0400

    Merge branch 'main' into dependabot/github_actions/codecov/codecov-action-3

[33mcommit af586e3b399206d094e6beaf1b152cd5571277b1[m
Merge: 65ad650 beb3419
Author: zsk <shaokunzhang529@gmail.com>
Date:   Tue Nov 1 20:13:12 2022 -0400

    Merge pull request #700 from microsoft/dependabot/github_actions/actions/setup-python-4
    
    Bump actions/setup-python from 2 to 4

[33mcommit 0d6714c05f7ccc408e73e5d041a2ef2334aead66[m
Merge: dfdef8d 65ad650
Author: zsk <shaokunzhang529@gmail.com>
Date:   Tue Nov 1 16:07:09 2022 -0400

    Merge branch 'main' into dependabot/github_actions/codecov/codecov-action-3

[33mcommit beb3419e8409d8852e29d4eea31e186cb7ebefbf[m
Merge: 06cff07 65ad650
Author: zsk <shaokunzhang529@gmail.com>
Date:   Tue Nov 1 16:07:01 2022 -0400

    Merge branch 'main' into dependabot/github_actions/actions/setup-python-4

[33mcommit 65ad6508ce360d5b3a0135c743819cd47cc71736[m
Author: Nicolas Beltran-Velez <61052993+velezbeltran@users.noreply.github.com>
Date:   Tue Nov 1 15:14:08 2022 -0400

    Docs (#765)
    
    * Small docstring change for clarity
    
    * Added tentative changes to docs
    
    * Update website/docs/Use-Cases/Task-Oriented-AutoML.md
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update flaml/model.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Updated model.py to reflect `n_jobs = None` suggestion
    
    * Updated tutorial to reflect `n_jobs=None` suggestion
    
    * Update model.py
    
    Improved string
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit dfdef8db32018744d1beb36344ada6f5eddb71cc[m
Merge: d7f5a54 29dea3a
Author: zsk <shaokunzhang529@gmail.com>
Date:   Tue Nov 1 11:07:47 2022 -0400

    Merge branch 'main' into dependabot/github_actions/codecov/codecov-action-3

[33mcommit 06cff076f0b393bbf627d6bc44da08f12c4f35e2[m
Merge: c224694 29dea3a
Author: zsk <shaokunzhang529@gmail.com>
Date:   Tue Nov 1 11:07:39 2022 -0400

    Merge branch 'main' into dependabot/github_actions/actions/setup-python-4

[33mcommit 29dea3a983f2a334343e96024e27c8712650d840[m
Merge: b63f1bc 4d4e6ba
Author: zsk <shaokunzhang529@gmail.com>
Date:   Tue Nov 1 11:03:49 2022 -0400

    Merge pull request #786 from evensure/patch-1
    
    Included hint to escape brackets for pip setup

[33mcommit 4d4e6ba499aac9e71e2e051f5a18c4ed904eca39[m
Author: evensure <42479629+evensure@users.noreply.github.com>
Date:   Mon Oct 31 17:51:11 2022 +0100

    Added hint to escape brackets for pip setup
    
    As described in #777, I had trouble executing the setup using zsh.
    Eventually, I noticed that I had to escape the brackets.
    
    My proposed change includes both brackets to be escaped, however for me it was enough to escape the opening one only, since as far as I know a trailing non-escaped closing bracket will then be recognized, accordingly.

[33mcommit b63f1bc8b8b511932d3c519e0e214bd706e94068[m
Author: Kirito <74639234+Kirito-Excalibur@users.noreply.github.com>
Date:   Sun Oct 30 09:45:46 2022 +0530

    Indentation corrected (#778)

[33mcommit 58227a976bdbf91617a639831f1ed247bcc41538[m
Merge: 774773e 79c479a
Author: zsk <shaokunzhang529@gmail.com>
Date:   Wed Oct 19 09:23:47 2022 -0400

    Merge pull request #752 from Anonymous-submission-repo/LexiFlow
    
    Multiple objectives hyperparameter tuning with lexicographic preference

[33mcommit 79c479ae4662fed09c85d3f6f60753d87af28a83[m
Author: Anonymous-submission-repo <hahahah2021@163.com>
Date:   Tue Oct 18 23:18:09 2022 +0000

    update

[33mcommit e5b3cb4ef26b70585800d6ebc45d30c2a7e0009d[m
Author: Anonymous-submission-repo <hahahah2021@163.com>
Date:   Tue Oct 18 18:02:49 2022 +0000

    update

[33mcommit 02d643bc8037abe7f151a9f65e94bafe19c32537[m
Author: Anonymous-submission-repo <hahahah2021@163.com>
Date:   Tue Oct 18 17:33:12 2022 +0000

    update

[33mcommit 2f8f8ba9d851c2175863e29a85f9a5e998d9590a[m
Author: Anonymous-submission-repo <hahahah2021@163.com>
Date:   Tue Oct 18 14:48:04 2022 +0000

    update

[33mcommit 8bad7e7ea53d0f30a9f3859b8f78b070548c0729[m
Merge: e42cfab 774773e
Author: Anonymous-submission-repo <79179917+Anonymous-submission-repo@users.noreply.github.com>
Date:   Tue Oct 18 10:17:03 2022 -0400

    Merge branch 'main' into LexiFlow

[33mcommit e42cfabf219e6aff2883b533cf6e8960b055ba58[m
Author: Anonymous-submission-repo <hahahah2021@163.com>
Date:   Tue Oct 18 13:45:23 2022 +0000

    fix

[33mcommit 0869e9e99a082cbff9a2b932c86f498b38dbf65b[m
Author: Anonymous-submission-repo <hahahah2021@163.com>
Date:   Tue Oct 18 13:33:37 2022 +0000

    clean up

[33mcommit 774773eb5be673f84d474f59f6e85cf47ec7bd8e[m
Author: Susan Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Sat Oct 15 22:35:49 2022 -0400

    fix bug in current nlp documentation (#763)
    
    * fix bug in current nlp documentation
    
    * fixing nlp documentation bug
    
    * fixing nlp documentation bug
    
    * fixing nlp documentation bug
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 2daaa4c637d0bc42e4d6ed74eaf99aa38140c175[m
Author: Anonymous-submission-repo <hahahah2021@163.com>
Date:   Sat Oct 15 03:53:08 2022 +0000

    clean up

[33mcommit 44883f746329aa0ad891984e5cbdf5fd8f58aedb[m
Author: Anonymous-submission-repo <hahahah2021@163.com>
Date:   Sat Oct 15 03:42:23 2022 +0000

    update

[33mcommit 10d36dcc7bbc08f6a36d5041356ab0c35b1bf1fc[m
Author: Anonymous-submission-repo <79179917+Anonymous-submission-repo@users.noreply.github.com>
Date:   Fri Oct 14 22:58:14 2022 -0400

    Update flaml/tune/searcher/flow2.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 608c6bafdc3f1677d1e8abf8afaff2aaa14765e8[m
Author: Anonymous-submission-repo <79179917+Anonymous-submission-repo@users.noreply.github.com>
Date:   Fri Oct 14 22:57:57 2022 -0400

    Update flaml/tune/searcher/flow2.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 6df7782c5ecec2484c28d3ed72802a7febf18089[m
Author: Anonymous-submission-repo <79179917+Anonymous-submission-repo@users.noreply.github.com>
Date:   Fri Oct 14 22:52:07 2022 -0400

    Update test/tune/test_lexiflow.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 30520da5592ca235226279fc36ff3de7180d22f5[m
Author: Anonymous-submission-repo <79179917+Anonymous-submission-repo@users.noreply.github.com>
Date:   Fri Oct 14 22:51:50 2022 -0400

    Update website/docs/Use-Cases/Tune-User-Defined-Function.md
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 1683956559c9fb0a5a249254fd9fc918b1a3e22e[m
Author: Anonymous-submission-repo <79179917+Anonymous-submission-repo@users.noreply.github.com>
Date:   Fri Oct 14 22:51:21 2022 -0400

    Update flaml/tune/tune.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit c5992c1fbf309b9a6a5c02a02c9e1ef7174b51b3[m
Author: Anonymous-submission-repo <79179917+Anonymous-submission-repo@users.noreply.github.com>
Date:   Fri Oct 14 22:51:11 2022 -0400

    Update flaml/tune/searcher/flow2.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 7b530ad0e9ccb5a4d971c5cd17e10231f1ef05d2[m
Author: Anonymous-submission-repo <79179917+Anonymous-submission-repo@users.noreply.github.com>
Date:   Fri Oct 14 22:50:55 2022 -0400

    Update flaml/tune/searcher/blendsearch.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 0257f3df46262bbd86c113e4712625df63513bc0[m
Author: Anonymous-submission-repo <hahahah2021@163.com>
Date:   Sat Oct 15 00:28:50 2022 +0000

    update

[33mcommit a1d9e333fe08f14a2772e9f16821aa2137e09965[m
Author: Anonymous-submission-repo <hahahah2021@163.com>
Date:   Fri Oct 14 23:48:05 2022 +0000

    update

[33mcommit c3baf2d4ee7bbf76e85470f04ea056fa11163dff[m
Author: Anonymous-submission-repo <hahahah2021@163.com>
Date:   Fri Oct 14 23:30:24 2022 +0000

    delete automl

[33mcommit 585bde1ce6f8f8ea0d21a27cee833358d05b1626[m
Merge: bf81912 cafb671
Author: Anonymous-submission-repo <hahahah2021@163.com>
Date:   Fri Oct 14 20:43:50 2022 +0000

    Merge branch 'LexiFlow' of https://github.com/Anonymous-submission-repo/FLAML into LexiFlow

[33mcommit bf81912f0930777ea79479ea909ba921d17fdfe0[m
Author: Anonymous-submission-repo <hahahah2021@163.com>
Date:   Fri Oct 14 20:40:49 2022 +0000

    update

[33mcommit cafb67123a25b797218e9ad5bedcb79372d99287[m
Merge: 2334a9c d3e0d1d
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Fri Oct 14 11:04:18 2022 -0700

    Merge branch 'main' into LexiFlow

[33mcommit d3e0d1d852e15d3416dbb3f7f61411ea2dc825ac[m
Author: Sayan Roy <sayan98.roy@gmail.com>
Date:   Fri Oct 14 01:45:04 2022 +0530

    Discord Badge Added (#760)
    
    * Discord Badge
    
    Discord Badge added Issue #749
    
    * style changed
    
    plastic style to flat style

[33mcommit 2334a9c81dd55aff2be83ac164643b124586b1c4[m
Author: Anonymous-submission-repo <79179917+Anonymous-submission-repo@users.noreply.github.com>
Date:   Thu Oct 13 14:22:49 2022 -0400

    Update flaml/automl.py
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit 7f6e7b3d541c27a57a68255b936a8a1fd7d37ea9[m
Author: Anonymous-submission-repo <79179917+Anonymous-submission-repo@users.noreply.github.com>
Date:   Thu Oct 13 14:22:34 2022 -0400

    Update flaml/tune/searcher/search_thread.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 72f362948cbe8b799201aecdd4549db8257b2788[m
Merge: 8b1a260 2ebddd6
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Thu Oct 13 08:28:17 2022 -0700

    Merge branch 'main' into main

[33mcommit 2ebddd67ae4616e2bec2cc6010658050d883448c[m
Author: Susan Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Wed Oct 12 20:04:42 2022 -0400

    Remove NLP classification head (#756)
    
    * rm classification head in nlp
    
    * rm classification head in nlp
    
    * rm classification head in nlp
    
    * adding test cases for switch classification head
    
    * adding test cases for switch classification head
    
    * Update test/nlp/test_autohf_classificationhead.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * adding test cases for switch classification head
    
    * run each test separately
    
    * skip classification head test on windows
    
    * disabling wandb reporting
    
    * fix test nlp custom metric
    
    * fix test nlp custom metric
    
    * fix test nlp custom metric
    
    * fix test nlp custom metric
    
    * fix test nlp custom metric
    
    * fix test nlp custom metric
    
    * fix test nlp custom metric
    
    * fix test nlp custom metric
    
    * fix test nlp custom metric
    
    * fix test nlp custom metric
    
    * fix test nlp custom metric
    
    * Update website/docs/Examples/AutoML-NLP.md
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update website/docs/Examples/AutoML-NLP.md
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * fix test nlp custom metric
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 2d18c49cddf2ac58e7bd003e4297ce4224ae3d87[m
Author: Anonymous-submission-repo <hahahah2021@163.com>
Date:   Wed Oct 12 04:31:51 2022 +0000

    update

[33mcommit 8b1a260ad3bde9ca89141c72b96c4ee2fed1bae9[m
Author: Sayan Roy <sayan98.roy@gmail.com>
Date:   Tue Oct 11 23:35:43 2022 +0530

    style changed
    
    plastic style to flat style

[33mcommit 7e4d9bcce78daf140446d1d7273116073a965ad7[m
Author: Sayan Roy <sayan98.roy@gmail.com>
Date:   Tue Oct 11 23:33:59 2022 +0530

    Discord Badge
    
    Discord Badge added Issue #749

[33mcommit ecca161848161166fba831c5df5c6ae468989f8c[m
Merge: c8d52ab ee65035
Author: Anonymous-submission-repo <hahahah2021@163.com>
Date:   Mon Oct 10 13:44:01 2022 +0000

    Merge branch 'LexiFlow' of https://github.com/Anonymous-submission-repo/FLAML into LexiFlow

[33mcommit c8d52ab3ae46207c2735d6bdcd8450848f91cb58[m
Merge: ff995d0 f97c233
Author: Anonymous-submission-repo <hahahah2021@163.com>
Date:   Mon Oct 10 13:40:59 2022 +0000

    Merge branch 'main' into LexiFlow

[33mcommit ff995d08d838d57050f482aa0f064e3be083369d[m
Author: Anonymous-submission-repo <hahahah2021@163.com>
Date:   Mon Oct 10 13:37:01 2022 +0000

    notebook

[33mcommit ee650357f142ee770460ecb45f46d4b9cc41938a[m
Merge: 4e37826 f97c233
Author: Anonymous-submission-repo <79179917+Anonymous-submission-repo@users.noreply.github.com>
Date:   Sun Oct 9 22:29:43 2022 -0400

    Merge branch 'main' into LexiFlow

[33mcommit 4e37826417dbfc5eb3c658a50deb91e9a26d6107[m
Author: Anonymous-submission-repo <hahahah2021@163.com>
Date:   Mon Oct 10 01:24:22 2022 +0000

    update

[33mcommit e2c8c3544f31a162c49a23c2f6feb964c627033a[m
Author: Anonymous-submission-repo <hahahah2021@163.com>
Date:   Mon Oct 10 01:17:42 2022 +0000

    doc

[33mcommit f7a9d42dc7634a310221707ece0bb13206972a35[m
Author: Anonymous-submission-repo <hahahah2021@163.com>
Date:   Mon Oct 10 01:15:17 2022 +0000

    update

[33mcommit f97c233dc55a60315f84fdb84fd49dd9ea98a5bd[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sun Oct 9 11:40:45 2022 -0700

    Update Contribute (#741)

[33mcommit 4050d3f1cb4918ab27ed16aa52f00f2645f4e4f4[m
Author: Anonymous-submission-repo <hahahah2021@163.com>
Date:   Sun Oct 9 13:18:15 2022 -0400

    update

[33mcommit 9bc32acafb86297de406f776c3331624dc2b8f31[m
Author: Anonymous-submission-repo <hahahah2021@163.com>
Date:   Sun Oct 9 11:39:29 2022 -0400

    first

[33mcommit c01e65bb48d8f0b924f31ff627b257e73fd457d1[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Sun Oct 9 00:59:31 2022 -0400

    updating the data collator for seq-regression to handle the dim mismatch problem (#751)

[33mcommit 860cbc233e3ab7e44b8e4a7d0c558a6418f49364[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Oct 4 16:03:22 2022 -0700

    move searcher and scheduler into tune (#746)
    
    * move into tune
    
    * correct path
    
    * correct path
    
    * import path

[33mcommit 3e3ce3e33e4ffd198156879b8e6b8edcc0c672b3[m
Author: Prithvi Kannan <46332835+prithvikannan@users.noreply.github.com>
Date:   Tue Oct 4 12:03:11 2022 -0700

    log search_state.config directly instead of under tag config (#747)
    
    Signed-off-by: Prithvi Kannan <prithvi.kannan@databricks.com>
    
    Signed-off-by: Prithvi Kannan <prithvi.kannan@databricks.com>
    Co-authored-by: Xueqing Liu <liususan091219@users.noreply.github.com>

[33mcommit ceb3e300cd79eeada7ca449343d4d15ea170a2cd[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Tue Oct 4 10:51:12 2022 -0400

    Issue724 (#745)
    
    * fixing issue724
    
    * fixing issue724

[33mcommit 0df54ec3f3ec08cd2ae17dea66f1bf670e0c906a[m
Author: Vijaya Lakshmi Venkatraman <vijaya-lakshmi.venkatraman@socgen.com>
Date:   Sun Oct 2 05:55:53 2022 +0530

    Update model.py (#739)
    
    * Update model.py
    
    * Fix review comment

[33mcommit 74557472ececcd9a90b2f7a0938c73e1cdacf326[m
Author: Jason Swinehart <100892022+Libens-bufo@users.noreply.github.com>
Date:   Wed Sep 14 13:01:12 2022 -0400

    Fix issue 728 add hyperlink to GitHub location (#731)
    
    * added hyperlink to github of example code

[33mcommit b7a010e657300748b27e0df04ab0f0502491d9fd[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Sep 13 19:13:06 2022 -0700

    Move import location for Ray 2 (#721)
    
    * ray version check when importing
    
    * display learner_class when starting_points removed
    
    * test ray 2

[33mcommit a89efb552ffc99653b9d7479c18c9bfe70268822[m
Author: Vijaya Lakshmi Venkatraman <vijaya-lakshmi.venkatraman@socgen.com>
Date:   Thu Sep 8 09:50:23 2022 +0530

    Update Contribute.md (#716)
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit ac10d5a2ef1808ab50c73a7cd17bd03db8e7dad8[m
Author: zsk <shaokunzhang529@gmail.com>
Date:   Wed Sep 7 13:37:00 2022 -0400

    Dockerfile building problem (#719)
    
    * update
    
    * cleanup
    
    Co-authored-by: shaokunzhang529@gmail.com <svz5418@i4-l-qxw5138-01.ad.psu.edu>

[33mcommit 87d9b35d634f8085ea87b588a85a07bf7a3b7197[m
Author: EgorKraevTransferwise <62890791+EgorKraevTransferwise@users.noreply.github.com>
Date:   Tue Sep 6 03:10:03 2022 +0100

    Fix SARIMAX seasonal_order parameter (#711)

[33mcommit 9901156deec8eb2a603e2fbf74ca01ceac5e9b5c[m
Author: Jamie Magee <jamie.magee@gmail.com>
Date:   Tue Aug 30 08:00:32 2022 -0700

    Add `$schema` to `cgmanifest.json` (#708)
    
    Co-authored-by: Jamie Magee <jamie.magee@microsoft.com>

[33mcommit c224694f1743915f6c95a0e65ae29433c742a417[m
Merge: 8064ecf da2ae83
Author: zsk <shaokunzhang529@gmail.com>
Date:   Wed Aug 24 13:51:58 2022 -0400

    Merge branch 'main' into dependabot/github_actions/actions/setup-python-4

[33mcommit d7f5a54525ba21aae86906488c75f85d3c840a93[m
Merge: 822ca59 da2ae83
Author: zsk <shaokunzhang529@gmail.com>
Date:   Wed Aug 24 13:51:51 2022 -0400

    Merge branch 'main' into dependabot/github_actions/codecov/codecov-action-3

[33mcommit da2ae83765d85ea50d20b9e15865b47c40cfb393[m
Merge: 7b5c99a f06d27a
Author: zsk <shaokunzhang529@gmail.com>
Date:   Wed Aug 24 09:12:04 2022 -0400

    Merge pull request #669 from skzhang1/cv_strategy
    
    Support customized cross-validation strategy

[33mcommit f06d27aaacc722a20c3f9a85307b28faa0145076[m
Merge: 96f0688 7b5c99a
Author: zsk <shaokunzhang529@gmail.com>
Date:   Wed Aug 24 08:16:07 2022 -0400

    Merge branch 'main' into cv_strategy

[33mcommit 7b5c99a2e795171a32cdabb4224b52de6b847876[m
Merge: 21c1f83 8a4a401
Author: zsk <shaokunzhang529@gmail.com>
Date:   Wed Aug 24 08:15:34 2022 -0400

    Merge pull request #696 from microsoft/dependabot/github_actions/actions/cache-3
    
    Bump actions/cache from 1 to 3

[33mcommit 8a4a40109798395e4c4fa3a1770b4538a2aab122[m
Merge: 61ce233 21c1f83
Author: zsk <shaokunzhang529@gmail.com>
Date:   Tue Aug 23 23:06:54 2022 -0400

    Merge branch 'main' into dependabot/github_actions/actions/cache-3

[33mcommit 96f068859555ec1a1f9af389e647993ec7f2a213[m
Author: skzhang1 <shaokunzhang529@gmail.com>
Date:   Wed Aug 24 02:58:18 2022 +0000

    fix

[33mcommit 21c1f83fcf4d102c003079b275a9b9b43b256868[m
Merge: e5c8a16 74c19d2
Author: zsk <shaokunzhang529@gmail.com>
Date:   Tue Aug 23 22:25:03 2022 -0400

    Merge pull request #698 from microsoft/dependabot/github_actions/actions/setup-node-3
    
    Bump actions/setup-node from 2 to 3

[33mcommit 74c19d2a2e23f8a31b937fd08b173e52e4f2b7b0[m
Merge: 1adc190 e5c8a16
Author: zsk <shaokunzhang529@gmail.com>
Date:   Tue Aug 23 14:52:18 2022 -0400

    Merge branch 'main' into dependabot/github_actions/actions/setup-node-3

[33mcommit 61ce233b7baa967a3393502f03540254921097e4[m
Merge: efc33e0 e5c8a16
Author: zsk <shaokunzhang529@gmail.com>
Date:   Tue Aug 23 14:52:03 2022 -0400

    Merge branch 'main' into dependabot/github_actions/actions/cache-3

[33mcommit e5c8a16fabc74098751598950911d7b319f0573b[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Mon Aug 22 10:52:41 2022 -0700

    Update Research.md

[33mcommit efc33e04944574764c33c6f437e56c1bbf152372[m
Merge: af85eb3 2314cc5
Author: zsk <shaokunzhang529@gmail.com>
Date:   Mon Aug 22 17:05:18 2022 -0400

    Merge branch 'main' into dependabot/github_actions/actions/cache-3

[33mcommit 1adc19027f4743a1ebfc590a5c13ea784d596d87[m
Merge: 71a2d9f 2314cc5
Author: zsk <shaokunzhang529@gmail.com>
Date:   Mon Aug 22 17:04:38 2022 -0400

    Merge branch 'main' into dependabot/github_actions/actions/setup-node-3

[33mcommit 2314cc5a7ef93d51bb999ba8c2e4b2a33f167019[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Mon Aug 22 13:36:50 2022 -0400

    "intermediate_results" TypeError: argument of type 'NoneType' is not iterable (#695)
    
    * fix mlflow bug
    
    * bump version

[33mcommit 71a2d9fd89dd9db1e9cb46a7dab41891dcdd33a0[m
Merge: 07656e4 2ead296
Author: zsk <shaokunzhang529@gmail.com>
Date:   Mon Aug 22 10:30:02 2022 -0400

    Merge branch 'main' into dependabot/github_actions/actions/setup-node-3

[33mcommit af85eb3b25aedcca768f5eac922db79f22018cbe[m
Merge: 066842c 2ead296
Author: zsk <shaokunzhang529@gmail.com>
Date:   Mon Aug 22 10:29:37 2022 -0400

    Merge branch 'main' into dependabot/github_actions/actions/cache-3

[33mcommit 2ead2966765b8aa17ae262b13eb41b81d09fd502[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Mon Aug 22 07:20:48 2022 -0400

    updating nlp notebook (#693)
    
    * updating nlp notebook

[33mcommit f3bfc68412f1fa69bb7dd5db1f0fe8a7f7498880[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Mon Aug 22 00:02:10 2022 -0400

    talks and tutorials (#694)

[33mcommit 8064ecf0e7bd949d61a557762c959177721bee32[m
Author: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>
Date:   Sun Aug 21 22:46:02 2022 +0000

    Bump actions/setup-python from 2 to 4
    
    Bumps [actions/setup-python](https://github.com/actions/setup-python) from 2 to 4.
    - [Release notes](https://github.com/actions/setup-python/releases)
    - [Commits](https://github.com/actions/setup-python/compare/v2...v4)
    
    ---
    updated-dependencies:
    - dependency-name: actions/setup-python
      dependency-type: direct:production
      update-type: version-update:semver-major
    ...
    
    Signed-off-by: dependabot[bot] <support@github.com>

[33mcommit 07656e4af0ed763cc703981518fe5fa03f0f8fca[m
Author: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>
Date:   Sun Aug 21 22:45:54 2022 +0000

    Bump actions/setup-node from 2 to 3
    
    Bumps [actions/setup-node](https://github.com/actions/setup-node) from 2 to 3.
    - [Release notes](https://github.com/actions/setup-node/releases)
    - [Commits](https://github.com/actions/setup-node/compare/v2...v3)
    
    ---
    updated-dependencies:
    - dependency-name: actions/setup-node
      dependency-type: direct:production
      update-type: version-update:semver-major
    ...
    
    Signed-off-by: dependabot[bot] <support@github.com>

[33mcommit 822ca59ed22eb2d1692aa4b3d7e7a5e33170b590[m
Author: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>
Date:   Sun Aug 21 22:45:50 2022 +0000

    Bump codecov/codecov-action from 1 to 3
    
    Bumps [codecov/codecov-action](https://github.com/codecov/codecov-action) from 1 to 3.
    - [Release notes](https://github.com/codecov/codecov-action/releases)
    - [Changelog](https://github.com/codecov/codecov-action/blob/master/CHANGELOG.md)
    - [Commits](https://github.com/codecov/codecov-action/compare/v1...v3)
    
    ---
    updated-dependencies:
    - dependency-name: codecov/codecov-action
      dependency-type: direct:production
      update-type: version-update:semver-major
    ...
    
    Signed-off-by: dependabot[bot] <support@github.com>

[33mcommit 066842cfcb667c830f810d1f74ab028bfe68f36c[m
Author: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>
Date:   Sun Aug 21 22:45:46 2022 +0000

    Bump actions/cache from 1 to 3
    
    Bumps [actions/cache](https://github.com/actions/cache) from 1 to 3.
    - [Release notes](https://github.com/actions/cache/releases)
    - [Changelog](https://github.com/actions/cache/blob/main/RELEASES.md)
    - [Commits](https://github.com/actions/cache/compare/v1...v3)
    
    ---
    updated-dependencies:
    - dependency-name: actions/cache
      dependency-type: direct:production
      update-type: version-update:semver-major
    ...
    
    Signed-off-by: dependabot[bot] <support@github.com>

[33mcommit 9a5cabc5962f25350af89c66aacd7afd4b70b4b8[m
Merge: dffa802 126c41f
Author: zsk <shaokunzhang529@gmail.com>
Date:   Sun Aug 21 18:45:21 2022 -0400

    Merge pull request #688 from iemejia/main
    
    chore: Auto update github actions with dependabot

[33mcommit 126c41f3ee5726ba29bc69116cab971c4d35ebee[m
Merge: 40ce15c dffa802
Author: zsk <shaokunzhang529@gmail.com>
Date:   Sun Aug 21 13:58:18 2022 -0400

    Merge branch 'main' into main

[33mcommit 50fb20ebbcc2726d5868f5441e86f01f5bd4bbb6[m
Author: skzhang1 <shaokunzhang529@gmail.com>
Date:   Sun Aug 21 17:44:26 2022 +0000

    update

[33mcommit 462c27f8aec40e1ca3034879886d8a9a7314cc80[m
Author: skzhang1 <shaokunzhang529@gmail.com>
Date:   Sun Aug 21 12:54:58 2022 +0000

    fix

[33mcommit e3aa7ea9d13082a615169bf434043c576d193bbf[m
Author: skzhang1 <shaokunzhang529@gmail.com>
Date:   Sun Aug 21 12:52:27 2022 +0000

    update

[33mcommit bfacff2a3d9eef7cd475766e4241febc52c37599[m
Merge: f9c764c 5d2929c
Author: skzhang1 <shaokunzhang529@gmail.com>
Date:   Sun Aug 21 12:48:49 2022 +0000

    Merge branch 'cv_strategy' of https://github.com/skzhang1/FLAML into cv_strategy
    test

[33mcommit 5d2929cb83d5057cd912c1c7c1f562cd46ae9679[m
Author: zsk <shaokun.zhang@psu.edu>
Date:   Sun Aug 21 08:47:20 2022 -0400

    Update flaml/automl.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit f9c764c097e1420b9f789953e0c605a95f2c1caf[m
Author: skzhang1 <shaokunzhang529@gmail.com>
Date:   Sun Aug 21 12:43:43 2022 +0000

    update

[33mcommit 92dc41dc6939402d25bada30d5e4c15ab3e88fbc[m
Author: skzhang1 <shaokunzhang529@gmail.com>
Date:   Sun Aug 21 12:40:54 2022 +0000

    update doc

[33mcommit 39d8c0e3e8140b50298883aa1dec7c34f0db27d0[m
Author: zsk <shaokun.zhang@psu.edu>
Date:   Sun Aug 21 08:35:44 2022 -0400

    Update flaml/automl.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 5faafa01d41618b2f65843d7b6674d2229c46482[m
Merge: 34085b8 dffa802
Author: skzhang1 <shaokunzhang529@gmail.com>
Date:   Sun Aug 21 12:33:26 2022 +0000

    Merge branch 'main' into cv_strategy
    update

[33mcommit dffa802b3e377ea3dc591f0c7d99f3b3ccc1a26d[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Aug 20 18:38:56 2022 -0700

    use_best_model for catboost (#679)
    
    * use_best_model for catboost
    
    * bump version to 1.0.11

[33mcommit 3d1a28bfc04b6230badf1099474f8af38a5b6d1a[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Sat Aug 20 18:17:10 2022 -0400

    Add preserve_checkpoint to preserve the checkpoint after del (#692)
    
    * fix del bug

[33mcommit 47e034d2032c0e369024caec681ff72a11d9023c[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Aug 20 07:43:06 2022 -0700

    LightGBM notebook update (#690)
    
    * version update in notebook
    
    * comment about optuna install
    
    * monotone constraints

[33mcommit e3d26c0650ba3cf6b55ee9e9231cc54c680e9fb9[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Sat Aug 20 09:18:35 2022 -0400

    add guideline collection (#687)
    
    * add guideline collection
    
    * remove redundancy

[33mcommit 40ce15cbe3cf370ada675415570742ddb03f6428[m
Author: Ismaël Mejía <iemejia@gmail.com>
Date:   Wed Aug 17 21:58:13 2022 +0200

    chore: Auto update github actions with dependabot

[33mcommit 8b3c6e4d7bbabd8bce1bc07ca3ab082ad7ffdc7a[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Mon Aug 15 23:16:11 2022 -0400

    VW version requirement and documentation on config_constraints vs metric_constraints (#686)
    
    * add vw version requirement
    
    * vw version
    
    * version range
    
    * add documentation
    
    * vw version range
    
    * skip test on py3.10
    
    * vw version
    
    * rephrase
    
    * don't install vw on py 3.10
    
    * move import location
    
    * remove inherit
    
    * 3.10 in version
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 6c7d37374de8cbd16aa0d3038d4229242f7ed935[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Mon Aug 15 21:09:08 2022 -0400

    updating nlp notebook (#683)

[33mcommit 34085b8c251b68f883654fc8394cb59954317e2c[m
Author: skzhang1 <shaokunzhang529@gmail.com>
Date:   Mon Aug 15 14:41:30 2022 +0000

    update

[33mcommit d60d38b3e9e78c87f389c68ce64f78b1477f48ca[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Mon Aug 15 06:15:31 2022 -0700

    log_file_name in tune.run() (#681)
    
    * log_file_name in tune.run()
    
    * use_ray validates log_file_name
    
    * assert no ray_args when not use_ray
    
    * import os and use os.path

[33mcommit 3f33a9700b9d99f9d0d2f8dad38f354048690927[m
Merge: 6485c28 5e1059a
Author: skzhang1 <shaokunzhang529@gmail.com>
Date:   Mon Aug 15 13:08:09 2022 +0000

    Merge branch 'main' into cv_strategy

[33mcommit 5e1059ab82eeee9b557839b0e31dc87712bb8fd3[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Mon Aug 15 05:30:23 2022 -0700

    check config constraints for the initial config (#685)
    
    * check config constraints for the initial config
    
    * default config value

[33mcommit 2e8e3937ef7d1591060615c153ee8942a8eb6ce1[m
Author: Kevin Chen <74878789+int-chaos@users.noreply.github.com>
Date:   Sat Aug 13 21:58:45 2022 -0400

    update time series forecast notebook (#682)
    
    * update forecasting with exogeneous variables example
    
    Signed-off-by: Kevin Chen <chenkevin.8787@gmail.com>
    
    * update forecasting with exogeneous variables example on website
    
    Signed-off-by: Kevin Chen <chenkevin.8787@gmail.com>
    
    * rerun automl_time_series_forecast with new predict function for tft
    
    Signed-off-by: Kevin Chen <chenkevin.8787@gmail.com>
    
    * correct spelling error
    
    Signed-off-by: Kevin Chen <chenkevin.8787@gmail.com>
    
    Signed-off-by: Kevin Chen <chenkevin.8787@gmail.com>

[33mcommit 6485c28a08c8d202102bc8188b5fb24165efa695[m
Author: skzhang1 <shaokunzhang529@gmail.com>
Date:   Sat Aug 13 18:57:28 2022 +0000

    fix

[33mcommit a55ed0ed613dc2ca0dc8b699dd14ca14d914719c[m
Merge: fc633ef e434856
Author: skzhang1 <shaokunzhang529@gmail.com>
Date:   Sat Aug 13 18:56:46 2022 +0000

    update

[33mcommit fc633ef15e86fec76b959c5c86f7d65a2c753dcc[m
Author: skzhang1 <shaokunzhang529@gmail.com>
Date:   Sat Aug 13 18:51:33 2022 +0000

    update

[33mcommit e43485607ad429dbb5ea1fb65b94fbcb1ce086f0[m
Author: jmrichardson <jmrichardson@users.noreply.github.com>
Date:   Fri Aug 12 20:05:32 2022 -0400

    Disable shuffle for custom CV (#659)
    
    * Disable shuffle for custom CV
    
    * Add custom fold shuffle test
    
    * Update test_split.py
    
    * Update test_split.py

[33mcommit ca9f9054e73fb51f36ed5c22c7c66b115d9b59eb[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Fri Aug 12 13:55:17 2022 -0700

    categorical choice can be ordered or unordered (#677)
    
    * categorical choice can be ordered or unordered
    
    * ordered -> order
    
    * move choice into utils
    
    * version comparison
    
    * packaging -> setuptools
    
    * import version
    
    * version_parse
    
    * test order for choice

[33mcommit f718d18b5ea88c7fcbd8ecb49700963300f997f4[m
Author: Kevin Chen <74878789+int-chaos@users.noreply.github.com>
Date:   Fri Aug 12 11:39:22 2022 -0400

    time series forecasting with panel datasets (#541)
    
    * time series forecasting with panel datasets
    - integrate Temporal Fusion Transformer as a learner based on pytorchforecasting
    
    Signed-off-by: Kevin Chen <chenkevin.8787@gmail.com>
    
    * update setup.py
    
    Signed-off-by: Kevin Chen <chenkevin.8787@gmail.com>
    
    * update test_forecast.py
    
    Signed-off-by: Kevin Chen <chenkevin.8787@gmail.com>
    
    * update setup.py
    
    Signed-off-by: Kevin Chen <chenkevin.8787@gmail.com>
    
    * update setup.py
    
    Signed-off-by: Kevin Chen <chenkevin.8787@gmail.com>
    
    * update model.py and test_forecast.py
    - remove blank lines
    
    Signed-off-by: Kevin Chen <chenkevin.8787@gmail.com>
    
    * update model.py to prevent errors
    
    Signed-off-by: Kevin Chen <chenkevin.8787@gmail.com>
    
    * update automl.py and data.py
    - change forecast task name
    - update documentation for fit() method
    
    Signed-off-by: Kevin Chen <chenkevin.8787@gmail.com>
    
    * update test_forecast.py
    
    Signed-off-by: Kevin Chen <chenkevin.8787@gmail.com>
    
    * update test_forecast.py
    - add performance test
    - use 'fit_kwargs_by_estimator'
    
    Signed-off-by: Kevin Chen <chenkevin.8787@gmail.com>
    
    * add time index function
    
    Signed-off-by: Kevin Chen <chenkevin.8787@gmail.com>
    
    * update test_forecast.py performance test
    
    Signed-off-by: Kevin Chen <chenkevin.8787@gmail.com>
    
    * update data.py
    
    Signed-off-by: Kevin Chen <chenkevin.8787@gmail.com>
    
    * update automl.py
    
    Signed-off-by: Kevin Chen <chenkevin.8787@gmail.com>
    
    * update data.py to prevent type error
    
    Signed-off-by: Kevin Chen <chenkevin.8787@gmail.com>
    
    * update setup.py
    
    Signed-off-by: Kevin Chen <chenkevin.8787@gmail.com>
    
    * update for pytorch forecasting tft on panel datasets
    
    Signed-off-by: Kevin Chen <chenkevin.8787@gmail.com>
    
    * update automl.py documentations
    
    Signed-off-by: Kevin Chen <chenkevin.8787@gmail.com>
    
    * - rename estimator
    - add 'gpu_per_trial' for tft estimator
    
    Signed-off-by: Kevin Chen <chenkevin.8787@gmail.com>
    
    * update test_forecast.py
    
    Signed-off-by: Kevin Chen <chenkevin.8787@gmail.com>
    
    * include ts panel forecasting as an example
    
    Signed-off-by: Kevin Chen <chenkevin.8787@gmail.com>
    
    * update model.py
    
    Signed-off-by: Kevin Chen <chenkevin.8787@gmail.com>
    
    * update documentations
    
    Signed-off-by: Kevin Chen <chenkevin.8787@gmail.com>
    
    * update automl_time_series_forecast.ipynb
    
    Signed-off-by: Kevin Chen <chenkevin.8787@gmail.com>
    
    * update documentations
    
    Signed-off-by: Kevin Chen <chenkevin.8787@gmail.com>
    
    * "weights_summary" argument deprecated and removed for pl.Trainer()
    
    Signed-off-by: Kevin Chen <chenkevin.8787@gmail.com>
    
    * update model.py tft estimator prediction method
    
    Signed-off-by: Kevin Chen <chenkevin.8787@gmail.com>
    
    * update model.py
    
    Signed-off-by: Kevin Chen <chenkevin.8787@gmail.com>
    
    * update `fit_kwargs` documentation
    
    Signed-off-by: Kevin Chen <chenkevin.8787@gmail.com>
    
    * update automl.py
    
    Signed-off-by: Kevin Chen <chenkevin.8787@gmail.com>
    
    Signed-off-by: Kevin Chen <chenkevin.8787@gmail.com>
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit b436459e476a55e5cbca8a5fcf1f53fbf5434532[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Fri Aug 12 01:17:31 2022 -0400

    Documentation on search space and parallel/sequential tuning (#675)
    
    * add search space doc
    
    * remove redundancy
    
    * add parallel and sequential guidelines
    
    * add caveats
    
    * update doc
    
    * add code example
    
    * wording
    
    * revise example
    
    * add a tutorial link in readme
    
    * wording change
    
    * update readme
    
    * remove redundancy
    
    * Update website/docs/Use-Cases/Task-Oriented-AutoML.md
    
    Co-authored-by: Xueqing Liu <liususan091219@users.noreply.github.com>
    
    * Update website/docs/Use-Cases/Task-Oriented-AutoML.md
    
    Co-authored-by: Xueqing Liu <liususan091219@users.noreply.github.com>
    
    Co-authored-by: Xueqing Liu <liususan091219@users.noreply.github.com>

[33mcommit 809639f723e72e8f8f220f1975efc3906f2a0b8f[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Thu Aug 11 23:16:33 2022 -0400

    Update Research.md (#672)
    
    * Update Research.md
    
    Update Research.md
    
    * Update website/docs/Research.md
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>
    
    * Update Research.md
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit 524e5e214004fb7636a6b5d4591506db7ae715bf[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Thu Aug 11 17:35:41 2022 -0700

    pull request template (#668)
    
    * pull request template
    
    * update instructions about tests

[33mcommit 25ad397d555cef06c5bb896277fab9d775046d3d[m
Author: jmrichardson <jmrichardson@users.noreply.github.com>
Date:   Thu Aug 11 19:41:23 2022 -0400

    Skip transform (#665)
    
    * Skip transform
    
    * Fix logic and docstring, add test
    
    * Add period ending to skip_transform doc
    
    * Add skip_transform to retrain_from_log method
    
    * Update test/automl/test_classification.py
    
    Co-authored-by: Xueqing Liu <liususan091219@users.noreply.github.com>
    
    Co-authored-by: Xueqing Liu <liususan091219@users.noreply.github.com>

[33mcommit b6e8b9cccaa282fcd083bf037fd74628ea139a94[m
Author: Rui Zhuang <7812164+ruizhuanguw@users.noreply.github.com>
Date:   Wed Aug 10 20:20:21 2022 -0700

    Add pipeline tuner component and dependencies. (#671)
    
    * add pipeline tuner component and dependencies.
    
    * clean code.
    
    * do not need force rerun.
    
    * replace the resources.
    
    * update metrics retrieving.
    
    * Update test/pipeline_tuning_example/requirements.txt
    
    * Update test/pipeline_tuning_example/train/env.yaml
    
    * Update test/pipeline_tuning_example/tuner/env.yaml
    
    * Update test/pipeline_tuning_example/tuner/tuner_func.py
    
    * Update test/pipeline_tuning_example/data_prep/env.yaml
    
    * fix issues found by lint with flake8.
    
    * add documentation
    
    * add data.
    
    * do not need AML resource for local run.
    
    * AML -> AzureML
    
    * clean code.
    
    * Update website/docs/Examples/Tune-AzureML pipeline.md
    
    * rename and add pip install.
    
    * update figure name.
    
    * align docs with code.
    
    * remove extra line.

[33mcommit e3c9da50dabb46d3861ab4c6d4d4f394f60e23cd[m
Author: skzhang1 <shaokunzhang529@gmail.com>
Date:   Wed Aug 10 00:42:47 2022 +0000

    update

[33mcommit 7851a463aaf1edebf58e943abba8cfe5903a1546[m
Author: skzhang1 <shaokunzhang529@gmail.com>
Date:   Sun Aug 7 18:16:34 2022 +0000

    clean up

[33mcommit e5a422c41e621a94055295ddb12a5202a696fd11[m
Author: skzhang1 <shaokunzhang529@gmail.com>
Date:   Sun Aug 7 18:11:04 2022 +0000

    update

[33mcommit 816a82a1155b4de4705b21a615ccdff67c6da379[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Fri Aug 5 10:17:41 2022 -0700

    make test result more stable (#646)

[33mcommit 21fa6c10ec6f963edbda99e9020ad585ae60a1a5[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Wed Aug 3 00:11:29 2022 -0400

    Fixing the issue that FLAML trial number is significantly smaller than Transformers.hyperparameter_search (#657)
    
    * fix 636
    
    * adding low cost config
    
    * update padding; update tokenization output y type (series -> DF); update low cost init config
    
    * updating todf; updating metric_loss_score

[33mcommit 74e6026ab903b055dcffa89f93c1481263a44091[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Sun Jul 31 13:02:08 2022 -0400

    bump version to 1.0.9 (#656)

[33mcommit 5eb5d43d7f3f0a828638ea7c3f19ce22a3d67ef9[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Thu Jul 28 23:08:42 2022 -0400

    Fix HPO evaluation bug (#645)
    
    * fix eval automl metric bug on val_loss inconsistency
    
    * updating starting point search space to continuous
    
    * shortening notebok

[33mcommit d649fefa6b804b75ccdfc8acbfd9f2b98f849924[m
Author: Luis Quintanilla <46974588+luisquintanilla@users.noreply.github.com>
Date:   Tue Jul 26 19:53:49 2022 -0400

    Update .NET documentation (#643)
    
    * Updated install instructions
    
    * Update website/docs/Installation.md
    
    * Updated install and README

[33mcommit ebbfa0c7f58c3a1df72d9a9dc164dc539f94ee67[m
Merge: 05292c8 655b7bf
Author: zsk <shaokunzhang529@gmail.com>
Date:   Tue Jul 26 17:05:42 2022 -0400

    Merge pull request #644 from skzhang1/fix_alerts
    
    Fix alerts

[33mcommit 655b7bfefa0fecdc85051395b96b9fc0e080e66c[m
Merge: 26113dd 05292c8
Author: zsk <shaokunzhang529@gmail.com>
Date:   Tue Jul 26 16:25:56 2022 -0400

    Merge branch 'main' into fix_alerts

[33mcommit 05292c8c74d7f4eda68bf78e77c8b11853a2a952[m
Author: Zhonghua Zheng <zhonghua.zheng@outlook.com>
Date:   Tue Jul 26 14:19:37 2022 -0600

    added "**kwargs" to "predict" (#641)
    
    * added "**kwargs" to "predict" functions

[33mcommit 26113dd2d62ddcfe920043db000b6c08ab4e256c[m
Merge: 6ced9cb f3a0438
Author: skzhang1 <shaokunzhang529@gmail.com>
Date:   Tue Jul 26 15:31:08 2022 -0400

    Merge branch 'main' into fix_alerts

[33mcommit f3a0438c86c9ddb8b901f2b3960f7fe71ffb4b75[m
Merge: a2c3c7c 731afec
Author: zsk <shaokun.zhang@psu.edu>
Date:   Tue Jul 26 15:25:45 2022 -0400

    Merge branch 'microsoft:main' into main

[33mcommit 731afec9eb181af633cdbfe46c1f98a68ce332c0[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Mon Jul 25 17:46:33 2022 -0400

    This PR fixes the frequent NLP bugs in the other PRs (#647)
    
    * fix nlp bug
    
    * resetting model to electra small
    
    * removing model_path from fit_kwargs_by_estimator

[33mcommit 6ced9cb5cc2e6427ee23eacd90c8ba5a0ddd4558[m
Author: skzhang1 <shaokunzhang529@gmail.com>
Date:   Thu Jul 21 15:09:22 2022 -0400

    update node forge

[33mcommit d88c7390ce9b62a79de324d1ca49b106029962cb[m
Author: skzhang1 <shaokunzhang529@gmail.com>
Date:   Thu Jul 21 14:48:21 2022 -0400

    ignore engine

[33mcommit aaec58908ae16226d89cbe521b41104918eaddac[m
Author: skzhang1 <shaokunzhang529@gmail.com>
Date:   Thu Jul 21 14:32:28 2022 -0400

    update

[33mcommit a2c3c7cb1cf99dd70c4a544a0deba16ccd482be5[m
Merge: 8b0ff48 89d9c44
Author: zsk <shaokun.zhang@psu.edu>
Date:   Wed Jul 20 20:32:52 2022 -0400

    Merge branch 'microsoft:main' into main

[33mcommit 89d9c4426ec092ec6f29f5d22ccb8ece461a8bc0[m
Author: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>
Date:   Wed Jul 20 08:44:30 2022 -0700

    Bump terser from 5.10.0 to 5.14.2 in /website (#642)
    
    Bumps [terser](https://github.com/terser/terser) from 5.10.0 to 5.14.2.
    - [Release notes](https://github.com/terser/terser/releases)
    - [Changelog](https://github.com/terser/terser/blob/master/CHANGELOG.md)
    - [Commits](https://github.com/terser/terser/commits)
    
    ---
    updated-dependencies:
    - dependency-name: terser
      dependency-type: indirect
    ...
    
    Signed-off-by: dependabot[bot] <support@github.com>
    
    Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

[33mcommit a64956a7c8f98db6a7de7e8cc5d0ce53e9c86a03[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Mon Jul 11 18:20:09 2022 -0400

    updating search space (#633)
    
    * updating search space

[33mcommit 8fb1c1a29ac062d51d1823799297e9443b2565b0[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Sun Jul 10 23:04:26 2022 -0400

    fix NER roberta bug (#632)
    
    * fix NER roberta bug

[33mcommit e14e909af9a18ffe154007bf5355ceb33f0d57d0[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sun Jul 10 12:25:59 2022 -0700

    Feature names and importances (#621)
    
    * feature names and importances
    
    * None check
    
    * StackingClassifier has no feature_importances_
    
    * StackingClassifier has no feature_names_in_

[33mcommit 59bd3c19796cde127f78160cfd9d601bdd399e6c[m
Author: Aditya Agarwal <50960175+adi611@users.noreply.github.com>
Date:   Sun Jul 10 20:49:39 2022 +0530

    fix #630 n_cpus -> num_cpus (#631)

[33mcommit 214566313c90e5f34ee3bcbd8725290b9bf572b3[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Sun Jul 10 06:33:02 2022 -0400

    disable max_len for ner (#629)
    
    * disable max_len for ner

[33mcommit b7846048dcc4e78fa1733e29e4d3a2d2da818c2a[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Sat Jul 9 16:04:46 2022 -0400

    Allow FLAML_sample_size in starting_points (#619)
    
    * FLAML_sample_size
    
    * clean up
    
    * starting_points as a list
    
    * catch AssertionError
    
    * per estimator sample size
    
    * import
    
    * per estimator min_sample_size
    
    * Update flaml/automl.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update test/automl/test_warmstart.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * add warnings
    
    * adding more tests
    
    * fix a bug in validating starting points
    
    * improve test
    
    * revise test
    
    * revise test
    
    * documentation about custom_hp
    
    * doc and efficiency
    
    * update test
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 6cb6a2a19a5a4591bad3bececd9d6076bc79b590[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Wed Jul 6 13:22:05 2022 -0400

    isinstance(x, int) -> isinstance(x, (int, np.integer)) (#627)
    
    * isinstance(x, int) -> isinstance(x, (int, np.integer))

[33mcommit 6108493e0b774a0fb3676737610629a2ecb99b15[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Tue Jul 5 13:38:21 2022 -0400

    fix ner bug; refactor post processing of TransformersEstimator prediction (#615)
    
    * fix ner bug; refactor post processing
    
    * fix too many values to unpack
    
    * supporting id/token label for NER

[33mcommit 6dd93bc9396f5ad1821b3db528aff2bb8fa6d164[m
Author: Sanskrati <31sanskrati@gmail.com>
Date:   Sat Jul 2 21:34:32 2022 +0530

    Add space after comma (#623)
    
    Add space after comma in 'subscription_id='<azure-subscription-id>',resource_group='myresourcegroup')'

[33mcommit 9bf13d66f18a239ef26056e501b89975d8d7e1f0[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Fri Jul 1 13:28:16 2022 -0700

    use relative url in doc (#620)
    
    * use relative url in doc
    
    * update link

[33mcommit beb10273e821990f1e891ffdf6afa9d35308494c[m
Author: Zvi Baratz <z.baratz@gmail.com>
Date:   Thu Jun 30 16:43:09 2022 +0300

    Typo fix (#618)

[33mcommit 74cca60606f43c885a177d3a2eb4e47828ba36a1[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Wed Jun 29 21:04:25 2022 -0700

    Allow custom GroupKFold object as split_type (#616)
    
    * Allow custom GroupKFold object
    
    * handle unpickle error for prophet 1.1
    
    * eval_method in test_object()

[33mcommit 8b0ff486faca4e829efed35af151352e93159b38[m
Merge: 72deb84 cbb85e2
Author: zsk <shaokun.zhang@psu.edu>
Date:   Sun Jun 26 20:56:11 2022 -0400

    Merge branch 'microsoft:main' into main

[33mcommit cbb85e2aabdb656aafaf0cf42334f45ce2f03bdf[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sun Jun 26 08:32:28 2022 -0700

    Py36 (#614)
    
    * allow installation in py 3.6
    
    * test py 3.6

[33mcommit 72deb84b50053bc7fa1f5aeaa696131fb04a11fc[m
Merge: f471d6f 8e3fccf
Author: zsk <shaokun.zhang@psu.edu>
Date:   Sat Jun 25 14:49:48 2022 -0400

    Merge branch 'microsoft:main' into main

[33mcommit 8e3fccf592a6165b06f684e0644da54b1ea2f973[m
Author: Zvi Baratz <z.baratz@gmail.com>
Date:   Sat Jun 25 20:46:28 2022 +0300

    Updated hooks (#609)
    
    Updated the flake8 hook and black's version, closes #608.
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 7d6822aa40883550e72c4ee24adb765c6e937ce7[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Fri Jun 24 14:25:26 2022 +0000

    cath URLError

[33mcommit f471d6f822f06ddf090a8c9cdb6076c584a8eeb7[m
Merge: 9415fa2 127e482
Author: zsk <shaokun.zhang@psu.edu>
Date:   Thu Jun 23 23:26:14 2022 -0400

    Merge branch 'microsoft:main' into main

[33mcommit 127e482ac88223f5bedf561bd3dbe731fba65984[m
Author: Zvi Baratz <z.baratz@gmail.com>
Date:   Fri Jun 24 04:45:42 2022 +0300

    Replaced !pip calls with %pip magic command. (#604)
    
    Closes #603.

[33mcommit 6cb44484f6d3b5ac929550ff94dbab459ca92af5[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Thu Jun 23 19:44:02 2022 +0000

    min eci depends on cost_attr; cost_attr in ls

[33mcommit 9415fa2ec9771e3a758d3a31bbc5bd0e57542013[m
Merge: 7cfc41e 4377d53
Author: zsk <shaokun.zhang@psu.edu>
Date:   Thu Jun 23 14:23:33 2022 -0400

    Merge branch 'microsoft:main' into main

[33mcommit 4377d53a73777db9b05001f263b8d9a535232f76[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Thu Jun 23 08:02:46 2022 -0700

    update got version (#607)
    
    * update got version
    
    * None check

[33mcommit fefdb48ef3fcdaa3da8de1bc0fc99da35ca1d9a5[m
Author: Zvi Baratz <z.baratz@gmail.com>
Date:   Thu Jun 23 05:44:14 2022 +0300

    Fix automl settings in scikit-learn pipeline integration example (#602)
    
    * Added test directory and core file to gitignore.
    
    Closes #601.
    
    * Fixed pipeline fit parameters.
    
    Closes #600.
    
    * Reverted changes to gitignore.

[33mcommit 7cfc41e2ac3660bd3080d5b02badaf3468aa1aca[m
Merge: e4b7946 c45741a
Author: zsk <shaokun.zhang@psu.edu>
Date:   Wed Jun 22 11:00:47 2022 -0400

    Merge branch 'microsoft:main' into main

[33mcommit c45741a67b0a76bfe0bf2dda0cc7691b2b1954d4[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Jun 21 18:59:07 2022 -0700

    support latest xgboost version (#599)
    
    * support latest xgboost version
    
    * Update test_classification.py
    
    * Update
    
    Exists problems when installing xgb1.6.1 in py3.6
    
    * cleanup
    
    * xgboost version
    
    * remove time_budget_s in test
    
    * remove redundancy
    
    * stop support of python 3.6
    
    Co-authored-by: zsk <shaokunzhang529@gmail.com>
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit e4b7946de6155730d74082557c877af8cae16c74[m
Merge: e1e2faf c5272ad
Author: zsk <shaokun.zhang@psu.edu>
Date:   Mon Jun 20 16:19:19 2022 -0400

    Merge branch 'microsoft:main' into main

[33mcommit c5272ad377de257eb31765c419cbe330a2bde298[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Jun 18 01:22:03 2022 +0000

    log msg about ensemble

[33mcommit e1e2fafba90a9ae1585c7a3f51593bd02b4bae18[m
Merge: 2478a3f 1b40b4b
Author: zsk <shaokun.zhang@psu.edu>
Date:   Fri Jun 17 21:31:22 2022 -0400

    Merge branch 'microsoft:main' into main

[33mcommit 1b40b4b3a6602db1df2d315d4b9e12fa0c69bb65[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Thu Jun 16 16:30:50 2022 -0700

    set_search_properties (#595)
    
    * update the signature of set_search_properties

[33mcommit 4c044e88bd959d47e22983573e1679306ec19be2[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Thu Jun 16 16:52:03 2022 -0400

    Update documentation for NLP (#594)
    
    * Update Installation.md

[33mcommit 7740cd346645c493c17252415961623da40576ea[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Thu Jun 16 14:58:23 2022 -0400

    trying to fix the indexerror for ner (#596)
    
    * trying to fix the indexerror for ner

[33mcommit 3a7ebe6896190ee135a9b6f8f91ad9a8a5e6d828[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Wed Jun 15 20:13:33 2022 -0700

    Add python 3.10 in the CI (#591)
    
    * fix resource limit issue
    
    * add python 3.10 in CI
    
    * reinstall libomp in macos

[33mcommit 40a86a59416574da9e7ee7a18002ffa6164bed6d[m
Author: daniel-555 <48334472+daniel-555@users.noreply.github.com>
Date:   Wed Jun 15 23:45:33 2022 +0100

    Modified setup instructions (#593)

[33mcommit cf1dfd396670fabe88ab48c0931938f1cd05a1bd[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Wed Jun 15 13:46:52 2022 -0700

    fix resource limit issue (#589)

[33mcommit 79a24d06a9343b017a82d01ffc04cf9bb654facc[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Tue Jun 14 17:31:12 2022 -0400

    fixing a bug in nlp/utils.py (#590)
    
    * fixing a bug for ner

[33mcommit 1111d6d43a88b5106c73575e9cddbcf458cc2242[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Jun 14 11:03:54 2022 -0700

    backup & recover global vars for nested tune.run (#584)
    
    * backup & recover global vars for nested tune.run
    
    * ensure recovering global vars before return

[33mcommit 65fa72d58395a2df9c0447d4a7d4ead856bc5b3e[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Tue Jun 14 00:52:42 2022 -0400

    Class variables, cost_attr, and reproducibility (#587)
    
    * test reproducibility
    
    * cost_attr, _eps and penalty as instance variables

[33mcommit 2478a3fca1c6c53191a905cc4a277b80ac545c5d[m
Merge: cc3e9ae 5de3f54
Author: zsk <shaokun.zhang@psu.edu>
Date:   Mon Jun 13 17:28:38 2022 -0400

    Merge branch 'microsoft:main' into main

[33mcommit 5de3f54fd91d06d67e35460f8f307ecacd85fa8e[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sun Jun 12 21:12:22 2022 -0700

    update time from start when using ray (#586)

[33mcommit f8cc38bc16fc3a09074b91b82bfda1d4ed9fd9b0[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Fri Jun 10 21:28:47 2022 -0700

    enable ensemble when using ray (#583)
    
    * enable ensemble when using ray
    
    * sanitize config

[33mcommit 0642b6e7bbaed8aab3fb775c51af4fda3472e242[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Thu Jun 9 08:11:15 2022 -0700

    init value type match (#575)
    
    * init value type match
    
    * bump version to 1.0.6
    
    * add a note about flaml version in notebook
    
    * add note about mismatched ITER_HP
    
    * catch SSLError when accessing OpenML data
    
    * catch errors in autovw test
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>

[33mcommit cc3e9ae9685fb9a54e2055fabb800f5600b13257[m
Merge: 6e76974 619107e
Author: zsk <shaokun.zhang@psu.edu>
Date:   Wed Jun 8 22:35:14 2022 -0400

    Merge branch 'microsoft:main' into main

[33mcommit 619107edf504905b069e0ca77f117f8aca32d042[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Mon Jun 6 03:38:17 2022 +0000

    install openml for notebook example

[33mcommit 18f692281a08eaea1ea52f6feff24725f92f151c[m
Author: Prajwal Borkar <sunnyborkar7777@gmail.com>
Date:   Sun Jun 5 23:33:26 2022 +0530

    Updated doc (#572)
    
    * Update website/docs/FAQ.md

[33mcommit 2d31138191d2cdf79d3400e2e52b32e09bee601e[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sun Jun 5 09:53:18 2022 -0700

    set holiday version <0.14 for prophet (#573)
    
    * set holiday version <0.14 for prophet
    
    * bump version to 1.0.5

[33mcommit c9bac02ea432e33de59ff1a3b5911fba5eb005f3[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Jun 4 12:00:58 2022 -0700

    add zeroshot notebook (#569)
    
    * add zeroshot notebook

[33mcommit 9d164a0119641922e975f3bc78df1627361af1cd[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Fri Jun 3 20:05:02 2022 -0400

    Update fit_kwargs_by_estimator example in Task-Oriented-AutoML.md (#561)
    
    * Update Task-Oriented-AutoML.md

[33mcommit e0e317bfb1bef6dbaa267ffd6c37f4ecd4f502b1[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Fri Jun 3 15:19:22 2022 -0400

    fixing trainable and update function, completing NOTE (#566)
    
    * fix checkpoint naming + trial id for non-ray mode, fix the bug in running test mode, delete all the checkpoints in non-ray mode
    
    * finished testing for checkpoint naming, delete checkpoint, ray, max iter = 1

[33mcommit c79c07f450a920c29d4282e29fd44ef7f1ed4d83[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Thu Jun 2 16:49:58 2022 +0000

    version update

[33mcommit 1af682b7f5f324d421a7c4d58cfe795468ff140c[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue May 31 17:21:57 2022 -0700

    update doc about scheduler exception (#564)
    
    * update doc about scheduler exception
    
    * remove assert

[33mcommit 927a4eeae53daa78fb6fed1dbf53ead056da60fe[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Tue May 31 15:11:21 2022 -0400

    Update documentation for FAQ about how to handle imbalanced data (#560)
    
    * Update website/docs/FAQ.md

[33mcommit d747800509e4e1145ded044ad394809fc504e08c[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue May 31 04:52:27 2022 +0000

    include .json file in flaml.default package

[33mcommit 6e76974823decb947b7dd3d6bc4dc3f6b7e817c3[m
Merge: bb6cd73 c35b844
Author: zsk <shaokun.zhang@psu.edu>
Date:   Sun May 29 02:06:17 2022 -0400

    Merge branch 'microsoft:main' into main

[33mcommit c35b8440305b3caacc572dbce38b19561039d717[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat May 28 19:17:40 2022 -0700

    simplify warmstart in blendsearch (#558)
    
    * simplify warmstart in blendsearch
    
    * bump version to 1.0.3

[33mcommit 49e8f7f0284603d44791375837584c0a7b4b3f77[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat May 28 17:22:09 2022 -0700

    use zeroshot when no budget is given; custom_hp (#563)
    
    * use zeroshot when no budget is given; custom_hp
    
    * update Getting-Started
    
    * protobuf version
    
    * X_val

[33mcommit 7748e0ff49b3982908f456e3bbda50486c0fbd18[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Thu May 26 11:13:08 2022 -0700

    Update Tune-User-Defined-Function.md (#562)
    
    Added one more use case of tune.

[33mcommit f8babac21beb24a54f554c03f8c73b61539e005d[m
Author: Prajwal Borkar <48290911+PrajwalBorkar@users.noreply.github.com>
Date:   Thu May 26 22:51:51 2022 +0530

    Removed cat_hp_host (#559)

[33mcommit dcc640c1a35cb0f4a2f632955add820478423d37[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Thu May 26 10:12:30 2022 -0400

    Documentation, test and bugfix (#556)
    
    * add bs restore test
    
    * use default metric when not provided
    
    * update documentation
    
    * remove print
    
    * period
    
    * remove bs restore test
    
    * Update website/docs/Use-Cases/Task-Oriented-AutoML.md

[33mcommit 515a77ac712893700766575be67500ac4f8f22cd[m
Author: LinWencong <503848070@qq.com>
Date:   Tue May 24 02:23:00 2022 +0800

    solve issue #542. fix pickle.UnpickingError while blendsearch warm start (#554)
    
    Issue I encountered:
    
    #542 run test_restore.py and got _pickle.UnpicklingError: state is not a dictionary
    
    I observed:
    
    1. numpy version
      i. When numpy==1.16*, np.random.RandomState.__getstate__() returns a tuple, not a dict.
        _pickle.UnpicklingError occurs
      ii. When numpy>1.17.0rc1, it returns a dict;
        _pickle.UnpicklingError does not occur
      iii. When numpy>1.17.0rc1, flaml uses np_random_generator = np.random.Generator,
        _pickle.UnpicklingError does not occur
    
    2. class _BackwardsCompatibleNumpyRng
      When I remove func _BackwardsCompatibleNumpyRng.__getattr__() , _pickle.UnpicklingError doesn't occur (regardless of numpy version == 1.16* or 1.17*)
    
    To sum up,
    I think making modifications to class _BackwardsCompatibleNumpyRng is not a good choice (_BackwardsCompatibleNumpyRng came from ray）and we still need to learn more about the operation mechanism of pickle.
    
    So I upgraded the numpy version that flaml requires：
      setup.py："NumPy>=1.17.0rc1"

[33mcommit d402c633124f8eaf865db94f5d7073cf3d008dd0[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Fri May 20 10:49:39 2022 -0700

    align indent and add missing quotation (#555)
    
    * align indent and add missing quotation

[33mcommit 992ea3416c83ddcdc13d999aae924b4c1897aa04[m
Author: harish445 <harishthakur4455@gmail.com>
Date:   Fri May 20 04:59:45 2022 +0530

    fix indentation in automl.py (#553)
    
    * fix indentation in flaml.py

[33mcommit 28511340528dfc9def29862f5076b4516eb7305f[m
Author: Qiaochu Song <qsong6@stevens.edu>
Date:   Thu May 19 11:43:34 2022 -0400

    Quick-fix (#539)
    
    * fix doc string; enable label transform in automl.score

[33mcommit 7126b69ce0d2d9c54b7774a3434e122313ed2734[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Wed May 18 21:01:51 2022 -0700

    choose n_jobs for ensemble according to n_jobs per learner (#551)
    
    * set n_jobs in ensemble dict
    
    * catch the ensemble error
    
    * choose n_jobs for stacker
    
    * clarify

[33mcommit 2ca9e41e4bea5b364df37494c26eaa77e8b150d0[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Thu May 12 10:57:25 2022 -0400

    fixing roberta add_prefix_space bug (#546)
    
    * fixing roberta add_prefix_space bug

[33mcommit 2a8decdc50bb5da054c20fb91760d30e445a77a0[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Tue May 10 17:22:57 2022 -0400

    fix the post-processing bug in NER (#534)
    
    * fix conll bug
    
    * update DataCollatorForAuto
    
    * adding label_list comments

[33mcommit c1bb66980c4d3b64f270faea8ee456bd94009d2c[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat May 7 09:13:17 2022 -0700

    test reproducibility from retrain (#533)

[33mcommit bcdfdc873553de42ff8221ae01d7596d09b11759[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Fri May 6 14:09:35 2022 -0400

    handle non-flaml scheduler in flaml.tune (#532)
    
    * handle non-flaml scheduler in flaml.tune
    
    * revise time budget
    
    * Update website/docs/Use-Cases/Tune-User-Defined-Function.md
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update website/docs/Use-Cases/Tune-User-Defined-Function.md
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update flaml/tune/tune.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * add docstr
    
    * remove random seed
    
    * StopIteration
    
    * StopIteration format
    
    * format
    
    * Update flaml/tune/tune.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * revise docstr
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit c1e1299855dcea378591628ae4ecb818426cb98f[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Mon May 2 11:05:23 2022 -0400

    fixing use_ray in automl.py (#531)
    
    * fixing use_ray

[33mcommit dab0a3f6e59bbdddf94d64b7735c05f305dfe594[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Apr 30 11:54:43 2022 -0700

    Bump cross-fetch from 3.1.4 to 3.1.5 in /website (#529)
    
    * Bump cross-fetch from 3.1.4 to 3.1.5 in /website
    
    * Bump async from 2.6.3 to 2.6.4 in /website
    
    * cleanup

[33mcommit ca35fa969f3031dd042af6d72841136f36477a27[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Thu Apr 28 14:06:29 2022 -0400

    refactoring TransformersEstimator to support default and custom_hp (#511)
    
    * refactoring TransformersEstimator to support default and custom_hp
    
    * handling starting_points not in search space
    
    * addressing starting point more than max_iter
    
    * fixing upper < lower bug

[33mcommit d03038bfcb0dace521f20130af6829058465403f[m
Author: Jaden Kropp <98624709+elbowgreasel@users.noreply.github.com>
Date:   Wed Apr 27 08:50:38 2022 -0600

    docstr cleanup #523: removed lines 259 to 260 in a1c49ca (#524)

[33mcommit a1c49ca27be8439e69904bec222eed65705a5f0d[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Apr 23 16:22:34 2022 -0700

    allow evaluated_rewards shorter than points_to_evaluate (#522)
    
    * allow evaluated_rewards shorter than points_to_evaluate
    
    * docstr update

[33mcommit f301bf8d8f1a4ad71b5a0038250cd1b90b2d8355[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Apr 23 15:33:35 2022 -0700

    max choice is n-1 (#521)
    
    close #520

[33mcommit 46f80dfa16a1396027a2f8fea2460f5795e3ee20[m
Author: Jay Shankar <jayshankar.pandit@smartcoin.co.in>
Date:   Fri Apr 15 23:23:43 2022 +0530

    Fix AttributeError: readonly attribute for Python 3.10.4

[33mcommit cfed6578121ac5d1e7f2212b15f6fb7babfd751d[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Tue Apr 12 14:46:14 2022 -0400

    Handling fractional gpu_per_trial for NLP (#513)
    
    * handling fractional gpu_per_trial

[33mcommit e877de6414684c7bb6ef638aae5092bcab10b23d[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Thu Mar 31 18:06:24 2022 +0000

    use ffill in forecasting example

[33mcommit 84f1ae7424c8761f29890dfffc7720a7baa31938[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Wed Mar 30 22:19:47 2022 -0700

    Bump minimist from 1.2.5 to 1.2.6 in /website (#502)
    
    * Bump minimist from 1.2.5 to 1.2.6 in /website
    
    * check best_config in test

[33mcommit 2cdc08a75ae664f49ab23e5a5b310d0bf5152cc6[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Wed Mar 30 22:01:18 2022 +0000

    update notebook and test

[33mcommit 9128c8811ad7bccde6cf2fb68c89ec4d9a0ec219[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Mon Mar 28 16:57:52 2022 -0700

    handle failing trials (#505)
    
    * handle failing trials
    
    * clarify when to return {}
    
    * skip ensemble in accuracy check

[33mcommit 0bcf618feabc21590edb21b09d20da6858dc3cd8[m
Author: liususan091219 <xliu127@stevens.edu>
Date:   Sun Mar 27 20:10:51 2022 -0400

    fixing bug

[33mcommit 6c16e47e425d282441e2730f34282cf581579601[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Sat Mar 26 21:11:45 2022 -0400

    Bug fix and add documentation for metric_constraints (#498)
    
    * metric constraint documentation
    
    * update link
    
    * update notebook
    
    * fix a bug in adding 'time_total_s' to result
    
    * use the default multiple factor from config file
    
    * update notebook
    
    * format
    
    * improve test
    
    * revise test budget for macos
    
    * bug fix in adding time_total_s
    
    * increase performance check budget
    
    * revise test
    
    * update notebook
    
    * uncomment test
    
    * remove redundancy
    
    * clear output
    
    * remove n_jobs
    
    * remove constraint in notebook
    
    * increase budget
    
    * revise test
    
    * add python version
    
    * use getattr
    
    * improve code robustness
    
    Co-authored-by: Qingyun Wu <qxw5138@psu.edu>

[33mcommit 72301b856814b7c011f02ad8d49ed15f2b93fac1[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Sat Mar 26 14:08:51 2022 -0400

    fixing a few bugs in nlp (#503)
    
    * fixing bugs in nlp

[33mcommit 7eb7b46ea9ecc5b0e1b368d75353927dd4e33cb5[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Fri Mar 25 17:32:37 2022 -0700

    version number and doc (#497)
    
    * version number
    
    * add missing tasks in documentation
    
    * update node-forge version

[33mcommit 5f97532986958be4eeaf969fa100a81d253d70cd[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Fri Mar 25 17:00:08 2022 -0400

    adding evaluation (#495)
    
    * adding automl.score
    
    * fixing the metric name in train_with_config
    
    * adding pickle after score
    
    * fixing a bug in automl.pickle

[33mcommit 1d029436e7062ad9cebcd16c5b3c4e852246e1db[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Mon Mar 21 17:39:03 2022 +0000

    doc update (#490)

[33mcommit af423463c3d0896932c916ad616bb52b901d16a6[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Sun Mar 20 22:03:02 2022 -0400

    fixing bug for ner (#463)
    
    * fixing bug for ner
    
    * removing global var
    
    * adding class for trial counter
    
    * adding notebook
    
    * adding use_ray dict
    
    * updating documentation for nlp

[33mcommit 5f688c166283d86c133a2706e13a7bfab40bcf8c[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sun Mar 20 15:56:31 2022 +0000

    lightgbm

[33mcommit f6ae1331f54af88d516d2a99287e53ff539f9cf8[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Sat Mar 12 00:39:35 2022 -0500

    metric constraints in flaml.automl (#479)
    
    * metric constraints
    
    * revise docstr
    
    * fix docstr
    
    * improve docstr
    
    * Update flaml/automl.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update flaml/automl.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update flaml/automl.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * docstr
    
    Co-authored-by: Qingyun Wu <qxw5138@psu.edu>
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit f9eda0cc405bf45986ccf12e4f31b833d6b654ed[m
Author: Kevin Chen <74878789+int-chaos@users.noreply.github.com>
Date:   Tue Mar 8 14:21:18 2022 -0500

    update documentation for time series forecasting (#472)
    
    * update automl.py
    - documentation update
    
    * update test_forecast.py
    
    * update model.py
    
    * update automl_time_series_forecast.ipynb
    
    * update time series forecast website examples
    
    Signed-off-by: Kevin Chen <chenkevin.8787@gmail.com>

[33mcommit f0b0cae682ce827f0356cc31b961bdf98a08b714[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Mar 5 11:49:39 2022 -0800

    zero-shot AutoML in readme (#474)
    
    * zero-shot AutoML in readme
    
    * use pydoc-markdown 4.5.0 to avoid error in 4.6.0

[33mcommit 31ac984c4bc5e2122ee0e8c2e93b2cdd7fc28859[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Mar 1 18:39:16 2022 -0800

    don't init global search with points_to_evaluate unless evaluated_rewards is provided; handle callbacks in fit kwargs (#469)

[33mcommit df01031cfe34fd056c97b51f191b35f419dd4713[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Mar 1 15:39:09 2022 -0800

    Zero-shot AutoML (#468)
    
    * Prepare for release
    
    Co-authored-by: Moe Kayali <t-moekayali@microsoft.com>
    
    * bug fix
    
    * improve doc and code quality
    
    Co-authored-by: Qingyun Wu

[33mcommit 01ca0422eaa236620fc5dfbc1420b5137664ca7f[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Feb 26 06:17:12 2022 +0000

    Bump prismjs from 1.25.0 to 1.27.0 in /website

[33mcommit e3e737c71a7592954a15c3f8499b46558ab7f2ef[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Fri Feb 25 22:13:41 2022 -0800

    make AutoML.classes_ an array (#467)
    
    * remove .tolist()
    
    * docstr

[33mcommit 6095be039ff6f45f82078120da0109aea82b66f5[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Feb 15 13:17:43 2022 -0800

    update regression metrics in notebooks (#454)

[33mcommit 05f9065ade50ebf31b781e44db0d86090b0840ff[m
Author: Qingyun Wu <qw2ky@virginia.edu>
Date:   Tue Feb 15 12:41:53 2022 -0500

    Docstr update (#460)
    
    * parallel tuning docstr
    
    * update n_concurrent_trials docstr
    
    * n_jobs default
    
    * parallel tuning in tune docstr

[33mcommit 393106d53187d810d01b6e2b398f6f47bfe0c513[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Feb 15 04:48:11 2022 +0000

    Bump follow-redirects from 1.14.7 to 1.14.8 in /website

[33mcommit dea2beec34b4612063d276d6f2cdf8390dd91930[m
Author: Camila Martinez Bedoya <44549364+cammarb@users.noreply.github.com>
Date:   Sat Feb 12 16:12:19 2022 -0500

    Update Getting-Started.md
    
    Solving issue #456 related to a typo on the webpage.

[33mcommit 9e88f221679cbe99a8e7ebcb4d89ac29cd68b7e0[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Fri Feb 11 20:14:10 2022 -0800

    fix a bug when using ray & update ray on aml (#455)
    
    * fix a bug when using ray & update ray on aml
    When using with_parameters(), the config argument must be the first argument in the trainable function.
    * make training function runnable standalone

[33mcommit b4d312412a6b11ab7d799f670eeeedcca9348f6f[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Wed Feb 9 15:04:29 2022 -0800

    bump ray version to 1.10 (#450)
    
    * bump ray version to 1.10
    
    * init ray in test
    
    * Update setup.py to include hotfixes
    
    Co-authored-by: Antoni Baum <antoni.baum@protonmail.com>

[33mcommit a4970d279c192ec3341efe13eb948978ee849737[m
Author: MichaelMarien <marien.mich@gmail.com>
Date:   Fri Feb 4 22:03:09 2022 +0100

    corrected typo in example xgboost documentation (#449)

[33mcommit b930de0e1f661d8f1e4f047dc0cac4c9464bf2d9[m
Author: vvijayalakshmi21 <34595292+vvijayalakshmi21@users.noreply.github.com>
Date:   Thu Feb 3 23:10:57 2022 +0530

    Update Tune-User-Defined-Function.md (#448)
    
    Fix for #445

[33mcommit 34557de30c6bb38ab6a22c64dbbebd287d3c5d5d[m
Author: vvijayalakshmi21 <34595292+vvijayalakshmi21@users.noreply.github.com>
Date:   Thu Feb 3 22:34:49 2022 +0530

    Update Task-Oriented-AutoML.md (#447)
    
    Fix for issue #444

[33mcommit 6d7c2e3e9bdd34a1bf95662963a357754b783498[m
Author: vvijayalakshmi21 <34595292+vvijayalakshmi21@users.noreply.github.com>
Date:   Thu Feb 3 12:22:43 2022 +0530

    Update Task-Oriented-AutoML.md
    
    Fix Typo for issue 443

[33mcommit ba5d4d19f0658613aa93e2c8a6ff50a33ab36a79[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sun Jan 30 21:14:47 2022 -0800

    note about preview feature (#431)

[33mcommit 8a44dd4318e9a1454d6e0b80d872997482d5c8d5[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sun Jan 30 19:36:41 2022 -0800

    data in csv (#430)
    
    * data in csv
    
    * support ray ObjectRef #365
    
    * use object store to store data when using ray
    
    * make lgbm tuning example a test
    
    * homepage title

[33mcommit 6960a833eca93b14d1da9201eb1d030a745bab51[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sun Jan 30 13:02:18 2022 -0800

    Gpu support for xgboost (#442)
    
    * xgboost gpu support
    
    * test xgboost gpu
    
    * test sparse data
    
    * add xgboost test
    
    * remove ray.init to avoid pytest error

[33mcommit c75f97b475ba94da8bd943d45bb001706fde8209[m
Author: Kevin Chen <74878789+int-chaos@users.noreply.github.com>
Date:   Sun Jan 30 10:30:30 2022 -0500

    Change the upper bound for "lags" hyperparameter for sklearn forecast models (#437)
    
    * update model.py
    - change upper bound for "lags" hyperparameter
    
    * update test_forecast.py
    - add a test for a large dataset
    
    * update sample.py
    - pre-commit changes

[33mcommit 438ccaa0c9411a1157c8f9dc9c2db8ef0a307789[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Sun Jan 30 01:53:32 2022 -0500

    adding catch for HTTP error (#432)

[33mcommit 1a479e4bdb249a4179f7181ae2f9d7598d6026a4[m
Author: m13uz <murat@unitary.ai>
Date:   Fri Jan 28 21:27:40 2022 +0300

    fix a broken link in README.md

[33mcommit 99de9204b3d92703f1afc0773e6d4441b5c14348[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Jan 25 15:29:38 2022 -0800

    homepage update (#425)
    
    * homepage update
    
    * update README

[33mcommit 81f54026c94312557a3e258c3073ede63fbb35be[m
Author: Kevin Chen <74878789+int-chaos@users.noreply.github.com>
Date:   Mon Jan 24 21:39:36 2022 -0500

    Support time series forecasting for discrete target variable (#416)
    
    * support 'ts_forecast_classification' task to forecast discrete values
    
    * update test_forecast.py
    - add test for forecasting discrete values
    
    * update test_model.py
    
    * pre-commit changes

[33mcommit 4814091d87ce00c8c231fc94ebd1c4c2f18c880b[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Mon Jan 24 17:24:14 2022 -0500

    remove redundant imports (#426)
    
    * remove redundant imports
    
    * getting ride of hf dataset

[33mcommit 6a7caa6a3d06b1d8253b250471eaa0d62c4d6df6[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sun Jan 23 01:24:15 2022 -0800

    max_iter < 2 -> no search; sign in metric constraints; test and example for forecasting (#415)
    
    * max_iter < 2 -> no search
    
    * use_ray in test
    
    * eval_method in ts example
    
    * check sign of constraints
    
    * test metric constraint sign

[33mcommit 38ad31ea2537569d737d8f407a5ff8b69197fc77[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Jan 22 22:59:44 2022 -0800

    remove FLAML sample size from config (#418)

[33mcommit 113539545c0c7a02300a76edc5f2dcd2a4d3f361[m
Author: Antoni Baum <antoni.baum@protonmail.com>
Date:   Sun Jan 23 07:14:49 2022 +0100

    Use Ray _BackwardsCompatibleNumpyRng if possible (#421)

[33mcommit 4e8b6b98b0536d6ea5b342e2d4472adebee71b6b[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Jan 22 20:43:48 2022 +0000

    bump flaml version to 0.9.6

[33mcommit d2b2f98a0d8bc5d50f372653c98defefb21be0a1[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Jan 22 19:26:02 2022 +0000

    bump version of node-fetch to 3.1.1 in website/

[33mcommit 66bbe782ee9522780322818b755853b1aaaae8d4[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Jan 22 11:02:32 2022 +0000

    Bump nanoid from 3.1.30 to 3.2.0 in /website

[33mcommit 47d2295fb7c9480051fbdbcaabdd1f4e8111cf53[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Tue Jan 18 21:37:35 2022 -0500

    Set use_ray to True for logging to databricks (#414)
    
    * fixing use_ray bug

[33mcommit bb6cd73fb53d2ab6a930a705fc4492e504ad682b[m
Merge: d7ff258 3ef758c
Author: Z.sk <shaokunzhang@psu.edu>
Date:   Tue Jan 18 09:30:36 2022 +0800

    Merge pull request #3 from microsoft/main
    
    update

[33mcommit 3ef758cd7bb50551018b1efae2db0d8e2f538c5c[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Mon Jan 17 14:44:11 2022 -0500

    reducing AutoConfig.from_pretrained (#411)
    
    * reducing AutoConfig.from_pretrained

[33mcommit 1c911da9f83b8575a1a9849d2276474733aef98c[m
Author: MichaelMarien <marien.mich@gmail.com>
Date:   Sun Jan 16 23:37:56 2022 +0100

    Sklearn api x (#405)
    
    * changed signature of automl.predict and automl.predict_proba to X
    
    * XGBoostEstimator
    
    * changed signature of Prophet predict to X
    
    * changed signature of ARIMA predict to X
    
    * changed signature of TS_SKLearn_Regressor predict to X

[33mcommit a6d70efff76f5bcb80dedfe8d7cdad3563cd9ac3[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sun Jan 16 09:41:11 2022 -0800

    Bump shelljs from 0.8.4 to 0.8.5 in /website (#402)

[33mcommit cb9c7b0d1613eae1b573736a6ad0faf80b9054b2[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Sun Jan 16 12:07:31 2022 -0500

    adding logging of training loss (#406)
    
    * reducing AutoTokenizer load to only once
    
    * fixing early stop bug

[33mcommit 8f0737c57cd59c6173a8fa7e123ab8b213b82445[m
Author: Qingyun Wu <qw2ky@virginia.edu>
Date:   Sat Jan 15 17:44:42 2022 -0500

    update browser icon (#407)
    
    * update ico

[33mcommit ac16c31000a525ec8c5e00f23aba5abb0cf68a2c[m
Author: Qingyun Wu <qw2ky@virginia.edu>
Date:   Sat Jan 15 00:32:04 2022 -0500

    Logo (#399)
    
    * add logo
    
    * update link to file
    
    * Update README.md
    
    * del png
    
    * update website logo
    
    * update icon
    
    Co-authored-by: Qingyun Wu <qxw5138@psu.edu>
    Co-authored-by: 张少坤 <zhangshaokun@fuzhi.ai>
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 31645187f3f6e3887acc5a1ee649715dff226896[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Fri Jan 14 20:55:38 2022 -0500

    Update flaml/nlp/README.md (#404)

[33mcommit dda4ac90a1e7ec02f7ab454059e541488d0a30ee[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Fri Jan 14 20:26:10 2022 -0500

    moving intermediate_results logging from model.py to huggingface/trainer.py (#403)
    
    * replacing val_loss with automl_metric

[33mcommit 569908fbe64f08b19fbef7487513b81d62e6eaba[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Fri Jan 14 13:39:09 2022 -0800

    fix issues in logging, bug in space.py, constraint sign, and improve code coverage (#388)
    
    * console log handler
    
    * version update
    
    * doc
    
    * skippable steps
    
    * notebook update
    
    * constraint sign
    
    * doc for constraints
    
    * bug fix: define-by-run and unflatten_hierarchical
    
    * const
    
    * handle nested space in indexof()
    
    * test grid search
    
    * test suggestion
    
    * model test
    
    * >1 ckpts
    
    * always increase iter count
    
    * log total # iterations
    
    * security patch
    
    * make iter_per_learner consistent

[33mcommit d7ff258b89c8170e29f4ecd9a8ab12a7fddf2d22[m
Merge: b66930e c1b5cb5
Author: Z.sk <shaokunzhang@psu.edu>
Date:   Fri Jan 14 23:07:06 2022 +0800

    Merge pull request #2 from microsoft/main
    
    update

[33mcommit c1b5cb534890262bce52985a7ea8bbc1f2c80e36[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Fri Jan 14 00:08:51 2022 -0500

    fixing default metric for regression + change verbosity for transformers (#397)
    
    * fixing default metric for regression + change verbosity for transformers
    
    * fixing per_device_train_batch_size
    
    * Update flaml/automl.py for gpu_per_trial

[33mcommit 8e72904b9ef1d2d106221c184a08067315279fc4[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Wed Jan 12 22:24:17 2022 -0800

    postcss version update (#385)

[33mcommit f41f1c2198b9301f9a0c77501be2349de48b9d20[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Wed Jan 12 22:50:39 2022 -0500

    Logging multiple checkpoints (#394)

[33mcommit 303d40c76c8bde3f287ebdf2a433dc454d739825[m
Author: liususan091219 <xliu127@stevens.edu>
Date:   Wed Jan 12 00:10:31 2022 -0500

    set verbose for transformers

[33mcommit 99667dad5f4931120551b56aa9a955b4ff0e6f15[m
Author: Kevin Chen <74878789+int-chaos@users.noreply.github.com>
Date:   Tue Jan 11 16:16:59 2022 -0500

    Regression forecast debug (#391)
    
    * update automl.py
    - fix bug with removing "catboost"

[33mcommit bd66e4029614bc2bdcb8eea37ef878783b5f85e4[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Tue Jan 11 13:47:53 2022 -0500

    fixing load best model at the end (#389)

[33mcommit b66930e4f0349ce1efeee790b6fd0b3134a8cf08[m
Merge: f3fc35c c54c124
Author: Z.sk <shaokunzhang@psu.edu>
Date:   Tue Jan 11 08:32:50 2022 +0800

    Merge pull request #1 from microsoft/main
    
    update

[33mcommit c54c1246c63068487c14ddecee9cd435b4d29ca5[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Fri Jan 7 19:25:58 2022 -0500

    fixing auto metric bug (#387)

[33mcommit d4273669e6b223c3ad4bfddef568ad13ab64c007[m
Author: Kevin Chen <74878789+int-chaos@users.noreply.github.com>
Date:   Fri Jan 7 02:12:38 2022 -0500

    Time series forecasting with sklearn regressors (#362)
    
    * add sklearn regressors as learners for ts_forecast task
    
    * add direct forecasting strategy
    warnings and errors for duplicate rows and missing values
    
    - add preprocess for sklearn time series forecast
     update automl.py
     update test/test_forecast.py
    
    * update model.py and test_forecast.py for cv eval_method
    
    * add "hcrystalball" dependency in setup.py
    
    * update automl.py
    - add _validate_ts_data function for abstraction
    - include xgb_limitdepth as a learner
    
    * update model.py
    - update search space for sklearn ts regressors
    
    * update automl.py and test_forecast.py for numpy array inputs
    
    * add documentations to model.py
    
    * add documentation for removing catboost regressor
    
    * update automl.py
    - _validate_ts_data() function
    
    Signed-off-by: Kevin Chen <chenkevin.8787@gmail.com>

[33mcommit 612668e8ed7bbed66ee1a6f50914e6b4204dd5b7[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Thu Jan 6 10:28:19 2022 -0800

    serialize TransformerEstimator (#381)
    
    * serialize TransformerEstimator
    
    * check has_attr
    
    * custom metric needs trainer
    
    * skip test on mac

[33mcommit cd9740f022defa065578d9f1709195c9ac439dff[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Wed Jan 5 13:49:12 2022 -0800

    Fix several issues for nlp tasks (#380)
    
    * num cpu issue #378;
    * temp fix for ray issue #379;
    * transformers version.

[33mcommit 8593a3fe273791eafa19957741777830cd6548a7[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Jan 4 15:13:14 2022 -0800

    citation file (#364)

[33mcommit 207b6935d9b11966c5cc0d82c4d047bf28303a1e[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Mon Jan 3 13:44:10 2022 -0500

    adding token classification (#376)
    
    * adding ner

[33mcommit 8602def1c4535c5d023a0b69c1a999d3c348abb9[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sun Jan 2 21:37:19 2022 -0800

    logging (#371)
    
    * query logged runs
    
    * mlflow log when using ray
    
    * key check for newer version of ray #363
    
    * catch importerror
    
    * log and load AutoML model
    
    * retrain if necessary when ensemble fails

[33mcommit 9c00e4272a7d448131aaead72342f52c6a900388[m
Author: oberonbot <91398474+oberonbot@users.noreply.github.com>
Date:   Sun Jan 2 20:12:34 2022 -0500

    Finish the Multiple Choice Classification (#367)
    
    * adding multiple choice
    
    * update test cases (hard coded)
    
    * merged common code in predict_proba and predict in TransformersEstimator

[33mcommit 2f5d6169d3b5cc025eb2516cbd003fced924a88e[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Dec 25 16:13:39 2021 -0800

    example update (#359)
    
    update some examples for consistencies with others.

[33mcommit b2900f4b222a8cf236fcb90b4c7ea22cffe64d6a[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Fri Dec 24 16:23:09 2021 -0500

    fixing custom metric (#357)
    
    * fixing the error for custom metric

[33mcommit c6c0c29769ab9982c4b57783ca36e3a4c61667cb[m
Author: Rui Zhuang <7812164+ruizhuanguw@users.noreply.github.com>
Date:   Thu Dec 23 23:05:14 2021 -0800

    Simplify lgbm example (#358)
    
    * simplify lgbm examples
    
    * provide link to lgbm example script.
    
    * simply lgbm example in the example script.
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit dcfd2181086a74949f40d033cb5f36ccb05b9186[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Thu Dec 23 18:44:53 2021 -0500

    Fixing the bug in custom metric (#356)
    
    * fixing the bug for custom metric

[33mcommit 300f28666716e659bc9e4b457ad00e92fd4ec80e[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Thu Dec 23 13:37:07 2021 -0800

    azureml + ray (#344)
    
    * examples and documentation about how to use azureml + ray

[33mcommit baa0359324d73921b67e37e40c96b7dbbe6e0f8b[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Wed Dec 22 14:35:13 2021 -0800

    doc update (#352)
    
    * custom splitter
    * NLP
    * version number

[33mcommit 0b25e89f294189ef1b92ff45e1346a6f0896ca13[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Wed Dec 22 12:12:25 2021 -0800

    reproducibility for random sampling (#349)
    
    * reproducibility for random sampling #236
    
    * doc update

[33mcommit ee3162e23281f96842ec91854af269019b8f53c4[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Mon Dec 20 17:19:32 2021 -0500

    Adding the NLP task summarization (#346)
    
    * Add test_autohf_summarization.py
    
    * adding seq2seq
    
    * Update flaml/nlp/huggingface/trainer.py
    
    * rouge metrics
    
    Co-authored-by: XinZofStevens <xzhao4346@gmail.com>
    Co-authored-by: JinzhuoWu <wujinzhuo0105@gmail.com>
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit a340dbc55469d388c81ffc2b5a04d5184812311e[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Dec 18 20:27:42 2021 +0000

    url update for doc edit

[33mcommit f3fc35c438c137bb2b2f118ffbc0d890c5432da3[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Fri Dec 17 01:37:31 2021 +0000

    version update

[33mcommit efd85b4c868de3366f56f08cb38f1c3ade0f7a80[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Thu Dec 16 17:11:33 2021 -0800

    Deploy a new doc website (#338)
    
    A new documentation website. And:
    
    * add actions for doc
    
    * update docstr
    
    * installation instructions for doc dev
    
    * unify README and Getting Started
    
    * rename notebook
    
    * doc about best_model_for_estimator #340
    
    * docstr for keep_search_state #340
    
    * DNN
    
    Co-authored-by: Qingyun Wu <qingyun.wu@psu.edu>
    Co-authored-by: Z.sk <shaokunzhang@psu.edu>

[33mcommit 671ccbbe3fa64865e0729bb0ff8c4b66107a5358[m
Author: Chia-Chi Hsu <wuchi5457@gmail.com>
Date:   Fri Dec 17 08:13:04 2021 +0800

    support for customized splitters (#333)
    
    * add support for customized splitters
    
    * use the param split_type for feeding generators
    
    * use single API for customized splitter and add test
    
    * when task==TS_FORCAST, always set shuffle=False
    
    * update docstr
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 7b24662dca1b54ead02bc034cd800a66f575c1d4[m
Author: Z.sk <shaokunzhang529@gmail.com>
Date:   Thu Dec 16 13:12:47 2021 +0800

    Makes the evaluation_function could receive the incumbent best result as input in Tune (#339)
    
    * update tune function
    
    * pass incumbent result to the training function
    
    * Update test/tune/test_record_incumbent.py
    
    * Update flaml/searcher/search_thread.py
    
    * Update flaml/searcher/blendsearch.py
    
    * Update flaml/tune/tune.py
    
    * add constant variable
    
    Co-authored-by: 张少坤 <zhangshaokun@fuzhi.ai>
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 228b00cbee8c0d9739d473ed4cd6cf57adb994cb[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sun Dec 12 21:10:06 2021 -0800

    use cfo in tune.run if bs is not installed (#334)
    
    Use cfo in tune.run if bs is not installed and issue a warning.

[33mcommit 434586e2e2d77d91328925cd31c83bfd71403804[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sun Dec 12 20:05:18 2021 -0800

    train at least one iter when not trained (#336)
    
    * train at least one iter when not trained
    
    * bump version to 0.9.1

[33mcommit 1a3e01c3521ee5dbb288e6cd6a1fca65c411d64e[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Fri Dec 10 12:32:49 2021 -0500

    adding HF metrics (#335)
    
    * adding nlp metrics
    
    * fix ndcg

[33mcommit b773e2898f0c62091687001ce57f121716244077[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Mon Dec 6 14:55:05 2021 -0800

    Update flaml_pytorch_cifar10.ipynb
    
    training_function -> train_cifar

[33mcommit dd60dbc5eb7e6d298c5f1506a8e0b7a8bb390052[m
Author: Qingyun Wu <qw2ky@virginia.edu>
Date:   Mon Dec 6 17:03:43 2021 -0500

    rename training_function (#327)
    
    * rename training_function
    
    * add docstr
    
    * update docstr
    
    * update docstr and comments
    
    Co-authored-by: Qingyun Wu <qxw5138@psu.edu>

[33mcommit 3111084c0766e8dd77b8ca8d36eea358d939adc2[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Mon Dec 6 08:12:49 2021 +0000

    add __init__.py in nlp

[33mcommit 17b17d084ff1d1daf28090ce18039fc195f995d7[m
Author: Qingyun Wu <qw2ky@virginia.edu>
Date:   Sat Dec 4 21:52:20 2021 -0500

    tune api for schedulers (#322)
    
    * revise api and tests
    
    * rename prune_attr
    
    * update finetune notebook
    
    * add scheduler test and notebook
    
    * update tune api for scheduler
    
    * remove scheduler notebook
    
    * Update flaml/tune/tune.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * docstr
    
    * fix imports
    
    * clear notebook output
    
    * fix ray import
    
    * Update flaml/tune/tune.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * improve docstr
    
    * Update flaml/searcher/blendsearch.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * remove redundant import
    
    Co-authored-by: Qingyun Wu <qxw5138@psu.edu>
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 7d269435aeb2c23ef91802f59f694fbd73c27ae5[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Dec 4 18:27:38 2021 +0000

    add save_best_config()

[33mcommit 54d303a95ab8615ec298a5a7a530f8d1d477bf68[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Fri Dec 3 19:37:49 2021 -0800

    bug fix in confg2params (#323)
    
    * bug fix in confg2params
    
    * set the task property before config2params

[33mcommit 18230ed22f9cd1f10c9c044dfde1623b5abc038b[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Fri Dec 3 16:02:00 2021 -0800

    pred_time_limit clarification and logging (#319)
    
    * pred_time_limit clarification
    
    * log prediction time
    
    * handle ChunkedEncodingError in test

[33mcommit fb59bb992843aefd67a49f876eae4175ee3622d4[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Fri Dec 3 12:45:16 2021 -0500

    adding TODOs for NLP module, so students can implement other tasks easier (#321)
    
    * fixing ray pickle bug, skipping macosx bug, completing code for seqregression
    
    * catching connectionerror
    
    * ading TODOs for NLP module

[33mcommit c57954fbbd13e2e66a5bba9d0f2fb3555c4f945f[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Fri Dec 3 09:15:21 2021 -0800

    include default value in rf search space (#317)
    
    * include default value in rf search space
    
    * init _mem_per_iter with -1
    
    * bump version to 0.8.2
    
    * docstr for search space's arguments

[33mcommit 1545d5a6d22597715ba04e59526df2b0470f7a98[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sun Nov 28 11:18:55 2021 -0800

    skip cv preparation if eval_method is holdout (#314)
    
    * skip cv preparation if eval_method is holdout
    
    * bump version to 0.8.1

[33mcommit 2f25a87d98205eccd4c8e39954e320d0932d9aaa[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sun Nov 28 10:14:25 2021 -0800

    Code quality improvement based on #275 (#313)
    
    * simplify & restructure
    
    Co-authored-by: Albern S <62778698+albernsrya@users.noreply.github.com>

[33mcommit 63f402b29e500badb286bf409cef799941f2f534[m
Author: liususan091219 <xliu127@stevens.edu>
Date:   Fri Nov 26 22:40:37 2021 -0500

    fixing config2params for transformersestimator

[33mcommit b0ef3b79957f3f7c44512920420ce429014667ab[m
Author: Michal Chromcak <michalchromcak@gmail.com>
Date:   Thu Nov 25 22:58:20 2021 +0100

    Add conda forge minimal test (#309)
    
    * add conda forge minimal test, create pytest markers

[33mcommit 5dc948da18a6448621be19c780306316112992dd[m
Author: 晓宇 <57928993+fengsxy@users.noreply.github.com>
Date:   Fri Nov 26 00:18:22 2021 +0800

    Update test_regression.py (#306)
    
    * Update test_regression.py
    
    There is a another way for mutioutput-model-trian.
    RegressorChain is more adapting to the targets which are relavant.

[33mcommit fd136b02d19ea7c046b04e8aa8ae65805efb0579[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Tue Nov 23 14:26:39 2021 -0500

    bug fix for TransformerEstimator (#293)
    
    * fix checkpoint naming + trial id for non-ray mode, fix the bug in running test mode, delete all the checkpoints in non-ray mode
    
    * finished testing for checkpoint naming, delete checkpoint, ray, max iter = 1
    
    * adding predict_proba, address PR 293's comments
    
    close #293 #291

[33mcommit 85e21864ce20a323fefe297b18b8aa75f9a72f59[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Mon Nov 22 22:17:29 2021 -0800

    test -> val; docstr (#300)
    
    * rename test -> val in custom metric function
    * add an example in docstr
    resolve #299

[33mcommit ea6d28d7bd739cce57c654306dbfd6b6a741aa00[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Mon Nov 22 21:17:48 2021 -0800

    add max_depth to xgboost search space (#282)
    
    * add max_depth to xgboost search space
    
    * notebook update
    
    * two learners for xgboost (max_depth or max_leaves)

[33mcommit d937b03e42b7cd0d96d35b2dc1ecc5fbf30fe4a2[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Mon Nov 22 06:59:42 2021 -0800

    multioutput regression (#292)
    
    * make AutoML inherit sklearn.base.BaseEstimator such that it can be wrapped in sklearn.multioutput.MultiOutputRegressor for multi-output regression.
    
    * moved and simplified preprocessing code in AutoML.predictI() to _preprocess()

[33mcommit 00da79a90b12158d3ce799099a8f09ae5c7d8750[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Nov 20 20:05:28 2021 -0800

    empty search space (#295)
    
    fix the error when an empty dictionary is passed to BlendSearch as the search space.

[33mcommit 49f9e9f86be3201f8e670d9cc0a4d1b288754be7[m
Author: Qingyun Wu <qw2ky@virginia.edu>
Date:   Sat Nov 20 20:23:54 2021 -0500

    add warmstart test (#298)
    
    * add warmstart test
    
    * remove redundancy
    
    * add more types of hps
    
    * revise comments
    
    * simplify name
    
    * reduce redundancy

[33mcommit db1fb9b47b52d82e24368a0527be88db7025c0f7[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Thu Nov 18 11:19:53 2021 -0800

    datetime feature engineering (#285)
    
    resolve #284
    When transforming test data, keep a derived column as long as it is kept in the training data.

[33mcommit 72caa2172dc6e27b25caa4962dc968bb8b05b0ca[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Thu Nov 18 09:39:45 2021 -0800

    model_history, ITER_HP, settings in AutoML(), checkpoint bug fix (#283)
    
    if save_best_model_per_estimator is False and retrain_final is True, unfit the model after evaluation in HPO.
    retrain if using ray.
    update ITER_HP in config after a trial is finished.
    change prophet logging level.
    example and notebook update.
    allow settings to be passed to AutoML constructor. Are you planning to add multi-output-regression capability to FLAML #192 Is multi-tasking allowed? #277 can pass the auotml setting to the constructor instead of requiring a derived class.
    remove model_history.
    checkpoint bug fix.
    
    * model_history meaning save_best_model_per_estimator
    
    * ITER_HP
    
    * example update
    
    * prophet logging level
    
    * comment update in forecast notebook
    
    * print format improvement
    
    * allow settings to be passed to AutoML constructor
    
    * checkpoint bug fix
    
    * time limit for autohf regression test
    
    * skip slow test on macos
    
    * cleanup before del

[33mcommit e9551de3ccdefab32405706be8416274d49ccce8[m
Author: Qingyun Wu <qingyun.wu@psu.edu>
Date:   Thu Nov 18 05:03:12 2021 +0000

    add best_loss_per_estimator

[33mcommit 42de3075e972e435f0998f768b97e57f1b9b9205[m
Author: Xueqing Liu <liususan091219@users.noreply.github.com>
Date:   Tue Nov 16 14:06:20 2021 -0500

    Make NLP tasks available from AutoML.fit() (#210)
    
    Sequence classification and regression: "seq-classification" and "seq-regression"
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 59083fbdcb95c15819a0063a355969203022271c[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Fri Nov 12 22:29:33 2021 -0800

    example update (#281)
    
    * example update
    
    * bump version to 0.7.2
    
    * notebook update

[33mcommit 92ebd1f7f9bb2e674de5d94721f13544fbc52d82[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Nov 9 21:51:23 2021 -0800

    when max_iter=1, skip search only if retrain_final (#280)
    
    * when max_iter=1, skip search only if retrain_final
    
    * remove nlp
    redesign in #210
    
    * minor change in readme example

[33mcommit 5b0932e442e41316a8ddaff460ec15cfdffd18ca[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Nov 9 21:23:54 2021 -0800

    Unify regression and classification for XGBoost (#276)
    
    * scikit-learn API for XGBoostRegressor

[33mcommit 3f09c694a3129aeecf4414547d66ba8a5bed3b6e[m
Merge: 62a3170 5b68f55
Author: Z.sk <shaokunzhang529@gmail.com>
Date:   Mon Nov 8 09:59:23 2021 +0800

    Merge pull request #274 from microsoft/docstr
    
    update docstr

[33mcommit 5b68f556dcb113c4757dea6e65bfa9050833a42e[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sun Nov 7 08:05:13 2021 -0800

    bump version to 0.7.1

[33mcommit 0c7bf7219f3e2c92745095fca6d2d37238bf29a6[m
Merge: 09e75c9 62a3170
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Nov 6 21:58:26 2021 -0700

    Merge branch 'main' into docstr

[33mcommit 62a31704eeb03b34d4fd4874b2f733a3b21459ef[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Nov 6 21:58:05 2021 -0700

    default to cfo for single estimator (#273)
    
    * default to cfo for single estimator
    
    * use bs for parallel tuning
    
    * comment about overhead

[33mcommit 09e75c9b9c1f3710379e326cacbb762b1d8941c6[m
Author: Qingyun Wu <qw2ky@virginia.edu>
Date:   Sun Nov 7 02:46:27 2021 +0000

    fix onlineaml docstr

[33mcommit 03bc62363f31789846738a29a853b4898c3a0985[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Nov 6 12:44:10 2021 -0700

    add periods

[33mcommit c4d5986ee8b73ce61a4c0d8e359c6860c9371283[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Nov 6 11:37:57 2021 -0700

    no retraining when max_iter=0 and not retrain_full

[33mcommit 0d9439212f5e8e6202cf1132d29774f95695133e[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Nov 6 09:37:33 2021 -0700

    update docstr

[33mcommit fc32eca24bfc3ff80092f46a074ec1f1428cc93c[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Thu Nov 4 22:06:19 2021 -0700

    make default verbose level > 0 when using ray (#272)
    
    * make default verbose level > 0 when using ray
    
    * default hpo method when using ray
    
    * bug fix: == -> =

[33mcommit 549a0dfb5392642a634ad1b10cd809509a11b4c2[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Wed Nov 3 19:08:23 2021 -0700

    limit time and memory consumption (#264)
    
    * limit time and memory
    
    * separate tests
    
    * lrl1 can't be limited by limit_resource
    
    * free memory when possible
    
    * passthrough=False when ensemble fails;
    retrain when trained_estimator is None
    
    * use callback to for resource limit
    
    * handle lower version of xgb with no callback
    
    * free mem ratio
    
    * reduce verbosity
    
    * retrain_final when max_iter==1
    
    * remove trained_estimator from result
    
    * model_history
    
    * wheel
    
    * retrain time as best_config_train_time
    
    * ci: libomp version for xgboost on macos
    
    * limit_resource not working in windows
    
    * test pickle load
    
    * mute forecaster
    
    * notebook update
    
    * check hard
    
    * preventive callback
    
    * add use_ray

[33mcommit 6c66cd67f7f3a2762d7ade2b684da6e1ca51606e[m
Author: Chia-Chi Hsu <wuchi5457@gmail.com>
Date:   Wed Nov 3 03:24:43 2021 +0800

    Update Dockerfile (#269)

[33mcommit 519bfc2a185073996a84b411e53cc475e6dda721[m
Author: Kevin Chen <74878789+int-chaos@users.noreply.github.com>
Date:   Sat Oct 30 12:48:57 2021 -0400

    Integrate multivariate time series forecasting (#254)
    
    * Integrate multivariate time series forecasting, now supports
    continuous and categorical variables
    
    - update data.py to transform time series data
    - update search space
    - update documentations to reflect changes
    - update test_forecast.py
    - rename 'forecast' task to 'ts_forecast' task
    
    * update automl.py and test_forecast.py
    
    * update forecast notebook
    
    * update README.md and setup.py
    
    * update ml.py and test_forecast.py
    
    - make "ds" and "y" constant variables
    
    * replace constants with constant variables
    
    * bump version to 0.7.0
    
    * update setup.py
    - support 'forecast' and 'ts_forecast'
    
    * update automl.py and data.py
    - support 'forecast' and 'ts_forecast' tasks

[33mcommit e0155c2339d75f4bb98258e461db47ee987adc58[m
Author: Antoni Baum <antoni.baum@protonmail.com>
Date:   Fri Oct 29 20:44:16 2021 +0200

    Fix exception in CFO's `_create_condition` if all candidate start points didn't return yet (#263)
    
    * Fix exception if first trial returns None
    
    * Add test

[33mcommit 94a81a95adf08436b7121cd173aa6c8c52a2b7d9[m
Author: Qingyun Wu <qw2ky@virginia.edu>
Date:   Tue Oct 19 16:39:28 2021 -0400

    Add documentation for warm-start (#255)
    
    * add documentation for warm-start
    
    * fix typo
    
    * fix typo
    
    * Update flaml/tune/tune.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    * Update automl.py
    
    Co-authored-by: Qingyun Wu <qxw5138@psu.edu>
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit 7809ec15ac7c9da87ee08f8e76b77ca8799beb59[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Oct 19 09:03:10 2021 -0700

    catch import error

[33mcommit 29fac8807be077718b929c9b3650595e396076ae[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Oct 19 08:46:43 2021 -0700

    fix bug in subspace identification

[33mcommit 46cfb76863f065c55d2ef36fb5586cf8be58a0a8[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Mon Oct 18 21:11:24 2021 -0700

    bump version to 0.6.9

[33mcommit b3715e1e348782fac1abe2d4e9fa39cecdf1e62f[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Oct 16 11:49:46 2021 -0700

    cleanup

[33mcommit 7d6e8601026f28f835073cb3ac0370b39e11f3d2[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Oct 16 10:40:01 2021 -0700

    n_estimators for catboost

[33mcommit 9e9356f436978017b698f763612c06a0db2c956d[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Oct 16 08:21:14 2021 -0700

    time budget in state

[33mcommit b2d8b097d78ad77cf2d82a909d5100bdf5f5b995[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Oct 16 03:09:56 2021 -0700

    check n_iter == 1

[33mcommit 46b29e05c7718891b564f5c3b06b5a0f045f1724[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Oct 16 02:08:43 2021 -0700

    .params

[33mcommit b03a87e7375352530b8906ff2ebb726306dc8e33[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Oct 16 01:11:12 2021 -0700

    no search when max_iter < 2

[33mcommit 5fb843234f62f8b879d37f2cc3a742f3ddcc8ee2[m
Author: Michal <michal.chromcak@heidelbergcement.com>
Date:   Wed Oct 13 12:02:06 2021 +0200

    Add conda forge badge

[33mcommit 524f22bcc5834eda61ac66dc76e75b8abd99d17e[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Fri Oct 15 21:36:42 2021 -0700

    fix bug in hierarchical search space (#248); optional dependency on lgbm and xgb (#250)
    
    * close #249
    
    * admissible region
    
    * best_config can be None
    
    * optional dependency on lgbm and xgb
    resolve #252

[33mcommit fe65fa143dc77035f0e1de6f32528fe05458f485[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Oct 12 15:08:40 2021 -0700

    v0.6.8 (#247)

[33mcommit ddc1a63a764d546e902acd3599c2de387ab2673e[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sun Oct 10 22:57:22 2021 -0700

    Package (#244)
    
    * build and upload pypi package
    
    * pandas in dependency

[33mcommit 948f68874228b92767ba35dc781383b32f025eda[m
Author: Christoph Deil <Deil.Christoph@gmail.com>
Date:   Sat Oct 9 16:52:07 2021 +0200

    Consistent California (#245)

[33mcommit f48ca2618fed2193ffa929af7a44d3031dfb16dd[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Fri Oct 8 16:09:43 2021 -0700

    warning -> info for low cost partial config (#231)
    
    * warning -> info for low cost partial config
    #195, #110
    
    * when n_estimators < 0, use trained_estimator's
    
    * log debug info
    
    * test random seed
    
    * remove "objective"; avoid ZeroDivisionError
    
    * hp config to estimator params
    
    * check type of searcher
    
    * default n_jobs
    
    * try import
    
    * Update searchalgo_auto.py
    
    * CLASSIFICATION
    
    * auto_augment flag
    
    * min_sample_size
    
    * make catboost optional

[33mcommit a99e939404caeda88f32724cc264841f2f5dcfca[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Mon Sep 27 21:30:49 2021 -0700

    update config if n_estimators is modified (#225)
    
    * update config if n_estimators is modified
    
    * prediction as int
    
    * handle the case n_estimators <= 0
    
    * if trained and no budget to train more, return the trained model
    
    * split_type=group for classification & regression

[33mcommit 7d9e28f02d66d11e43ae6da0f2db921716a5f9ae[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Sep 25 19:23:08 2021 -0700

    seed for hpo method (#224)
    
    set the seed for hpo method according to the seed passed to AutoML.fit()

[33mcommit 16a97bec76ba101d62b1eb05484b20cc7c271e1c[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Thu Sep 23 10:49:02 2021 -0700

    set converge flag when no trial can be sampled (#217)
    
    * set converge flag when no trial can be sampled
    
    * require custom_metric to return dict for logging
    close #218
    
    * estimate time budget needed
    
    * log info per iteration

[33mcommit b1115d5347e00326d10e5d20836b912bb2cc95e9[m
Author: Qingyun Wu <qw2ky@virginia.edu>
Date:   Sun Sep 19 20:44:25 2021 -0400

    add consistency test (#216)
    
    * add consistency test
    
    * test_consistency and format
    
    * add results attribute
    
    * skip when ray is not installed
    
    * Update flaml/tune/analysis.py
    
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>
    
    Co-authored-by: Qingyun Wu <qxw5138@psu.edu>
    Co-authored-by: Chi Wang <wang.chi@microsoft.com>

[33mcommit f3e50136e8bdcd0e2db71f1b38f210368f2fecce[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sun Sep 19 11:19:23 2021 -0700

    random search (#213)
    
    * random search as a child class of CFO
    
    * random search in sequential search of AutoML
    
    * time to find best model as a property of AutoML

[33mcommit 0ba58e0acecc788670a1b28f7ceb5908746ec6fc[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Sep 14 23:16:28 2021 -0700

    accommodate nni usage pattern (#209)

[33mcommit a9d39b71dae7aec7d73f995eb0edf12bfe4bc27b[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Tue Sep 14 18:36:10 2021 -0700

    consider num_samples in bs thread priority (#207)
    
    * consider num_samples in bs thread priority
    
    * continue search for bs

[33mcommit ea6c6ded2f05d3ef6a752a1affe81516cf20371d[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Mon Sep 13 21:16:42 2021 -0700

    clean up forecast notebook (#202)

[33mcommit f4529dfe892f33d1b01589a088d75c8933b4361c[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Sep 11 21:19:18 2021 -0700

    package name in setup (#198)
    
    * package name
    
    * learning to rank example: close #200
    
    * try import prophet #201

[33mcommit 8f9f08cebcd892af723da3c9023a0bd48efcdfd9[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Fri Sep 10 20:09:08 2021 -0700

    try import catboost (#197)

[33mcommit 71219df6c600889294e59c54f88d1d70efd6af1a[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Fri Sep 10 16:39:16 2021 -0700

    notebook example (#189)
    
    * config in result
    
    * value can be float
    
    * pytorch notebook example
    
    * docker, pre-commit
    
    * max_failure (#192); early_stop
    
    * extend starting_points (#196)
    
    Co-authored-by: Chi Wang (MSR) <wang.chi@microsoft.com>
    Co-authored-by: Qingyun Wu <qw2ky@virginia.edu>

[33mcommit 339eb80f4404c0a5968c4170e796848d08ee88ba[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Sep 4 20:28:37 2021 -0700

    variable name (#187)

[33mcommit e46573a01d077b999f669f072ed41a40ac76c37b[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Sat Sep 4 01:42:21 2021 -0700

    warmstart blendsearch (#186)
    
    * increase test coverage
    
    * use define by run only when needed
    
    * warmstart bs
    
    * classification -> binary, multi
    
    * warm start with evaluated rewards
    
    * data transformer; resource attr for gs
    
    * BlendSearchTuner bug fix and unittest
    
    * bug fix
    
    * docstr and import
    
    * task type

[33mcommit 5fdfa2559bd7728b786b49e6edf0fade8d6a7f64[m
Author: Qingyun Wu <qw2ky@virginia.edu>
Date:   Thu Sep 2 16:07:30 2021 -0400

    Cleanml (#185)
    
    * reorg ml
    
    * return y_pred in eval_estimator
    
    * add train loss into metric_for_logging dict

[33mcommit 63bba92fd03d94be66b44ebcb1415ff9f00134c0[m
Author: Gian Pio Domiziani <gpdomiziani@gmail.com>
Date:   Thu Sep 2 17:50:22 2021 +0200

    Fix decide_split_type bug. (#184)
    
    * Fix decide_split_type bug.

[33mcommit ec34427ca8c9a88d91bbfd0f2c0f505456682724[m
Author: Kevin Chen <74878789+int-chaos@users.noreply.github.com>
Date:   Wed Sep 1 21:06:37 2021 -0400

    Forecast v2 (#182)
    
    * update flaml_forecast.ipynb
    
    * visualize predictions for comparison
    
    Signed-off-by: Kevin Chen <chenkevin.8787@gmail.com>

[33mcommit 6ab0730793f42ff5bb7f53b3a9d43d640e597189[m
Author: Chi Wang <wang.chi@microsoft.com>
Date:   Wed Sep 1 16:25:04 2021 -0700

    remove catboost training di