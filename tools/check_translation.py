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
correction_path=STATE/'SOURCE_CORRECTIONS.json'
corrections=json.loads(correction_path.read_text(encoding='utf-8'))['actions'] if correction_path.exists() else []
corrections_by_unit={}
for c in corrections:corrections_by_unit.setdefault(c['unit_id'],[]).append(c)
def localize_text(s):
 out='';pos=0
 for m in re.finditer(r'\\(?:text|intertext|emph|textrm)\{',s):
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
 return Counter(re.findall(r'\\(?:olfileid|ollabel|olref|olimport|olasset|cite\w*|label|cref|ref|url|oliflabeldef|printtoken)(?:\[[^\]]*\])*(?:\{[^{}]*\})',s)+re.findall(r'\\tagrefs\{(?:[^{}]|\{[^{}]*\})*\}',s))
STRUCTURAL_MACRO_NAMES=set('documentclass iftag olchapter olpart olsection subsection subsubsection olfileid olimport OLEndChapterHook Article Axiom AxiomC Deduce DeduceC UnaryInf UnaryInfC BinaryInf BinaryInfC TrinaryInf TrinaryInfC QuaternaryInf QuaternaryInfC RightLabel LeftLabel DischargeRule DisplayProof noLine doubleLine bottomAlignProof Intro Elim FalseInt FalseCl LeftR RightR tagprob tagitem tagtrue tagfalse tagrefs item footnote caption olasset includegraphics href url cite citep citet ollabel label olref ref cref'.split())
def structural_macros(s):
 s=re.sub(r'(?m)(?<!\\)%.*$','',s)
 return Counter(x for x in re.findall(r'\\([A-Za-z]+)',s) if x in STRUCTURAL_MACRO_NAMES)
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
 sm,tm=math(sa),math(sb);source_only=sm-tm;target_only=tm-sm
 si,ti=ids(sa),ids(sb);identifier_source_only=si-ti;identifier_target_only=ti-si
 expected_source=Counter();expected_target=Counter()
 expected_macro_source=Counter();expected_macro_target=Counter()
 expected_identifier_source=Counter();expected_identifier_target=Counter()
 for c in corrections_by_unit.get(uid,[]):
  e=c.get('qa_math_exception',{});expected_source.update(e.get('source_only',[]));expected_target.update(e.get('target_only',[]))
  me=c.get('qa_macro_exception',{});expected_macro_source.update(me.get('source_only',[]));expected_macro_target.update(me.get('target_only',[]))
  ie=c.get('qa_identifier_exception',{});expected_identifier_source.update(ie.get('source_only',[]));expected_identifier_target.update(ie.get('target_only',[]))
 macro_source_only=structural_macros(sa)-structural_macros(sb);macro_target_only=structural_macros(sb)-structural_macros(sa)
 checks=dict(block_count=len(aa)==len(bb),environments=re.findall(r'\\(?:begin|end)\{[^}]+\}',sa)==re.findall(r'\\(?:begin|end)\{[^}]+\}',sb),identifiers=identifier_source_only==expected_identifier_source and identifier_target_only==expected_identifier_target,structural_macros=macro_source_only==expected_macro_source and macro_target_only==expected_macro_target,math=source_only==expected_source and target_only==expected_target,tokens=Counter(re.findall(r'!!\^?a?\{[^{}]+\}s?',sa))==Counter(re.findall(r'!!\^?a?\{[^{}]+\}s?',sb)),nfc=unicodedata.normalize('NFC',sb)==sb,no_replacement_character='\ufffd' not in sb)
 checks['named_token_macros']=Counter(re.findall(r'\\usetoken\{[^{}]*\}\{[^{}]*\}',sa))==Counter(re.findall(r'\\usetoken\{[^{}]*\}\{[^{}]*\}',sb))
 residual=re.sub(r'(?m)^%.*$','',sb)
 residual=re.sub(r'\\usetoken\{[^{}]*\}\{[^{}]*\}','',residual)
 diagram=lambda s:[re.sub(r'\s+','',d) for d in re.findall(r'(?s)\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}',s)]
 if diagram(sa) or diagram(sb):
  checks['unchanged_numeric_diagrams']=diagram(sa)==diagram(sb)
  residual=re.sub(r'(?s)\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}','',residual)
 tableau=lambda s:[re.sub(r'\s+','',d) for d in re.findall(r'(?s)\\begin\{(?:oltableau|tableau)\}.*?\\end\{(?:oltableau|tableau)\}',s)]
 source_tableaux,target_tableaux=tableau(sa),tableau(sb)
 if source_tableaux or target_tableaux:
  expected_tableaux=list(source_tableaux)
  for c in corrections_by_unit.get(uid,[]):
   for change in c.get('qa_tableau_replacements',[]):
    old,new=re.sub(r'\s+','',change['source']),re.sub(r'\s+','',change['target'])
    actual=sum(x.count(old) for x in expected_tableaux)
    assert actual==change['count'],(uid,c['id'],old,actual,change['count'])
    expected_tableaux=[x.replace(old,new) for x in expected_tableaux]
  checks['unchanged_tableau_diagrams']=expected_tableaux==target_tableaux
 residual=re.sub(r'(?s)\\begin\{(?:oltableau|tableau)\}.*?\\end\{(?:oltableau|tableau)\}','',residual)
 residual=re.sub(r'\\tagrefs\{(?:[^{}]|\{[^{}]*\})*\}','',residual)
 residual=re.sub(r'\\olchapter\{[^}]+\}\{[^}]+\}',r'\\olchapter',residual)
 residual=re.sub(r'\\olpart\{[^}]+\}',r'\\olpart',residual)
 residual=re.sub(r'\\addcontentsline\{[^}]+\}\{[^}]+\}',r'\\addcontentsline',residual)
 residual=re.sub(r'\\(?:texttt|textsc|textsf|textrm)\{[^{}]*\}','',residual)
 residual=re.sub(r'https?://[^}\s]+|openlogicproject\.org','',residual)
 residual=re.sub(r'(?:OLFUN|OLSIZ|PSSIZ|OLARI|OLINF|OLPL|OLPF|OLSQ|OLND|OLTAB|OLAX|OLCOM)-\d+','',residual)
 residual=re.sub(r'(?s)\$.*?\$|\\\[.*?\\\]|\\begin\{(?:align\*?|multline\*?|equation\*?)\}.*?\\end\{(?:align\*?|multline\*?|equation\*?)\}','',residual)
 residual=re.sub(r'\\(?:documentclass|olfileid|olimport|olasset|olref|oliflabeldef|begin|end|ollabel|label|cref|ref|cite\w*|printtoken|tagprob|Article)(?:\[[^\]]*\])*(?:\{[^{}]*\})+','',residual)
 residual=re.sub(r'\\(?:iftag|tagitem|tagtrue|tagfalse)\{[^{}]*\}','',residual)
 residual=re.sub(r'\\begin\{(?:tagblock|tagenumerate)\}\{[^{}]*\}','',residual)
 residual=re.sub(r'!!\^?a?\{[^{}]+\}s?|\\[A-Za-z]+','',residual)
 residual=re.sub(r'\[[+-]?[0-9.]+(?:em|ex|pt|cm|mm|in)\]','',residual)
 residual=re.sub(r'(?<![A-Za-z])[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:em|ex|pt|cm|mm|in)\b','',residual)
 english=sorted(set(re.findall(r'[A-Za-z]{2,}',residual)))
 checks['no_ordinary_english']=not english
 result=dict(unit_id=uid,path=p,source_sha256=H(a),translation_sha256=H(b),source_blocks=len(aa),target_blocks=len(bb),checks=checks,residual_english=english,extra_locale_macros=Counter(re.findall(r'\\ps\w+',sb)),source_correction_ids=[c['id'] for c in corrections_by_unit.get(uid,[])],status='structural-pass' if all(checks.values()) else 'deterministic-defects')
 if source_only or target_only: result['math_diff']={'source_only':list(source_only.elements()),'target_only':list(target_only.elements()),'expected_by_source_correction':checks['math']}
 if identifier_source_only or identifier_target_only: result['identifier_diff']={'source_only':list(identifier_source_only.elements()),'target_only':list(identifier_target_only.elements()),'expected_by_source_correction':checks['identifiers']}
 if macro_source_only or macro_target_only: result['structural_macro_diff']={'source_only':list(macro_source_only.elements()),'target_only':list(macro_target_only.elements()),'expected_by_source_correction':checks['structural_macros']}
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
report=dict(schema='ps-openlogic-qa/1',status='in-progress',source_hashes='722 raw units verified',translation_coverage={'total':722,'draft_units':len(results),'structural_pass':sum(all(x['checks'].values()) for x in results),'visually_accepted':0,'published':0},publication_coverage={'reader_units':0,'source_snapshot_units':0,'published_definition':'published counts units in an accepted public reader; source_snapshot_units separately counts structurally verified drafts included in the public source archive'},canon_sources=4,canon_passages=len(passages),batch=plan['batch_id'],units=results,semantic_review=plan['semantic_review'],builds=[],publication_verified=False)
report['canon_sources']=len((STATE/'CANON_SOURCES.jsonl').read_text(encoding='utf-8').splitlines())
accepted_path=STATE/'ACCEPTED_BUILDS.json'
accepted_unit_ids=set()
if accepted_path.exists():
 accepted=json.loads(accepted_path.read_text(encoding='utf-8'))
 hashes={r['unit_id']:r['translation_sha256'] for r in results}
 current=[b for b in accepted if all(hashes.get(u['unit_id'])==u['sha256'] for u in b['units'])]
 report['builds']=current
 accepted_unit_ids={u['unit_id'] for b in current for u in b['units']}
 report['translation_coverage']['visually_accepted']=len(accepted_unit_ids)
pubpath=STATE/'PUBLICATION_VERIFIED.json'
if pubpath.exists():
 pub=json.loads(pubpath.read_text(encoding='utf-8'))
 public_source_ids={u['unit_id'] for u in pub.get('source_units',[]) if any(r['unit_id']==u['unit_id'] and r['translation_sha256']==u['sha256'] for r in results)}
 public_reader_ids=set(pub.get('reader_units',[]))
 report['translation_coverage']['published']=len(accepted_unit_ids & public_source_ids & public_reader_ids)
 report['publication_coverage']['reader_units']=report['translation_coverage']['published']
 report['publication_coverage']['source_snapshot_units']=len(public_source_ids)
 report['publication_verified']=pub.get('verified',False)
(OUTPUT/'QA.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'units':len(results),'failures':[r for r in results if not all(r['checks'].values())],'aligned_blocks':len(alignment),'consultation_records':len(use)},ensure_ascii=False,indent=2))
