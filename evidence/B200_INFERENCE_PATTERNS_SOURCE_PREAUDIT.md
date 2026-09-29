# B200 source preaudit — OLP-0606

Frozen source: content/methods/proofs/inference-patterns.tex,
revision 9620cc73f9c8e0ad003c514a5d3748f29611c4c0,
SHA-256 dec51f23018334023107ecfaa7a2f31fdf964b2b0cb7aebaeeb4e1688ed6dd31.
The full target is drafted and focused-checked, SHA-256
7a414633d110b202ef594a31be0afbfa1acddd60a68ee279df2d3ddafd85f032,
but not cumulatively accepted. B200_INFERENCE_PATTERNS_DRAFT_QA.json
passes 46 paired blocks, 41 changed blocks, 301 exact ordered math
spans, identifiers, term tokens, structural macros, comments, CRLF
and final newline. The unit includes headings,
two embedded proofs, quoted instructional commentary and a final
deliberately invalid proof that conflates existential witnesses.

The source presents use and proof of conjunctions and disjunctions,
conditional and biconditional proofs, arbitrary-object reasoning for
universal claims, proof by cases, existential witness construction,
and the fresh-name condition for using an existence claim. The final
invalid argument is intentional: two nonempty sets need not intersect.
It must remain visibly invalid, not silently made valid.

Two separate printed formula defects have adjacent Pashto disclosure
without altering the frozen mathematics:

- OLSTH-032: source lines 198–199 print "$\in D$" and "$\in E$" after referring
  to an arbitrary x. Membership needs a left argument; the intended
  instances are apparent from the next sentence but the exact printed
  spans must remain.
- OLSTH-033: source lines 310–311 conclude "$x \neq \emptyset$ iff for some $x$,
  $x \in A$" while the surrounding proof concerns the nonemptiness
  of A. The x/A substitution is a printed typo, not an equivalence
  to silently repair in the translation.

The misspelling "asusmption" at line 291 and "an end" in the
biconditional paragraph are ordinary source spelling errors and do
not require importing English errors into natural Pashto prose.

Pakistani scholarly prose PK-IQRAM-P1-PROSE was inspected for
orthography and adult exposition. AF-NIAZMAN-P7-PROPOSITION,
AF-NIAZMAN-P24-SEMANTIC-ENTAILMENT and
AF-NIAZMAN-P39-THEORY-PROOF were inspected as labelled regional
comparators for statements, logical consequence and proof. They
do not certify every specialized compound in this pedagogical unit.
The frozen English remains the mathematical-semantic authority.
