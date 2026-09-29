# OLP-0588 — simplifying infinite cardinal arithmetic, checked draft

Frozen source: `upstream/content/set-theory/card-arithmetic/simp.tex`, 5,779 bytes, SHA-256 `a606bab065a11c689b655ff8053e3e77894decb42b88e70605a981c129148da0`, upstream revision `9620cc73f9c8e0ad003c514a5d3748f29611c4c0`.

Target: `ps-Arab-PK/content/set-theory/card-arithmetic/simp.tex`, 7,256 bytes, SHA-256 `b6480f600316a8aa35bcc6f0209008e27e10c9bcbd307089cf3e5c8dcd509887`. Focused QA `B182_CARDINAL_SIMPLIFICATION_DRAFT_QA.json`, SHA-256 `35e492f7e889d4d37dd202211581953c3e1bbd6f4a4037ba4f3f4b9b451cb4f2`: 18 paired blocks, 15 changed, 70 ordered math spans; identifiers, references, structural macros, token calls, comments and CRLF preserved. This draft is not cumulatively accepted yet.

Canon actually consulted before drafting:

- `PK-IQRAM-P1-PROSE`, printed p. 1, image SHA-256 `c1cd7112ceaeef4e8cf4de1812d789e0ceec3561d378e1d0bdc6776de17ff83b`: Pakistani scholarly expository syntax/spelling, not a cardinal-arithmetic attestation.
- `AF-NIAZMAN-P109-RELATION`, printed p. 109, image SHA-256 `53be16c240bf8d4bd2f2122d95374f6bd039938d7f38cc81ba8c17b6f4c70b25`: Afghan regional comparator for relation on Cartesian powers, not this theorem's proof.
- `AF-NIAZMAN-P178-ORDER`, printed p. 178, image SHA-256 `3430c7a07383a8759de401ac274c9cbfd89f68fabab222cc78964fb1cedc6f5a`: Afghan regional comparator for order relations and pairs; no exact Pakistani term for canonical ordering was located.
- `AF-BUKOVSKY-P192-DEDEKIND-FINITE`, printed p. 192, image SHA-256 `c83532df1dcb4602632b929578b3aa2f8ba988ed147151c536a6ef364bd2a89f`: regional comparison for infinite sets and Choice dependence only; OpenLogic controls the present cardinal calculation.

`معياري ترتيب` for *canonical ordering* is provisional and defined by the source's three lexicographic-by-maximum clauses. It is not claimed to be an exact printed Pakistani specialist term. The target keeps the least-counterexample proof for $\alpha \approx \alpha\times\alpha$, the displayed segment bounds, Cantor/Schröder–Bernstein dependencies, the maximum rule for infinite cardinal addition/multiplication, and the footnote pointing to Choice when a family of injections is fixed. In the union proof, $v\notin X_\gamma$ for each earlier $\gamma\in\beta$ remains the unique least-index selection condition. The source leaves the finite-$\gamma$ segment case implicit before concluding the order-type bound; the translation does not claim to have inserted a new proof. No frozen-source bytes or formulas are changed.

Next: register exact canon uses and block-level reverse paraphrases for OLP-0587–0588, then dual 588-unit corpus QA and canonical replay before acceptance. Continue source OLP-0589 independently of TeX slot state.
