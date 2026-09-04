from pathlib import Path
from collections import Counter
import json,re,hashlib,unicodedata
REPO=Path(__file__).resolve().parents[1]
STATE=REPO/'evidence'
OUTPUT=REPO/'build/qa'
OUTPUT.mkdir(parents=True,exist_ok=True)
H=lambda s:hashlib.sha256(s if isinstance(s,bytes) else s.encode('utf-8')).hexdigest()
manifest={x['unit_id']:x for x in map(json.loads,(STATE/'SOURCE_MANIFEST.jsonl').read_text().splitlines())}
plan=json.loads((STATE/'consultation-plan.json').read_text(encoding='utf-8'))
passages={p['passage_id']:p for p in map(json.loads,(STATE/'CANON_PASSAGES.jsonl').read_text(encoding='utf-8').splitlines())}
def localize_text(s):
 out='';pos=0
 for m in re.finditer(r'\\(?:text|intertext)\{',s):
  if m.start()<pos: continue
  i=m.end(); depth=1
  while i<len(s) and depth:
   if s[i]=='{' and s[i-1]!='\\': depth+=1
   if s[i]=='}' and s[i-1]!='\\': depth-=1
   i+=1
  assert depth==0, 'unbalanced text argument'
  content=s[m.end():i-1]
  embedded=''.join(re.findall(r'\$[^$]*\$',content))
  out+=s[pos:m.start()]+m.group(0)+'LOCALIZED'+embedded+'}';pos=i
 return out+s[pos:]
def math(s):
 spans=re.findall(r'(?s)\$.*?\$|\\\[.*?\\\]|\\begin\{(?:align\*?|multline\*?|equation\*?)\}.*?\\end\{(?:align\*?|multline\*?|equation\*?)\}',s)
 return Counter(re.sub(r'\s+','',localize_text(x)) for x in spans)
def ids(s):
 return Counter(re.findall(r'\\(?:olfileid|ollabel|olref|olimport|olasset|cite\w*|label|ref|url|oliflabeldef)(?:\[[^\]]*\])*(?:\{[^{}]*\})',s))
def lineblocks(s):
 out=[]
 for m in re.finditer(r'(?s)(?:\A|(?<=\n)\n)(.*?)(?=\n\s*\n|\Z)',s):
  if m.group(1).strip(): out.append((m.group(1),s[:m.start(1)].count('\n')+1))
 return out
