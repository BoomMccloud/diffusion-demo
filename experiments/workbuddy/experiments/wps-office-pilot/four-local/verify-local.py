import argparse,json,os,pathlib,sys,pytest
parser=argparse.ArgumentParser()
parser.add_argument('task')
parser.add_argument('output')
args=parser.parse_args()
tests=pathlib.Path('/private/tmp/wps-four-task-source')/args.task/'tests'
workspace=pathlib.Path('/private/tmp/wps-four-task')/args.task
os.environ.update(WB_BENCH_OUTPUT_PATH=str(pathlib.Path(args.output).resolve()),WB_BENCH_GOLD_PATH=str(tests/'gold/gold_answer.json'),WB_BENCH_FIXTURES_DIR=str(tests/'gold/fixtures'),WB_BENCH_CASE_DIR=str(workspace),WB_BENCH_VERIFIER_LOGS=str(pathlib.Path('/private/tmp/wps-four-task-source/logs')/args.task))
sys.path.insert(0,str(tests/'grading'))
import eval_core
if hasattr(eval_core,'load_gold'):
 def load_gold():
  with open(os.environ['WB_BENCH_GOLD_PATH'],encoding='utf8') as f:return json.load(f)
 eval_core.load_gold=load_gold
if args.task=='drug-inventory-split-L2-006':
 original=pathlib.Path
 def mapped_path(*parts):
  if parts and str(parts[0]).startswith('/workspace/'):
   return workspace.joinpath(str(parts[0])[len('/workspace/'):],*parts[1:])
  return original(*parts)
 eval_core.Path=mapped_path
raise SystemExit(pytest.main([str(tests/'grading'),'-p','no:cacheprovider','-q','--tb=short']))
