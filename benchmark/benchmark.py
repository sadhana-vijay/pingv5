import json
import argparse
import psutil
import os
from datetime import datetime
from pathlib import Path
from scenarios import SCENARIOS
from runner import load_model, load_grammar, build_prompt, run_inference

TIERS = ["bare", "structured", "engineered"]
GRAMMAR_PATH = Path(__file__).parent / "grammar.gbnf"
RESULTS_DIR = Path(__file__).parent / "results"


def get_memory_mb() -> float:
    process = psutil.Process(os.getpid())
    return round(process.memory_info().rss / (1024 * 1024), 1)


def run_benchmark(model_path: str, context_size: int) -> dict:
    model_name = Path(model_path).stem
    print(f"Loading model: {model_name}")

    mem_before = get_memory_mb()
    model = load_model(model_path, context_size)
    grammar = load_grammar(str(GRAMMAR_PATH))
    mem_after = get_memory_mb()

    print(f"Model loaded. Memory: {mem_before}MB -> {mem_after}MB")

    results = {
        "model": model_name,
        "model_path": model_path,
        "context_size": context_size,
        "memory_mb": mem_after,
        "timestamp": datetime.now().isoformat(),
        "runs": []
    }

    total = len(SCENARIOS) * len(TIERS)
    count = 0

    for scenario in SCENARIOS:
        for tier in TIERS:
            count += 1
            label = f"[{count}/{total}] {scenario['id']} @ {tier}"
            print(f"  Running {label}...", end=" ", flush=True)

            prompt = build_prompt(scenario, tier)
            run_result = run_inference(model, prompt, grammar)

            run_result["scenario_id"] = scenario["id"]
            run_result["category"] = scenario["category"]
            run_result["class"] = scenario["class"]
            run_result["prompt_tier"] = tier

            results["runs"].append(run_result)
            print(f"done ({run_result['latency_ms']}ms, valid={run_result['valid_json']})")

    return results


def main():
    parser = argparse.ArgumentParser(description="Benchmark a 1B model for D&D harness use")
    parser.add_argument("model_path", help="Path to a GGUF model file")
    parser.add_argument("--context-size", type=int, default=2048, help="Context window size (default: 2048)")
    args = parser.parse_args()

    results = run_benchmark(args.model_path, args.context_size)

    RESULTS_DIR.mkdir(exist_ok=True)
    model_name = Path(args.model_path).stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = RESULTS_DIR / f"{model_name}_{timestamp}.json"

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to {output_path}")
    print(f"Total runs: {len(results['runs'])}")

    valid = sum(1 for r in results["runs"] if r["valid_json"])
    avg_latency = sum(r["latency_ms"] for r in results["runs"]) / len(results["runs"])
    avg_tps = sum(r["tokens_per_sec"] for r in results["runs"]) / len(results["runs"])

    print(f"Valid JSON: {valid}/{len(results['runs'])}")
    print(f"Avg latency: {round(avg_latency, 1)}ms")
    print(f"Avg tokens/sec: {round(avg_tps, 1)}")


if __name__ == "__main__":
    main()