results=[]; alignment=[]; use=[]
for uid,consult in plan['units'].items():
 row=manifest[uid]; p=row['source_path']
 a=(REPO/'upstream'/p).read_bytes(); b=(REPO/'ps-Arab-PK'/p).read_bytes()
 assert H(a)==row['source_sha256']
 sa=a.decode(); sb=b.decode(); aa=re.split(r'\n\s*\n',sa.strip()); bb=re.split(r'\n\s*\n',sb.strip())
 checks=dict(block_count=len(aa)==len(bb),environments=re.findall(r'\\(?:begin|end)\{[^}]+\}',sa)==re.findall(r'\\(?:begin|end)\{[^}]+\}',sb),identifiers=ids(sa)==ids(sb),math=math(sa)==math(sb),tokens=Counter(re.findall(r'!!\^?a?\{\w+\}s?',sa))==Counter(re.findall(r'!!\^?a?\{\w+\}s?',sb)),nfc=unicodedata.normalize('NFC',sb)==sb,no_replacement_character='\ufffd' not in sb)
 residual=re.sub(r'(?m)^%.*$','',sb)
 if uid in ['OLP-0017','OLP-0018']:
  diagram=lambda s:[re.sub(r'\s+','',d) for d in re.findall(r'(?s)\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}',s)]
  checks['unchanged_numeric_diagrams']=diagram(sa)==diagram(sb)
  residual=re.sub(r'(?s)\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}','',residual)
 residual=re.sub(r'\\olchapter\{[^}]+\}\{[^}]+\}',r'\\olchapter',residual)
 residual=re.sub(r'\\olpart\{[^}]+\}',r'\\olpart',residual)
 residual=re.sub(r'\\addcontentsline\{[^}]+\}\{[^}]+\}',r'\\addcontentsline',residual)
 residual=re.sub(r'https?://[^}\s]+|openlogicproject\.org','',residual)
 residual=re.sub(r'(?s)\$.*?\$|\\\[.*?\\\]','',residual)
 residual=re.sub(r'\\(?:documentclass|olfileid|olimport|olasset|olref|oliflabeldef|begin|end|ollabel|cite\w*)(?:\[[^\]]*\])*(?:\{[^{}]*\})+','',residual)
 residual=re.sub(r'!!\^?a?\{\w+\}s?|\\[A-Za-z]+','',residual)
 english=sorted(set(re.findall(r'[A-Za-z]{2,}',residual)))
 checks['no_ordinary_english']=not english
 result=dict(unit_id=uid,path=p,source_sha256=H(a),translation_sha256=H(b),source_blocks=len(aa),target_blocks=len(bb),checks=checks,residual_english=english,extra_locale_macros=Counter(re.findall(r'\\ps\w+',sb)),status='structural-pass' if all(checks.values()) else 'deterministic-defects')
 if not checks['math']: result['math_diff']={'source_only':list((math(sa)-math(sb)).elements()),'target_only':list((math(sb)-math(sa)).elements())}
 results.append(result)
 if len(aa)==len(bb):
  for k,(src,dst) in enumerate(zip(aa,bb),1):
   sid=f'{uid}-B{k:03d}'; changed=src!=dst
   rec=dict(segment_id=sid,unit_id=uid,source_path=p,block_1based=k,source_sha256=H(src),target_sha256=H(dst),source=src,target=dst,classification='translated-content' if changed else 'unchanged-structural',source_file_sha256=H(a),target_file_sha256=H(b))
   alignment.append(rec)
   if changed:
    use.append(dict(segment_id=sid,source_sha256=H(src),target_sha256=H(dst),batch_id=consult.get('batch_id',plan['batch_id']),consulted_passages=[{'passage_id':pid,'source_sha256':passages[pid]['source_sha256'],'page_image_sha256':passages[pid]['page_image_sha256']} for pid in consult['passages']],consultation_scope=consult['scope'],terms=consult['terms'],limitation='Prose/grammar evidence applies across the paragraph; technical attestation is limited to the cited witness roles. Canon never overrides source mathematics.'))
out=OUTPUT/'ALIGNMENT.jsonl';out.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in alignment),encoding='utf-8')
(OUTPUT/'SEGMENT_CANON_USE.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in use),encoding='utf-8')
report=dict(schema='ps-openlogic-qa/1',status='in-progress',source_hashes='722 raw units verified',translation_coverage={'total':722,'draft_units':len(results),'structural_pass':sum(all(x['checks'].values()) for x in results),'visually_accepted':0,'published':0},canon_sources=4,canon_passages=len(passages),batch=plan['batch_id'],units=results,semantic_review=plan['semantic_review'],builds=[],publication_verified=False)
accepted_path=STATE/'ACCEPTED_BUILDS.json'
if accepted_path.exists():
 accepted=json.loads(accepted_path.read_text(encoding='utf-8'))
 hashes={r['unit_id']:r['translation_sha256'] for r in results}
 current=[b for b in accepted if all(hashes.get(u['unit_id'])==u['sha256'] for u in b['units'])]
 report['builds']=current
 report['translation_coverage']['visually_accepted']=len({u['unit_id'] for b in current for u in b['units']})
pubpath=STATE/'PUBLICATION_VERIFIED.json'
if pubpath.exists():
 pub=json.loads(pubpath.read_text(encoding='utf-8'))
 report['translation_coverage']['published']=len({u['unit_id'] for u in pub.get('source_units',[]) if any(r['unit_id']==u['unit_id'] and r['translation_sha256']==u['sha256'] for r in results)})
 report['publication_verified']=pub.get('verified',False)
(OUTPUT/'QA.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'units':len(results),'failures':[r for r in results if not all(r['checks'].values())],'aligned_blocks':len(alignment),'consultation_records':len(use)},ensure_ascii=False,indent=2))
