"""Check the actual Pashto review-summary counts against the review records."""
from pathlib import Path
import json,re,argparse

def check_status(status_path:Path,progress_path:Path)->dict:
    progress=json.loads(progress_path.read_text('utf-8-sig'))
    lines=[line for line in status_path.read_text('utf8').splitlines() if 'د پخواني ماډل په ساحه کښې' in line]
    if len(lines)!=1:raise ValueError('Expected one current native review-summary sentence.')
    line=lines[0]
    total=re.search(r'ساحه کښې ([۰-۹0-9]+) واحدونه',line)
    reviewed=re.search(r'يعنې ([۰-۹0-9]+) بشپړ واحدونه',line)
    pending=re.search(r'؛ ([۰-۹0-9]+) پاتې دي',line)
    if not all([total,reviewed,pending]):raise ValueError('Cannot parse native review-summary counts.')
    actual=[int(x[1]) for x in [total,reviewed,pending]]
    expected=[progress['total_explicit_translation_units'],len(progress['whole_units_reaudited']),progress['whole_units_pending']]
    if actual!=expected or actual[0]!=actual[1]+actual[2]:
        raise ValueError(f'Native review summary disagrees with records/arithmetic: {actual} vs {expected}')
    return {'status':'PASS','total':actual[0],'reviewed':actual[1],'pending':actual[2]}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--status',type=Path,required=True);p.add_argument('--progress',type=Path,required=True);a=p.parse_args()
    print(json.dumps(check_status(a.status,a.progress)))
