# Protein Drug Discovery Agent System

This project implements a multi-agent system using the Autogen framework to identify and rank protein targets for small-molecule drug discovery.

## Core Task

The system answers the following query:

“Identify the top {N} protein targets associated with {disease} that are considered promising for small-molecule drug discovery within the period {start_year}–{end_year}. Rank the targets based on their therapeutic relevance, level of supporting evidence (e.g., publications, clinical trials, bioactivity data), and druggability features.”

## Parameters

-   `N` (integer): The number of top protein targets to return.
-   `disease` (string): The disease of interest.
-   `start_year`, `end_year` (integers): The time frame for the search.

## Agents and Roles

-   **Search Agent (Web):** Queries search engines (Google, Bing, DuckDuckGo, etc.) for relevant information.
-   **Search Agent (PubMed):** Queries PubMed abstracts for publications matching the disease and timeframe.
-   **Analysis Agent:** Synthesizes a list of protein targets, ensuring results are relevant to small molecule drug discovery for the given disease.
-   **Ranking Agent:** Ranks the identified protein targets based on druggability, strength of disease association, and novelty.
-   **Critique Agent:** Reviews the ranked list of protein targets and provides a critique.

## System Properties

-   **Model-Agnostic:** Allows for easy substitution of backend LLMs.
-   **Logging:** Logs total runtime, number of tokens used, total cost of API calls, and LLM I/O.
-   **Modular:** The system is designed with a clear separation of concerns between agents, orchestration, and logging.
