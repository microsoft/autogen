import autogen
from protein_drug_discovery.agents import (
    SearchAgentWeb,
    SearchAgentPubMed,
    AnalysisAgent,
    RankingAgent,
    CritiqueAgent,
)

class Orchestrator:
    def __init__(self, llm_config):
        self.llm_config = llm_config
        self.search_agent_web = SearchAgentWeb("SearchAgentWeb", llm_config=self.llm_config)
        self.search_agent_pubmed = SearchAgentPubMed("SearchAgentPubMed", llm_config=self.llm_config)
        self.analysis_agent = AnalysisAgent("AnalysisAgent", llm_config=self.llm_config)
        self.ranking_agent = RankingAgent("RankingAgent", llm_config=self.llm_config)
        self.critique_agent = CritiqueAgent("CritiqueAgent", llm_config=self.llm_config)
        self.user_proxy = autogen.UserProxyAgent("UserProxy", code_execution_config=False)

    def run(self, n, disease, start_year, end_year):
        initial_prompt = f"Identify the top {n} protein targets associated with {disease} that are considered promising for small-molecule drug discovery within the period {start_year}–{end_year}. Rank the targets based on their therapeutic relevance, level of supporting evidence (e.g., publications, clinical trials, bioactivity data), and druggability features."

        groupchat = autogen.GroupChat(
            agents=[
                self.user_proxy,
                self.search_agent_web,
                self.search_agent_pubmed,
                self.analysis_agent,
                self.ranking_agent,
                self.critique_agent,
            ],
            messages=[],
            max_round=10,
        )
        manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=self.llm_config)

        self.user_proxy.initiate_chat(
            manager,
            message=initial_prompt,
        )
