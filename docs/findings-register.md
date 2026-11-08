# VelaLang Findings Register

Assurance and design findings raised by Vela specification and qualification items, extracted from [VerifiedOS](https://github.com/symbiogenesis/VerifiedOS).

**F-353** owed-act: the graded substitution reference's call-by-name accounting does not establish once-only evaluation of effectful arguments in the proposed call-by-value language
· Raised: Q25a
· Disposition: open; the foundation dossier restricts the displayed substitution equations to pure values and accounts effectful binding separately. Q25d owns the missing composed evaluation, capture and erasure laws and their implementation assignment.

**F-354** owed-act: task, scope, continuation and completion-frame occupancy is not classified explicitly in R-08-046's bounded-pool inventory
· Raised: Q25b
· Disposition: open; Q25d must justify classification under an existing inventory member or amend R-08-046 and its cited prose, preserving the complete pool manifest, before dependent runtime implementation opens.

**F-355** measurement: taking the maximum of a precommit cancellation delay and a committed suffix omits the reachable path containing both
· Raised: Q25b
· Disposition: closed in design review; the bound adds decision delay before the maximum over complete outcome suffixes and also covers ordinary execution from registration, with child collection explicit. Concrete target bounds and the progress theorem remain open.

**F-356** measurement: cancellation of a registered but unstarted child must not return its frame before terminal-result collection
· Raised: Q25c
· Disposition: closed in design review; returned inputs enter the reserved cancelled-completion record, and the frame remains owned until terminal collection and its release gate.
