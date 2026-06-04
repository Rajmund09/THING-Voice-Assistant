import sys; sys.path.insert(0,'.')
import warnings; warnings.filterwarnings('ignore')
from backend.engine.intent_router import get_local_intent
from backend.modules.action_executor import _build_vision_query

tests = [
    ('close Gemini API Free Key tab', 'ui_click'),
    ('close this tab',                'browser_nav'),
    ('click x',                       'ui_click'),
    ('click the close icon',          'ui_click'),
    ('click close',                   'ui_click'),
]

print('=== Routing + Query Enrichment Tests ===')
all_ok = True
for cmd, expected_action in tests:
    r = get_local_intent(cmd, use_llm_fallback=False)
    if not r:
        print(f'  [FAIL] "{cmd}" -> no match (expected {expected_action})')
        all_ok = False
        continue
    action  = r.get('action', '?')
    target  = r.get('target', '')
    query   = _build_vision_query(target) if len(target) < 40 else target
    status  = 'PASS' if action == expected_action else 'FAIL'
    if status == 'FAIL': all_ok = False
    print(f'  [{status}] "{cmd}"')
    print(f'         action  = {action}')
    print(f'         target  = {target[:60]}')
    print(f'         query-> = {query[:80]}')
    print()

print('All passed!' if all_ok else 'SOME FAILED')
