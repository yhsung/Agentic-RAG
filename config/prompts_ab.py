"""
A/B Testing Prompt Variants for RAG System

This module defines multiple RAG prompt variants for A/B testing
to optimize answer generation quality.
"""

from typing import Dict, Literal

# Import the baseline RAG_PROMPT from the main prompts module
from config.prompts import RAG_PROMPT

# ==================== Prompt Variants ====================

# Variant A: Baseline (Current)
# Characteristics: Concise, 2-3 sentences, factual only
# Best For: Quick factual answers
# Focus: Brevity and accuracy
RAG_PROMPT_BASELINE = RAG_PROMPT


# Variant B: Detailed Explanations
# Characteristics: 4-6 sentences, includes reasoning
# Best For: Complex questions requiring explanation
# Focus: Completeness and understanding
RAG_PROMPT_DETAILED = """You are an assistant for question-answering tasks.
Use the following pieces of retrieved context to answer the question.
If you don't know the answer based on the context, just say that you don't know.

Provide a detailed answer in 4-6 sentences that:
1. Directly answers the question
2. Includes relevant context and background from the source material
3. Explains the reasoning or connections between concepts
4. Structures the information logically (main point first, then supporting details)
5. Acknowledges any limitations or uncertainties in the context

Question: {question}

Context: {context}

Answer:"""


# Variant C: Bullet Point Format
# Characteristics: Structured with bullet points, easy to scan
# Best For: Multi-part questions or comparisons
# Focus: Readability and organization
RAG_PROMPT_BULLETS = """You are an assistant for question-answering tasks.
Use the following pieces of retrieved context to answer the question.
If you don't know the answer based on the context, just say that you don't know.

Format your answer using bullet points for clarity:
1. Start with a brief 1-sentence summary answering the question
2. Use 3-5 bullet points for key information from the context
3. Each bullet should be 1-2 sentences
4. Use clear, concise language
5. Acknowledge any limitations or uncertainties

Question: {question}

Context: {context}

Answer:"""


# Variant D: Step-by-Step Reasoning
# Characteristics: Shows thought process, chains reasoning
# Best For: Complex analytical questions
# Focus: Transparency and logic
RAG_PROMPT_REASONING = """You are an assistant for question-answering tasks.
Use the following pieces of retrieved context to answer the question.
If you don't know the answer based on the context, just say that you don't know.

Think through the question step-by-step and show your reasoning:
1. Identify what the question is asking
2. Extract relevant information from the context
3. Synthesize the information into a coherent answer
4. Show your reasoning process clearly
5. Provide a final conclusion based on the reasoning

Structure your response to show your thought process.

Question: {question}

Context: {context}

Answer:"""


# ==================== Prompt Registry ====================

RAG_PROMPT_VARIANTS: Dict[str, str] = {
    "baseline": RAG_PROMPT_BASELINE,
    "detailed": RAG_PROMPT_DETAILED,
    "bullets": RAG_PROMPT_BULLETS,
    "reasoning": RAG_PROMPT_REASONING,
}

PromptVariant = Literal["baseline", "detailed", "bullets", "reasoning"]

PROMPT_VARIANT_DESCRIPTIONS = {
    "baseline": "Concise answers (2-3 sentences), best for quick factual questions",
    "detailed": "Detailed explanations (4-6 sentences), best for complex questions requiring depth",
    "bullets": "Bullet point format, best for multi-part questions and easy scanning",
    "reasoning": "Step-by-step reasoning shown explicitly, best for analytical questions"
}


# ==================== Helper Functions ====================

def get_prompt_variant(variant: PromptVariant = "baseline") -> str:
    """
    Get a specific prompt variant.

    Args:
        variant: Which variant to retrieve (baseline, detailed, bullets, reasoning)

    Returns:
        The prompt template string for the requested variant

    Example:
        >>> prompt = get_prompt_variant("detailed")
        >>> "4-6 sentences" in prompt
        True
    """
    return RAG_PROMPT_VARIANTS.get(variant, RAG_PROMPT_VARIANTS["baseline"])


def list_prompt_variants() -> list[str]:
    """
    List available prompt variants.

    Returns:
        List of variant names

    Example:
        >>> variants = list_prompt_variants()
        >>> "baseline" in variants
        True
    """
    return list(RAG_PROMPT_VARIANTS.keys())


def get_variant_description(variant: PromptVariant) -> str:
    """
    Get description of a prompt variant.

    Args:
        variant: Which variant to describe

    Returns:
        Description string explaining the variant's purpose

    Example:
        >>> desc = get_variant_description("bullets")
        >>> "bullet point" in desc
        True
    """
    return PROMPT_VARIANT_DESCRIPTIONS.get(variant, "Unknown variant")


if __name__ == "__main__":
    """Display all prompt variants for review."""
    print("A/B Testing Prompt Variants")
    print("=" * 80)

    for variant_name in list_prompt_variants():
        print(f"\n{variant_name.upper()}:")
        print("-" * 80)
        print(get_variant_description(variant_name))
        print("\nPrompt:")
        print(get_prompt_variant(variant_name))
        print("-" * 80)
