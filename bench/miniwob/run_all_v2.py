import subprocess
import sys
import time
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

batches = [1, 2, 3]

print("="*70)
print("🚀 LAUNCHING COMPLETE MINIWOB++ V2 BENCHMARK LOOP")
print("Target: 120 tasks across Batches 1, 2, 3 with Upgraded Harness")
print("Strict Rate-Limit Guarantee: RPS < 2.0")
print("="*70)

overall_results = []

for b in batches:
    print(f"\n▶️ Starting Batch {b}...")
    cmd = [
        sys.executable,
        HERE + "/run_miniwob_v2.py",
        "--batch", str(b)
    ]
    p = subprocess.run(cmd)
    if p.returncode != 0:
        print(f"⚠️ Batch {b} finished with code {p.returncode}")
    else:
        print(f"✅ Batch {b} successfully finished.")

    # Load results
    res_path = HERE + f"/results/miniwob_v2_results_batch_{b}.json"
    if os.path.exists(res_path):
        with open(res_path) as f:
            data = json.load(f)
            overall_results.extend(data.get("results", []))

# Write combined summary
final_path = HERE + "/results/miniwob_v2_results_final.json"
passed_total = sum(1 for r in overall_results if r.get("passed"))
with open(final_path, "w") as f:
    json.dump({
        "total_evaluated": len(overall_results),
        "total_passed": passed_total,
        "pass_rate": (passed_total / len(overall_results) * 100) if overall_results else 0,
        "results": overall_results
    }, f, indent=2)

print("\n" + "="*70)
print("🏆 ALL BATCHES COMPLETE - V2 BENCHMARK SUMMARY")
print("="*70)
print(f"Total Tasks Evaluated: {len(overall_results)}")
print(f"Total Passed:          {passed_total}/{len(overall_results)} ({(passed_total / len(overall_results) * 100):.1f}%)")
print(f"Final Artifact:        {final_path}")
print("="*70)
