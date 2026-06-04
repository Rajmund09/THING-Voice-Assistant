import warnings; warnings.filterwarnings('ignore')
import sys
sys.path.insert(0, '.')

from backend.modules.vision_engine import analyze_screen

print('Testing vision description (should be plain text, no raw JSON)...')
print('-' * 55)
result = analyze_screen('What is on my screen?')
print('Success      :', result['success'])
print('Has preview  :', result['screenshot_b64'] is not None)
print()
desc = result['description']
starts_with_brace = desc.strip().startswith('{')
print('Raw JSON leak:', starts_with_brace)
print()
print('Description  :')
print(desc)
print()
if result['success'] and not starts_with_brace:
    print('CLEAN plain text description. Bug FIXED.')
elif result['success'] and starts_with_brace:
    print('WARNING: Still showing raw JSON.')
else:
    print('Error:', desc)
