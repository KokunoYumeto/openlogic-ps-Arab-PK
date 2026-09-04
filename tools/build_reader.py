"""Prepare the current complete-chapter reader; launch TeX only via guard_tex.ps1."""
from pathlib import Path
import re,json,hashlib,argparse
R=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--build-dir',type=Path,default=R/'build/reader')
B=parser.parse_args().build_dir.resolve();B.mkdir(parents=True,exist_ok=True)
H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
chapters=[('sets','sets'),('relations','relations-complete')]
inputs=[]
tokens={'element':('غړے','غړي','غړي','غړو'),'formula':('فارمول','فارمولونه','فارمول','فارمولونو'),'derivation':('اشتقاق','اشتقاقونه','اشتقاق','اشتقاقونو')}
def prepare(s):
 s=s.split(r'\begin{document}',1)[1].rsplit(r'\end{document}',1)[0]
 def oblique(m):
  key=m[1];plural=bool(m[2]);assert key in tokens,key
  return tokens[key][3 if plural else 2]
 s=re.sub(r'\\psOblique\{!!\^?a?\{(\w+)\}(s?)\}',oblique,s)
 def token(m):
  key=m[1];assert key in tokens,key
  return tokens[key][1 if m[2] else 0]
 s=re.sub(r'!!\^?a?\{(\w+)\}(s?)',token,s)
 out='';pos=0
 for m in re.finditer(r'\\(?:text|intertext)\{',s):
  if m.start()<pos:continue
  i=m.end();depth=1
  while depth:
   assert i<len(s),'Unbalanced text argument'
   if s[i]=='{' and s[i-1]!='\\':depth+=1
   if s[i]=='}' and s[i-1]!='\\':depth-=1
   i+=1
  out+=s[pos:m.end()]+r'\RL{'+s[m.end():i-1]+'}}';pos=i
 s=out+s[pos:]
 s=re.sub(r'\$([^$]+)\$',lambda m:r'\LR{$'+m[1]+'$}',s)
 return s
body=[]
for directory,driver_name in chapters:
 root=R/'ps-Arab-PK/content/sets-functions-relations'/directory
 driver=root/(driver_name+'.tex');s=driver.read_text(encoding='utf-8')
 title=re.search(r'\\olchapter\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}',s)
 assert title
 inputs.append({'path':driver.relative_to(R).as_posix(),'sha256':H(driver),'role':'chapter-title-and-import-order'})
 body.append(title.group(0))
 for name in re.findall(r'\\olimport\{([^}]+)\}',s):
  p=root/(name+'.tex');inputs.append({'path':p.relative_to(R).as_posix(),'sha256':H(p)})
  body.append(prepare(p.read_text(encoding='utf-8')))
notes=R/'ps-Arab-PK/editorial/reader-notes.tex'
body.append(prepare(notes.read_text(encoding='utf-8')))
# One citation in these chapters, bound to its original BibTeX entry.
bib=R/'upstream/bib/open-logic.bib';raw=bib.read_text(encoding='utf-8')
entry=re.search(r'@Article\{Benacerraf1965,.*?\n\}',raw,re.S).group(0)
field=lambda k:re.search(r'\b'+k+r'\s*=\s*\{([^}]+)\}',entry).group(1)
assert field('year')=='1965'
bibliography=r'''
\clearpage
\begin{LTR}\latinfont
\begin{thebibliography}{1}
\bibitem[Benacerraf(1965)]{Benacerraf1965}
'''+field('author')+'. ('+field('year')+'). '+field('title')+'. '+r'\emph{'+field('journal')+'}, '+field('volume')+'('+field('number')+'), '+field('pages')+r'''.
\end{thebibliography}
\end{LTR}
\end{document}
'''
preamble=R/'tools/reader-preamble.tex'
text=preamble.read_text(encoding='utf-8').replace('OLP_UPSTREAM_PATH',(R/'upstream').as_posix())+'\n'+'\n'.join(body)+bibliography
(B/'reader.tex').write_bytes(text.encode('utf-8'))
record={'input_files':inputs,'preamble_sha256':H(preamble),'builder_sha256':H(Path(__file__)),'generated_tex_sha256':H(B/'reader.tex'),'bibliography_sha256':H(bib),'cited_entry_sha256':hashlib.sha256(entry.encode()).hexdigest(),'reader_units':len(inputs),'editorial_notes':{'path':notes.relative_to(R).as_posix(),'sha256':H(notes),'role':'edition-authored notation clarifications; not source translation or extra source-unit credit','language_witnesses':['PK-IQRAM-P1-PROSE','AF-NIAZMAN-P109-RELATION','AF-NIAZMAN-P138-EQUALITY']},'status':'prepared','conditional_content':'The original cumul-part condition is false in this partial reader; both translated source branches are retained. The full reader must resolve against the full part graph.'}
(B/'build-inputs.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'reader_units':len(inputs),'generated_tex_sha256':record['generated_tex_sha256']}))
