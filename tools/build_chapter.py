from pathlib import Path
import re,hashlib,json,argparse
REPO=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--build-dir',type=Path,default=REPO/'build/sets')
OUT=parser.parse_args().build_dir.resolve();OUT.mkdir(parents=True,exist_ok=True)
parts=['basics','subsets','important-sets','unions-and-intersections','pairs-and-products','russells-paradox']
def prepare(s):
 s=s.split(r'\begin{document}',1)[1].rsplit(r'\end{document}',1)[0]
 s=re.sub(r'\\psOblique\{(!!\^?a?\{element\}s?)\}',lambda m:'غړو' if m[1].endswith('s') else 'غړي',s)
 s=re.sub(r'!!\^?a?\{element\}(s?)',lambda m:'غړي' if m[1] else 'غړے',s)
 # Arabic text inside mathematical text boxes receives explicit RTL direction.
 out='';pos=0
 for m in re.finditer(r'\\text\{',s):
  if m.start()<pos:continue
  i=m.end();depth=1
  while depth:
   if s[i]=='{' and s[i-1]!='\\':depth+=1
   if s[i]=='}' and s[i-1]!='\\':depth-=1
   i+=1
  content=s[m.end():i-1]
  out+=s[pos:m.start()]+r'\text{\RL{'+content+'}}';pos=i
 s=out+s[pos:]
 # Bidi's explicit LTR wrapper isolates each inline formula.
 s=re.sub(r'\$([^$]+)\$',lambda m:r'\LR{$'+m[1]+'$}',s)
 return s
preamble=(REPO/'tools/sets-preamble.tex').read_text(encoding='utf-8')
preamble=preamble.replace('OLP_UPSTREAM_PATH',str(REPO/'upstream').replace('\\','/'))
driver=REPO/'ps-Arab-PK/content/sets-functions-relations/sets/sets.tex'
driver_text=driver.read_text(encoding='utf-8')
title=re.search(r'\\olchapter\{sfr\}\{set\}\{([^}]+)\}',driver_text).group(1)
assert re.findall(r'\\olimport\{([^}]+)\}',driver_text)==parts
preamble=preamble.replace('SETS_CHAPTER_TITLE',title)
pieces=[];inputs=[{'path':str(driver.relative_to(REPO)),'sha256':hashlib.sha256(driver.read_bytes()).hexdigest(),'role':'chapter-title-and-import-order'}]
for n in parts:
 p=REPO/'ps-Arab-PK/content/sets-functions-relations/sets'/f'{n}.tex'
 inputs.append({'path':str(p.relative_to(REPO)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
 pieces.append(prepare(p.read_text(encoding='utf-8')))
text=preamble+'\n'+''.join(pieces)+'\n\\end{document}\n'
(OUT/'sets.tex').write_bytes(text.encode('utf-8'))
glyph_preamble=preamble.split(r'\begin{document}')[0]+r'\begin{document}\setRTL'
glyphs=r'''
\section*{د پښتو توري، نښلېدل او نښې}
ټ ډ ړ ږ ښ څ ځ ڼ ګ ې ۍ ئ ے ۀ

پښتو، ښوونځے، نړۍ، ژبه، ډېر، وړوکے، کېږدئ، زړۀ، تڼۍ۔

نۀ، ښۀ، زَبر، زِېر، پېښ، پوښتنه؟ يو؛ دوه: درې۔

که \LR{$A\subsetneq B$} وي، نو \LR{$B\setminus A\neq\emptyset$}۔
\[\forall x(x\in A\rightarrow x\in B)\]
\[\Setabs{x}{x\text{\RL{ کامل دے او }}0\leq x\leq 10}\]
\begin{LTR}\latinfont
Font specimen: Amiri. Explicit Pashto letters, contextual joining,
combining marks, punctuation, and left-to-right mathematical isolation.
This page is a diagnostic artifact, not translated source content.
\end{LTR}
\end{document}
'''
(OUT/'glyph-test.tex').write_bytes((glyph_preamble+glyphs).encode('utf-8'))
(OUT/'build-inputs.json').write_text(json.dumps({'input_files':inputs,'preamble_sha256':hashlib.sha256(preamble.encode()).hexdigest(),'generated_tex_sha256':hashlib.sha256(text.encode()).hexdigest(),'status':'rendering-in-progress'},indent=2)+'\n',encoding='utf-8')
print('Prepared six-section chapter; inputs recorded in build-inputs.json')
