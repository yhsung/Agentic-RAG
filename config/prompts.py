"""
Centralized prompt templates for the Agentic RAG system.

All prompts are defined here to make them easy to modify and experiment with.
Each prompt has a specific purpose in the agentic workflow.
"""

# ==================== Document Relevance Grading ====================

RELEVANCE_GRADER_PROMPT = """You are a grader assessing relevance of a retrieved document to a user question.

Retrieved document:
{document}

User question: {question}

If the document contains keyword(s) or semantic meaning related to the question, grade it as relevant.
Give a binary score 'yes' or 'no' to indicate whether the document is relevant to the question.

Provide the binary score as a JSON with a single key 'score' and no preamble or explanation.

Example output format:
{{"score": "yes"}}
or
{{"score": "no"}}
"""


# ==================== Hallucination Detection ====================

HALLUCINATION_GRADER_PROMPT = """You are a grader assessing whether an LLM generation is grounded in / supported by a set of retrieved facts.

Set of facts:
{documents}

LLM generation: {generation}

Give a binary score 'yes' or 'no'. 'Yes' means that the answer is grounded in / supported by the set of facts.
'No' means that the answer contains information not supported by the facts or contradicts the facts.

Provide the binary score as a JSON with a single key 'score' and no preamble or explanation.

Example output format:
{{"score": "yes"}}
or
{{"score": "no"}}
"""


# ==================== Answer Usefulness Grading ====================

ANSWER_GRADER_PROMPT = """You are a grader assessing whether an answer addresses / resolves a question.

User question: {question}

LLM generation: {generation}

Give a binary score 'yes' or 'no'. 'Yes' means that the answer resolves the question.
'No' means that the answer does not address the question or is incomplete.

Provide the binary score as a JSON with a single key 'score' and no preamble or explanation.

Example output format:
{{"score": "yes"}}
or
{{"score": "no"}}
"""


# ==================== Query Rewriting ====================

QUERY_REWRITER_PROMPT = """You are a question re-writer that converts an input question to a better version that is optimized for vectorstore retrieval.

Look at the input question and try to reason about the underlying semantic intent / meaning.

Here is the initial question:
{question}

Formulate an improved question that will retrieve more relevant documents from the vectorstore.
The improved question should be:
- More specific and detailed
- Use keywords likely to appear in relevant documents
- Maintain the original intent
- Be a complete, well-formed question

Provide only the improved question with no preamble or explanation.
"""


# ==================== RAG Answer Generation ====================

RAG_PROMPT = """You are an assistant for question-answering tasks.
Use the following pieces of retrieved context to answer the question.
If you don't know the answer based on the context, just say that you don't know.
Use three sentences maximum and keep the answer concise.

Question: {question}

Context: {context}

Answer:"""


# ==================== Web Search Query ====================

WEB_SEARCH_QUERY_PROMPT = """Given the following question, generate a web search query that will find relevant information.

Question: {question}

Generate a concise search query (3-6 words) optimized for search engines.
Provide only the search query with no preamble or explanation.
"""


# ==================== Prompt Descriptions ====================

PROMPT_DESCRIPTIONS = {
    "RELEVANCE_GRADER_PROMPT": "Evaluates if a retrieved document is relevant to the user's question (binary yes/no)",
    "HALLUCINATION_GRADER_PROMPT": "Checks if the generated answer is grounded in the source documents",
    "ANSWER_GRADER_PROMPT": "Assesses if the answer addresses the user's question",
    "QUERY_REWRITER_PROMPT": "Rewrites vague queries to improve retrieval quality",
    "RAG_PROMPT": "Generates concise answers from retrieved context",
    "WEB_SEARCH_QUERY_PROMPT": "Converts questions to effective web search queries"
}


def get_prompt_description(prompt_name: str) -> str:
    """Get description of a specific prompt."""
    return PROMPT_DESCRIPTIONS.get(prompt_name, "No description available")


def list_all_prompts() -> None:
    """Print all available prompts and their descriptions."""
    print("Available Prompts:")
    print("=" * 80)
    for name, description in PROMPT_DESCRIPTIONS.items():
        print(f"\n{name}:")
        print(f"  {description}")
    print("=" * 80)


if __name__ == "__main__":
    """Display all prompts for review."""
    list_all_prompts()

    print("\n\nPrompt Templates:")
    print("=" * 80)

    prompts = {
        "Relevance Grader": RELEVANCE_GRADER_PROMPT,
        "Hallucination Grader": HALLUCINATION_GRADER_PROMPT,
        "Answer Grader": ANSWER_GRADER_PROMPT,
        "Query Rewriter": QUERY_REWRITER_PROMPT,
        "RAG Prompt": RAG_PROMPT,
        "Web Search Query": WEB_SEARCH_QUERY_PROMPT
    }

    for name, prompt in prompts.items():
        print(f"\n{name}:")
        print("-" * 80)
        print(prompt)
        print("-" * 80)
