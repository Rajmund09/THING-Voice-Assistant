import warnings; warnings.filterwarnings('ignore')
import sys
sys.path.insert(0, '.')

from backend.engine.intent_router import get_local_intent

tests = [
    ('click on search bar',                 'search bar'),
    ('click the login button',              'login'),
    ('click where you see localhost:5173/', 'localhost:5173/'),
    ('press the close icon',                'close'),
    ('click submit',                        'submit'),
]

print('=== Click Target Extraction Tests ===')
all_pass = True
for cmd, expected_substr in tests:
    result = get_local_intent(cmd, use_llm_fallback=False)
    target = result.get('target', '(none)') if result else '(no match)'
    ok = expected_substr.lower() in target.lower() if result else False
    status = 'PASS' if ok else 'FAIL'
    if not ok: all_pass = False
    print(f'  [{status}] "{cmd}" -> target="{target}"')

print()
print('All tests passed!' if all_pass else 'SOME TESTS FAILED')
