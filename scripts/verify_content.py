"""Run catalog answer programs through the same local judge used by the app.

Examples:
  python scripts/verify_content.py
  python scripts/verify_content.py --languages cpp --styles brief annotated
  python scripts/verify_content.py --ids 5 70 146 --languages python
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from server.catalog import PROBLEMS, detail
from server.runner import capabilities, run


def verify(task):
    problem, language, mode, style = task
    started = time.monotonic()
    code = detail(problem['id'])['solutions'][language][mode][style]
    try:
        outcome = run(problem, {'language': language, 'mode': mode, 'code': code})
    except Exception as error:
        outcome = {'status': 'exception', 'message': repr(error), 'cases': []}
    return {
        'id': problem['id'], 'title': problem['title'], 'language': language,
        'mode': mode, 'style': style, 'seconds': round(time.monotonic() - started, 3),
        **outcome,
    }


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--languages', nargs='+', choices=['python', 'cpp'], default=['python', 'cpp'])
    parser.add_argument('--modes', nargs='+', choices=['leetcode', 'acm'], default=['leetcode', 'acm'])
    parser.add_argument('--styles', nargs='+', choices=['brief', 'annotated'], default=['annotated'])
    parser.add_argument('--ids', nargs='+', type=int)
    parser.add_argument('--jobs', type=int, choices=[1, 2], default=2)
    parser.add_argument('--report', type=Path, default=ROOT / '.local' / 'content-verification.json')
    args = parser.parse_args()
    problems = [p for p in PROBLEMS if not args.ids or p['id'] in args.ids]
    if args.ids and set(args.ids) - {p['id'] for p in problems}:
        parser.error('Some requested problem IDs are missing from the catalog.')
    if not args.ids and len(problems) != 100:
        parser.error(f'Expected exactly 100 catalog problems; found {len(problems)}.')
    if 'cpp' in args.languages and not capabilities()['cpp']['available']:
        parser.error('C++ compiler unavailable; run scripts/setup-cpp.ps1 or set CODERECALL_CXX.')
    tasks = [(p, language, mode, style) for p in problems for language in args.languages
             for mode in args.modes for style in args.styles]
    started = time.monotonic()
    results = []
    print(f'Running {len(tasks)} answer variants across {len(problems)} problems.', flush=True)
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = [pool.submit(verify, task) for task in tasks]
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            if result['status'] != 'passed':
                print(f"FAIL {result['id']} {result['language']}/{result['mode']}/{result['style']}: "
                      f"{result['message'][:1500]}", flush=True)
            if len(results) % 20 == 0 or len(results) == len(tasks):
                passed = sum(r['status'] == 'passed' for r in results)
                print(f'{len(results)}/{len(tasks)} completed; {passed} passed.', flush=True)
    failures = [r for r in results if r['status'] != 'passed']
    report = {
        'generatedAt': datetime.now(timezone.utc).isoformat(),
        'seconds': round(time.monotonic() - started, 3),
        'problemCount': len(problems), 'variantCount': len(results),
        'caseCount': sum(len(r.get('cases', [])) for r in results),
        'passed': len(failures) == 0, 'failureCount': len(failures),
        'capabilities': capabilities(),
        'results': sorted(results, key=lambda r: (r['id'], r['language'], r['mode'], r['style'])),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"{report['caseCount']} cases evaluated; {len(failures)} failing variants. Report: {args.report}")
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
