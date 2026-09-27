# B098 canon consultation — connective rules

The frozen OpenLogic source governs each truth function and proof tree. I read the following rendered witness pages before drafting OLP-0406 and checked their local image hashes against CANON_PASSAGES.jsonl.

| Passage | Location and image SHA-256 | Actual use and limit |
|---|---|---|
| PK-IQRAM-P1-PROSE | Pakistani Pashto scholarly prose, printed p. 1; c1cd7112ceaeef4e8cf4de1812d789e0ceec3561d378e1d0bdc6776de17ff83b | Primary guide for کښې, final ے and explanatory register in the opening dependency paragraph. It does not attest n-sided sequent terminology. |
| PK-IQRAM-P2-SEMANTICS | Pakistani semantics discussion, printed p. 2; 4bf4703777dcc07248973705785454761cf5846b830205d3a9305ad2929cebc6 | Primary guide for scholarly semantic exposition and syntax/meaning distinctions. It does not provide the three-valued truth functions. |
| GRAMMAR-P166-SOV | Reference grammar, printed p. 166; 4ea5f09844b03ad466989401970a2ca49e9f94fd02375968d3285a0709a3592c | Verb-final clause order and complement placement in rule descriptions and the parenthetical Gödel qualification. |
| AF-NIAZMAN-P8-TRUTH-TABLE | Afghan regional comparator, printed p. 8; 32696bdfaa990fef2a2559c32c44cb872d1fa33ab7229d9aced0027686fb1fd6 | Shows native truth-table prose, negation and conjunction. Supports the vocabulary of truth values and connectives, but not these three-valued tables or Pakistani orthography. |
| AF-NIAZMAN-P37-AXIOMATIC-PROOF | Afghan regional comparator, printed p. 37; 23547670f5d3c65140dea9fc3f374af9fc1934b2abdda60d403943c56f8ffa71 | Displays a finite propositional axiom scheme and proof prose; guides rule-description register, not the OpenLogic rule list. |
| AF-NIAZMAN-P39-THEORY-PROOF | Afghan regional comparator, printed p. 39; a80089b12f04029e2e326e03122c0cea7ca1a18664130df42b67947c8d090e67 | Explicit inference-rule and derivation-sequence vocabulary; informs د استنتاج قاعدې and caption context. |
| AF-NIAZMAN-P48-MODUS-PONENS | Afghan regional comparator, printed p. 48; 3182d952a9b827e583f9e88faa258fe7ad0ce1d00627f24bd7b65ee576cca76f | Shows a premise-over-conclusion rule and derivability proof. Its specific rule is not substituted for an n-sided OpenLogic rule. |

Existing decisions TERM-TRUTH-FUNCTION, TERM-LOGIC-FORMS, TERM-SEQUENT-STRUCTURE, TERM-SEQUENT-RULES and TERM-SEQUENT-SOUNDNESS govern the repeated compounds and the difference between semantics and derivation. The exact labels for Łukasiewicz, Kleene and Gödel rules remain editorial choices guided by adjacent accepted Pashto units; they are not claimed as externally attested standards.
