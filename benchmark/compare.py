import json
import glob
from pathlib import Path

def main():
    results_dir = Path(__file__).parent / "results"
    files = list(results_dir.glob("*.json"))
    
    print("=" * 80)
    print("BENCHMARK COMPARISON REPORT")
    print("=" * 80)
    
    summary_data = []

    for f in sorted(files):
        with open(f, "r", encoding="utf-8") as fp:
            data = json.load(fp)
        
        runs = data["runs"]
        valid_cnt = sum(1 for r in runs if r.get("valid_json"))
        avg_lat = sum(r["latency_ms"] for r in runs) / len(runs)
        avg_tps = sum(r["tokens_per_sec"] for r in runs) / len(runs)
        
        summary_data.append({
            "model": data["model"],
            "mem_mb": data.get("memory_mb", "N/A"),
            "valid": f"{valid_cnt}/{len(runs)}",
            "lat": round(avg_lat, 1),
            "tps": round(avg_tps, 1),
            "runs": runs
        })
    
    # Print high-level metrics table
    print(f"{'Model':<35} | {'RAM (MB)':<10} | {'Valid JSON':<10} | {'Latency':<10} | {'Tokens/sec':<10}")
    print("-" * 85)
    for s in summary_data:
        print(f"{s['model']:<35} | {str(s['mem_mb']):<10} | {s['valid']:<10} | {str(s['lat']) + 'ms':<10} | {str(s['tps']):<10}")
    print("=" * 80)

    # Detailed qualitative comparison for key scenarios
    key_scenarios = ["combat_01", "combat_02", "trap_01", "trap_02", "resource_01"]
    
    for sc in key_scenarios:
        print(f"\n>>> Scenario: {sc}")
        for s in summary_data:
            print(f"  [{s['model']}]")
            for tier in ["bare", "structured", "engineered"]:
                match = next((r for r in s["runs"] if r["scenario_id"] == sc and r["prompt_tier"] == tier), None)
                if match:
                    out = match['output'].replace('\n', ' ')
                    print(f"    - {tier:<10}: {out}")

if __name__ == "__main__":
    main()
