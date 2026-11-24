"""Summarize checkpointed Qwen Office results without interpreting rubric scores."""
import argparse, json, statistics
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('checkout',type=Path);args=p.parse_args();root=args.checkout.resolve();ledger=root/'results/qwen36-flash-office-serial/queue.jsonl'
rows=[json.loads(line) for line in ledger.read_text().splitlines()] if ledger.exists() else []
results=[]
for row in rows:
 if row.get('status')!='completed':continue
 path=root/row['result'];trial=json.loads(path.read_text());rewards=(trial.get('verifier_result') or {}).get('rewards') or {};score=rewards.get('reward')
 results.append({'task':row['task'],'job':row['job'],'rule_score':score,'checks_passed':rewards.get('tests_passed'),'checks_total':rewards.get('tests_total'),'output_tokens':row.get('output_tokens'),'result':row['result']})
scores=[r['rule_score'] for r in results if isinstance(r['rule_score'],(float,int))]
print(json.dumps({'tasks_expected':50,'trials_completed':len(results),'tasks_with_rule_scores':len(scores),'equal_weight_rule_mean':statistics.mean(scores) if scores else None,'rubric_grading':'deferred','rows':results},ensure_ascii=False,indent=2))
