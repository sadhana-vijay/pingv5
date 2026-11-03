import time
import json
from pathlib import Path
from llama_cpp import Llama, LlamaGrammar


def load_model(model_path: str, context_size: int = 2048) -> Llama:
    return Llama(
        model_path=model_path,
        n_ctx=context_size,
        n_threads=6,
        verbose=False
    )


def load_grammar(grammar_path: str) -> LlamaGrammar:
    return LlamaGrammar.from_file(grammar_path)


def build_prompt(scenario: dict, tier: str) -> str:
    obs = scenario["observation"]
    stats = scenario["stats"]
    cls = scenario["class"]

    if tier == "bare":
        return f"{obs}\n\nRespond with a JSON action."

    if tier == "structured":
        stats_block = (
            f"Class: {cls}\n"
            f"HP: {stats['hp']}/{stats['max_hp']}\n"
            f"Attack: {stats['attack']} | Defense: {stats['defense']}\n"
            f"Abilities: {', '.join(stats['abilities'])}\n"
            f"Inventory: {', '.join(stats['inventory'])}"
        )
        return (
            f"=== YOUR STATS ===\n{stats_block}\n\n"
            f"=== SITUATION ===\n{obs}\n\n"
            f"Respond with a JSON action containing \"action\" and \"target\" fields."
        )

    if tier == "engineered":
        stats_block = (
            f"Class: {cls}\n"
            f"HP: {stats['hp']}/{stats['max_hp']}\n"
            f"Attack: {stats['attack']} | Defense: {stats['defense']}\n"
            f"Abilities: {', '.join(stats['abilities'])}\n"
            f"Inventory: {', '.join(stats['inventory'])}"
        )
        return (
            f"You are a {cls} in a dungeon. Your primary goal is survival.\n\n"
            f"=== YOUR STATS ===\n{stats_block}\n\n"
            f"=== SITUATION ===\n{obs}\n\n"
            f"Think step by step:\n"
            f"1. What is the immediate threat or opportunity?\n"
            f"2. What are your options given your abilities and inventory?\n"
            f"3. What is the safest effective action?\n\n"
            f"Respond with a JSON action containing \"action\" and \"target\" fields."
        )

    raise ValueError(f"Unknown tier: {tier}")


def run_inference(model: Llama, prompt: str, grammar: LlamaGrammar, max_tokens: int = 128) -> dict:
    start = time.perf_counter()
    result = model(
        prompt,
        max_tokens=max_tokens,
        grammar=grammar,
        temperature=0.7
    )
    elapsed_ms = (time.perf_counter() - start) * 1000

    output_text = result["choices"][0]["text"]
    prompt_tokens = result["usage"]["prompt_tokens"]
    output_tokens = result["usage"]["completion_tokens"]
    tokens_per_sec = output_tokens / (elapsed_ms / 1000) if elapsed_ms > 0 else 0

    try:
        json.loads(output_text)
        valid_json = True
    except (json.JSONDecodeError, TypeError):
        valid_json = False

    return {
        "output": output_text,
        "prompt_tokens": prompt_tokens,
        "output_tokens": output_tokens,
        "latency_ms": round(elapsed_ms, 1),
        "tokens_per_sec": round(tokens_per_sec, 1),
        "valid_json": valid_json
    }
