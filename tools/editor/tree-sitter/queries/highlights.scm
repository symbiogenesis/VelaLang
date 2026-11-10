; SPDX-License-Identifier: Apache-2.0
(identifier) @variable
(number) @number
(string) @string
(character) @string
(interpolated_string) @string
(line_comment) @comment
(block_comment) @comment
(lifetime) @label
(hole) @error
["Nat" "bool"] @type.builtin
((identifier) @type.builtin (#match? @type.builtin "^(Nat|bool)$"))
["true" "false"] @boolean
["Fn" "FnMut" "FnOnce" "add" "admits" "alias" "as" "assert" "async" "await" "break" "by" "calc" "cancel" "captures" "carrier" "coinductive" "commit" "const" "continue" "cycle" "decreases" "definition" "dispose" "domain" "effect" "effects" "else" "ensures" "exists" "forall" "foreach" "ghost" "grade" "grows" "handle" "hardware" "if" "impl" "import" "in" "inductive" "interface" "internal" "interpret" "invariant" "is" "laws" "lemma" "let" "lifts" "machine" "match" "module" "move" "mul" "namespace" "next" "on" "one" "open" "out" "owned" "predicate" "private" "progress" "proof" "public" "record" "ref" "region" "register" "rehandle" "requires" "restores" "resume" "resumes" "return" "rule" "schedule" "scope" "scoped" "shallow" "spawn" "state" "struct" "theorem" "tracked" "transition" "type" "union" "universe" "var" "view" "when" "where" "while" "with" "zero"] @keyword
["(" ")" "{" "}" "[" "]"] @punctuation.bracket
[";" "," "."] @punctuation.delimiter
