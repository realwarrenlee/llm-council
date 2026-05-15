"""Prompt templates for LLM Council operations."""

# =============================================================================
# Peer Review Prompts
# =============================================================================

PAIRWISE_COMPARISON_PROMPT = """You are evaluating responses to the task: "{task}"

Below are two responses to compare:

--- Response {id_a} ---
{content_a}

--- Response {id_b} ---
{content_b}

Compare these responses based on:
- Accuracy and correctness
- Clarity and coherence  
- Completeness of the answer
- Insightfulness and depth

First, provide a brief explanation of your evaluation. Explain what each response does well and what it does poorly. Then, conclude with your verdict using EXACTLY one of these labels in double brackets:
- [[{id_a}>>{id_b}]]: The first response is significantly better
- [[{id_a}>{id_b}]]: The first response is slightly better
- [[{id_a}={id_b}]]: Both responses are equally good
- [[{id_b}>{id_a}]]: The second response is slightly better
- [[{id_b}>>{id_a}]]: The second response is significantly better

Example format:
Response {id_a} provides good detail on X but misses Y...
Response {id_b} is accurate but lacks depth on Z...
[[{id_a}>{id_b}]]

Now provide your evaluation:"""


RANKING_PROMPT = """You are participating in a peer review process. Below are anonymized responses to the task: "{task}"

Your job is to rank these responses from best to worst based on:
- Accuracy and correctness
- Clarity and coherence
- Completeness of the answer
- Insightfulness and depth

{responses}

Please provide your ranking as a simple ordered list (best first):
1. Response X
2. Response Y
3. Response Z

Also briefly explain your reasoning (2-3 sentences)."""


EVALUATION_PROMPT = """You are participating in a peer review process. Below are anonymized responses to the task: "{task}"

Your job is to evaluate each response on the following criteria:
- Strengths: What does this response do well?
- Weaknesses: What could be improved?
- Score: Rate 1-10 (10 = excellent)

{responses}

Please provide your evaluation for each response in this format:

Response X:
- Score: [1-10]
- Strengths: [your assessment]
- Weaknesses: [your assessment]

Response Y:
- Score: [1-10]
- Strengths: [your assessment]
- Weaknesses: [your assessment]

(Continue for all responses...)"""


# =============================================================================
# Chairman Synthesis Prompts
# =============================================================================

CHAIRMAN_SYNTHESIS_PROMPT = """You are the Chairman of an LLM Council. Multiple AI models have provided responses to a user's question, and then ranked each other's responses.

Original Question: {task}

STAGE 1 - Individual Responses:
{stage1_responses}

{stage2_reviews}

Your task as Chairman is to synthesize all of this information into a single, comprehensive, accurate answer to the user's original question. Consider:
- The individual responses and their insights
- The peer rankings and what they reveal about response quality
- Any patterns of agreement or disagreement

Provide a clear, well-reasoned final answer that represents the council's collective wisdom:"""


PEER_REVIEW_SYNTHESIS_PROMPT = """You are synthesizing peer review results. The task was: "{task}"

Initial responses were anonymized and reviewed by multiple roles. Here are the results:

{review_results}

Please synthesize these reviews into a coherent summary that:
1. Identifies which responses were most highly rated and why
2. Highlights key points of agreement/disagreement among reviewers
3. Provides actionable insights for improving the overall response quality

Keep your synthesis concise but informative."""
