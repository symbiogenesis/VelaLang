// SPDX-License-Identifier: Apache-2.0
const MONACO_VERSION = "0.55.1";
const MONACO_BASE = `https://cdn.jsdelivr.net/npm/monaco-editor@${MONACO_VERSION}/min`;
const DOCUMENT_URI = "untitled:playground.vela";
const MAX_SOURCE_BYTES = 65536;
const MAX_EXPRESSION_DEPTH = 64;
const MAX_BLOCK_DEPTH = 64;
const MAX_LITERAL_DIGITS = 256;
const MAX_CONSOLE_EXPRESSION_BYTES = 4096;
const MAX_STATIC_STEPS = 4096;
const MAX_EMITTED_GALLINA_BYTES = 262144;
const MAX_NAT_VALUE = 10n ** 256n - 1n;

export const EXAMPLES = {
  squares: {
    source: [
      "module Playground;",
      "",
      "/// Square a natural number.",
      "public Nat Square(Nat x)",
      "{",
      "    let result = x * x;",
      "    return result;",
      "}",
      "",
      "/// Report whether a natural value stays within the demo threshold.",
      "public bool WithinThreshold(Nat x) => Square(x: x) <= 50;",
      "",
      "/// Sum two squares with a local binding.",
      "public Nat Total()",
      "{",
      "    let first = Square(3);",
      "    let second = Square(4);",
      "    return first + second;",
      "}",
      "",
    ].join("\n"),
    expression: "Total()",
    valueType: "Nat",
    suggestions: [
      { expression: "Total()", valueType: "Nat" },
      { expression: "Square(x: 7) + 1", valueType: "Nat" },
      { expression: "WithinThreshold(7)", valueType: "bool" },
      { expression: "WithinThreshold(8)", valueType: "bool" },
    ],
  },
  branches: {
    source: [
      "module Branching;",
      "",
      "/// Double a natural value.",
      "public Nat Double(Nat value) => value + value;",
      "",
      "/// Pick a branch from a Boolean flag.",
      "public Nat Choose(bool flag, Nat left, Nat right)",
      "{",
      "    if (flag)",
      "    {",
      "        return Double(value: left);",
      "    }",
      "    else",
      "    {",
      "        return right + 1;",
      "    }",
      "}",
      "",
    ].join("\n"),
    expression: "Choose(flag: true, left: 9, right: 2)",
    valueType: "Nat",
    suggestions: [
      { expression: "Choose(flag: true, left: 9, right: 2)", valueType: "Nat" },
      { expression: "Choose(flag: false, left: 9, right: 2)", valueType: "Nat" },
      { expression: "Double(value: 12) == 24", valueType: "bool" },
    ],
  },
  logic: {
    source: [
      "module Logic;",
      "",
      "/// Check whether a value falls inside a half-open range.",
      "public bool InWindow(Nat value, Nat low, Nat high) => value >= low && value < high;",
      "",
      "/// Combine negated, ordered and equality checks.",
      "public bool Ready(Nat count, Nat limit, bool paused) =>",
      "    !paused && (InWindow(value: count, low: 1, high: limit) || count == limit);",
      "",
    ].join("\n"),
    expression: "Ready(14, 10, false)",
    valueType: "bool",
    suggestions: [
      { expression: "Ready(14, 10, false)", valueType: "bool" },
      { expression: "Ready(10, 10, false)", valueType: "bool" },
      { expression: "InWindow(value: 5, low: 2, high: 8) && 5 != 8", valueType: "bool" },
      { expression: "!Ready(3, 10, true)", valueType: "bool" },
    ],
  },
  subtraction: {
    source: [
      "module Subtraction;",
      "",
      "/// Natural subtraction saturates at zero in the pure prototype.",
      "public Nat Remaining(Nat budget, Nat used) => budget - used;",
      "",
      "/// Report whether spending leaves a positive natural balance.",
      "public bool HasRoom(Nat budget, Nat used) => budget - used > 0;",
      "",
    ].join("\n"),
    expression: "Remaining(10, 4) + Remaining(3, 10)",
    valueType: "Nat",
    suggestions: [
      { expression: "Remaining(10, 4) + Remaining(3, 10)", valueType: "Nat" },
      { expression: "Remaining(3, 10)", valueType: "Nat" },
      { expression: "HasRoom(10, 4)", valueType: "bool" },
      { expression: "HasRoom(3, 10)", valueType: "bool" },
    ],
  },
  division: {
    source: [
      "module Division;",
      "",
      "/// Count full groups of size items.",
      "public Nat Groups(Nat count, Nat size) => count / size;",
      "",
      "/// Compute the leftover items after full groups.",
      "public Nat Leftover(Nat count, Nat size) => count % size;",
      "",
      "/// Mathematical Nat division defines a zero divisor to yield 0.",
      "public const Nat ZeroDivisorQuotient = 17 / 0;",
      "",
      "/// Mathematical Nat remainder leaves the dividend when dividing by 0.",
      "public const Nat ZeroDivisorRemainder = 17 % 0;",
      "",
    ].join("\n"),
    expression: "Groups(count: 17, size: 5) * 10 + Leftover(17, 5)",
    valueType: "Nat",
    suggestions: [
      { expression: "Groups(count: 17, size: 5) * 10 + Leftover(17, 5)", valueType: "Nat" },
      { expression: "20 / 3 * 2", valueType: "Nat" },
      { expression: "20 % 6 == 2", valueType: "bool" },
      { expression: "ZeroDivisorQuotient == 0 && ZeroDivisorRemainder == 17", valueType: "bool" },
    ],
  },
  constants: {
    source: [
      "module Constants;",
      "",
      "/// Base factor evaluated during compilation.",
      "public const Nat Factor = 8;",
      "",
      "/// Double a compile-time natural value.",
      "public const Nat Twice(Nat x) => x + x;",
      "",
      "/// Scale a runtime value with a required-static parameter.",
      "public Nat Scale(const Nat factor, Nat value)",
      "{",
      "    const Nat multiplier = Twice(factor);",
      "    return multiplier * value;",
      "}",
      "",
      "/// Default scaling entry point.",
      "public const Nat DefaultScale(Nat value) => Scale(Factor, value: value);",
      "",
    ].join("\n"),
    expression: "DefaultScale(value: 3)",
    valueType: "Nat",
    suggestions: [
      { expression: "DefaultScale(value: 3)", valueType: "Nat" },
      { expression: "Twice(Factor) + 4", valueType: "Nat" },
      { expression: "DefaultScale(value: 2) <= 40", valueType: "bool" },
    ],
  },
  bindings: {
    source: [
      "module Bindings;",
      "",
      "/// Compute a bounded step using explicit and type-first immutable locals.",
      "public Nat ClampFloor(Nat value, Nat floor)",
      "{",
      "    let Nat lifted = value + floor;",
      "    Nat span = 4;",
      "    let total = lifted + span;",
      "    return total;",
      "}",
      "",
    ].join("\n"),
    expression: "ClampFloor(value: 7, floor: 2)",
    valueType: "Nat",
    suggestions: [
      { expression: "ClampFloor(value: 7, floor: 2)", valueType: "Nat" },
      { expression: "ClampFloor(0, floor: 5) == 9", valueType: "bool" },
    ],
  },
  named: {
    source: [
      "module NamedCalls;",
      "",
      "/// Baseline window size with numeric thousands separators.",
      "public const Nat BaseWindow = 10_000;",
      "",
      "public Nat clampWindow(Nat low, Nat high, Nat step)",
      "{",
      "    let span = high + step;",
      "    if (low <= span)",
      "    {",
      "        return span + 25000;",
      "    }",
      "    else",
      "    {",
      "        return BaseWindow;",
      "    }",
      "}",
      "",
    ].join("\n"),
    expression: "clampWindow(low: 1_000, high: 2_500, step: 500)",
    valueType: "Nat",
    suggestions: [
      { expression: "clampWindow(low: 1_000, high: 2_500, step: 500)", valueType: "Nat" },
      { expression: "BaseWindow <= 25_000", valueType: "bool" },
    ],
  },
  generic: {
    source: [
      "module Dependent.Generic;",
      "",
      "public definition T Identity<T>(T value) => value;",
      "",
      "public definition A Pick<A, B>(A first, B ignored) => Identity<A>(first);",
      "",
      "public definition T ApplyTwice<T>(Fn(T x) -> T step, T start) =>",
      "    step(step(start));",
      "",
    ].join("\n"),
    expression: "ApplyTwice<Nat>((Nat x) => x + 3, Pick<Nat, bool>(4, true))",
    valueType: "Nat",
    suggestions: [
      {
        expression: "ApplyTwice<Nat>((Nat x) => x + 3, Pick<Nat, bool>(4, true))",
        valueType: "Nat",
      },
      { expression: "Identity<Nat>(19)", valueType: "Nat" },
      { expression: "Pick<bool, Nat>(true, 7)", valueType: "bool" },
    ],
  },
  vectors: {
    source: [
      "module Dependent.Vectors;",
      "",
      "public definition Vec<Nat, 3> Samples() =>",
      "    VCons(4, VCons(9, VCons(16, VNil<Nat>())));",
      "",
      "public definition Nat First() => At(Samples(), FZero<2>());",
      "",
      "public definition Nat Second() => At(Samples(), FSucc(FZero<1>()));",
      "",
      "public definition bool SecondIsNine() =>",
      "    match (Second()) {",
      "        Zero => false,",
      "        Succ(_) => true,",
      "    };",
      "",
    ].join("\n"),
    expression: "Second()",
    valueType: "Nat",
    suggestions: [
      { expression: "Second()", valueType: "Nat" },
      { expression: "First() + Second()", valueType: "Nat" },
      { expression: "SecondIsNine()", valueType: "bool" },
    ],
  },
  dependent: {
    source: [
      "module Dependent.Proofs;",
      "",
      "public definition Vec<T, Succ(n)> KeepLength<T, ghost Nat n>(",
      "    T head,",
      "    Vec<T, n> tail)",
      "    ensures result == Prepend(head, tail)",
      "    => Prepend(head, tail);",
      "",
      "public definition Vec<Nat, 2> BasePair() =>",
      "    VCons(2, VCons(5, VNil<Nat>()));",
      "",
      "public definition Vec<Nat, 3> Extended() =>",
      "    KeepLength<Nat, 2>(1, BasePair());",
      "",
      "public definition Nat ExtendedLast() =>",
      "    At(Extended(), FSucc(FSucc(FZero<0>())));",
      "",
      "public bool SameNat(Nat left, Nat right)",
      "    ensures result == (left == right)",
      "{",
      "    return left == right;",
      "}",
      "",
      "public lemma PlusZeroRight(Nat n)",
      "    ensures n + 0 == n",
      "    proof",
      "    {",
      "        calc",
      "        {",
      "            assert n + 0 == n;",
      "        }",
      "        assert n + 0 == n;",
      "    }",
      "",
    ].join("\n"),
    expression: "ExtendedLast()",
    valueType: "Nat",
    suggestions: [
      { expression: "ExtendedLast()", valueType: "Nat" },
      { expression: "SameNat(ExtendedLast(), 5)", valueType: "bool" },
      { expression: "SameNat(ExtendedLast(), 2)", valueType: "bool" },
    ],
  },
  formatting: {
    source: [
      "module Surface.Formatting;",
      "",
      'public const String Banner = """',
      "    Vela raw string:",
      '    "quotes" stay unescaped',
      '    """;',
      "",
      "public Nat BannerBytes() => ByteLength(Banner);",
      "",
      "public bool BannerFits() => BannerBytes() == 40;",
      "",
      "public Nat FormatLine(Nat count)",
      "{",
      "    var TextBuilder<32> builder = TextBuilder.Empty<32>();",
      '    let _ = Format.Write(ref builder, $"items={count}; ok={true}");',
      "    return Written<32>(builder);",
      "}",
      "",
      "public bool LineFits<const Nat cap>(Nat count)",
      "{",
      "    var TextBuilder<cap> builder = TextBuilder.Empty<cap>();",
      '    let _ = Format.Write(ref builder, $"items={count}; ok={true}");',
      "    return Fits<cap>(builder);",
      "}",
      "",
    ].join("\n"),
    expression: "FormatLine(7)",
    valueType: "Nat",
    suggestions: [
      { expression: "FormatLine(7)", valueType: "Nat" },
      { expression: "BannerBytes()", valueType: "Nat" },
      { expression: "BannerFits()", valueType: "bool" },
      { expression: "LineFits<16>(7)", valueType: "bool" },
      { expression: "LineFits<14>(7)", valueType: "bool" },
    ],
  },
  ergonomics: {
    source: [
      "module Surface.Ergonomics;",
      "",
      "public record Counter(Nat Value, Nat Limit)",
      "{",
      "    public Nat Remaining => this.Limit - this.Value;",
      "    public bool Full => this.Value >= this.Limit;",
      "}",
      "",
      "public Counter Advance(Counter counter, Nat step) =>",
      "    if (counter.Full) counter with { Limit = counter.Limit + step }",
      "    else counter with { Value = counter.Value + step };",
      "",
      "public Nat ReadRemaining(Counter counter) =>",
      "    match (counter) {",
      "        Counter(Value: current, Limit: limit) => limit - current,",
      "    };",
      "",
      "public Nat StepTwice(Nat start, Nat limit)",
      "{",
      "    let Counter first = Advance(Counter(start, limit), 1);",
      "    let Counter second = Advance(first, 1);",
      "    return second.Value + second.Remaining;",
      "}",
      "",
      "public bool CanAdvance(Nat start, Nat limit)",
      "{",
      "    let Counter c = Counter(start, limit);",
      "    return !c.Full && ReadRemaining(c) > 0;",
      "}",
      "",
      "public Nat PreviousOrZero(Nat value)",
      "{",
      "    let Succ(previous) = value else {",
      "        return 0;",
      "    };",
      "    if (previous is Succ(inner)) {",
      "        return inner + 1;",
      "    }",
      "    return 0;",
      "}",
      "",
    ].join("\n"),
    expression: "StepTwice(4, 10)",
    valueType: "Nat",
    suggestions: [
      { expression: "StepTwice(4, 10)", valueType: "Nat" },
      { expression: "StepTwice(9, 10)", valueType: "Nat" },
      { expression: "CanAdvance(4, 10)", valueType: "bool" },
      { expression: "PreviousOrZero(Succ(Succ(Zero())))", valueType: "Nat" },
    ],
  },
};

const SHA256_K = new Uint32Array([
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
  0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
  0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
  0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
  0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
  0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
  0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
]);

function rotr32(value, shift) {
  return (value >>> shift) | (value << (32 - shift));
}

const UTF8_ENCODER = new TextEncoder();
const UTF8_DECODER = new TextDecoder("utf-8", { fatal: true });

function utf8Bytes(text) {
  return UTF8_ENCODER.encode(text);
}

export function sha256Hex(input) {
  const bytes = typeof input === "string" ? utf8Bytes(input) : input;
  const bitLenHi = Math.floor((bytes.length * 8) / 0x100000000);
  const bitLenLo = (bytes.length * 8) >>> 0;
  const paddedLength = (((bytes.length + 9 + 63) >> 6) << 6);
  const buffer = new Uint8Array(paddedLength);
  buffer.set(bytes);
  buffer[bytes.length] = 0x80;
  const view = new DataView(buffer.buffer);
  view.setUint32(paddedLength - 8, bitLenHi, false);
  view.setUint32(paddedLength - 4, bitLenLo, false);

  let h0 = 0x6a09e667;
  let h1 = 0xbb67ae85;
  let h2 = 0x3c6ef372;
  let h3 = 0xa54ff53a;
  let h4 = 0x510e527f;
  let h5 = 0x9b05688c;
  let h6 = 0x1f83d9ab;
  let h7 = 0x5be0cd19;
  const w = new Uint32Array(64);

  for (let offset = 0; offset < paddedLength; offset += 64) {
    for (let i = 0; i < 16; i += 1) {
      w[i] = view.getUint32(offset + i * 4, false);
    }
    for (let i = 16; i < 64; i += 1) {
      const s0 = rotr32(w[i - 15], 7) ^ rotr32(w[i - 15], 18) ^ (w[i - 15] >>> 3);
      const s1 = rotr32(w[i - 2], 17) ^ rotr32(w[i - 2], 19) ^ (w[i - 2] >>> 10);
      w[i] = (w[i - 16] + s0 + w[i - 7] + s1) >>> 0;
    }
    let a = h0;
    let b = h1;
    let c = h2;
    let d = h3;
    let e = h4;
    let f = h5;
    let g = h6;
    let h = h7;
    for (let i = 0; i < 64; i += 1) {
      const S1 = rotr32(e, 6) ^ rotr32(e, 11) ^ rotr32(e, 25);
      const ch = (e & f) ^ (~e & g);
      const temp1 = (h + S1 + ch + SHA256_K[i] + w[i]) >>> 0;
      const S0 = rotr32(a, 2) ^ rotr32(a, 13) ^ rotr32(a, 22);
      const maj = (a & b) ^ (a & c) ^ (b & c);
      const temp2 = (S0 + maj) >>> 0;
      h = g;
      g = f;
      f = e;
      e = (d + temp1) >>> 0;
      d = c;
      c = b;
      b = a;
      a = (temp1 + temp2) >>> 0;
    }
    h0 = (h0 + a) >>> 0;
    h1 = (h1 + b) >>> 0;
    h2 = (h2 + c) >>> 0;
    h3 = (h3 + d) >>> 0;
    h4 = (h4 + e) >>> 0;
    h5 = (h5 + f) >>> 0;
    h6 = (h6 + g) >>> 0;
    h7 = (h7 + h) >>> 0;
  }

  return [h0, h1, h2, h3, h4, h5, h6, h7]
    .map((word) => word.toString(16).padStart(8, "0"))
    .join("");
}

class VelaError extends Error {
  constructor(kind, line, column, message) {
    super(message);
    this.kind = kind;
    this.line = line;
    this.column = column;
    this.message = message;
  }
}

function normalizeNewlines(text) {
  return text.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
}

function codePointSite(prefix) {
  const normalized = normalizeNewlines(prefix);
  const parts = normalized.split("\n");
  const last = parts[parts.length - 1];
  return { line: parts.length, column: Array.from(last).length + 1 };
}

function checkSourceText(sourceText) {
  const bytes = utf8Bytes(sourceText);
  if (bytes.length > MAX_SOURCE_BYTES) {
    throw new VelaError("limit", 1, 1, `source exceeds ${MAX_SOURCE_BYTES} bytes`);
  }
  return { text: sourceText, bytes };
}

function diagnosticLspPosition(sourceText, line, column) {
  const lines = normalizeNewlines(sourceText).split("\n");
  const safeLine = Math.max(1, Math.min(line, lines.length));
  const codePoints = Array.from(lines[safeLine - 1] || "");
  const safeCol = Math.max(1, Math.min(column, codePoints.length + 1));
  const utf16Col = codePoints.slice(0, safeCol - 1).join("").length;
  return { line: safeLine - 1, character: utf16Col };
}

function endOfDocumentLspPosition(sourceText) {
  const lines = normalizeNewlines(sourceText).split("\n");
  return { line: lines.length - 1, character: lines[lines.length - 1].length };
}

const PURE_KEYWORDS = new Set([
  "module",
  "public",
  "return",
  "let",
  "const",
  "if",
  "else",
  "Nat",
  "bool",
  "true",
  "false",
]);

const PURE_UNSUPPORTED = new Set([
  "fn",
  "Bool",
  "async",
  "await",
  "effect",
  "effects",
  "handler",
  "handle",
  "resume",
  "dispose",
  "mut",
  "var",
  "unsafe",
  "borrow",
  "requires",
  "ensures",
  "restores",
  "ghost",
  "tracked",
  "grade",
  "proof",
  "owned",
  "move",
  "ref",
  "in",
  "out",
  "captures",
  "scope",
  "spawn",
  "commit",
  "on",
  "cancel",
  "region",
  "view",
  "union",
  "foreach",
]);

const GALLINA_RESERVED = new Set([
  "Axiom",
  "CoFixpoint",
  "Definition",
  "End",
  "Fixpoint",
  "From",
  "Fun",
  "If",
  "Import",
  "Inductive",
  "Let",
  "Match",
  "Module",
  "Prop",
  "Record",
  "Require",
  "Return",
  "Section",
  "Set",
  "Struct",
  "Then",
  "Theorem",
  "Type",
  "Variable",
  "Where",
  "With",
  "as",
  "at",
  "bool",
  "else",
  "end",
  "exists",
  "false",
  "fix",
  "for",
  "forall",
  "fun",
  "if",
  "in",
  "let",
  "match",
  "mod",
  "nat",
  "return",
  "struct",
  "then",
  "true",
  "type",
  "with",
]);

const PURE_TWO_CHAR_SYMBOLS = new Set(["=>", "==", "!=", "<=", ">=", "&&", "||"]);
const PURE_ONE_CHAR_SYMBOLS = new Set([
  "{",
  "}",
  "(",
  ")",
  ",",
  ";",
  ":",
  "=",
  "+",
  "-",
  "*",
  "/",
  "%",
  "<",
  ">",
  "!",
]);
const PURE_BINARY_OPERATORS = new Set([
  "||",
  "&&",
  "==",
  "!=",
  "<",
  "<=",
  ">",
  ">=",
  "+",
  "-",
  "*",
  "/",
  "%",
]);
const PURE_COMPARISON_OPERATORS = new Set(["==", "!=", "<", "<=", ">", ">="]);

function unsupportedMessage(spelling) {
  const modes = {
    in: "a shared read loan",
    ref: "an initialized exclusive loan",
    out: "an exclusive initialization loan",
    owned: "consuming ownership",
    move: "an explicit ownership transfer",
  };
  if (spelling === "var") {
    return (
      "'var' declares a mutable binding; let and unmarked type-first bindings are immutable. " +
      "Local reassignment requires the wider Vela surface; the pure prototype does not support mutation"
    );
  }
  if (modes[spelling]) {
    return (
      `'${spelling}' requests ${modes[spelling]}; the pure Nat/bool prototype cannot check ` +
      "ownership, borrowing or resource lifetimes"
    );
  }
  return `'${spelling}' is outside the pure prototype`;
}

function makeExpr(kind, value, site, children = [], labels = []) {
  let maxChildDepth = 0;
  let maxChildNesting = 1;
  for (const child of children) {
    if (child.depth > maxChildDepth) maxChildDepth = child.depth;
    if (child.nesting > maxChildNesting) maxChildNesting = child.nesting;
  }
  const depth = maxChildDepth + (kind !== "group" ? 1 : 0);
  if (depth > MAX_EXPRESSION_DEPTH) {
    throw new VelaError(
      "limit",
      site.line,
      site.column,
      `expression exceeds depth ${MAX_EXPRESSION_DEPTH}`
    );
  }
  let nesting = maxChildNesting;
  if (kind === "group" || kind === "unary" || (kind === "call" && children.length > 0)) {
    nesting += 1;
  }
  if (nesting > MAX_EXPRESSION_DEPTH) {
    throw new VelaError(
      "limit",
      site.line,
      site.column,
      `expression nesting exceeds ${MAX_EXPRESSION_DEPTH}`
    );
  }
  return { kind, value, site, children, depth, nesting, labels };
}

function pureTokenize(sourceText, { allowSemicolon = true } = {}) {
  checkSourceText(sourceText);
  const tokens = [];
  let index = 0;
  let line = 1;
  let column = 1;

  while (index < sourceText.length) {
    const ch = sourceText[index];
    if (ch === " " || ch === "\t") {
      index += 1;
      column += 1;
      continue;
    }
    if (ch === "\r") {
      if (sourceText[index + 1] === "\n") {
        index += 2;
      } else {
        index += 1;
      }
      line += 1;
      column = 1;
      continue;
    }
    if (ch === "\n") {
      index += 1;
      line += 1;
      column = 1;
      continue;
    }
    if (sourceText.startsWith("//", index)) {
      while (index < sourceText.length && sourceText[index] !== "\r" && sourceText[index] !== "\n") {
        const cp = sourceText.codePointAt(index);
        index += cp > 0xffff ? 2 : 1;
        column += 1;
      }
      continue;
    }
    if (sourceText.startsWith("/*", index)) {
      throw new VelaError(
        "syntax",
        line,
        column,
        "block comments are not part of the pure prototype"
      );
    }
    const twoChar = sourceText.slice(index, index + 2);
    if (PURE_TWO_CHAR_SYMBOLS.has(twoChar)) {
      tokens.push({ kind: "symbol", text: twoChar, site: { line, column }, offset: index });
      index += 2;
      column += 2;
      continue;
    }
    if (PURE_ONE_CHAR_SYMBOLS.has(ch)) {
      if (!allowSemicolon && ch === ";") {
        throw new VelaError("syntax", line, column, "unexpected ';'");
      }
      tokens.push({ kind: "symbol", text: ch, site: { line, column }, offset: index });
      index += 1;
      column += 1;
      continue;
    }
    const rest = sourceText.slice(index);
    const wordMatch = /^[A-Za-z_][A-Za-z0-9_]*/.exec(rest);
    if (wordMatch) {
      const word = wordMatch[0];
      tokens.push({ kind: "word", text: word, site: { line, column }, offset: index });
      index += word.length;
      column += word.length;
      continue;
    }
    const decMatch = /^[0-9](?:_?[0-9])*/.exec(rest);
    if (decMatch) {
      const digits = decMatch[0];
      const nextChar = sourceText[index + digits.length] || "";
      if (/[A-Za-z0-9_]/.test(nextChar)) {
        throw new VelaError("syntax", line, column, "invalid numeric literal");
      }
      if (digits.replace(/_/g, "").length > MAX_LITERAL_DIGITS) {
        throw new VelaError(
          "limit",
          line,
          column,
          `integer literal exceeds ${MAX_LITERAL_DIGITS} digits`
        );
      }
      tokens.push({ kind: "nat", text: digits, site: { line, column }, offset: index });
      index += digits.length;
      column += digits.length;
      continue;
    }
    throw new VelaError("syntax", line, column, `unexpected character '${ch}'`);
  }
  tokens.push({ kind: "eof", text: "<eof>", site: { line, column }, offset: index });
  return tokens;
}

class PureParser {
  constructor(tokens) {
    this.tokens = tokens;
    this.index = 0;
    this.declarationSites = new Map();
  }

  get current() {
    return this.tokens[this.index];
  }

  peek(offset = 1) {
    return this.tokens[Math.min(this.index + offset, this.tokens.length - 1)];
  }

  advance() {
    const tok = this.current;
    this.index = Math.min(this.index + 1, this.tokens.length - 1);
    return tok;
  }

  match(kind, text = null) {
    if (this.current.kind === kind && (text === null || this.current.text === text)) {
      return this.advance();
    }
    return null;
  }

  unsupported() {
    if (this.current.kind === "word" && PURE_UNSUPPORTED.has(this.current.text)) {
      throw new VelaError(
        "unsupported",
        this.current.site.line,
        this.current.site.column,
        unsupportedMessage(this.current.text)
      );
    }
  }

  expect(kind, text, description = null) {
    this.unsupported();
    const tok = this.match(kind, text);
    if (!tok) {
      const label = description || `'${text}'`;
      throw new VelaError(
        "syntax",
        this.current.site.line,
        this.current.site.column,
        `expected ${label}, found '${this.current.text}'`
      );
    }
    return tok;
  }

  parseName(role) {
    this.unsupported();
    const tok = this.current;
    if (tok.kind !== "word") {
      throw new VelaError(
        "syntax",
        tok.site.line,
        tok.site.column,
        `expected ${role}, found '${tok.text}'`
      );
    }
    if (PURE_KEYWORDS.has(tok.text)) {
      throw new VelaError(
        "syntax",
        tok.site.line,
        tok.site.column,
        `expected ${role}, found keyword '${tok.text}'`
      );
    }
    this.advance();
    return { text: tok.text, site: tok.site, offset: tok.offset };
  }

  parseType(role) {
    this.unsupported();
    const tok = this.current;
    if (tok.kind === "word" && (tok.text === "Nat" || tok.text === "bool")) {
      this.advance();
      return tok.text;
    }
    if (tok.kind === "word" && !PURE_KEYWORDS.has(tok.text)) {
      throw new VelaError(
        "unsupported",
        tok.site.line,
        tok.site.column,
        `unsupported ${role} '${tok.text}'; the pure prototype supports Nat and bool`
      );
    }
    throw new VelaError(
      "syntax",
      tok.site.line,
      tok.site.column,
      `expected ${role}, found '${tok.text}'`
    );
  }

  parseModule() {
    this.expect("word", "module");
    const name = this.parseName("module name");
    this.expect("symbol", ";");
    const declarations = [];
    while (this.current.kind !== "eof") {
      this.unsupported();
      const pub = this.expect("word", "public", "'public' function or constant declaration");
      const constTok = this.match("word", "const");
      const result = this.parseType(constTok ? "constant or return type" : "return type");
      const declName = this.parseName(constTok ? "constant name" : "function name");
      this.declarationSites.set(`${declName.site.line}:${declName.site.column}`, pub.site);
      if (constTok && this.match("symbol", "=")) {
        const value = this.parseExpression();
        this.expect("symbol", ";");
        declarations.push({
          kind: "constant",
          name: declName,
          valueType: result,
          value,
          site: pub.site,
        });
        continue;
      }
      this.expect("symbol", "(");
      const parameters = [];
      const constParameters = new Set();
      if (!this.match("symbol", ")")) {
        while (true) {
          const isConstParam = Boolean(this.match("word", "const"));
          const pType = this.parseType("parameter type");
          const pName = this.parseName("parameter name");
          parameters.push([pName, pType]);
          if (isConstParam) {
            constParameters.add(pName.text);
          }
          if (this.match("symbol", ")")) break;
          this.expect("symbol", ",");
          if (this.match("symbol", ")")) break;
        }
      }
      let body;
      const bodykind = this.current.text === "=>" ? "expression" : "block";
      if (this.match("symbol", "=>")) {
        const value = this.parseExpression();
        const semi = this.expect("symbol", ";");
        body = {
          bindings: [],
          terminal: { kind: "return", value, site: value.site },
          site: semi.site,
        };
      } else {
        body = this.parseBlock(1);
      }
      declarations.push({
        kind: "function",
        name: declName,
        result,
        parameters,
        body,
        bodyKind: bodykind,
        isConst: Boolean(constTok),
        constParameters,
      });
    }
    if (declarations.length === 0) {
      throw new VelaError(
        "syntax",
        this.current.site.line,
        this.current.site.column,
        "expected at least one public function or constant"
      );
    }
    return { name, declarations };
  }

  parseBlock(depth) {
    if (depth > MAX_BLOCK_DEPTH) {
      throw new VelaError(
        "limit",
        this.current.site.line,
        this.current.site.column,
        `block nesting exceeds ${MAX_BLOCK_DEPTH}`
      );
    }
    const openTok = this.expect("symbol", "{");
    const bindings = [];
    while (!["return", "if", "}", "<eof>"].includes(this.current.text)) {
      this.unsupported();
      if (this.current.kind === "word" && this.current.text === "const") {
        const constTok = this.advance();
        const valueType = this.parseType("constant type");
        const name = this.parseName("constant name");
        this.expect("symbol", "=");
        const value = this.parseExpression();
        this.expect("symbol", ";");
        bindings.push({
          kind: "constant",
          name,
          valueType,
          value,
          site: constTok.site,
        });
        continue;
      }
      if (
        this.current.kind === "word" &&
        (this.current.text === "let" ||
          this.current.text === "Nat" ||
          this.current.text === "bool")
      ) {
        const startTok = this.current;
        const letTok = this.match("word", "let");
        let annotation = null;
        if (
          this.current.kind === "word" &&
          (this.current.text === "Nat" || this.current.text === "bool")
        ) {
          annotation = this.parseType("local type");
        }
        const name = this.parseName("local binding name");
        this.expect("symbol", "=");
        const value = this.parseExpression();
        this.expect("symbol", ";");
        bindings.push({
          kind: "binding",
          name,
          value,
          site: startTok.site,
          annotation,
          explicitBinding: Boolean(letTok),
          typeOffset: annotation && !letTok ? startTok.offset : null,
        });
        continue;
      }
      if (this.current.kind === "word" && this.peek().text === "=") {
        const name = this.parseName("variable name");
        this.expect("symbol", "=");
        const value = this.parseExpression();
        this.expect("symbol", ";");
        bindings.push({
          kind: "reassignment",
          name,
          value,
          site: name.site,
        });
        continue;
      }
      break;
    }
    if (bindings.length > MAX_BLOCK_DEPTH) {
      throw new VelaError(
        "limit",
        openTok.site.line,
        openTok.site.column,
        `block exceeds ${MAX_BLOCK_DEPTH} bindings`
      );
    }
    let terminal;
    if (this.match("word", "return")) {
      const value = this.parseExpression();
      this.expect("symbol", ";");
      terminal = { kind: "return", value, site: value.site };
    } else if (this.match("word", "if")) {
      const openCond = this.expect("symbol", "(");
      const condition = this.parseExpression();
      this.expect("symbol", ")");
      const yes = this.parseBlock(depth + 1);
      this.expect("word", "else");
      const no = this.parseBlock(depth + 1);
      terminal = { kind: "conditional", condition, yes, no, site: openCond.site };
    } else {
      this.unsupported();
      throw new VelaError(
        "syntax",
        this.current.site.line,
        this.current.site.column,
        `expected 'let', 'return' or 'if', found '${this.current.text}'`
      );
    }
    this.expect("symbol", "}");
    return { bindings, terminal, site: openTok.site };
  }

  parseExpression() {
    return this.parseDisjunction();
  }

  parseDisjunction() {
    let left = this.parseConjunction();
    while (this.current.kind === "symbol" && this.current.text === "||") {
      const op = this.advance();
      left = makeExpr("binary", op.text, op.site, [left, this.parseConjunction()]);
    }
    return left;
  }

  parseConjunction() {
    let left = this.parseComparison();
    while (this.current.kind === "symbol" && this.current.text === "&&") {
      const op = this.advance();
      left = makeExpr("binary", op.text, op.site, [left, this.parseComparison()]);
    }
    return left;
  }

  parseComparison() {
    let left = this.parseAdditive();
    if (this.current.kind === "symbol" && PURE_COMPARISON_OPERATORS.has(this.current.text)) {
      const op = this.advance();
      left = makeExpr("binary", op.text, op.site, [left, this.parseAdditive()]);
      if (this.current.kind === "symbol" && PURE_COMPARISON_OPERATORS.has(this.current.text)) {
        throw new VelaError(
          "syntax",
          this.current.site.line,
          this.current.site.column,
          "comparisons do not chain; parenthesize or combine with &&"
        );
      }
    }
    return left;
  }

  parseAdditive() {
    let left = this.parseMultiplicative();
    while (
      this.current.kind === "symbol" &&
      (this.current.text === "+" || this.current.text === "-")
    ) {
      const op = this.advance();
      left = makeExpr("binary", op.text, op.site, [left, this.parseMultiplicative()]);
    }
    return left;
  }

  parseMultiplicative() {
    let left = this.parseUnary();
    while (
      this.current.kind === "symbol" &&
      (this.current.text === "*" || this.current.text === "/" || this.current.text === "%")
    ) {
      const op = this.advance();
      left = makeExpr("binary", op.text, op.site, [left, this.parseUnary()]);
    }
    return left;
  }

  parseUnary() {
    if (this.current.kind === "symbol" && this.current.text === "!") {
      const op = this.advance();
      return makeExpr("unary", op.text, op.site, [this.parseUnary()]);
    }
    return this.parsePrimary();
  }

  parsePrimary() {
    this.unsupported();
    const tok = this.current;
    if (tok.kind === "nat") {
      this.advance();
      return makeExpr("nat", tok.text, tok.site);
    }
    if (tok.kind === "word" && (tok.text === "true" || tok.text === "false")) {
      this.advance();
      return makeExpr("bool", tok.text === "true", tok.site);
    }
    if (this.match("symbol", "(")) {
      const inner = this.parseExpression();
      this.expect("symbol", ")");
      return makeExpr("group", "", tok.site, [inner]);
    }
    if (tok.kind === "word") {
      const name = this.parseName("identifier");
      if (this.match("symbol", "(")) {
        const args = [];
        const labels = [];
        if (!this.match("symbol", ")")) {
          while (true) {
            let label = null;
            if (this.current.kind === "word" && this.peek().text === ":") {
              label = this.parseName("argument label");
              this.expect("symbol", ":");
            }
            labels.push(label);
            args.push(this.parseExpression());
            if (this.match("symbol", ")")) break;
            this.expect("symbol", ",");
            if (this.match("symbol", ")")) break;
          }
        }
        return makeExpr("call", name.text, name.site, args, labels);
      }
      return makeExpr("name", name.text, name.site);
    }
    throw new VelaError(
      "syntax",
      tok.site.line,
      tok.site.column,
      `expected expression, found '${tok.text}'`
    );
  }
}

function extractPureDocumentation(sourceText, declSite) {
  const lines = normalizeNewlines(sourceText).split("\n");
  const targetLineIdx = declSite.line - 1;
  if (targetLineIdx <= 0 || targetLineIdx >= lines.length) return null;
  const prefix = Array.from(lines[targetLineIdx]).slice(0, declSite.column - 1).join("");
  if (prefix.trim() !== "") return null;
  const pieces = [];
  let lineIdx = targetLineIdx - 1;
  while (lineIdx >= 0) {
    const trimmed = lines[lineIdx].replace(/^[ \t]+/, "");
    if (!trimmed.startsWith("///")) break;
    const after = trimmed.slice(3);
    pieces.push(after.startsWith(" ") ? after.slice(1) : after);
    lineIdx -= 1;
  }
  if (pieces.length === 0) return null;
  pieces.reverse();
  return pieces.join("\n");
}

function mangleGallina(prefix, name) {
  return `${prefix}_${name.replace(/_/g, "__")}`;
}

function mangleGallinaModule(name) {
  if (GALLINA_RESERVED.has(name) || name.startsWith("m_") || name.startsWith("v_")) {
    return mangleGallina("m", name);
  }
  return name;
}

function gallinaType(valueType) {
  return valueType === "Nat" ? "nat" : "bool";
}

function gallinaStaticValue(value) {
  if (typeof value === "boolean") {
    return value ? "true" : "false";
  }
  return `${value.toString()}%nat`;
}

function checkPureCallArguments(item, sig, facts) {
  let seenNamed = false;
  for (let i = 0; i < item.children.length; i += 1) {
    const label = item.labels[i];
    if (label === null || label === undefined) {
      if (seenNamed) {
        throw new VelaError(
          "type",
          item.children[i].site.line,
          item.children[i].site.column,
          `positional argument in call to '${item.value}' cannot follow a named argument`
        );
      }
      continue;
    }
    seenNamed = true;
    if (i < sig.parameterNames.length && label.text === sig.parameterNames[i]) {
      if (facts && sig.parameterIds[i] !== undefined) {
        facts.reference(sig.parameterIds[i], label.site);
      }
      continue;
    }
    if (sig.parameterNames.includes(label.text)) {
      throw new VelaError(
        "type",
        label.site.line,
        label.site.column,
        `named argument '${label.text}:' in call to '${item.value}' must appear in parameter order`
      );
    }
    throw new VelaError(
      "type",
      label.site.line,
      label.site.column,
      `unknown argument label '${label.text}' in call to '${item.value}'`
    );
  }
}

class PureFacts {
  constructor(sourceText, declarationSites) {
    this.sourceText = sourceText;
    this.declarationSites = declarationSites || new Map();
    this.symbols = [];
    this.occurrences = [];
  }

  declare(name, kind, detail, { inferred = null } = {}) {
    const id = this.symbols.length;
    const siteKey = `${name.site.line}:${name.site.column}`;
    const pubSite = this.declarationSites.get(siteKey);
    const documentation = pubSite ? extractPureDocumentation(this.sourceText, pubSite) : null;
    this.symbols.push({
      name: name.text,
      kind,
      detail,
      line: name.site.line,
      column: name.site.column,
      inferred,
      documentation,
    });
    this.reference(id, name.site, { declaration: true });
    return id;
  }

  reference(symbolId, site, { declaration = false } = {}) {
    this.occurrences.push({
      symbol: symbolId,
      line: site.line,
      column: site.column,
      declaration,
    });
  }

  result() {
    const indexed = this.symbols.map((sym, idx) => ({ idx, sym }));
    indexed.sort((a, b) => a.sym.line - b.sym.line || a.sym.column - b.sym.column);
    const remap = new Map();
    const orderedSymbols = indexed.map((entry, newIdx) => {
      remap.set(entry.idx, newIdx);
      return entry.sym;
    });
    const orderedOccurrences = this.occurrences
      .map((occ) => ({
        symbol: remap.get(occ.symbol),
        line: occ.line,
        column: occ.column,
        declaration: occ.declaration,
      }))
      .sort((a, b) => a.line - b.line || a.column - b.column);
    return { status: "ok", symbols: orderedSymbols, occurrences: orderedOccurrences };
  }
}

class PureStaticEvaluator {
  constructor(constants, functions, constFunctions, facts = null) {
    this.constants = new Map(constants);
    this.functions = functions;
    this.constFunctions = constFunctions;
    this.facts = facts;
    this.steps = 0;
  }

  step(site) {
    this.steps += 1;
    if (this.steps > MAX_STATIC_STEPS) {
      throw new VelaError(
        "limit",
        site.line,
        site.column,
        `compile-time evaluation exceeds ${MAX_STATIC_STEPS} steps`
      );
    }
  }

  record(facts) {
    return facts ? this.facts : null;
  }

  evaluateConstant(declaration, facts = true) {
    const value = this.evalExpr(declaration.value, new Map(), new Set(), facts);
    const actual = typeof value === "boolean" ? "bool" : "Nat";
    if (actual !== declaration.valueType) {
      throw new VelaError(
        "type",
        declaration.site.line,
        declaration.site.column,
        `constant '${declaration.name.text}' has type ${declaration.valueType}, got ${actual}`
      );
    }
    this.constants.set(declaration.name.text, [
      declaration.valueType,
      value,
      this.facts
        ? this.facts.declare(
            declaration.name,
            "constant",
            `const ${declaration.valueType} ${declaration.name.text} = ${
              typeof value === "boolean" ? (value ? "true" : "false") : value.toString()
            }`
          )
        : -1,
    ]);
    return value;
  }

  evalBlock(block, env, runtimeNames, facts) {
    const localEnv = new Map(env);
    const localRuntime = new Set(runtimeNames);
    for (const stmt of block.bindings) {
      if (stmt.kind === "reassignment") {
        throw new VelaError(
          "unsupported",
          stmt.site.line,
          stmt.site.column,
          "reassignment is not supported in compile-time functions"
        );
      }
      const val = this.evalExpr(stmt.value, localEnv, localRuntime, facts);
      const actual = typeof val === "boolean" ? "bool" : "Nat";
      const expected = stmt.kind === "constant" ? stmt.valueType : stmt.annotation;
      if (expected !== null && expected !== undefined && actual !== expected) {
        const role = stmt.kind === "constant" ? "constant" : "local";
        throw new VelaError(
          "type",
          stmt.site.line,
          stmt.site.column,
          `${role} '${stmt.name.text}' has type ${expected}, got ${actual}`
        );
      }
      localRuntime.delete(stmt.name.text);
      localEnv.set(stmt.name.text, [actual, val, -1]);
    }
    if (block.terminal.kind === "return") {
      return this.evalExpr(block.terminal.value, localEnv, localRuntime, facts);
    }
    const cond = this.evalExpr(block.terminal.condition, localEnv, localRuntime, facts);
    if (typeof cond !== "boolean") {
      throw new VelaError(
        "type",
        block.terminal.site.line,
        block.terminal.site.column,
        "if condition must have type bool"
      );
    }
    return this.evalBlock(cond ? block.terminal.yes : block.terminal.no, localEnv, localRuntime, facts);
  }

  evalExpr(item, env, runtimeNames, facts) {
    this.step(item.site);
    if (item.kind === "nat") {
      const value = BigInt(String(item.value).replace(/_/g, ""));
      if (value > MAX_NAT_VALUE) {
        throw new VelaError(
          "limit",
          item.site.line,
          item.site.column,
          `compile-time Nat value exceeds ${MAX_LITERAL_DIGITS} digits`
        );
      }
      return value;
    }
    if (item.kind === "bool") {
      return Boolean(item.value);
    }
    if (item.kind === "group") {
      return this.evalExpr(item.children[0], env, runtimeNames, facts);
    }
    if (item.kind === "name") {
      const name = String(item.value);
      const local = env.get(name);
      if (local !== undefined) {
        const rec = this.record(facts);
        if (rec && local[2] >= 0) rec.reference(local[2], item.site);
        return local[1];
      }
      if (runtimeNames.has(name)) {
        throw new VelaError(
          "unsupported",
          item.site.line,
          item.site.column,
          `required-static expression cannot depend on runtime binding '${name}'`
        );
      }
      const constant = this.constants.get(name);
      if (constant !== undefined) {
        const rec = this.record(facts);
        if (rec && constant[2] >= 0) rec.reference(constant[2], item.site);
        return constant[1];
      }
      throw new VelaError("name", item.site.line, item.site.column, `unknown variable '${name}'`);
    }
    if (item.kind === "unary") {
      const operand = this.evalExpr(item.children[0], env, runtimeNames, facts);
      if (typeof operand !== "boolean") {
        throw new VelaError(
          "type",
          item.site.line,
          item.site.column,
          "operator '!' requires a bool operand"
        );
      }
      return !operand;
    }
    if (item.kind === "call") {
      const callee = String(item.value);
      const sig = this.functions.get(callee);
      const fnDecl = this.constFunctions.get(callee);
      if (!sig || !fnDecl) {
        throw new VelaError(
          "name",
          item.site.line,
          item.site.column,
          `unknown function '${callee}'`
        );
      }
      const rec = this.record(facts);
      if (rec && sig.symbol >= 0) rec.reference(sig.symbol, item.site);
      if (item.children.length !== sig.parameters.length) {
        throw new VelaError(
          "type",
          item.site.line,
          item.site.column,
          `function '${callee}' expects ${sig.parameters.length} argument(s), got ${item.children.length}`
        );
      }
      checkPureCallArguments(item, sig, rec);
      const callEnv = new Map();
      for (let i = 0; i < fnDecl.parameters.length; i += 1) {
        const [pName, pType] = fnDecl.parameters[i];
        const argVal = this.evalExpr(item.children[i], env, runtimeNames, facts);
        const actual = typeof argVal === "boolean" ? "bool" : "Nat";
        if (actual !== pType) {
          throw new VelaError(
            "type",
            item.children[i].site.line,
            item.children[i].site.column,
            `argument ${i + 1} of '${callee}' expects ${pType}, got ${actual}`
          );
        }
        callEnv.set(pName.text, [pType, argVal, -1]);
      }
      const result = this.evalBlock(fnDecl.body, callEnv, new Set(), false);
      const actual = typeof result === "boolean" ? "bool" : "Nat";
      if (actual !== fnDecl.result) {
        throw new VelaError(
          "type",
          item.site.line,
          item.site.column,
          `return value of '${callee}' has type ${actual}, expected ${fnDecl.result}`
        );
      }
      return result;
    }
    const op = String(item.value);
    const left = this.evalExpr(item.children[0], env, runtimeNames, facts);
    if (op === "&&" || op === "||") {
      if (typeof left !== "boolean") {
        throw new VelaError(
          "type",
          item.site.line,
          item.site.column,
          `operator '${op}' requires bool operands`
        );
      }
      if ((op === "&&" && !left) || (op === "||" && left)) {
        const rightType = inferPureExpression(
          item.children[1],
          env,
          this.constants,
          this.functions,
          this,
          runtimeNames,
          null
        )[0];
        if (rightType !== "bool") {
          throw new VelaError(
            "type",
            item.site.line,
            item.site.column,
            `operator '${op}' requires bool operands`
          );
        }
        return left;
      }
      const right = this.evalExpr(item.children[1], env, runtimeNames, facts);
      if (typeof right !== "boolean") {
        throw new VelaError(
          "type",
          item.site.line,
          item.site.column,
          `operator '${op}' requires bool operands`
        );
      }
      return right;
    }
    const right = this.evalExpr(item.children[1], env, runtimeNames, facts);
    if (op === "==" || op === "!=") {
      if (typeof left !== typeof right) {
        throw new VelaError(
          "type",
          item.site.line,
          item.site.column,
          `operator '${op}' requires operands of the same type`
        );
      }
      return op === "==" ? left === right : left !== right;
    }
    if (typeof left === "boolean" || typeof right === "boolean") {
      throw new VelaError(
        "type",
        item.site.line,
        item.site.column,
        `operator '${op}' requires Nat operands`
      );
    }
    if (op === "<") return left < right;
    if (op === "<=") return left <= right;
    if (op === ">") return left > right;
    if (op === ">=") return left >= right;
    let value;
    if (op === "+") value = left + right;
    else if (op === "-") value = left > right ? left - right : 0n;
    else if (op === "*") value = left * right;
    else if (op === "/") value = right === 0n ? 0n : left / right;
    else value = right === 0n ? left : left % right;
    if (value > MAX_NAT_VALUE) {
      throw new VelaError(
        "limit",
        item.site.line,
        item.site.column,
        `compile-time Nat value exceeds ${MAX_LITERAL_DIGITS} digits`
      );
    }
    return value;
  }
}

function inferPureExpression(item, env, constants, functions, evaluator, runtimeNames, facts) {
  if (item.kind === "nat") {
    return ["Nat", `${BigInt(String(item.value).replace(/_/g, "")).toString()}%nat`];
  }
  if (item.kind === "bool") {
    return ["bool", item.value ? "true" : "false"];
  }
  if (item.kind === "group") {
    const [vt, rendered] = inferPureExpression(
      item.children[0],
      env,
      constants,
      functions,
      evaluator,
      runtimeNames,
      facts
    );
    return [vt, `(${rendered})`];
  }
  if (item.kind === "name") {
    const name = String(item.value);
    const local = env.get(name);
    if (local !== undefined) {
      if (facts && local[2] >= 0) facts.reference(local[2], item.site);
      return [local[0], mangleGallina("v", name)];
    }
    const constant = constants.get(name);
    if (constant !== undefined) {
      if (facts && constant[2] >= 0) facts.reference(constant[2], item.site);
      return [constant[0], mangleGallina("d", name)];
    }
    throw new VelaError("name", item.site.line, item.site.column, `unknown variable '${name}'`);
  }
  if (item.kind === "call") {
    const callee = String(item.value);
    const sig = functions.get(callee);
    if (!sig) {
      throw new VelaError("name", item.site.line, item.site.column, `unknown function '${callee}'`);
    }
    if (facts && sig.symbol >= 0) facts.reference(sig.symbol, item.site);
    if (item.children.length !== sig.parameters.length) {
      throw new VelaError(
        "type",
        item.site.line,
        item.site.column,
        `function '${callee}' expects ${sig.parameters.length} argument(s), got ${item.children.length}`
      );
    }
    checkPureCallArguments(item, sig, facts);
    const staticEnv = new Map();
    for (const [k, v] of env.entries()) {
      if (v[1] !== null && v[1] !== undefined) {
        staticEnv.set(k, [v[0], v[1], v[2]]);
      }
    }
    const renderedArgs = [];
    for (let i = 0; i < item.children.length; i += 1) {
      const child = item.children[i];
      const expected = sig.parameters[i];
      if (sig.constIndices.has(i)) {
        const val = evaluator.evalExpr(child, staticEnv, runtimeNames, true);
        const actual = typeof val === "boolean" ? "bool" : "Nat";
        if (actual !== expected) {
          throw new VelaError(
            "type",
            child.site.line,
            child.site.column,
            `argument ${i + 1} of '${callee}' expects ${expected}, got ${actual}`
          );
        }
        renderedArgs.push(gallinaStaticValue(val));
      } else {
        const [actual, rendered] = inferPureExpression(
          child,
          env,
          constants,
          functions,
          evaluator,
          runtimeNames,
          facts
        );
        if (actual !== expected) {
          throw new VelaError(
            "type",
            child.site.line,
            child.site.column,
            `argument ${i + 1} of '${callee}' expects ${expected}, got ${actual}`
          );
        }
        renderedArgs.push(rendered);
      }
    }
    const target = mangleGallina("d", callee);
    return [sig.result, renderedArgs.length > 0 ? `(${target} ${renderedArgs.join(" ")})` : target];
  }
  if (item.kind === "unary") {
    const [operandType, rendered] = inferPureExpression(
      item.children[0],
      env,
      constants,
      functions,
      evaluator,
      runtimeNames,
      facts
    );
    if (operandType !== "bool") {
      throw new VelaError(
        "type",
        item.site.line,
        item.site.column,
        "operator '!' requires a bool operand"
      );
    }
    return ["bool", `(negb ${rendered})`];
  }
  const [lt, lr] = inferPureExpression(
    item.children[0],
    env,
    constants,
    functions,
    evaluator,
    runtimeNames,
    facts
  );
  const [rt, rr] = inferPureExpression(
    item.children[1],
    env,
    constants,
    functions,
    evaluator,
    runtimeNames,
    facts
  );
  const op = String(item.value);
  if (op === "+" || op === "-" || op === "*" || op === "/" || op === "%") {
    if (lt !== "Nat" || rt !== "Nat") {
      throw new VelaError(
        "type",
        item.site.line,
        item.site.column,
        `operator '${op}' requires Nat operands`
      );
    }
    const fn = {
      "+": "Corelib.Init.Nat.add",
      "-": "Corelib.Init.Nat.sub",
      "*": "Corelib.Init.Nat.mul",
      "/": "Corelib.Init.Nat.div",
      "%": "Corelib.Init.Nat.modulo",
    }[op];
    return ["Nat", `(${fn} ${lr} ${rr})`];
  }
  if (op === "<" || op === "<=" || op === ">" || op === ">=") {
    if (lt !== "Nat" || rt !== "Nat") {
      throw new VelaError(
        "type",
        item.site.line,
        item.site.column,
        `operator '${op}' requires Nat operands`
      );
    }
    if (op === "<") return ["bool", `(Corelib.Init.Nat.ltb ${lr} ${rr})`];
    if (op === "<=") return ["bool", `(Corelib.Init.Nat.leb ${lr} ${rr})`];
    if (op === ">") return ["bool", `(Corelib.Init.Nat.ltb ${rr} ${lr})`];
    return ["bool", `(Corelib.Init.Nat.leb ${rr} ${lr})`];
  }
  if (op === "==" || op === "!=") {
    if (lt !== rt) {
      throw new VelaError(
        "type",
        item.site.line,
        item.site.column,
        `operator '${op}' requires operands of the same type`
      );
    }
    const eqFn = lt === "Nat" ? "Corelib.Init.Nat.eqb" : "Bool.eqb";
    const eqExpr = `(${eqFn} ${lr} ${rr})`;
    return ["bool", op === "==" ? eqExpr : `(negb ${eqExpr})`];
  }
  if (lt !== "bool" || rt !== "bool") {
    throw new VelaError(
      "type",
      item.site.line,
      item.site.column,
      `operator '${op}' requires bool operands`
    );
  }
  const boolFn = op === "&&" ? "andb" : "orb";
  return ["bool", `(${boolFn} ${lr} ${rr})`];
}

function checkPureBlock(
  block,
  env,
  immutable,
  expected,
  constants,
  functions,
  evaluator,
  indent,
  facts
) {
  const localEnv = new Map(env);
  const localImmutable = new Set(immutable);
  const lines = [];
  const pad = " ".repeat(indent);
  const runtimeNames = new Set();
  for (const [k, v] of localEnv.entries()) {
    if ((v[1] === null || v[1] === undefined) && !v[3]) runtimeNames.add(k);
  }
  for (const stmt of block.bindings) {
    if (stmt.kind === "reassignment") {
      if (localImmutable.has(stmt.name.text)) {
        throw new VelaError(
          "unsupported",
          stmt.site.line,
          stmt.site.column,
          `cannot reassign immutable binding '${stmt.name.text}'; let, parameter, const and unmarked type-first bindings are immutable`
        );
      }
      throw new VelaError(
        "name",
        stmt.site.line,
        stmt.site.column,
        `unknown variable '${stmt.name.text}'`
      );
    }
    const staticEnv = new Map();
    for (const [k, v] of localEnv.entries()) {
      if (v[1] !== null && v[1] !== undefined) staticEnv.set(k, [v[0], v[1], v[2]]);
      else if (v[3]) staticEnv.set(k, [v[0], v[0] === "Nat" ? 0n : false, v[2]]);
    }
    if (stmt.kind === "constant") {
      const [inferredType, renderedInit] = inferPureExpression(
        stmt.value,
        localEnv,
        constants,
        functions,
        evaluator,
        runtimeNames,
        facts
      );
      if (inferredType !== stmt.valueType) {
        throw new VelaError(
          "type",
          stmt.site.line,
          stmt.site.column,
          `constant '${stmt.name.text}' has type ${stmt.valueType}, got ${inferredType}`
        );
      }
      const value = evaluator.evalExpr(stmt.value, staticEnv, runtimeNames, false);
      const dependsOnSymbolic = Array.from(localEnv.entries()).some(
        ([, v]) => v[3] && (v[1] === null || v[1] === undefined)
      );
      const lit = typeof value === "boolean" ? (value ? "true" : "false") : value.toString();
      const detail = dependsOnSymbolic
        ? `const ${stmt.valueType} ${stmt.name.text}`
        : `const ${stmt.valueType} ${stmt.name.text} = ${lit}`;
      const symId = facts ? facts.declare(stmt.name, "constant", detail) : -1;
      localEnv.set(stmt.name.text, [
        stmt.valueType,
        dependsOnSymbolic ? null : value,
        symId,
        true,
      ]);
      localImmutable.add(stmt.name.text);
      runtimeNames.delete(stmt.name.text);
      const rhs = dependsOnSymbolic ? renderedInit : gallinaStaticValue(value);
      lines.push(
        `${pad}let ${mangleGallina("v", stmt.name.text)} : ${gallinaType(stmt.valueType)} := ${rhs} in`
      );
      continue;
    }
    const [vt, rendered] = inferPureExpression(
      stmt.value,
      localEnv,
      constants,
      functions,
      evaluator,
      runtimeNames,
      facts
    );
    if (stmt.annotation !== null && stmt.annotation !== undefined && vt !== stmt.annotation) {
      throw new VelaError(
        "type",
        stmt.site.line,
        stmt.site.column,
        `local '${stmt.name.text}' has type ${stmt.annotation}, got ${vt}`
      );
    }
    const symId = facts
      ? facts.declare(stmt.name, "variable", `${stmt.name.text}: ${vt}`, {
          inferred: stmt.annotation === null ? null : false,
        })
      : -1;
    localEnv.set(stmt.name.text, [vt, null, symId]);
    localImmutable.add(stmt.name.text);
    runtimeNames.add(stmt.name.text);
    lines.push(`${pad}let ${mangleGallina("v", stmt.name.text)} : ${gallinaType(vt)} := ${rendered} in`);
  }
  if (block.terminal.kind === "return") {
    const [vt, rendered] = inferPureExpression(
      block.terminal.value,
      localEnv,
      constants,
      functions,
      evaluator,
      runtimeNames,
      facts
    );
    if (vt !== expected) {
      throw new VelaError(
        "type",
        block.terminal.site.line,
        block.terminal.site.column,
        `return value has type ${vt}, expected ${expected}`
      );
    }
    lines.push(`${pad}${rendered}`);
    return lines.join("\n");
  }
  const [condType, condRendered] = inferPureExpression(
    block.terminal.condition,
    localEnv,
    constants,
    functions,
    evaluator,
    runtimeNames,
    facts
  );
  if (condType !== "bool") {
    throw new VelaError(
      "type",
      block.terminal.site.line,
      block.terminal.site.column,
      "if condition must have type bool"
    );
  }
  const yesRendered = checkPureBlock(
    block.terminal.yes,
    localEnv,
    localImmutable,
    expected,
    constants,
    functions,
    evaluator,
    indent + 2,
    facts
  );
  const noRendered = checkPureBlock(
    block.terminal.no,
    localEnv,
    localImmutable,
    expected,
    constants,
    functions,
    evaluator,
    indent + 2,
    facts
  );
  lines.push(`${pad}if ${condRendered} then`, yesRendered, `${pad}else`, noRendered);
  return lines.join("\n");
}

function parsePureModule(sourceText) {
  const parser = new PureParser(pureTokenize(sourceText));
  const parsed = parser.parseModule();
  return { parsed, declarationSites: parser.declarationSites };
}

function runPureTranslate(sourceText, collectFacts = false) {
  const { parsed, declarationSites } = parsePureModule(sourceText);
  const facts = collectFacts ? new PureFacts(sourceText, declarationSites) : null;
  const declarations = new Set();
  const constants = new Map();
  const functions = new Map();
  const constFunctions = new Map();

  for (const item of parsed.declarations) {
    if (declarations.has(item.name.text)) {
      throw new VelaError(
        "name",
        item.name.site.line,
        item.name.site.column,
        `duplicate declaration '${item.name.text}'`
      );
    }
    declarations.add(item.name.text);
    if (item.kind === "constant") {
      continue;
    }
    const seenParams = new Set();
    const parameterIds = [];
    for (const [pName, pType] of item.parameters) {
      if (seenParams.has(pName.text)) {
        throw new VelaError(
          "name",
          pName.site.line,
          pName.site.column,
          `duplicate parameter '${pName.text}' in '${item.name.text}'`
        );
      }
      seenParams.add(pName.text);
      const prefix = item.constParameters.has(pName.text) ? "const " : "";
      parameterIds.push(
        facts ? facts.declare(pName, "parameter", `${prefix}${pName.text}: ${pType}`) : -1
      );
    }
    const detailParams = item.parameters
      .map(
        ([pName, pType]) =>
          `${item.constParameters.has(pName.text) ? "const " : ""}${pType} ${pName.text}`
      )
      .join(", ");
    const qualifier = item.isConst ? "const " : "";
    const fnSymId = facts
      ? facts.declare(
          item.name,
          "function",
          `public ${qualifier}${item.result} ${item.name.text}(${detailParams})`
        )
      : -1;
    const constIndices = new Set();
    item.parameters.forEach(([pName], idx) => {
      if (item.constParameters.has(pName.text)) constIndices.add(idx);
    });
    functions.set(item.name.text, {
      parameters: item.parameters.map(([, pType]) => pType),
      parameterNames: item.parameters.map(([pName]) => pName.text),
      parameterIds,
      result: item.result,
      symbol: fnSymId,
      isConst: item.isConst,
      constIndices,
    });
    constFunctions.set(item.name.text, item);
  }

  const evaluator = new PureStaticEvaluator(constants, functions, constFunctions, facts);
  const mangledModule = mangleGallinaModule(parsed.name.text);
  const outLines = [
    "(* Generated by the Vela pure prototype. *)",
    "From Stdlib Require Import Bool Arith PeanoNat.",
    `Module ${mangledModule}.`,
  ];

  for (const item of parsed.declarations) {
    if (item.kind === "constant") {
      const value = evaluator.evaluateConstant(item);
      outLines.push(
        `Definition ${mangleGallina("d", item.name.text)} : ${gallinaType(item.valueType)} := ${gallinaStaticValue(value)}.`
      );
      continue;
    }
    const sig = functions.get(item.name.text);
    const paramEnv = new Map();
    const binders = [];
    for (let i = 0; i < item.parameters.length; i += 1) {
      const [pName, pType] = item.parameters[i];
      const isConstParam = item.constParameters.has(pName.text);
      paramEnv.set(pName.text, [pType, null, sig.parameterIds[i], isConstParam]);
      binders.push(`(${mangleGallina("v", pName.text)} : ${gallinaType(pType)})`);
    }
    const bodyEnv = new Map(paramEnv);
    for (const [cName] of evaluator.constants.entries()) {
      bodyEnv.delete(cName);
    }
    const immutableSet = new Set([
      ...paramEnv.keys(),
      ...evaluator.constants.keys(),
    ]);
    const bodyRendered = checkPureBlock(
      item.body,
      bodyEnv,
      immutableSet,
      item.result,
      evaluator.constants,
      functions,
      evaluator,
      2,
      facts
    );
    if (item.isConst) {
      const sample = new Map();
      for (const [pName, pType] of item.parameters) {
        sample.set(pName.text, [pType, pType === "Nat" ? 0n : false, -1]);
      }
      const probe = new PureStaticEvaluator(evaluator.constants, functions, constFunctions);
      const val = probe.evalBlock(item.body, sample, new Set(), false);
      const actual = typeof val === "boolean" ? "bool" : "Nat";
      if (actual !== item.result) {
        throw new VelaError(
          "type",
          item.name.site.line,
          item.name.site.column,
          `return value of '${item.name.text}' has type ${actual}, expected ${item.result}`
        );
      }
    }
    if (binders.length > 0) {
      outLines.push(
        `Definition ${mangleGallina("d", item.name.text)} ${binders.join(" ")} : ${gallinaType(item.result)} :=`,
        `${bodyRendered}.`
      );
    } else {
      outLines.push(
        `Definition ${mangleGallina("d", item.name.text)} : ${gallinaType(item.result)} := ${bodyRendered.trim()}.`
      );
    }
  }
  outLines.push(`End ${mangledModule}.`, "");
  const gallina = outLines.join("\n");
  if (utf8Bytes(gallina).length > MAX_EMITTED_GALLINA_BYTES) {
    throw new VelaError(
      "limit",
      parsed.name.site.line,
      parsed.name.site.column,
      `emitted Gallina exceeds ${MAX_EMITTED_GALLINA_BYTES} bytes`
    );
  }
  return {
    module: parsed.name.text,
    gallina,
    parsed,
    evaluator,
    facts: facts ? facts.result() : null,
  };
}

function pureEvaluate(sourceText, expressionText, valueType) {
  const { evaluator } = runPureTranslate(sourceText, false);
  if (valueType !== "Nat" && valueType !== "bool") {
    throw new VelaError("type", 1, 1, "expression: expected Nat or bool result type");
  }
  if (typeof expressionText !== "string") {
    throw new VelaError("syntax", 1, 1, "expression: expected UTF-8 text");
  }
  const rawBytes = utf8Bytes(expressionText);
  if (rawBytes.length > MAX_CONSOLE_EXPRESSION_BYTES) {
    throw new VelaError(
      "limit",
      1,
      1,
      `expression: exceeds ${MAX_CONSOLE_EXPRESSION_BYTES} bytes`
    );
  }
  try {
    const tokens = pureTokenize(expressionText, { allowSemicolon: false });
    if (tokens.length === 1) {
      throw new VelaError("syntax", 1, 1, "expected an expression");
    }
    const parser = new PureParser(tokens);
    const expr = parser.parseExpression();
    if (parser.current.kind !== "eof") {
      throw new VelaError(
        "syntax",
        parser.current.site.line,
        parser.current.site.column,
        `unexpected '${parser.current.text}' after expression`
      );
    }
    const probe = new PureStaticEvaluator(
      evaluator.constants,
      evaluator.functions,
      evaluator.constFunctions
    );
    const value = probe.evalExpr(expr, new Map(), new Set(), false);
    const actual = typeof value === "boolean" ? "bool" : "Nat";
    if (actual !== valueType) {
      throw new VelaError(
        "type",
        expr.site.line,
        expr.site.column,
        `expression has type ${actual}, expected ${valueType}`
      );
    }
    return {
      valueType,
      value: typeof value === "boolean" ? (value ? "true" : "false") : value.toString(),
    };
  } catch (err) {
    if (err instanceof VelaError) {
      throw new VelaError(err.kind, err.line, err.column, `expression: ${err.message}`);
    }
    throw err;
  }
}

function isPascalCase(text) {
  return /^[A-Z][A-Za-z0-9]*$/.test(text);
}

function isCamelCase(text) {
  return /^[a-z][A-Za-z0-9]*$/.test(text);
}

function formatDecimalLiteral(text) {
  if (text.includes("_") || text.length < 5) {
    return text;
  }
  const groups = [];
  let end = text.length;
  while (end > 0) {
    const start = Math.max(0, end - 3);
    groups.push(text.slice(start, end));
    end = start;
  }
  groups.reverse();
  return groups.join("_");
}

function purePrecedence(item) {
  if (item.kind === "binary") {
    const op = String(item.value);
    if (op === "||") return 1;
    if (op === "&&") return 2;
    if (PURE_COMPARISON_OPERATORS.has(op)) return 3;
    if (op === "+" || op === "-") return 4;
    return 5;
  }
  if (item.kind === "unary") return 6;
  return 7;
}

function formatPureExpr(item) {
  if (item.kind === "group") {
    return formatPureExpr(item.children[0]);
  }
  if (item.kind === "nat") {
    return formatDecimalLiteral(String(item.value));
  }
  if (item.kind === "bool") {
    return item.value ? "true" : "false";
  }
  if (item.kind === "name") {
    return String(item.value);
  }
  if (item.kind === "call") {
    const renderedArgs = item.children.map((child, idx) => {
      const label = item.labels[idx];
      const val = formatPureExpr(child);
      return label ? `${label.text}: ${val}` : val;
    });
    return `${item.value}(${renderedArgs.join(", ")})`;
  }
  if (item.kind === "unary") {
    const child = item.children[0].kind === "group" ? item.children[0].children[0] : item.children[0];
    const text = formatPureExpr(child);
    return purePrecedence(child) < purePrecedence(item) ? `!(${text})` : `!${text}`;
  }
  const left = item.children[0].kind === "group" ? item.children[0].children[0] : item.children[0];
  const right = item.children[1].kind === "group" ? item.children[1].children[0] : item.children[1];
  const prec = purePrecedence(item);
  let leftText = formatPureExpr(left);
  let rightText = formatPureExpr(right);
  if (purePrecedence(left) < prec) {
    leftText = `(${leftText})`;
  }
  if (
    purePrecedence(right) < prec ||
    (purePrecedence(right) === prec && right.kind === "binary")
  ) {
    rightText = `(${rightText})`;
  }
  return `${leftText} ${item.value} ${rightText}`;
}

function formatPureBlock(block, indent) {
  const pad = " ".repeat(indent);
  const inner = " ".repeat(indent + 4);
  const lines = [`${pad}{`];
  for (const stmt of block.bindings) {
    if (stmt.kind === "constant") {
      lines.push(
        `${inner}const ${stmt.valueType} ${stmt.name.text} = ${formatPureExpr(stmt.value)};`
      );
    } else if (stmt.kind === "reassignment") {
      lines.push(`${inner}${stmt.name.text} = ${formatPureExpr(stmt.value)};`);
    } else {
      const prefix = stmt.explicitBinding ? "let " : "";
      const ann = stmt.annotation ? `${stmt.annotation} ` : "";
      lines.push(`${inner}${prefix}${ann}${stmt.name.text} = ${formatPureExpr(stmt.value)};`);
    }
  }
  if (block.terminal.kind === "return") {
    lines.push(`${inner}return ${formatPureExpr(block.terminal.value)};`);
  } else {
    lines.push(
      `${inner}if (${formatPureExpr(block.terminal.condition)})`,
      ...formatPureBlock(block.terminal.yes, indent + 4),
      `${inner}else`,
      ...formatPureBlock(block.terminal.no, indent + 4)
    );
  }
  lines.push(`${pad}}`);
  return lines;
}

function pureFormatSource(sourceText) {
  const { parsed, declarationSites } = parsePureModule(sourceText);
  runPureTranslate(sourceText, false);
  const lines = [`module ${parsed.name.text};`];
  for (const decl of parsed.declarations) {
    lines.push("");
    const siteKey = `${decl.name.site.line}:${decl.name.site.column}`;
    const pubSite = declarationSites.get(siteKey);
    const doc = pubSite ? extractPureDocumentation(sourceText, pubSite) : null;
    if (doc !== null) {
      for (const docLine of doc.split("\n")) {
        lines.push(docLine ? `/// ${docLine}` : "///");
      }
    }
    if (decl.kind === "constant") {
      lines.push(`public const ${decl.valueType} ${decl.name.text} = ${formatPureExpr(decl.value)};`);
      continue;
    }
    const params = decl.parameters
      .map(
        ([pName, pType]) =>
          `${decl.constParameters.has(pName.text) ? "const " : ""}${pType} ${pName.text}`
      )
      .join(", ");
    const qualifier = decl.isConst ? "const " : "";
    const sig = `public ${qualifier}${decl.result} ${decl.name.text}(${params})`;
    if (
      decl.bodyKind === "expression" &&
      decl.body.bindings.length === 0 &&
      decl.body.terminal.kind === "return"
    ) {
      lines.push(`${sig} => ${formatPureExpr(decl.body.terminal.value)};`);
    } else {
      lines.push(sig, ...formatPureBlock(decl.body, 0));
    }
  }
  return `${lines.join("\n")}\n`;
}

function unwrapPureGroup(expr) {
  let current = expr;
  while (current.kind === "group") {
    current = current.children[0];
  }
  return current;
}

function lintPureExpression(expr, findings) {
  if (
    expr.kind === "binary" &&
    expr.value === "==" &&
    expr.children.some((child) => unwrapPureGroup(child).kind === "bool")
  ) {
    findings.push({
      code: "VELA103",
      message: "Boolean literal comparison is redundant; prefer direct Boolean logic",
      line: expr.site.line,
      column: expr.site.column,
    });
  }
  for (const child of expr.children) {
    lintPureExpression(child, findings);
  }
}

function lintPureBinding(name, findings) {
  if (name.text !== "_" && !isCamelCase(name.text)) {
    findings.push({
      code: "VELA101",
      message: `binding '${name.text}' should use camelCase`,
      line: name.site.line,
      column: name.site.column,
    });
  }
}

function lintPureBlock(block, findings) {
  for (const stmt of block.bindings) {
    lintPureBinding(stmt.name, findings);
    lintPureExpression(stmt.value, findings);
  }
  if (block.terminal.kind === "return") {
    lintPureExpression(block.terminal.value, findings);
  } else {
    lintPureExpression(block.terminal.condition, findings);
    lintPureBlock(block.terminal.yes, findings);
    lintPureBlock(block.terminal.no, findings);
  }
}

function pureLintSource(sourceText) {
  const { parsed, declarationSites } = parsePureModule(sourceText);
  runPureTranslate(sourceText, false);
  const findings = [];
  for (const decl of parsed.declarations) {
    const siteKey = `${decl.name.site.line}:${decl.name.site.column}`;
    const pubSite = declarationSites.get(siteKey);
    const doc = pubSite ? extractPureDocumentation(sourceText, pubSite) : null;
    if (!isPascalCase(decl.name.text)) {
      findings.push({
        code: "VELA100",
        message: `public member '${decl.name.text}' should use PascalCase`,
        line: decl.name.site.line,
        column: decl.name.site.column,
      });
    }
    if (doc === null) {
      findings.push({
        code: "VELA102",
        message: `public member '${decl.name.text}' should have a /// documentation comment`,
        line: decl.name.site.line,
        column: decl.name.site.column,
      });
    }
    if (decl.kind === "constant") {
      lintPureExpression(decl.value, findings);
      continue;
    }
    for (const [pName] of decl.parameters) {
      lintPureBinding(pName, findings);
    }
    lintPureBlock(decl.body, findings);
  }
  findings.sort((a, b) => a.line - b.line || a.column - b.column || a.code.localeCompare(b.code));
  return findings;
}

function purePreviewBindings(sourceText) {
  const tokens = pureTokenize(sourceText);
  const parser = new PureParser(tokens);
  const parsed = parser.parseModule();
  runPureTranslate(sourceText, false);
  const insertOffsets = [];

  function walkBlock(block) {
    for (const stmt of block.bindings) {
      if (stmt.kind === "binding" && !stmt.explicitBinding) {
        let tokIdx = tokens.findIndex(
          (t) => t.site.line === stmt.site.line && t.site.column === stmt.site.column
        );
        if (tokIdx >= 0) {
          insertOffsets.push(tokens[tokIdx].offset);
        }
      }
    }
    if (block.terminal.kind === "conditional") {
      walkBlock(block.terminal.yes);
      walkBlock(block.terminal.no);
    }
  }

  for (const decl of parsed.declarations) {
    if (decl.kind === "function") {
      walkBlock(decl.body);
    }
  }
  if (insertOffsets.length === 0) {
    return sourceText;
  }
  insertOffsets.sort((a, b) => b - a);
  let updated = sourceText;
  for (const offset of insertOffsets) {
    updated = `${updated.slice(0, offset)}let ${updated.slice(offset)}`;
  }
  checkSourceText(updated);
  return updated;
}

function compareLspPos(a, b) {
  if (a.line !== b.line) return a.line - b.line;
  return a.character - b.character;
}

function projectPureInspection(sourceText, facts, method, position, includeDeclaration, reqRange) {
  const empty =
    method === "textDocument/references" ||
    method === "textDocument/documentSymbol" ||
    method === "textDocument/inlayHint"
      ? []
      : method === "textDocument/semanticTokens/full"
        ? { data: [] }
        : null;
  if (!facts || facts.status !== "ok") {
    return empty;
  }
  const symbols = facts.symbols.map((sym) => {
    const start = diagnosticLspPosition(sourceText, sym.line, sym.column);
    const end = diagnosticLspPosition(sourceText, sym.line, sym.column + sym.name.length);
    let typeHint = null;
    if (sym.kind === "variable" && sym.inferred !== false) {
      if (sym.detail === `${sym.name}: Nat`) typeHint = ": Nat";
      else if (sym.detail === `${sym.name}: bool`) typeHint = ": bool";
    }
    return {
      ...sym,
      start,
      end,
      typeHint,
    };
  });
  const occurrences = facts.occurrences.map((occ) => {
    const sym = symbols[occ.symbol];
    const start = diagnosticLspPosition(sourceText, occ.line, occ.column);
    const end = diagnosticLspPosition(sourceText, occ.line, occ.column + sym.name.length);
    return {
      symbol: occ.symbol,
      start,
      end,
      declaration: occ.declaration,
    };
  });

  if (method === "textDocument/semanticTokens/full") {
    const data = [];
    let prevLine = 0;
    let prevStart = 0;
    for (const occ of occurrences) {
      const sym = symbols[occ.symbol];
      const line = occ.start.line;
      const start = occ.start.character;
      const tokenType = sym.kind === "function" ? 0 : sym.kind === "parameter" ? 1 : 2;
      const modifiers = (occ.declaration ? 1 : 0) | (sym.kind === "function" ? 0 : 2);
      data.push(
        line - prevLine,
        line === prevLine ? start - prevStart : start,
        occ.end.character - start,
        tokenType,
        modifiers
      );
      prevLine = line;
      prevStart = start;
    }
    return { data };
  }

  if (method === "textDocument/inlayHint") {
    const [first, last] = reqRange;
    return symbols
      .filter(
        (sym) =>
          sym.typeHint !== null &&
          compareLspPos(first, sym.start) <= 0 &&
          compareLspPos(sym.end, last) <= 0
      )
      .map((sym) => ({
        position: { line: sym.end.line, character: sym.end.character },
        label: sym.typeHint,
        kind: 1,
      }));
  }

  if (method === "textDocument/documentSymbol") {
    const kinds = { function: 12, constant: 14, parameter: 13, variable: 13 };
    return symbols.map((sym) => ({
      name: sym.name,
      kind: kinds[sym.kind] || 13,
      location: {
        uri: DOCUMENT_URI,
        range: { start: sym.start, end: sym.end },
      },
    }));
  }

  const selected = occurrences.find(
    (occ) =>
      position &&
      compareLspPos(occ.start, position) <= 0 &&
      compareLspPos(position, occ.end) < 0
  );
  if (!selected) {
    return empty;
  }
  const sym = symbols[selected.symbol];
  if (method === "textDocument/hover") {
    const doc = sym.documentation ? `\n\n${sym.documentation}` : "";
    return {
      contents: {
        kind: "plaintext",
        value: `${sym.detail}${doc}\nVela pure prototype (unqualified)`,
      },
      range: { start: selected.start, end: selected.end },
    };
  }
  if (method === "textDocument/definition") {
    return {
      uri: DOCUMENT_URI,
      range: { start: sym.start, end: sym.end },
    };
  }
  return occurrences
    .filter((occ) => occ.symbol === selected.symbol && (includeDeclaration || !occ.declaration))
    .map((occ) => ({
      uri: DOCUMENT_URI,
      range: { start: occ.start, end: occ.end },
    }));
}

class BrowserLspSession {
  constructor() {
    this.initialized = false;
    this.document = null;
    this.cachedFacts = null;
  }

  handle(message) {
    const method = message.method;
    const hasId = Object.prototype.hasOwnProperty.call(message, "id");
    const id = message.id;
    const params = message.params || {};

    if (method === "initialize") {
      this.initialized = true;
      return [
        {
          jsonrpc: "2.0",
          id,
          result: {
            capabilities: {
              textDocumentSync: { openClose: true, change: 1 },
              hoverProvider: true,
              definitionProvider: true,
              referencesProvider: true,
              documentSymbolProvider: true,
              inlayHintProvider: true,
              documentFormattingProvider: true,
              semanticTokensProvider: {
                legend: {
                  tokenTypes: ["function", "parameter", "variable"],
                  tokenModifiers: ["declaration", "readonly"],
                },
                full: true,
              },
            },
            serverInfo: { name: "vela-lsp-browser", version: "0.1.0" },
          },
        },
      ];
    }
    if (method === "initialized" || method === "exit") {
      return [];
    }
    if (method === "shutdown") {
      return hasId ? [{ jsonrpc: "2.0", id, result: null }] : [];
    }
    if (method === "textDocument/didOpen") {
      const item = params.textDocument || {};
      this.document = { uri: item.uri, version: item.version, text: item.text };
      return [this.diagnose()];
    }
    if (method === "textDocument/didChange") {
      const item = params.textDocument || {};
      const changes = params.contentChanges || [];
      if (this.document && changes.length > 0 && item.version > this.document.version) {
        this.document = { uri: item.uri, version: item.version, text: changes[0].text };
        return [this.diagnose()];
      }
      this.cachedFacts = null;
      return [];
    }
    if (method === "textDocument/didClose") {
      const item = params.textDocument || {};
      this.document = null;
      this.cachedFacts = null;
      return [
        {
          jsonrpc: "2.0",
          method: "textDocument/publishDiagnostics",
          params: { uri: item.uri || DOCUMENT_URI, diagnostics: [] },
        },
      ];
    }
    if (method === "textDocument/formatting") {
      if (!this.document) {
        return [{ jsonrpc: "2.0", id, error: { code: -32602, message: "Document is not open" } }];
      }
      try {
        const formatted = pureFormatSource(this.document.text);
        if (formatted === this.document.text) {
          return [{ jsonrpc: "2.0", id, result: [] }];
        }
        return [
          {
            jsonrpc: "2.0",
            id,
            result: [
              {
                range: {
                  start: { line: 0, character: 0 },
                  end: endOfDocumentLspPosition(this.document.text),
                },
                newText: formatted,
              },
            ],
          },
        ];
      } catch {
        return [{ jsonrpc: "2.0", id, result: [] }];
      }
    }
    if (!this.document) {
      return [{ jsonrpc: "2.0", id, error: { code: -32602, message: "Document is not open" } }];
    }
    let position = null;
    let reqRange = null;
    if (params.position) {
      position = { line: params.position.line, character: params.position.character };
    }
    if (params.range) {
      reqRange = [params.range.start, params.range.end];
    }
    const includeDeclaration = Boolean(params.context && params.context.includeDeclaration);
    const result = projectPureInspection(
      this.document.text,
      this.cachedFacts,
      method,
      position,
      includeDeclaration,
      reqRange
    );
    return [{ jsonrpc: "2.0", id, result }];
  }

  diagnose() {
    if (!this.document) {
      return {
        jsonrpc: "2.0",
        method: "textDocument/publishDiagnostics",
        params: { uri: DOCUMENT_URI, diagnostics: [] },
      };
    }
    try {
      const res = runPureTranslate(this.document.text, true);
      this.cachedFacts = res.facts;
      return {
        jsonrpc: "2.0",
        method: "textDocument/publishDiagnostics",
        params: {
          uri: this.document.uri,
          version: this.document.version,
          diagnostics: [],
        },
      };
    } catch (err) {
      this.cachedFacts = null;
      const line = err instanceof VelaError ? err.line : 1;
      const col = err instanceof VelaError ? err.column : 1;
      const code = err instanceof VelaError ? err.kind : "internal";
      const msg = err instanceof VelaError ? err.message : String(err);
      const pos = diagnosticLspPosition(this.document.text, line, col);
      return {
        jsonrpc: "2.0",
        method: "textDocument/publishDiagnostics",
        params: {
          uri: this.document.uri,
          version: this.document.version,
          diagnostics: [
            {
              range: { start: pos, end: pos },
              severity: 1,
              source: "vela-lsp (unqualified)",
              code,
              message: msg,
            },
          ],
        },
      };
    }
  }
}

const MATH_MULTI_SYMBOLS = [
  "<==>",
  "==>",
  "..",
  "=>",
  "==",
  "!=",
  "<=",
  ">=",
  "&&",
  "||",
  "+=",
  "-=",
  "::",
];

const MATH_SINGLE_SYMBOLS = new Set([
  "{",
  "}",
  "(",
  ")",
  "[",
  "]",
  "<",
  ">",
  ",",
  ";",
  ":",
  ".",
  "=",
  "+",
  "-",
  "*",
  "/",
  "%",
  "!",
  "|",
  "^",
  "&",
  "~",
  "?",
  "@",
  "'",
]);

function parseRawStringLiteral(sourceText, startIndex, startLine, startCol) {
  let quoteCount = 0;
  while (sourceText[startIndex + quoteCount] === '"') {
    quoteCount += 1;
  }
  let idx = startIndex + quoteCount;
  if (sourceText[idx] === "\r" && sourceText[idx + 1] === "\n") {
    idx += 2;
  } else if (sourceText[idx] === "\n") {
    idx += 1;
  } else {
    throw new VelaError(
      "syntax",
      startLine,
      startCol,
      "raw string opening quotes must be followed immediately by a newline"
    );
  }
  const closingQuotes = '"'.repeat(quoteCount);
  const contentLines = [];
  let lineStart = idx;
  let currentLine = startLine + 1;
  while (idx <= sourceText.length) {
    if (idx === sourceText.length) {
      throw new VelaError("syntax", startLine, startCol, "unterminated raw string literal");
    }
    if (sourceText[idx] === "\r" || sourceText[idx] === "\n") {
      const rawLine = sourceText.slice(lineStart, idx);
      const trimmedLeft = rawLine.replace(/^[ \t]+/, "");
      if (trimmedLeft.startsWith(closingQuotes)) {
        const indentPrefix = rawLine.slice(0, rawLine.length - trimmedLeft.length);
        const dedented = contentLines.map((cl, lineOffset) => {
          if (cl.length === 0) return "";
          if (!cl.startsWith(indentPrefix)) {
            throw new VelaError(
              "syntax",
              startLine + 1 + lineOffset,
              1,
              "raw string content line has less indentation than closing quotes"
            );
          }
          return cl.slice(indentPrefix.length);
        });
        const textValue = dedented.join("\n");
        if (utf8Bytes(textValue).length > 256) {
          throw new VelaError(
            "limit",
            startLine,
            startCol,
            "string literal exceeds 256 UTF-8 bytes"
          );
        }
        const endIdx = lineStart + indentPrefix.length + quoteCount;
        const endCol = Array.from(indentPrefix).length + quoteCount + 1;
        return {
          value: textValue,
          endIndex: endIdx,
          endLine: currentLine,
          endCol,
        };
      }
      contentLines.push(rawLine);
      if (sourceText[idx] === "\r" && sourceText[idx + 1] === "\n") {
        idx += 2;
      } else {
        idx += 1;
      }
      lineStart = idx;
      currentLine += 1;
      continue;
    }
    const rawLine = sourceText.slice(lineStart);
    const newlinePos = rawLine.search(/\r|\n/);
    const lineSlice = newlinePos >= 0 ? rawLine.slice(0, newlinePos) : rawLine;
    const trimmedLeft = lineSlice.replace(/^[ \t]+/, "");
    if (trimmedLeft.startsWith(closingQuotes)) {
      const indentPrefix = lineSlice.slice(0, lineSlice.length - trimmedLeft.length);
      const dedented = contentLines.map((cl, lineOffset) => {
        if (cl.length === 0) return "";
        if (!cl.startsWith(indentPrefix)) {
          throw new VelaError(
            "syntax",
            startLine + 1 + lineOffset,
            1,
            "raw string content line has less indentation than closing quotes"
          );
        }
        return cl.slice(indentPrefix.length);
      });
      const textValue = dedented.join("\n");
      if (utf8Bytes(textValue).length > 256) {
        throw new VelaError(
          "limit",
          startLine,
          startCol,
          "string literal exceeds 256 UTF-8 bytes"
        );
      }
      const endIdx = lineStart + indentPrefix.length + quoteCount;
      const endCol = Array.from(indentPrefix).length + quoteCount + 1;
      return {
        value: textValue,
        endIndex: endIdx,
        endLine: currentLine,
        endCol,
      };
    }
    idx += 1;
  }
  throw new VelaError("syntax", startLine, startCol, "unterminated raw string literal");
}

function mathTokenize(sourceText, { allowSemicolon = true } = {}) {
  checkSourceText(sourceText);
  const tokens = [];
  let index = 0;
  let line = 1;
  let column = 1;

  while (index < sourceText.length) {
    const ch = sourceText[index];
    if (ch === " " || ch === "\t") {
      index += 1;
      column += 1;
      continue;
    }
    if (ch === "\r") {
      if (sourceText[index + 1] === "\n") index += 2;
      else index += 1;
      line += 1;
      column = 1;
      continue;
    }
    if (ch === "\n") {
      index += 1;
      line += 1;
      column = 1;
      continue;
    }
    if (sourceText.startsWith("//", index)) {
      while (index < sourceText.length && sourceText[index] !== "\r" && sourceText[index] !== "\n") {
        const cp = sourceText.codePointAt(index);
        index += cp > 0xffff ? 2 : 1;
        column += 1;
      }
      continue;
    }
    if (sourceText.startsWith("/*", index)) {
      let depth = 1;
      index += 2;
      column += 2;
      while (depth > 0 && index < sourceText.length) {
        if (sourceText.startsWith("/*", index)) {
          depth += 1;
          index += 2;
          column += 2;
        } else if (sourceText.startsWith("*/", index)) {
          depth -= 1;
          index += 2;
          column += 2;
        } else if (sourceText[index] === "\r") {
          if (sourceText[index + 1] === "\n") index += 2;
          else index += 1;
          line += 1;
          column = 1;
        } else if (sourceText[index] === "\n") {
          index += 1;
          line += 1;
          column = 1;
        } else {
          const cp = sourceText.codePointAt(index);
          index += cp > 0xffff ? 2 : 1;
          column += 1;
        }
      }
      if (depth > 0) {
        throw new VelaError("syntax", line, column, "unterminated block comment");
      }
      continue;
    }
    if (sourceText.startsWith('$"', index)) {
      const startSite = { line, column };
      index += 2;
      column += 2;
      let rawTemplate = "";
      while (index < sourceText.length && sourceText[index] !== '"') {
        if (sourceText[index] === "\r" || sourceText[index] === "\n") {
          throw new VelaError("syntax", startSite.line, startSite.column, "unterminated format string");
        }
        if (sourceText[index] === "\\") {
          rawTemplate += sourceText.slice(index, index + 2);
          index += 2;
          column += 2;
          continue;
        }
        const cp = sourceText.codePointAt(index);
        const step = cp > 0xffff ? 2 : 1;
        rawTemplate += sourceText.slice(index, index + step);
        index += step;
        column += 1;
      }
      if (sourceText[index] !== '"') {
        throw new VelaError("syntax", startSite.line, startSite.column, "unterminated format string");
      }
      index += 1;
      column += 1;
      tokens.push({ kind: "format", text: rawTemplate, site: startSite });
      continue;
    }
    if (sourceText.startsWith('"""', index)) {
      const startSite = { line, column };
      const rawRes = parseRawStringLiteral(sourceText, index, line, column);
      tokens.push({ kind: "string", text: rawRes.value, site: startSite });
      index = rawRes.endIndex;
      line = rawRes.endLine;
      column = rawRes.endCol;
      continue;
    }
    if (ch === '"') {
      const startSite = { line, column };
      index += 1;
      column += 1;
      let val = "";
      while (index < sourceText.length && sourceText[index] !== '"') {
        if (sourceText[index] === "\r" || sourceText[index] === "\n") {
          throw new VelaError("syntax", startSite.line, startSite.column, "unterminated string literal");
        }
        if (sourceText[index] === "\\") {
          const esc = sourceText[index + 1];
          const map = { n: "\n", r: "\r", t: "\t", '"': '"', "\\": "\\", "0": "\0" };
          if (map[esc] === undefined) {
            throw new VelaError("syntax", line, column, `invalid string escape '\\${esc || ""}'`);
          }
          val += map[esc];
          index += 2;
          column += 2;
          continue;
        }
        const cp = sourceText.codePointAt(index);
        const step = cp > 0xffff ? 2 : 1;
        val += sourceText.slice(index, index + step);
        index += step;
        column += 1;
      }
      if (sourceText[index] !== '"') {
        throw new VelaError("syntax", startSite.line, startSite.column, "unterminated string literal");
      }
      index += 1;
      column += 1;
      if (utf8Bytes(val).length > 256) {
        throw new VelaError(
          "limit",
          startSite.line,
          startSite.column,
          "string literal exceeds 256 UTF-8 bytes"
        );
      }
      tokens.push({ kind: "string", text: val, site: startSite });
      continue;
    }
    let matchedMulti = null;
    for (const sym of MATH_MULTI_SYMBOLS) {
      if (sourceText.startsWith(sym, index)) {
        matchedMulti = sym;
        break;
      }
    }
    if (matchedMulti) {
      tokens.push({ kind: "symbol", text: matchedMulti, site: { line, column } });
      index += matchedMulti.length;
      column += matchedMulti.length;
      continue;
    }
    if (MATH_SINGLE_SYMBOLS.has(ch)) {
      if (!allowSemicolon && ch === ";") {
        throw new VelaError("syntax", line, column, "unexpected ';'");
      }
      tokens.push({ kind: "symbol", text: ch, site: { line, column } });
      index += 1;
      column += 1;
      continue;
    }
    const rest = sourceText.slice(index);
    const numMatch =
      /^(?:0[xX][0-9A-Fa-f](?:_?[0-9A-Fa-f])*|0[bB][01](?:_?[01])*|[0-9](?:_?[0-9])*)/.exec(
        rest
      );
    if (numMatch) {
      const rawNum = numMatch[0];
      const suffixRest = rest.slice(rawNum.length);
      const suffixMatch = /^(?:u8|u16|u32|u64|usize|byte|i8|i16|i32|i64)?/.exec(suffixRest);
      const suffix = suffixMatch ? suffixMatch[0] : "";
      const after = rest[rawNum.length + suffix.length] || "";
      if (/[A-Za-z0-9_]/.test(after)) {
        throw new VelaError("syntax", line, column, "invalid numeric literal");
      }
      const cleaned = rawNum.replace(/_/g, "");
      if (cleaned.length > MAX_LITERAL_DIGITS) {
        throw new VelaError(
          "limit",
          line,
          column,
          `integer literal exceeds ${MAX_LITERAL_DIGITS} digits`
        );
      }
      tokens.push({ kind: "nat", text: rawNum, suffix, site: { line, column } });
      const totalLen = rawNum.length + suffix.length;
      index += totalLen;
      column += totalLen;
      continue;
    }
    const wordMatch = /^[A-Za-z_][A-Za-z0-9_]*/.exec(rest);
    if (wordMatch) {
      const word = wordMatch[0];
      tokens.push({ kind: "word", text: word, site: { line, column } });
      index += word.length;
      column += word.length;
      continue;
    }
    throw new VelaError("syntax", line, column, `unexpected character '${ch}'`);
  }
  tokens.push({ kind: "eof", text: "<eof>", site: { line, column } });
  return tokens;
}

function parseMathBigInt(text) {
  const cleaned = String(text).replace(/_/g, "");
  return BigInt(cleaned);
}

class MathParser {
  constructor(tokens) {
    this.tokens = tokens;
    this.index = 0;
    this.genericTypeBinders = [];
  }

  get current() {
    return this.tokens[this.index];
  }

  peek(offset = 1) {
    return this.tokens[Math.min(this.index + offset, this.tokens.length - 1)];
  }

  advance() {
    const tok = this.current;
    this.index = Math.min(this.index + 1, this.tokens.length - 1);
    return tok;
  }

  match(kind, text = null) {
    if (this.current.kind === kind && (text === null || this.current.text === text)) {
      return this.advance();
    }
    return null;
  }

  expect(kind, text = null, label = null) {
    const tok = this.match(kind, text);
    if (!tok) {
      const desc = label || (text ? `'${text}'` : kind);
      throw new VelaError(
        "syntax",
        this.current.site.line,
        this.current.site.column,
        `expected ${desc}, found '${this.current.text}'`
      );
    }
    return tok;
  }

  parseDottedName(role = "identifier") {
    const first = this.expect("word", null, role);
    const parts = [first.text];
    while (this.match("symbol", ".")) {
      parts.push(this.expect("word", null, role).text);
    }
    return { text: parts.join("."), site: first.site };
  }

  parseGenericParameters() {
    if (!this.match("symbol", "<")) return [];
    const params = [];
    if (!this.match("symbol", ">")) {
      while (true) {
        let mode = "type";
        let valueType = null;
        if (this.current.kind === "word" && (this.current.text === "ghost" || this.current.text === "const")) {
          mode = this.advance().text;
          valueType = this.parseType();
        } else if (this.current.kind === "word" && this.current.text === "region") {
          mode = "region";
          this.advance();
          this.match("symbol", "'");
        } else if (
          this.current.kind === "word" &&
          this.peek().kind === "word" &&
          this.peek().text !== "where"
        ) {
          mode = "value";
          valueType = this.parseType();
        }
        const nameTok = this.expect("word", null, "generic parameter name");
        if (mode === "type") {
          this.genericTypeBinders.push({ text: nameTok.text, site: nameTok.site });
        }
        params.push({ mode, valueType, name: nameTok.text, site: nameTok.site });
        if (this.match("symbol", ">")) break;
        this.expect("symbol", ",");
        if (this.match("symbol", ">")) break;
      }
    }
    return params;
  }

  parseType() {
    const site = this.current.site;
    if (this.current.kind === "word" && ["in", "ref", "out", "owned", "ghost", "tracked"].includes(this.current.text)) {
      const mode = this.advance().text;
      if (this.match("symbol", "<")) {
        this.match("symbol", "'");
        this.parseDottedName("region");
        this.expect("symbol", ">");
      }
      const inner = this.parseType();
      return { kind: "mode_type", mode, inner, site };
    }
    if (this.current.kind === "word" && (this.current.text === "Fn" || this.current.text === "FnMut" || this.current.text === "FnOnce")) {
      const fnKind = this.advance().text;
      this.expect("symbol", "(");
      const params = [];
      if (!this.match("symbol", ")")) {
        while (true) {
          const pType = this.parseType();
          let pName = null;
          if (this.current.kind === "word") {
            pName = this.advance().text;
          }
          params.push({ type: pType, name: pName });
          if (this.match("symbol", ")")) break;
          this.expect("symbol", ",");
          if (this.match("symbol", ")")) break;
        }
      }
      if (this.match("symbol", "-") && this.match("symbol", ">")) {
        const result = this.parseType();
        return { kind: "fn_type", fnKind, params, result, site };
      }
      return { kind: "fn_type", fnKind, params, result: { kind: "named_type", name: "Unit", args: [], site }, site };
    }
    if (this.match("symbol", "(")) {
      if (this.match("symbol", ")")) {
        return { kind: "named_type", name: "Unit", args: [], site };
      }
      const items = [this.parseType()];
      while (this.match("symbol", ",")) {
        if (this.current.text === ")") break;
        items.push(this.parseType());
      }
      this.expect("symbol", ")");
      return items.length === 1 ? items[0] : { kind: "tuple_type", items, site };
    }
    const nameTok = this.expect("word", null, "type name");
    let name = nameTok.text;
    while (this.match("symbol", ".")) {
      name = `${name}.${this.expect("word", null, "type member").text}`;
    }
    const args = [];
    if (this.match("symbol", "<")) {
      if (!this.match("symbol", ">")) {
        while (true) {
          if (this.match("symbol", "'")) {
            const reg = this.parseDottedName("region");
            args.push({ kind: "region_arg", name: reg.text, site: reg.site });
          } else if (this.current.kind === "nat") {
            const natTok = this.advance();
            args.push({ kind: "nat_index", value: parseMathBigInt(natTok.text), site: natTok.site });
          } else if (
            this.current.kind === "word" &&
            this.peek().text === "("
          ) {
            const expr = this.parsePostfix();
            args.push({ kind: "expr_index", expr, site: expr.site });
          } else {
            const tArg = this.parseType();
            args.push(tArg);
          }
          if (this.match("symbol", ">")) break;
          this.expect("symbol", ",");
          if (this.match("symbol", ">")) break;
        }
      }
    }
    return { kind: "named_type", name, args, site };
  }

  parseParameters() {
    this.expect("symbol", "(");
    const params = [];
    if (!this.match("symbol", ")")) {
      while (true) {
        let mode = "value";
        if (
          this.current.kind === "word" &&
          ["const", "ghost", "tracked", "in", "ref", "out", "owned"].includes(this.current.text)
        ) {
          mode = this.advance().text;
        }
        if (this.current.kind === "word" && this.current.text === "this") {
          const thisTok = this.advance();
          params.push({
            mode,
            type: { kind: "named_type", name: "Self", args: [], site: thisTok.site },
            name: "this",
            site: thisTok.site,
          });
        } else {
          const pType = this.parseType();
          const pName = this.expect("word", null, "parameter name");
          params.push({ mode, type: pType, name: pName.text, site: pName.site });
        }
        if (this.match("symbol", ")")) break;
        this.expect("symbol", ",");
        if (this.match("symbol", ")")) break;
      }
    }
    return params;
  }

  parsePattern() {
    const tok = this.current;
    if (tok.kind === "word" && tok.text === "_") {
      this.advance();
      return { kind: "wildcard", site: tok.site };
    }
    if (tok.kind === "nat") {
      this.advance();
      return { kind: "nat_pat", value: parseMathBigInt(tok.text), site: tok.site };
    }
    if (tok.kind === "word" && (tok.text === "true" || tok.text === "false")) {
      this.advance();
      return { kind: "bool_pat", value: tok.text === "true", site: tok.site };
    }
    if (this.match("symbol", "(")) {
      const items = [];
      if (!this.match("symbol", ")")) {
        while (true) {
          items.push(this.parsePattern());
          if (this.match("symbol", ")")) break;
          this.expect("symbol", ",");
          if (this.match("symbol", ")")) break;
        }
      }
      return { kind: "tuple_pat", items, site: tok.site };
    }
    const nameTok = this.expect("word", null, "pattern");
    const isCtor = /^[A-Z]/.test(nameTok.text);
    if (this.match("symbol", "(")) {
      const args = [];
      if (!this.match("symbol", ")")) {
        while (true) {
          let label = null;
          if (this.current.kind === "word" && this.peek().text === ":") {
            label = this.advance().text;
            this.expect("symbol", ":");
          }
          const pat = this.parsePattern();
          args.push({ label, pattern: pat });
          if (this.match("symbol", ")")) break;
          this.expect("symbol", ",");
          if (this.match("symbol", ")")) break;
        }
      }
      return { kind: "ctor_pat", name: nameTok.text, args, site: nameTok.site };
    }
    if (isCtor) {
      return { kind: "ctor_pat", name: nameTok.text, args: [], site: nameTok.site };
    }
    return { kind: "var_pat", name: nameTok.text, site: nameTok.site };
  }

  parseProofBlock() {
    const site = this.expect("word", "proof").site;
    this.expect("symbol", "{");
    const steps = [];
    while (this.current.kind !== "eof" && !this.match("symbol", "}")) {
      if (this.match("word", "calc")) {
        const calcSite = this.current.site;
        this.expect("symbol", "{");
        const calcAssertions = [];
        while (this.current.kind !== "eof" && !this.match("symbol", "}")) {
          const assertSite = this.expect("word", "assert").site;
          const prop = this.parseExpression();
          if (this.match("word", "by")) {
            if (this.current.text === "{") {
              this.skipBalancedBraces();
            } else {
              this.parseExpression();
            }
          }
          this.expect("symbol", ";");
          calcAssertions.push({ prop, site: assertSite });
        }
        steps.push({ kind: "calc", assertions: calcAssertions, site: calcSite });
        continue;
      }
      const assertSite = this.expect("word", "assert").site;
      const prop = this.parseExpression();
      if (this.match("word", "by")) {
        if (this.current.text === "{") {
          this.skipBalancedBraces();
        } else {
          this.parseExpression();
        }
      }
      this.expect("symbol", ";");
      steps.push({ kind: "assert", prop, site: assertSite });
    }
    return { kind: "proof", steps, site };
  }

  skipBalancedBraces() {
    this.expect("symbol", "{");
    let depth = 1;
    while (depth > 0 && this.current.kind !== "eof") {
      if (this.current.text === "{") depth += 1;
      else if (this.current.text === "}") depth -= 1;
      this.advance();
    }
  }

  parseContractClauses() {
    const requires = [];
    const ensures = [];
    let decreases = null;
    while (
      this.current.kind === "word" &&
      ["where", "requires", "ensures", "restores", "decreases", "effects"].includes(
        this.current.text
      )
    ) {
      const kw = this.advance();
      if (kw.text === "where") {
        this.parseDottedName("constraint");
        if (this.match("symbol", "(")) {
          while (this.current.kind !== "eof" && !this.match("symbol", ")")) {
            this.advance();
          }
        }
      } else if (kw.text === "effects") {
        while (
          this.current.kind !== "eof" &&
          !["requires", "ensures", "restores", "decreases", "proof", "{", "=>", ";"].includes(
            this.current.text
          )
        ) {
          this.advance();
        }
      } else if (kw.text === "requires") {
        requires.push({ expr: this.parseExpression(), site: kw.site });
      } else if (kw.text === "ensures" || kw.text === "restores") {
        ensures.push({ expr: this.parseExpression(), site: kw.site });
      } else if (kw.text === "decreases") {
        decreases = this.parseExpression();
      }
    }
    return { requires, ensures, decreases };
  }

  parseModule() {
    this.expect("word", "module");
    const modName = this.parseDottedName("module name");
    this.expect("symbol", ";");
    const declarations = [];
    while (this.current.kind !== "eof") {
      if (this.match("word", "import")) {
        const impName = this.parseDottedName("imported module");
        this.expect("symbol", ";");
        declarations.push({ kind: "import", name: impName.text, site: impName.site });
        continue;
      }
      let visibility = "public";
      if (
        this.current.kind === "word" &&
        (this.current.text === "public" || this.current.text === "private")
      ) {
        visibility = this.advance().text;
      } else {
        throw new VelaError(
          "syntax",
          this.current.site.line,
          this.current.site.column,
          `expected 'public' or 'private' declaration, found '${this.current.text}'`
        );
      }
      if (this.match("word", "record")) {
        const nameTok = this.expect("word", null, "record name");
        const generics = this.parseGenericParameters();
        const fields = this.parseParameters();
        const invariants = [];
        while (this.match("word", "invariant")) {
          const invName = this.expect("word", null, "invariant name");
          this.expect("symbol", ":");
          const invExpr = this.parseExpression();
          invariants.push({ name: invName.text, expr: invExpr, site: invName.site });
        }
        const properties = [];
        if (this.match("symbol", "{")) {
          while (this.current.kind !== "eof" && !this.match("symbol", "}")) {
            if (this.current.text === "public" || this.current.text === "private") {
              this.advance();
            }
            const propType = this.parseType();
            const propName = this.expect("word", null, "property name");
            this.expect("symbol", "=>");
            const propExpr = this.parseExpression();
            this.expect("symbol", ";");
            properties.push({
              name: propName.text,
              type: propType,
              expr: propExpr,
              site: propName.site,
            });
          }
        } else {
          this.expect("symbol", ";");
        }
        declarations.push({
          kind: "record",
          visibility,
          name: nameTok.text,
          generics,
          fields,
          invariants,
          properties,
          site: nameTok.site,
        });
        continue;
      }
      if (this.match("word", "union") || this.match("word", "inductive")) {
        const nameTok = this.expect("word", null, "union name");
        const generics = this.parseGenericParameters();
        this.expect("symbol", "{");
        const cases = [];
        while (this.current.kind !== "eof" && !this.match("symbol", "}")) {
          const caseName = this.expect("word", null, "union case");
          const caseFields = this.parseParameters();
          this.expect("symbol", ";");
          cases.push({ name: caseName.text, fields: caseFields, site: caseName.site });
        }
        declarations.push({
          kind: "union",
          visibility,
          name: nameTok.text,
          generics,
          cases,
          site: nameTok.site,
        });
        continue;
      }
      if (this.match("word", "interface") || this.match("word", "impl") || this.match("word", "struct")) {
        const kw = this.tokens[this.index - 1];
        const genericsBefore = this.parseGenericParameters();
        const nameTok = this.parseDottedName("declaration name");
        const genericsAfter = this.parseGenericParameters();
        this.skipBalancedBraces();
        declarations.push({
          kind: kw.text,
          visibility,
          name: nameTok.text,
          generics: [...genericsBefore, ...genericsAfter],
          site: nameTok.site,
        });
        continue;
      }
      if (this.match("word", "theorem") || this.match("word", "lemma")) {
        const role = this.tokens[this.index - 1].text;
        const nameTok = this.expect("word", null, `${role} name`);
        const generics = this.parseGenericParameters();
        const parameters = this.parseParameters();
        const contracts = this.parseContractClauses();
        const proof = this.current.text === "proof" ? this.parseProofBlock() : null;
        declarations.push({
          kind: "lemma",
          role,
          visibility,
          name: nameTok.text,
          generics,
          parameters,
          contracts,
          proof,
          site: nameTok.site,
        });
        continue;
      }
      const isConst = Boolean(this.match("word", "const"));
      const isDefinition = Boolean(this.match("word", "definition"));
      const returnType = this.parseType();
      const nameTok = this.expect("word", null, "declaration name");
      if (isConst && this.match("symbol", "=")) {
        const value = this.parseExpression();
        this.expect("symbol", ";");
        declarations.push({
          kind: "constant",
          visibility,
          name: nameTok.text,
          valueType: returnType,
          value,
          site: nameTok.site,
        });
        continue;
      }
      const generics = this.parseGenericParameters();
      const parameters = this.parseParameters();
      const contracts = this.parseContractClauses();
      const proof = this.current.text === "proof" ? this.parseProofBlock() : null;
      let body = null;
      if (this.match("symbol", "=>")) {
        const expr = this.parseExpression();
        this.expect("symbol", ";");
        body = { kind: "expr_body", expr, site: expr.site };
      } else if (this.current.text === "{") {
        body = this.parseBlock();
      } else {
        this.expect("symbol", ";");
      }
      declarations.push({
        kind: isDefinition ? "definition" : "function",
        visibility,
        isConst,
        name: nameTok.text,
        generics,
        parameters,
        returnType,
        contracts,
        proof,
        body,
        site: nameTok.site,
      });
    }
    return {
      name: modName.text,
      site: modName.site,
      declarations,
      genericTypeBinders: this.genericTypeBinders,
    };
  }

  parseBlock() {
    const site = this.expect("symbol", "{").site;
    const statements = [];
    while (this.current.kind !== "eof" && !this.match("symbol", "}")) {
      statements.push(this.parseStatement());
    }
    return { kind: "block", statements, site };
  }

  parseStatement() {
    const tok = this.current;
    if (this.match("word", "return")) {
      if (this.match("symbol", ";")) {
        return { kind: "return", value: { kind: "unit", site: tok.site }, site: tok.site };
      }
      const value = this.parseExpression();
      this.expect("symbol", ";");
      return { kind: "return", value, site: tok.site };
    }
    if (this.match("word", "if")) {
      this.expect("symbol", "(");
      const condition = this.parseExpression();
      this.expect("symbol", ")");
      const thenBranch = this.parseBlock();
      let elseBranch = null;
      if (this.match("word", "else")) {
        elseBranch = this.current.text === "if" ? { kind: "block", statements: [this.parseStatement()], site: this.current.site } : this.parseBlock();
      }
      return { kind: "if_stmt", condition, thenBranch, elseBranch, site: tok.site };
    }
    if (this.match("word", "match")) {
      this.expect("symbol", "(");
      const scrutinee = this.parseExpression();
      this.expect("symbol", ")");
      this.expect("symbol", "{");
      const arms = [];
      while (this.current.kind !== "eof" && !this.match("symbol", "}")) {
        const pattern = this.parsePattern();
        this.expect("symbol", "=>");
        const armBody = this.current.text === "{" ? this.parseBlock() : { kind: "expr_body", expr: this.parseExpression(), site: this.current.site };
        this.match("symbol", ",");
        arms.push({ pattern, body: armBody });
      }
      this.match("symbol", ";");
      return { kind: "match_stmt", scrutinee, arms, site: tok.site };
    }
    if (this.match("word", "foreach")) {
      this.expect("symbol", "(");
      this.match("word", "let");
      this.match("word", "in");
      this.match("word", "ref");
      const binder = this.expect("word", null, "loop variable");
      this.expect("word", "in");
      const rangeExpr = this.parseExpression();
      this.expect("symbol", ")");
      while (this.match("word", "invariant")) {
        this.parseExpression();
      }
      const body = this.parseBlock();
      return { kind: "foreach_stmt", binder: binder.text, range: rangeExpr, body, site: tok.site };
    }
    if (this.match("word", "while")) {
      this.expect("symbol", "(");
      const condition = this.parseExpression();
      this.expect("symbol", ")");
      while (this.match("word", "invariant") || this.match("word", "decreases")) {
        this.parseExpression();
      }
      const body = this.parseBlock();
      return { kind: "while_stmt", condition, body, site: tok.site };
    }
    if (this.match("word", "open")) {
      if (this.match("symbol", "(")) {
        while (this.current.kind !== "eof" && !this.match("symbol", ")")) {
          this.advance();
        }
      }
      if (this.match("word", "lifts")) {
        while (this.current.kind !== "eof" && this.current.text !== "{") {
          this.advance();
        }
      }
      const body = this.parseBlock();
      return { kind: "open_stmt", body, site: tok.site };
    }
    if (
      this.current.kind === "word" &&
      ["let", "var", "const"].includes(this.current.text)
    ) {
      const kw = this.advance();
      const savedIdx = this.index;
      if (
        kw.text === "let" &&
        this.current.kind === "word" &&
        /^[A-Z]/.test(this.current.text) &&
        (this.peek().text === "(" || this.peek().text === "=")
      ) {
        const pattern = this.parsePattern();
        if (this.match("symbol", "=")) {
          const value = this.parseExpression();
          let elseBlock = null;
          if (this.match("word", "else")) {
            elseBlock = this.parseBlock();
          }
          this.match("symbol", ";");
          return {
            kind: "let_pattern",
            pattern,
            value,
            elseBlock,
            site: kw.site,
          };
        }
        this.index = savedIdx;
      }
      let annotation = null;
      if (this.current.kind === "word" && this.current.text === "_") {
        this.advance();
        this.expect("symbol", "=");
        const value = this.parseExpression();
        this.expect("symbol", ";");
        return { kind: "local", role: kw.text, annotation: null, name: "_", value, site: kw.site };
      }
      if (
        this.current.kind === "word" &&
        (this.peek().kind === "word" || this.peek().text === "<")
      ) {
        annotation = this.parseType();
      }
      const nameTok = this.expect("word", null, "local variable name");
      this.expect("symbol", "=");
      const value = this.parseExpression();
      this.expect("symbol", ";");
      return {
        kind: "local",
        role: kw.text,
        annotation,
        name: nameTok.text,
        value,
        site: kw.site,
      };
    }
    const lhs = this.parseExpression();
    if (
      this.current.kind === "symbol" &&
      ["=", "+=", "-="].includes(this.current.text)
    ) {
      const op = this.advance();
      const rhs = this.parseExpression();
      this.expect("symbol", ";");
      return { kind: "assign", op: op.text, target: lhs, value: rhs, site: op.site };
    }
    this.expect("symbol", ";");
    return { kind: "expr_stmt", expr: lhs, site: lhs.site };
  }

  parseExpression() {
    const tok = this.current;
    if (this.match("word", "if")) {
      this.expect("symbol", "(");
      const condition = this.parseExpression();
      this.expect("symbol", ")");
      const thenExpr = this.parseExpression();
      this.expect("word", "else");
      const elseExpr = this.parseExpression();
      return { kind: "if_expr", condition, thenExpr, elseExpr, site: tok.site };
    }
    if (this.match("word", "forall") || this.match("word", "exists")) {
      const qKind = tok.text;
      const params = this.parseParameters();
      this.expect("symbol", "=>");
      const body = this.parseExpression();
      return { kind: "quantifier", qKind, params, body, site: tok.site };
    }
    if (this.isLambdaStart()) {
      return this.parseLambda();
    }
    return this.parseImplication();
  }

  isLambdaStart() {
    if (this.current.kind === "word" && this.peek().text === "=>") {
      return true;
    }
    if (this.current.text !== "(") return false;
    let depth = 0;
    for (let i = this.index; i < this.tokens.length; i += 1) {
      if (this.tokens[i].text === "(") depth += 1;
      else if (this.tokens[i].text === ")") {
        depth -= 1;
        if (depth === 0) {
          return this.tokens[i + 1] && this.tokens[i + 1].text === "=>";
        }
      }
    }
    return false;
  }

  parseLambda() {
    const site = this.current.site;
    if (this.current.kind === "word") {
      const pName = this.advance();
      this.expect("symbol", "=>");
      const body = this.parseExpression();
      return {
        kind: "lambda",
        params: [{ mode: "value", type: null, name: pName.text, site: pName.site }],
        body,
        site,
      };
    }
    const params = this.parseParameters();
    this.expect("symbol", "=>");
    const body = this.parseExpression();
    return { kind: "lambda", params, body, site };
  }

  parseImplication() {
    let left = this.parseDisjunction();
    if (
      this.current.kind === "symbol" &&
      (this.current.text === "==>" || this.current.text === "<==>")
    ) {
      const op = this.advance();
      const right = this.parseImplication();
      return { kind: "binary", op: op.text, left, right, site: op.site };
    }
    return left;
  }

  parseDisjunction() {
    let left = this.parseConjunction();
    while (this.current.kind === "symbol" && this.current.text === "||") {
      const op = this.advance();
      left = { kind: "binary", op: op.text, left, right: this.parseConjunction(), site: op.site };
    }
    return left;
  }

  parseConjunction() {
    let left = this.parseComparison();
    while (this.current.kind === "symbol" && this.current.text === "&&") {
      const op = this.advance();
      left = { kind: "binary", op: op.text, left, right: this.parseComparison(), site: op.site };
    }
    return left;
  }

  parseComparison() {
    let left = this.parseRange();
    if (this.current.kind === "word" && this.current.text === "is") {
      const isTok = this.advance();
      const pattern = this.parsePattern();
      return { kind: "is_expr", target: left, pattern, site: isTok.site };
    }
    if (
      this.current.kind === "symbol" &&
      PURE_COMPARISON_OPERATORS.has(this.current.text)
    ) {
      const op = this.advance();
      const right = this.parseRange();
      return { kind: "binary", op: op.text, left, right, site: op.site };
    }
    return left;
  }

  parseRange() {
    const left = this.parseAdditive();
    if (this.current.kind === "symbol" && this.current.text === "..") {
      const op = this.advance();
      const right = this.parseAdditive();
      return { kind: "range", low: left, high: right, site: op.site };
    }
    return left;
  }

  parseAdditive() {
    let left = this.parseMultiplicative();
    while (
      this.current.kind === "symbol" &&
      (this.current.text === "+" || this.current.text === "-")
    ) {
      const op = this.advance();
      left = {
        kind: "binary",
        op: op.text,
        left,
        right: this.parseMultiplicative(),
        site: op.site,
      };
    }
    return left;
  }

  parseMultiplicative() {
    let left = this.parseWithUpdate();
    while (
      this.current.kind === "symbol" &&
      (this.current.text === "*" || this.current.text === "/" || this.current.text === "%")
    ) {
      const op = this.advance();
      left = { kind: "binary", op: op.text, left, right: this.parseWithUpdate(), site: op.site };
    }
    return left;
  }

  parseWithUpdate() {
    let base = this.parseUnary();
    while (this.current.kind === "word" && this.current.text === "with") {
      const withTok = this.advance();
      this.expect("symbol", "{");
      const updates = [];
      if (!this.match("symbol", "}")) {
        while (true) {
          const fieldTok = this.expect("word", null, "field name");
          this.expect("symbol", "=");
          const value = this.parseExpression();
          updates.push({ field: fieldTok.text, value, site: fieldTok.site });
          if (this.match("symbol", "}")) break;
          this.expect("symbol", ",");
          if (this.match("symbol", "}")) break;
        }
      }
      base = { kind: "with_update", base, updates, site: withTok.site };
    }
    return base;
  }

  parseUnary() {
    if (
      this.current.kind === "symbol" &&
      (this.current.text === "!" || this.current.text === "-")
    ) {
      const op = this.advance();
      return { kind: "unary", op: op.text, operand: this.parseUnary(), site: op.site };
    }
    if (
      this.current.kind === "word" &&
      ["in", "ref", "out", "move"].includes(this.current.text)
    ) {
      const modeTok = this.advance();
      return { kind: "loan_arg", mode: modeTok.text, operand: this.parseUnary(), site: modeTok.site };
    }
    return this.parsePostfix();
  }

  hasGenericCallAhead() {
    if (this.current.text !== "<") return false;
    let depth = 0;
    for (let i = this.index; i < this.tokens.length; i += 1) {
      const t = this.tokens[i].text;
      if (t === "<") depth += 1;
      else if (t === ">") {
        depth -= 1;
        if (depth === 0) {
          return this.tokens[i + 1] && this.tokens[i + 1].text === "(";
        }
      } else if ([";", "{", "}", "==", "!=", "<=", ">=", "&&", "||"].includes(t)) {
        return false;
      }
    }
    return false;
  }

  parsePostfix() {
    let target = this.parsePrimaryExpression();
    while (true) {
      if (this.match("symbol", ".")) {
        const memberTok = this.expect("word", null, "member name");
        target = { kind: "member", object: target, member: memberTok.text, site: memberTok.site };
        continue;
      }
      if (this.hasGenericCallAhead()) {
        const typeArgs = [];
        this.expect("symbol", "<");
        if (!this.match("symbol", ">")) {
          while (true) {
            if (this.current.kind === "nat") {
              const nt = this.advance();
              typeArgs.push({ kind: "nat_index", value: parseMathBigInt(nt.text), site: nt.site });
            } else {
              typeArgs.push(this.parseType());
            }
            if (this.match("symbol", ">")) break;
            this.expect("symbol", ",");
            if (this.match("symbol", ">")) break;
          }
        }
        const callArgs = this.parseCallArguments();
        target = {
          kind: "call",
          callee: target,
          typeArgs,
          args: callArgs,
          site: target.site,
        };
        continue;
      }
      if (this.current.text === "(") {
        const callArgs = this.parseCallArguments();
        target = {
          kind: "call",
          callee: target,
          typeArgs: [],
          args: callArgs,
          site: target.site,
        };
        continue;
      }
      if (this.match("symbol", "?")) {
        target = { kind: "try_expr", operand: target, site: target.site };
        continue;
      }
      break;
    }
    return target;
  }

  parseCallArguments() {
    this.expect("symbol", "(");
    const args = [];
    if (!this.match("symbol", ")")) {
      while (true) {
        let label = null;
        if (this.current.kind === "word" && this.peek().text === ":") {
          label = this.advance().text;
          this.expect("symbol", ":");
        }
        let mode = null;
        if (
          this.current.kind === "word" &&
          ["in", "ref", "out", "move"].includes(this.current.text)
        ) {
          mode = this.advance().text;
        }
        const value = this.parseExpression();
        args.push({ label, mode, value, site: value.site });
        if (this.match("symbol", ")")) break;
        this.expect("symbol", ",");
        if (this.match("symbol", ")")) break;
      }
    }
    return args;
  }

  parsePrimaryExpression() {
    const tok = this.current;
    if (tok.kind === "nat") {
      this.advance();
      return { kind: "nat", value: parseMathBigInt(tok.text), site: tok.site };
    }
    if (tok.kind === "string") {
      this.advance();
      return { kind: "string", value: tok.text, site: tok.site };
    }
    if (tok.kind === "format") {
      this.advance();
      return { kind: "format_string", template: tok.text, site: tok.site };
    }
    if (tok.kind === "word" && (tok.text === "true" || tok.text === "false")) {
      this.advance();
      return { kind: "bool", value: tok.text === "true", site: tok.site };
    }
    if (this.match("word", "match")) {
      this.expect("symbol", "(");
      const scrutinee = this.parseExpression();
      this.expect("symbol", ")");
      this.expect("symbol", "{");
      const arms = [];
      while (this.current.kind !== "eof" && !this.match("symbol", "}")) {
        const pattern = this.parsePattern();
        this.expect("symbol", "=>");
        const expr = this.parseExpression();
        this.match("symbol", ",");
        arms.push({ pattern, expr });
      }
      return { kind: "match_expr", scrutinee, arms, site: tok.site };
    }
    if (this.match("symbol", "(")) {
      if (this.match("symbol", ")")) {
        return { kind: "unit", site: tok.site };
      }
      const first = this.parseExpression();
      if (this.match("symbol", ",")) {
        const items = [first];
        while (this.current.text !== ")" && this.current.kind !== "eof") {
          items.push(this.parseExpression());
          if (!this.match("symbol", ",")) break;
        }
        this.expect("symbol", ")");
        return { kind: "tuple", items, site: tok.site };
      }
      this.expect("symbol", ")");
      return first;
    }
    if (tok.kind === "word") {
      this.advance();
      return { kind: "name", name: tok.text, site: tok.site };
    }
    throw new VelaError(
      "syntax",
      tok.site.line,
      tok.site.column,
      `expected expression, found '${tok.text}'`
    );
  }
}

function valuesEqual(a, b) {
  if (a === b) return true;
  if (typeof a !== typeof b || a === null || b === null) return false;
  if (typeof a === "object") {
    if (a.__kind !== b.__kind) return false;
    if (a.__kind === "vec") {
      if (a.length !== b.length || a.items.length !== b.items.length) return false;
      return a.items.every((item, idx) => valuesEqual(item, b.items[idx]));
    }
    if (a.__kind === "fin") {
      return a.index === b.index && a.bound === b.bound;
    }
    if (a.__kind === "record") {
      if (a.typeName !== b.typeName) return false;
      const keysA = Object.keys(a.fields);
      const keysB = Object.keys(b.fields);
      if (keysA.length !== keysB.length) return false;
      return keysA.every((k) => valuesEqual(a.fields[k], b.fields[k]));
    }
    if (a.__kind === "ctor") {
      if (a.name !== b.name || a.args.length !== b.args.length) return false;
      return a.args.every((arg, idx) => valuesEqual(arg, b.args[idx]));
    }
  }
  return false;
}

function parseFormatSegments(template, site) {
  const segments = [];
  let idx = 0;
  let literal = "";
  while (idx < template.length) {
    if (template.startsWith("{{", idx)) {
      literal += "{";
      idx += 2;
      continue;
    }
    if (template.startsWith("}}", idx)) {
      literal += "}";
      idx += 2;
      continue;
    }
    if (template[idx] === "{") {
      if (literal.length > 0) {
        segments.push({ kind: "text", value: literal });
        literal = "";
      }
      const closeIdx = template.indexOf("}", idx + 1);
      if (closeIdx < 0) {
        throw new VelaError("syntax", site.line, site.column, "unclosed '{' in format string");
      }
      const holeText = template.slice(idx + 1, closeIdx).trim();
      if (!holeText) {
        throw new VelaError("syntax", site.line, site.column, "empty hole in format string");
      }
      const holeTokens = mathTokenize(holeText, { allowSemicolon: false });
      const holeParser = new MathParser(holeTokens);
      const holeExpr = holeParser.parseExpression();
      if (holeParser.current.kind !== "eof") {
        throw new VelaError(
          "syntax",
          site.line,
          site.column,
          "invalid expression in format string hole"
        );
      }
      segments.push({ kind: "hole", expr: holeExpr });
      idx = closeIdx + 1;
      continue;
    }
    literal += template[idx];
    idx += 1;
  }
  if (literal.length > 0) {
    segments.push({ kind: "text", value: literal });
  }
  return segments;
}

class MathElaborator {
  constructor(parsedModule, sourceText) {
    this.module = parsedModule;
    this.sourceText = sourceText;
    this.records = new Map();
    this.unions = new Map();
    this.unionCtors = new Map();
    this.constants = new Map();
    this.callables = new Map();
    this.steps = 0;
  }

  step(site) {
    this.steps += 1;
    if (this.steps > 20000) {
      throw new VelaError(
        "limit",
        site ? site.line : 1,
        site ? site.column : 1,
        "mathematical reduction exceeded step limit"
      );
    }
  }

  evalTypeIndex(argNode, env) {
    if (!argNode) return null;
    if (argNode.kind === "nat_index") return argNode.value;
    if (argNode.kind === "named_type") {
      if (env.has(argNode.name)) {
        const v = env.get(argNode.name);
        if (typeof v === "bigint") return v;
      }
      if (this.constants.has(argNode.name)) {
        const v = this.constants.get(argNode.name);
        if (typeof v === "bigint") return v;
      }
    }
    if (argNode.kind === "expr_index") {
      const v = this.evalExpr(argNode.expr, env);
      if (typeof v === "bigint") return v;
    }
    return null;
  }

  matchPattern(pattern, value) {
    if (pattern.kind === "wildcard") {
      return { matched: true, bindings: new Map() };
    }
    if (pattern.kind === "var_pat") {
      return { matched: true, bindings: new Map([[pattern.name, value]]) };
    }
    if (pattern.kind === "nat_pat") {
      return { matched: value === pattern.value, bindings: new Map() };
    }
    if (pattern.kind === "bool_pat") {
      return { matched: value === pattern.value, bindings: new Map() };
    }
    if (pattern.kind === "ctor_pat") {
      if (pattern.name === "Zero") {
        if (typeof value === "bigint") {
          return { matched: value === 0n, bindings: new Map() };
        }
      }
      if (pattern.name === "Succ") {
        if (typeof value === "bigint") {
          if (value <= 0n || pattern.args.length !== 1) {
            return { matched: false, bindings: new Map() };
          }
          return this.matchPattern(pattern.args[0].pattern, value - 1n);
        }
      }
      if (value && typeof value === "object" && value.__kind === "record") {
        if (value.typeName !== pattern.name) {
          return { matched: false, bindings: new Map() };
        }
        const rec = this.records.get(pattern.name);
        if (!rec || pattern.args.length !== rec.fields.length) {
          throw new VelaError(
            "type",
            pattern.site.line,
            pattern.site.column,
            `pattern '${pattern.name}' expects ${rec ? rec.fields.length : 0} field(s)`
          );
        }
        const bindings = new Map();
        for (let i = 0; i < pattern.args.length; i += 1) {
          const arg = pattern.args[i];
          const expectedField = rec.fields[i].name;
          if (arg.label !== null && arg.label !== expectedField) {
            throw new VelaError(
              "type",
              pattern.site.line,
              pattern.site.column,
              `field pattern label '${arg.label}' must match '${expectedField}' in declaration order`
            );
          }
          const sub = this.matchPattern(arg.pattern, value.fields[expectedField]);
          if (!sub.matched) return { matched: false, bindings: new Map() };
          for (const [k, v] of sub.bindings.entries()) bindings.set(k, v);
        }
        return { matched: true, bindings };
      }
      if (value && typeof value === "object" && value.__kind === "ctor") {
        if (value.name !== pattern.name || value.args.length !== pattern.args.length) {
          return { matched: false, bindings: new Map() };
        }
        const bindings = new Map();
        for (let i = 0; i < pattern.args.length; i += 1) {
          const sub = this.matchPattern(pattern.args[i].pattern, value.args[i]);
          if (!sub.matched) return { matched: false, bindings: new Map() };
          for (const [k, v] of sub.bindings.entries()) bindings.set(k, v);
        }
        return { matched: true, bindings };
      }
      return { matched: false, bindings: new Map() };
    }
    return { matched: false, bindings: new Map() };
  }

  evalBlock(block, env) {
    if (block.kind === "expr_body") {
      return { returned: true, value: this.evalExpr(block.expr, env) };
    }
    const localEnv = new Map(env);
    for (const stmt of block.statements) {
      if (stmt.kind === "return") {
        return { returned: true, value: this.evalExpr(stmt.value, localEnv) };
      }
      if (stmt.kind === "local") {
        const val = this.evalExpr(stmt.value, localEnv);
        if (stmt.name !== "_") {
          localEnv.set(stmt.name, val);
        }
        continue;
      }
      if (stmt.kind === "let_pattern") {
        const val = this.evalExpr(stmt.value, localEnv);
        const matched = this.matchPattern(stmt.pattern, val);
        if (!matched.matched) {
          if (stmt.elseBlock) {
            const res = this.evalBlock(stmt.elseBlock, localEnv);
            if (res.returned) return res;
          }
          throw new VelaError(
            "type",
            stmt.site.line,
            stmt.site.column,
            "pattern binding did not match and else branch did not return"
          );
        }
        for (const [k, v] of matched.bindings.entries()) {
          localEnv.set(k, v);
        }
        continue;
      }
      if (stmt.kind === "if_stmt") {
        if (stmt.condition.kind === "is_expr") {
          const targetVal = this.evalExpr(stmt.condition.target, localEnv);
          const matched = this.matchPattern(stmt.condition.pattern, targetVal);
          if (matched.matched) {
            const branchEnv = new Map(localEnv);
            for (const [k, v] of matched.bindings.entries()) branchEnv.set(k, v);
            const res = this.evalBlock(stmt.thenBranch, branchEnv);
            if (res.returned) return res;
            for (const [k, v] of branchEnv.entries()) {
              if (localEnv.has(k) && !matched.bindings.has(k)) localEnv.set(k, v);
            }
          } else if (stmt.elseBranch) {
            const res = this.evalBlock(stmt.elseBranch, localEnv);
            if (res.returned) return res;
          }
          continue;
        }
        const cond = this.evalExpr(stmt.condition, localEnv);
        if (typeof cond !== "boolean") {
          throw new VelaError("type", stmt.site.line, stmt.site.column, "if condition must be bool");
        }
        if (cond) {
          const res = this.evalBlock(stmt.thenBranch, localEnv);
          if (res.returned) return res;
        } else if (stmt.elseBranch) {
          const res = this.evalBlock(stmt.elseBranch, localEnv);
          if (res.returned) return res;
        }
        continue;
      }
      if (stmt.kind === "match_stmt") {
        const scrut = this.evalExpr(stmt.scrutinee, localEnv);
        let matchedArm = false;
        for (const arm of stmt.arms) {
          const m = this.matchPattern(arm.pattern, scrut);
          if (m.matched) {
            matchedArm = true;
            const armEnv = new Map(localEnv);
            for (const [k, v] of m.bindings.entries()) armEnv.set(k, v);
            const res = this.evalBlock(arm.body, armEnv);
            if (res.returned) return res;
            for (const [k, v] of armEnv.entries()) {
              if (localEnv.has(k) && !m.bindings.has(k)) localEnv.set(k, v);
            }
            break;
          }
        }
        if (!matchedArm) {
          throw new VelaError("type", stmt.site.line, stmt.site.column, "non-exhaustive match");
        }
        continue;
      }
      if (stmt.kind === "foreach_stmt") {
        if (stmt.range.kind === "range") {
          const low = this.evalExpr(stmt.range.low, localEnv);
          const high = this.evalExpr(stmt.range.high, localEnv);
          if (typeof low === "bigint" && typeof high === "bigint") {
            for (let cur = low; cur < high; cur += 1n) {
              this.step(stmt.site);
              localEnv.set(stmt.binder, cur);
              const res = this.evalBlock(stmt.body, localEnv);
              if (res.returned) return res;
            }
          }
        }
        continue;
      }
      if (stmt.kind === "while_stmt") {
        while (true) {
          this.step(stmt.site);
          const cond = this.evalExpr(stmt.condition, localEnv);
          if (!cond) break;
          const res = this.evalBlock(stmt.body, localEnv);
          if (res.returned) return res;
        }
        continue;
      }
      if (stmt.kind === "open_stmt") {
        const res = this.evalBlock(stmt.body, localEnv);
        if (res.returned) return res;
        continue;
      }
      if (stmt.kind === "assign") {
        const rhs = this.evalExpr(stmt.value, localEnv);
        if (stmt.target.kind === "name") {
          const name = stmt.target.name;
          if (!localEnv.has(name)) {
            throw new VelaError("name", stmt.site.line, stmt.site.column, `unknown variable '${name}'`);
          }
          const prev = localEnv.get(name);
          if (stmt.op === "=") localEnv.set(name, rhs);
          else if (stmt.op === "+=") localEnv.set(name, prev + rhs);
          else if (stmt.op === "-=") localEnv.set(name, prev > rhs ? prev - rhs : 0n);
        }
        continue;
      }
      if (stmt.kind === "expr_stmt") {
        this.evalExpr(stmt.expr, localEnv);
      }
    }
    return { returned: false, value: { __kind: "unit" } };
  }

  evalExpr(expr, env) {
    this.step(expr.site);
    if (expr.kind === "nat") return expr.value;
    if (expr.kind === "bool") return expr.value;
    if (expr.kind === "string") return expr.value;
    if (expr.kind === "unit") return { __kind: "unit" };
    if (expr.kind === "format_string") {
      throw new VelaError(
        "type",
        expr.site.line,
        expr.site.column,
        "format template literals may only appear as the second argument to Format.Write"
      );
    }
    if (expr.kind === "tuple") {
      return { __kind: "tuple", items: expr.items.map((it) => this.evalExpr(it, env)) };
    }
    if (expr.kind === "name") {
      if (env.has(expr.name)) return env.get(expr.name);
      if (this.constants.has(expr.name)) return this.constants.get(expr.name);
      if (expr.name === "Zero") return 0n;
      if (expr.name === "None") return { __kind: "ctor", name: "None", args: [] };
      if (this.unionCtors.has(expr.name)) {
        const ctorInfo = this.unionCtors.get(expr.name);
        if (ctorInfo.fields.length === 0) {
          return { __kind: "ctor", name: expr.name, args: [] };
        }
      }
      if (this.callables.has(expr.name)) {
        const decl = this.callables.get(expr.name);
        return { __kind: "callable_ref", decl };
      }
      throw new VelaError(
        "name",
        expr.site.line,
        expr.site.column,
        `unknown identifier '${expr.name}'`
      );
    }
    if (expr.kind === "lambda") {
      const captured = new Map(env);
      return {
        __kind: "closure",
        params: expr.params,
        body: expr.body,
        env: captured,
      };
    }
    if (expr.kind === "quantifier") {
      const qEnv = new Map(env);
      for (const p of expr.params) {
        qEnv.set(p.name, 0n);
      }
      return Boolean(this.evalExpr(expr.body, qEnv));
    }
    if (expr.kind === "if_expr") {
      if (expr.condition.kind === "is_expr") {
        const targetVal = this.evalExpr(expr.condition.target, env);
        const m = this.matchPattern(expr.condition.pattern, targetVal);
        if (m.matched) {
          const thenEnv = new Map(env);
          for (const [k, v] of m.bindings.entries()) thenEnv.set(k, v);
          return this.evalExpr(expr.thenExpr, thenEnv);
        }
        return this.evalExpr(expr.elseExpr, env);
      }
      const cond = this.evalExpr(expr.condition, env);
      if (typeof cond !== "boolean") {
        throw new VelaError(
          "type",
          expr.site.line,
          expr.site.column,
          "if condition must have type bool"
        );
      }
      return cond ? this.evalExpr(expr.thenExpr, env) : this.evalExpr(expr.elseExpr, env);
    }
    if (expr.kind === "is_expr") {
      const targetVal = this.evalExpr(expr.target, env);
      return this.matchPattern(expr.pattern, targetVal).matched;
    }
    if (expr.kind === "match_expr") {
      const scrut = this.evalExpr(expr.scrutinee, env);
      for (const arm of expr.arms) {
        const m = this.matchPattern(arm.pattern, scrut);
        if (m.matched) {
          const armEnv = new Map(env);
          for (const [k, v] of m.bindings.entries()) armEnv.set(k, v);
          return this.evalExpr(arm.expr, armEnv);
        }
      }
      throw new VelaError("type", expr.site.line, expr.site.column, "non-exhaustive match");
    }
    if (expr.kind === "with_update") {
      const baseVal = this.evalExpr(expr.base, env);
      if (!baseVal || baseVal.__kind !== "record") {
        throw new VelaError(
          "type",
          expr.site.line,
          expr.site.column,
          "'with' update requires a record value"
        );
      }
      const rec = this.records.get(baseVal.typeName);
      const newFields = { ...baseVal.fields };
      let lastFieldIdx = -1;
      for (const upd of expr.updates) {
        const fIdx = rec.fields.findIndex((f) => f.name === upd.field);
        if (fIdx < 0) {
          throw new VelaError(
            "type",
            upd.site.line,
            upd.site.column,
            `unknown field '${upd.field}' on record '${baseVal.typeName}'`
          );
        }
        if (fIdx <= lastFieldIdx) {
          throw new VelaError(
            "type",
            upd.site.line,
            upd.site.column,
            `record update fields must appear in declaration order`
          );
        }
        lastFieldIdx = fIdx;
        newFields[upd.field] = this.evalExpr(upd.value, env);
      }
      return { __kind: "record", typeName: baseVal.typeName, fields: newFields };
    }
    if (expr.kind === "member") {
      const objVal = this.evalExpr(expr.object, env);
      if (objVal && objVal.__kind === "record") {
        if (Object.prototype.hasOwnProperty.call(objVal.fields, expr.member)) {
          return objVal.fields[expr.member];
        }
        const rec = this.records.get(objVal.typeName);
        if (rec) {
          const prop = rec.properties.find((p) => p.name === expr.member);
          if (prop) {
            const propEnv = new Map(env);
            propEnv.set("this", objVal);
            for (const [fk, fv] of Object.entries(objVal.fields)) {
              propEnv.set(fk, fv);
            }
            return this.evalExpr(prop.expr, propEnv);
          }
        }
      }
      throw new VelaError(
        "name",
        expr.site.line,
        expr.site.column,
        `unknown member '${expr.member}'`
      );
    }
    if (expr.kind === "loan_arg") {
      return this.evalExpr(expr.operand, env);
    }
    if (expr.kind === "unary") {
      const val = this.evalExpr(expr.operand, env);
      if (expr.op === "!") {
        if (typeof val !== "boolean") {
          throw new VelaError("type", expr.site.line, expr.site.column, "operator '!' requires bool");
        }
        return !val;
      }
      if (expr.op === "-") {
        if (typeof val !== "bigint") {
          throw new VelaError("type", expr.site.line, expr.site.column, "operator '-' requires integer");
        }
        return -val;
      }
    }
    if (expr.kind === "binary") {
      const op = expr.op;
      if (op === "&&" || op === "||" || op === "==>") {
        const left = this.evalExpr(expr.left, env);
        if (typeof left !== "boolean") {
          throw new VelaError("type", expr.site.line, expr.site.column, `operator '${op}' requires bool`);
        }
        if (op === "&&" && !left) return false;
        if (op === "||" && left) return true;
        if (op === "==>" && !left) return true;
        const right = this.evalExpr(expr.right, env);
        if (typeof right !== "boolean") {
          throw new VelaError("type", expr.site.line, expr.site.column, `operator '${op}' requires bool`);
        }
        return right;
      }
      const left = this.evalExpr(expr.left, env);
      const right = this.evalExpr(expr.right, env);
      if (op === "<==>") {
        if (typeof left !== "boolean" || typeof right !== "boolean") {
          throw new VelaError("type", expr.site.line, expr.site.column, "operator '<==>' requires bool");
        }
        return left === right;
      }
      if (op === "==" || op === "!=") {
        if (typeof left !== typeof right) {
          throw new VelaError(
            "type",
            expr.site.line,
            expr.site.column,
            `operator '${op}' requires operands of matching types`
          );
        }
        const eq = valuesEqual(left, right);
        return op === "==" ? eq : !eq;
      }
      if (typeof left !== "bigint" || typeof right !== "bigint") {
        throw new VelaError("type", expr.site.line, expr.site.column, `operator '${op}' requires Nat`);
      }
      if (op === "<") return left < right;
      if (op === "<=") return left <= right;
      if (op === ">") return left > right;
      if (op === ">=") return left >= right;
      if (op === "+") return left + right;
      if (op === "-") return left > right ? left - right : 0n;
      if (op === "*") return left * right;
      if (op === "/") return right === 0n ? 0n : left / right;
      if (op === "%") return right === 0n ? left : left % right;
    }
    if (expr.kind === "call") {
      return this.evalCall(expr, env);
    }
    throw new VelaError("unsupported", expr.site.line, expr.site.column, `unsupported expression kind '${expr.kind}'`);
  }

  evalCall(expr, env) {
    if (
      expr.callee.kind === "member" &&
      expr.callee.object.kind === "name" &&
      expr.callee.object.name === "TextBuilder" &&
      expr.callee.member === "Empty"
    ) {
      if (expr.typeArgs.length !== 1) {
        throw new VelaError("type", expr.site.line, expr.site.column, "TextBuilder.Empty expects 1 capacity argument");
      }
      const cap = this.evalTypeIndex(expr.typeArgs[0], env);
      if (cap === null) {
        throw new VelaError("type", expr.site.line, expr.site.column, "TextBuilder capacity must be a Nat");
      }
      return { __kind: "builder", capacity: cap, written: 0n, ok: true };
    }
    if (
      expr.callee.kind === "member" &&
      expr.callee.object.kind === "name" &&
      expr.callee.object.name === "Format" &&
      expr.callee.member === "Write"
    ) {
      if (expr.args.length !== 2) {
        throw new VelaError("type", expr.site.line, expr.site.column, "Format.Write expects 2 arguments");
      }
      const builderArg = expr.args[0];
      const fmtArg = expr.args[1];
      if (builderArg.mode !== "ref") {
        throw new VelaError(
          "type",
          builderArg.site.line,
          builderArg.site.column,
          "Format.Write requires an explicit 'ref' loan on the builder argument"
        );
      }
      if (builderArg.value.kind !== "name" || !env.has(builderArg.value.name)) {
        throw new VelaError(
          "type",
          builderArg.site.line,
          builderArg.site.column,
          "Format.Write requires a mutable TextBuilder binding"
        );
      }
      const builder = env.get(builderArg.value.name);
      if (!builder || builder.__kind !== "builder") {
        throw new VelaError(
          "type",
          builderArg.site.line,
          builderArg.site.column,
          "Format.Write first argument must be a TextBuilder"
        );
      }
      if (fmtArg.value.kind !== "format_string") {
        throw new VelaError(
          "type",
          fmtArg.site.line,
          fmtArg.site.column,
          "Format.Write second argument must be a format template literal"
        );
      }
      const segments = parseFormatSegments(fmtArg.value.template, fmtArg.site);
      let addedBytes = 0n;
      for (const seg of segments) {
        if (seg.kind === "text") {
          addedBytes += BigInt(utf8Bytes(seg.value).length);
        } else {
          const holeVal = this.evalExpr(seg.expr, env);
          let rendered;
          if (typeof holeVal === "bigint") rendered = holeVal.toString();
          else if (typeof holeVal === "boolean") rendered = holeVal ? "true" : "false";
          else if (typeof holeVal === "string") rendered = holeVal;
          else {
            throw new VelaError(
              "type",
              fmtArg.site.line,
              fmtArg.site.column,
              "format hole must have type Nat, bool, or String"
            );
          }
          addedBytes += BigInt(utf8Bytes(rendered).length);
        }
      }
      const totalWritten = builder.written + addedBytes;
      const fits = builder.ok && totalWritten <= builder.capacity;
      const updatedBuilder = {
        __kind: "builder",
        capacity: builder.capacity,
        written: totalWritten,
        ok: fits,
      };
      env.set(builderArg.value.name, updatedBuilder);
      return fits
        ? { __kind: "ctor", name: "Ok", args: [addedBytes] }
        : { __kind: "ctor", name: "Err", args: ["CapacityError"] };
    }

    if (expr.callee.kind === "name") {
      const name = expr.callee.name;
      if (name === "Zero") {
        if (expr.args.length !== 0) {
          throw new VelaError("type", expr.site.line, expr.site.column, "Zero() takes 0 arguments");
        }
        return 0n;
      }
      if (name === "Succ") {
        if (expr.args.length !== 1) {
          throw new VelaError("type", expr.site.line, expr.site.column, "Succ expects 1 argument");
        }
        const inner = this.evalExpr(expr.args[0].value, env);
        if (typeof inner !== "bigint") {
          throw new VelaError("type", expr.site.line, expr.site.column, "Succ requires a Nat argument");
        }
        return inner + 1n;
      }
      if (name === "VNil") {
        if (expr.args.length !== 0) {
          throw new VelaError("type", expr.site.line, expr.site.column, "VNil takes 0 value arguments");
        }
        return { __kind: "vec", items: [], length: 0n };
      }
      if (name === "VCons" || name === "Prepend") {
        if (expr.args.length !== 2) {
          throw new VelaError("type", expr.site.line, expr.site.column, `${name} expects 2 arguments`);
        }
        const head = this.evalExpr(expr.args[0].value, env);
        const tail = this.evalExpr(expr.args[1].value, env);
        if (!tail || tail.__kind !== "vec") {
          throw new VelaError("type", expr.site.line, expr.site.column, `${name} second argument must be a Vec`);
        }
        return { __kind: "vec", items: [head, ...tail.items], length: tail.length + 1n };
      }
      if (name === "FZero") {
        if (expr.typeArgs.length !== 1 || expr.args.length !== 0) {
          throw new VelaError("type", expr.site.line, expr.site.column, "FZero<n>() expects 1 index argument");
        }
        const nVal = this.evalTypeIndex(expr.typeArgs[0], env);
        if (nVal === null || nVal < 0n) {
          throw new VelaError("type", expr.site.line, expr.site.column, "FZero requires a Nat bound");
        }
        return { __kind: "fin", index: 0n, bound: nVal + 1n };
      }
      if (name === "FSucc") {
        if (expr.args.length !== 1) {
          throw new VelaError("type", expr.site.line, expr.site.column, "FSucc expects 1 Fin argument");
        }
        const inner = this.evalExpr(expr.args[0].value, env);
        if (!inner || inner.__kind !== "fin") {
          throw new VelaError("type", expr.site.line, expr.site.column, "FSucc requires a Fin argument");
        }
        return { __kind: "fin", index: inner.index + 1n, bound: inner.bound + 1n };
      }
      if (name === "At") {
        if (expr.args.length !== 2) {
          throw new VelaError("type", expr.site.line, expr.site.column, "At expects (Vec, Fin)");
        }
        const vec = this.evalExpr(expr.args[0].value, env);
        const fin = this.evalExpr(expr.args[1].value, env);
        if (!vec || vec.__kind !== "vec") {
          throw new VelaError("type", expr.site.line, expr.site.column, "At first argument must be a Vec");
        }
        if (!fin || fin.__kind !== "fin") {
          throw new VelaError("type", expr.site.line, expr.site.column, "At second argument must be a Fin");
        }
        if (vec.length !== fin.bound || fin.index < 0n || fin.index >= vec.length) {
          throw new VelaError(
            "type",
            expr.site.line,
            expr.site.column,
            `Fin<${fin.bound}> index does not match Vec<..., ${vec.length}>`
          );
        }
        return vec.items[Number(fin.index)];
      }
      if (name === "ByteLength") {
        if (expr.args.length !== 1) {
          throw new VelaError("type", expr.site.line, expr.site.column, "ByteLength expects 1 argument");
        }
        const target = this.evalExpr(expr.args[0].value, env);
        if (typeof target === "string") {
          return BigInt(utf8Bytes(target).length);
        }
        if (target && target.__kind === "builder") {
          return target.written;
        }
        throw new VelaError("type", expr.site.line, expr.site.column, "ByteLength requires String or TextBuilder");
      }
      if (name === "Written") {
        if (expr.args.length !== 1) {
          throw new VelaError("type", expr.site.line, expr.site.column, "Written expects 1 TextBuilder argument");
        }
        const target = this.evalExpr(expr.args[0].value, env);
        if (!target || target.__kind !== "builder") {
          throw new VelaError("type", expr.site.line, expr.site.column, "Written requires a TextBuilder");
        }
        if (expr.typeArgs.length === 1) {
          const cap = this.evalTypeIndex(expr.typeArgs[0], env);
          if (cap !== null && cap !== target.capacity) {
            throw new VelaError("type", expr.site.line, expr.site.column, "Written capacity mismatch");
          }
        }
        return target.written;
      }
      if (name === "Fits") {
        if (expr.args.length !== 1) {
          throw new VelaError("type", expr.site.line, expr.site.column, "Fits expects 1 TextBuilder argument");
        }
        const target = this.evalExpr(expr.args[0].value, env);
        if (!target || target.__kind !== "builder") {
          throw new VelaError("type", expr.site.line, expr.site.column, "Fits requires a TextBuilder");
        }
        if (expr.typeArgs.length === 1) {
          const cap = this.evalTypeIndex(expr.typeArgs[0], env);
          if (cap !== null && cap !== target.capacity) {
            throw new VelaError("type", expr.site.line, expr.site.column, "Fits capacity mismatch");
          }
        }
        return Boolean(target.ok && target.written <= target.capacity);
      }
      if (this.records.has(name)) {
        const rec = this.records.get(name);
        if (expr.args.length !== rec.fields.length) {
          throw new VelaError(
            "type",
            expr.site.line,
            expr.site.column,
            `record '${name}' expects ${rec.fields.length} argument(s)`
          );
        }
        const fields = {};
        let seenNamed = false;
        for (let i = 0; i < rec.fields.length; i += 1) {
          const arg = expr.args[i];
          const expectedName = rec.fields[i].name;
          if (arg.label !== null) {
            seenNamed = true;
            if (arg.label !== expectedName) {
              throw new VelaError(
                "type",
                arg.site.line,
                arg.site.column,
                `named field '${arg.label}' must match '${expectedName}' in declaration order`
              );
            }
          } else if (seenNamed) {
            throw new VelaError(
              "type",
              arg.site.line,
              arg.site.column,
              "positional argument cannot follow a named argument"
            );
          }
          fields[expectedName] = this.evalExpr(arg.value, env);
        }
        return { __kind: "record", typeName: name, fields };
      }
      if (this.unionCtors.has(name) || ["Some", "Ok", "Err"].includes(name)) {
        return {
          __kind: "ctor",
          name,
          args: expr.args.map((a) => this.evalExpr(a.value, env)),
        };
      }
      if (env.has(name)) {
        const localCallee = env.get(name);
        if (localCallee && localCallee.__kind === "closure") {
          if (expr.args.length !== localCallee.params.length) {
            throw new VelaError("type", expr.site.line, expr.site.column, "lambda argument count mismatch");
          }
          const callEnv = new Map(localCallee.env);
          for (let i = 0; i < localCallee.params.length; i += 1) {
            callEnv.set(localCallee.params[i].name, this.evalExpr(expr.args[i].value, env));
          }
          return this.evalExpr(localCallee.body, callEnv);
        }
      }
      if (this.callables.has(name)) {
        const decl = this.callables.get(name);
        if (expr.args.length !== decl.parameters.length) {
          throw new VelaError(
            "type",
            expr.site.line,
            expr.site.column,
            `'${name}' expects ${decl.parameters.length} argument(s), got ${expr.args.length}`
          );
        }
        const callEnv = new Map();
        const valueGenParams = decl.generics.filter((g) => g.mode !== "type");
        if (expr.typeArgs.length > 0) {
          if (expr.typeArgs.length === decl.generics.length) {
            for (let i = 0; i < decl.generics.length; i += 1) {
              const g = decl.generics[i];
              if (g.mode !== "type") {
                const idxVal = this.evalTypeIndex(expr.typeArgs[i], env);
                if (idxVal !== null) callEnv.set(g.name, idxVal);
              }
            }
          } else if (expr.typeArgs.length === valueGenParams.length) {
            for (let i = 0; i < valueGenParams.length; i += 1) {
              const idxVal = this.evalTypeIndex(expr.typeArgs[i], env);
              if (idxVal !== null) callEnv.set(valueGenParams[i].name, idxVal);
            }
          }
        }
        let seenNamed = false;
        for (let i = 0; i < decl.parameters.length; i += 1) {
          const param = decl.parameters[i];
          const arg = expr.args[i];
          if (arg.label !== null) {
            seenNamed = true;
            if (arg.label !== param.name) {
              throw new VelaError(
                "type",
                arg.site.line,
                arg.site.column,
                `named argument '${arg.label}:' must match '${param.name}' in parameter order`
              );
            }
          } else if (seenNamed) {
            throw new VelaError(
              "type",
              arg.site.line,
              arg.site.column,
              "positional argument cannot follow a named argument"
            );
          }
          const argVal = this.evalExpr(arg.value, env);
          if (
            param.type &&
            param.type.kind === "named_type" &&
            param.type.name === "Vec" &&
            param.type.args.length === 2
          ) {
            if (!argVal || argVal.__kind !== "vec") {
              throw new VelaError("type", arg.site.line, arg.site.column, `expected Vec argument for '${param.name}'`);
            }
            const lenArg = param.type.args[1];
            if (lenArg.kind === "named_type" && !callEnv.has(lenArg.name)) {
              callEnv.set(lenArg.name, argVal.length);
            } else {
              const expectedLen = this.evalTypeIndex(lenArg, callEnv);
              if (expectedLen !== null && argVal.length !== expectedLen) {
                throw new VelaError(
                  "type",
                  arg.site.line,
                  arg.site.column,
                  `Vec length mismatch: expected ${expectedLen}, got ${argVal.length}`
                );
              }
            }
          }
          callEnv.set(param.name, argVal);
        }
        if (!decl.body) {
          return { __kind: "unit" };
        }
        const res = this.evalBlock(decl.body, callEnv);
        const returnVal = res.value;
        this.checkReturnValueType(decl, returnVal, callEnv);
        for (const ens of decl.contracts.ensures) {
          const ensEnv = new Map(callEnv);
          ensEnv.set("result", returnVal);
          const ok = this.evalExpr(ens.expr, ensEnv);
          if (ok !== true) {
            throw new VelaError(
              "type",
              ens.site.line,
              ens.site.column,
              `postcondition 'ensures' of '${decl.name}' failed`
            );
          }
        }
        return returnVal;
      }
      throw new VelaError("name", expr.site.line, expr.site.column, `unknown function '${name}'`);
    }
    throw new VelaError("unsupported", expr.site.line, expr.site.column, "unsupported call target");
  }

  checkReturnValueType(decl, returnVal, env) {
    const rt = decl.returnType;
    if (!rt || rt.kind !== "named_type") return;
    if (rt.name === "Nat" && typeof returnVal !== "bigint") {
      throw new VelaError("type", decl.site.line, decl.site.column, `expected Nat return value in '${decl.name}'`);
    }
    if (rt.name === "bool" && typeof returnVal !== "boolean") {
      throw new VelaError("type", decl.site.line, decl.site.column, `expected bool return value in '${decl.name}'`);
    }
    if (rt.name === "Vec" && rt.args.length === 2) {
      if (!returnVal || returnVal.__kind !== "vec") {
        throw new VelaError("type", decl.site.line, decl.site.column, `expected Vec return value in '${decl.name}'`);
      }
      const expectedLen = this.evalTypeIndex(rt.args[1], env);
      if (expectedLen !== null && returnVal.length !== expectedLen) {
        throw new VelaError(
          "type",
          decl.site.line,
          decl.site.column,
          `Vec length mismatch in '${decl.name}': expected ${expectedLen}, got ${returnVal.length}`
        );
      }
    }
  }

  sampleValueForType(typeNode, env) {
    if (!typeNode) return 0n;
    if (typeNode.kind === "mode_type") {
      return this.sampleValueForType(typeNode.inner, env);
    }
    if (typeNode.kind === "fn_type") {
      return {
        __kind: "closure",
        params: typeNode.params.map((p, i) => ({
          mode: "value",
          type: p.type,
          name: p.name || `p${i}`,
        })),
        body: {
          kind: "name",
          name: typeNode.params[0] && typeNode.params[0].name ? typeNode.params[0].name : "p0",
          site: typeNode.site,
        },
        env: new Map(env),
      };
    }
    if (typeNode.kind === "named_type") {
      if (typeNode.name === "Nat" || typeNode.name === "usize" || typeNode.name === "u32") return 0n;
      if (typeNode.name === "bool") return false;
      if (typeNode.name === "String") return "";
      if (typeNode.name === "Vec" && typeNode.args.length === 2) {
        const len = this.evalTypeIndex(typeNode.args[1], env) ?? 2n;
        const elem = this.sampleValueForType(typeNode.args[0], env);
        const items = [];
        for (let i = 0n; i < len; i += 1n) items.push(elem);
        return { __kind: "vec", items, length: len };
      }
      if (typeNode.name === "Fin" && typeNode.args.length === 1) {
        const bound = this.evalTypeIndex(typeNode.args[0], env) ?? 1n;
        return { __kind: "fin", index: 0n, bound: bound > 0n ? bound : 1n };
      }
      if (typeNode.name === "TextBuilder") {
        const cap = this.evalTypeIndex(typeNode.args[0], env) ?? 32n;
        return { __kind: "builder", capacity: cap, written: 0n, ok: true };
      }
      if (this.records.has(typeNode.name)) {
        const rec = this.records.get(typeNode.name);
        const fields = {};
        for (const f of rec.fields) {
          fields[f.name] = this.sampleValueForType(f.type, env);
        }
        return { __kind: "record", typeName: typeNode.name, fields };
      }
      if (typeNode.name === "Option") {
        return { __kind: "ctor", name: "None", args: [] };
      }
      return 0n;
    }
    return 0n;
  }

  checkProofBlock(proof, env) {
    if (!proof) return;
    for (const step of proof.steps) {
      if (step.kind === "calc") {
        for (const item of step.assertions) {
          const val = this.evalExpr(item.prop, env);
          if (val !== true) {
            throw new VelaError("type", item.site.line, item.site.column, "calc proof assertion failed");
          }
        }
      } else if (step.kind === "assert") {
        const val = this.evalExpr(step.prop, env);
        if (val !== true) {
          throw new VelaError("type", step.site.line, step.site.column, "proof assertion failed");
        }
      }
    }
  }

  elaborate() {
    const gallinaBlocks = [];
    for (const decl of this.module.declarations) {
      if (decl.kind === "record") {
        this.records.set(decl.name, decl);
        const fieldLines = decl.fields
          .map((f) => `  ${decl.name}_${f.name} : ${renderMathTypeGallina(f.type)};`)
          .join("\n");
        gallinaBlocks.push(
          `Record ${decl.name} : Type := mk_${decl.name} {\n${fieldLines}\n}.`
        );
        for (const prop of decl.properties) {
          gallinaBlocks.push(
            `Definition ${decl.name}_${prop.name} (this : ${decl.name}) : ${renderMathTypeGallina(prop.type)} :=\n  (* property ${prop.name} *) ${renderMathExprGallina(prop.expr)}.`
          );
        }
        continue;
      }
      if (decl.kind === "union") {
        this.unions.set(decl.name, decl);
        const ctorLines = [];
        for (const c of decl.cases) {
          this.unionCtors.set(c.name, c);
          const paramTypes = c.fields.map((f) => `${renderMathTypeGallina(f.type)} -> `).join("");
          ctorLines.push(`| ${c.name} : ${paramTypes}${decl.name}`);
        }
        gallinaBlocks.push(`Inductive ${decl.name} : Type :=\n${ctorLines.join("\n")}.`);
        continue;
      }
      if (decl.kind === "constant") {
        const val = this.evalExpr(decl.value, new Map());
        this.constants.set(decl.name, val);
        gallinaBlocks.push(
          `Definition ${decl.name} : ${renderMathTypeGallina(decl.valueType)} := ${renderMathValueGallina(val)}.`
        );
        continue;
      }
      if (decl.kind === "definition" || decl.kind === "function") {
        this.callables.set(decl.name, decl);
        const sampleEnv = new Map();
        for (const g of decl.generics) {
          if (g.mode !== "type") {
            sampleEnv.set(g.name, 2n);
          }
        }
        for (const p of decl.parameters) {
          sampleEnv.set(p.name, this.sampleValueForType(p.type, sampleEnv));
        }
        if (decl.body) {
          const res = this.evalBlock(decl.body, sampleEnv);
          this.checkReturnValueType(decl, res.value, sampleEnv);
          for (const ens of decl.contracts.ensures) {
            const ensEnv = new Map(sampleEnv);
            ensEnv.set("result", res.value);
            const ok = this.evalExpr(ens.expr, ensEnv);
            if (ok !== true) {
              throw new VelaError(
                "type",
                ens.site.line,
                ens.site.column,
                `postcondition 'ensures' of '${decl.name}' failed`
              );
            }
          }
        }
        if (decl.proof) {
          this.checkProofBlock(decl.proof, sampleEnv);
        }
        const gBinders = decl.generics
          .map((g) => (g.mode === "type" ? `(${g.name} : Type)` : `(${g.name} : nat)`))
          .join(" ");
        const pBinders = decl.parameters
          .map((p) => `(${p.name} : ${renderMathTypeGallina(p.type)})`)
          .join(" ");
        const allBinders = [gBinders, pBinders].filter(Boolean).join(" ");
        const bodyText = decl.body ? renderMathBodyGallina(decl.body) : "tt";
        gallinaBlocks.push(
          `Definition ${decl.name}${allBinders ? " " + allBinders : ""} : ${renderMathTypeGallina(decl.returnType)} :=\n  ${bodyText}.`
        );
        continue;
      }
      if (decl.kind === "lemma") {
        const sampleEnv = new Map();
        for (const p of decl.parameters) {
          sampleEnv.set(p.name, this.sampleValueForType(p.type, sampleEnv));
        }
        if (decl.proof) {
          this.checkProofBlock(decl.proof, sampleEnv);
        }
        for (const ens of decl.contracts.ensures) {
          const ok = this.evalExpr(ens.expr, sampleEnv);
          if (ok !== true) {
            throw new VelaError(
              "type",
              ens.site.line,
              ens.site.column,
              `lemma '${decl.name}' ensures clause failed`
            );
          }
        }
        const pBinders = decl.parameters
          .map((p) => `(${p.name} : ${renderMathTypeGallina(p.type)})`)
          .join(" ");
        const propText =
          decl.contracts.ensures.length > 0
            ? renderMathExprGallina(decl.contracts.ensures[0].expr)
            : "True";
        gallinaBlocks.push(
          `Theorem ${decl.name}${pBinders ? " " + pBinders : ""} : ${propText} :=\n  eq_refl.`
        );
      }
    }

    const findings = [];
    for (const binder of this.module.genericTypeBinders) {
      if (!isPascalCase(binder.text)) {
        findings.push({
          code: "VELA105",
          message: `use PascalCase for generic type parameter '${binder.text}'`,
          line: binder.site.line,
          column: binder.site.column,
        });
      }
    }
    findings.sort((a, b) => a.line - b.line || a.column - b.column);

    const modIdent = `Vela_${this.module.name.replace(/\./g, "_")}`;
    const digest = sha256Hex(this.sourceText);
    const gallina = [
      "(* SPDX-License-" + "Identifier: Apache-2.0 *)",
      `(* Vela mathematical elaboration: unqualified kernel proposal. Source SHA256: ${digest} *)`,
      `Module ${modIdent}.`,
      "",
      "From Stdlib Require Import Bool Arith PeanoNat String.",
      "",
      ...gallinaBlocks,
      "",
      `End ${modIdent}.`,
      "",
    ].join("\n");

    return {
      module: this.module.name,
      gallina,
      findings,
    };
  }
}

function renderMathTypeGallina(typeNode) {
  if (!typeNode) return "unit";
  if (typeNode.kind === "mode_type") return renderMathTypeGallina(typeNode.inner);
  if (typeNode.kind === "fn_type") {
    const dom = typeNode.params.map((p) => renderMathTypeGallina(p.type)).join(" -> ");
    return `(${dom || "unit"} -> ${renderMathTypeGallina(typeNode.result)})`;
  }
  if (typeNode.kind === "nat_index") return `${typeNode.value.toString()}%nat`;
  if (typeNode.kind === "expr_index") return renderMathExprGallina(typeNode.expr);
  if (typeNode.kind === "named_type") {
    if (typeNode.name === "Nat") return "nat";
    if (typeNode.name === "bool") return "bool";
    if (typeNode.name === "Unit" || typeNode.name === "void") return "unit";
    if (typeNode.name === "String") return "string";
    if (typeNode.args && typeNode.args.length > 0) {
      const renderedArgs = typeNode.args.map((a) => renderMathTypeGallina(a)).join(" ");
      return `(${typeNode.name} ${renderedArgs})`;
    }
    return typeNode.name;
  }
  return "Type";
}

function renderMathValueGallina(val) {
  if (typeof val === "bigint") return `${val.toString()}%nat`;
  if (typeof val === "boolean") return val ? "true" : "false";
  if (typeof val === "string") return `"${val.replace(/"/g, '""')}"%string`;
  return "tt";
}

function renderMathExprGallina(expr) {
  if (!expr) return "tt";
  if (expr.kind === "nat") return `${expr.value.toString()}%nat`;
  if (expr.kind === "bool") return expr.value ? "true" : "false";
  if (expr.kind === "string") return `"${expr.value.replace(/"/g, '""')}"%string`;
  if (expr.kind === "name") return expr.name;
  if (expr.kind === "member") return `(${renderMathExprGallina(expr.object)}.${expr.member})`;
  if (expr.kind === "unary") return `(${expr.op}${renderMathExprGallina(expr.operand)})`;
  if (expr.kind === "binary") {
    return `(${renderMathExprGallina(expr.left)} ${expr.op} ${renderMathExprGallina(expr.right)})`;
  }
  if (expr.kind === "if_expr") {
    return `(if ${renderMathExprGallina(expr.condition)} then ${renderMathExprGallina(expr.thenExpr)} else ${renderMathExprGallina(expr.elseExpr)})`;
  }
  if (expr.kind === "call") {
    const callee = renderMathExprGallina(expr.callee);
    const args = expr.args.map((a) => renderMathExprGallina(a.value)).join(" ");
    return args ? `(${callee} ${args})` : callee;
  }
  if (expr.kind === "with_update") {
    const upd = expr.updates.map((u) => `${u.field} := ${renderMathExprGallina(u.value)}`).join("; ");
    return `(${renderMathExprGallina(expr.base)} with { ${upd} })`;
  }
  if (expr.kind === "match_expr") {
    const arms = expr.arms
      .map((a) => `| _ => ${renderMathExprGallina(a.expr)}`)
      .join(" ");
    return `(match ${renderMathExprGallina(expr.scrutinee)} with ${arms} end)`;
  }
  return "tt";
}

function renderMathBodyGallina(body) {
  if (body.kind === "expr_body") {
    return renderMathExprGallina(body.expr);
  }
  const parts = [];
  for (const stmt of body.statements) {
    if (stmt.kind === "local" && stmt.name !== "_") {
      parts.push(`let ${stmt.name} := ${renderMathExprGallina(stmt.value)} in`);
    } else if (stmt.kind === "return") {
      parts.push(renderMathExprGallina(stmt.value));
    }
  }
  return parts.length > 0 ? parts.join("\n  ") : "tt";
}

function compileMathematical(sourceText) {
  const tokens = mathTokenize(sourceText);
  const parser = new MathParser(tokens);
  const parsedModule = parser.parseModule();
  const elaborator = new MathElaborator(parsedModule, sourceText);
  return {
    ...elaborator.elaborate(),
    elaborator,
  };
}

function evaluateMathematical(sourceText, expressionText, valueType) {
  const { elaborator } = compileMathematical(sourceText);
  if (valueType !== "Nat" && valueType !== "bool") {
    throw new VelaError("type", 1, 1, "expression: expected Nat or bool result type");
  }
  if (typeof expressionText !== "string") {
    throw new VelaError("syntax", 1, 1, "expression: expected UTF-8 text");
  }
  const rawBytes = utf8Bytes(expressionText);
  if (rawBytes.length > MAX_CONSOLE_EXPRESSION_BYTES) {
    throw new VelaError(
      "limit",
      1,
      1,
      `expression: exceeds ${MAX_CONSOLE_EXPRESSION_BYTES} UTF-8 bytes`
    );
  }
  try {
    const tokens = mathTokenize(expressionText, { allowSemicolon: false });
    if (tokens.length === 1) {
      throw new VelaError("syntax", 1, 1, "expected an expression");
    }
    const parser = new MathParser(tokens);
    const expr = parser.parseExpression();
    if (parser.current.kind !== "eof") {
      throw new VelaError(
        "syntax",
        parser.current.site.line,
        parser.current.site.column,
        `unexpected '${parser.current.text}' after expression`
      );
    }
    const val = elaborator.evalExpr(expr, new Map());
    const actual = typeof val === "boolean" ? "bool" : typeof val === "bigint" ? "Nat" : "other";
    if (actual !== valueType) {
      throw new VelaError(
        "type",
        1,
        1,
        `expression reduced to ${actual}, expected ${valueType}`
      );
    }
    return {
      valueType,
      value: typeof val === "boolean" ? (val ? "true" : "false") : val.toString(),
    };
  } catch (err) {
    if (err instanceof VelaError) {
      throw new VelaError(err.kind, err.line, err.column, `expression: ${err.message}`);
    }
    throw err;
  }
}

const browserSessions = new Map();
let browserSessionCounter = 0;

function formatErrorPayload(sourceHash, error, extra = {}) {
  const kind = error instanceof VelaError ? error.kind : "internal";
  const line = error instanceof VelaError ? error.line : 1;
  const column = error instanceof VelaError ? error.column : 1;
  const message = error instanceof VelaError ? error.message : String(error);
  return {
    ok: false,
    sourceHash,
    ...extra,
    error: { kind, message, line, column },
  };
}

export async function browserApi(path, body) {
  if (path === "/api/capabilities") {
    return { mathematical: true };
  }
  if (path === "/api/session") {
    browserSessionCounter += 1;
    const sessionId = `browser-session-${browserSessionCounter}`;
    browserSessions.set(sessionId, new BrowserLspSession());
    return { session: sessionId };
  }
  if (path === "/api/close") {
    if (body && body.session) {
      browserSessions.delete(body.session);
    }
    return { closed: true };
  }
  if (path === "/api/lsp") {
    const session = browserSessions.get(body.session);
    if (!session) {
      throw new Error("LSP session expired");
    }
    return { messages: session.handle(body.message) };
  }
  const sourceText = typeof body.source === "string" ? body.source : "";
  const sourceHash = sha256Hex(sourceText);

  if (path === "/api/compile") {
    try {
      const pureRes = runPureTranslate(sourceText, false);
      return {
        ok: true,
        sourceHash,
        module: pureRes.module,
        gallina: pureRes.gallina,
        editorServices: true,
        findings: [],
      };
    } catch (pureErr) {
      if (pureErr instanceof VelaError && (pureErr.kind === "syntax" || pureErr.kind === "unsupported")) {
        try {
          const mathRes = compileMathematical(sourceText);
          return {
            ok: true,
            sourceHash,
            module: mathRes.module,
            gallina: mathRes.gallina,
            editorServices: false,
            findings: mathRes.findings,
          };
        } catch (mathErr) {
          return formatErrorPayload(sourceHash, mathErr, { editorServices: false });
        }
      }
      return formatErrorPayload(sourceHash, pureErr, { editorServices: true });
    }
  }

  if (path === "/api/evaluate") {
    let useMath = false;
    try {
      runPureTranslate(sourceText, false);
    } catch (pureErr) {
      if (pureErr instanceof VelaError && (pureErr.kind === "syntax" || pureErr.kind === "unsupported")) {
        useMath = true;
      } else {
        return formatErrorPayload(sourceHash, pureErr);
      }
    }
    try {
      const res = useMath
        ? evaluateMathematical(sourceText, body.expression, body.valueType)
        : pureEvaluate(sourceText, body.expression, body.valueType);
      return {
        ok: true,
        sourceHash,
        valueType: res.valueType,
        value: res.value,
      };
    } catch (evalErr) {
      return formatErrorPayload(sourceHash, evalErr);
    }
  }

  if (path === "/api/authoring") {
    try {
      const findings = pureLintSource(sourceText);
      const bindingPreview = purePreviewBindings(sourceText);
      return {
        ok: true,
        sourceHash,
        findings,
        bindingPreview,
      };
    } catch (authErr) {
      return formatErrorPayload(sourceHash, authErr);
    }
  }

  throw new Error(`Unknown API endpoint: ${path}`);
}

function initPlaygroundUi() {
  const token = readStartupToken();

  const elements = {
    connectionBadge: document.getElementById("connection-badge"),
    scopeBadge: document.getElementById("scope-badge"),
    editorModeBadge: document.getElementById("editor-mode-badge"),
    statusBanner: document.getElementById("status-banner"),
    exampleSelect: document.getElementById("example-select"),
    compileButton: document.getElementById("compile-button"),
    formatButton: document.getElementById("format-button"),
    authoringButton: document.getElementById("authoring-button"),
    downloadSourceButton: document.getElementById("download-source-button"),
    downloadGallinaButton: document.getElementById("download-gallina-button"),
    typeHintsToggle: document.getElementById("type-hints-toggle"),
    semanticTokensToggle: document.getElementById("semantic-tokens-toggle"),
    monacoContainer: document.getElementById("monaco-container"),
    fallbackEditor: document.getElementById("fallback-editor"),
    cursorStatus: document.getElementById("cursor-status"),
    selectionActionStatus: document.getElementById("selection-action-status"),
    evaluateForm: document.getElementById("evaluate-form"),
    expressionInput: document.getElementById("expression-input"),
    expressionType: document.getElementById("expression-type"),
    evaluateButton: document.getElementById("evaluate-button"),
    expressionSuggestions: document.getElementById("expression-suggestions"),
    consoleOutput: document.getElementById("console-output"),
    gallinaOutput: document.getElementById("gallina-output"),
    diagnosticsList: document.getElementById("diagnostics-list"),
    diagnosticCount: document.getElementById("diagnostic-count"),
    symbolsList: document.getElementById("symbols-list"),
    symbolCount: document.getElementById("symbol-count"),
    hoverOutput: document.getElementById("hover-output"),
    referencesList: document.getElementById("references-list"),
    authoringList: document.getElementById("authoring-list"),
    authoringCount: document.getElementById("authoring-count"),
    previewOutput: document.getElementById("preview-output"),
    previewStatus: document.getElementById("preview-status"),
    applyPreviewButton: document.getElementById("apply-preview-button"),
    undoPreviewButton: document.getElementById("undo-preview-button"),
    tabs: Array.from(document.querySelectorAll(".tab")),
    panels: {
      console: document.getElementById("panel-console"),
      gallina: document.getElementById("panel-gallina"),
      diagnostics: document.getElementById("panel-diagnostics"),
      inspect: document.getElementById("panel-inspect"),
      authoring: document.getElementById("panel-authoring"),
    },
  };

  const state = {
    source: EXAMPLES.squares.source,
    version: 1,
    session: null,
    sessionGeneration: 0,
    rpcId: 1,
    lspQueue: Promise.resolve(),
    monaco: null,
    editor: null,
    model: null,
    inlayDecorations: [],
    semanticDecorations: [],
    latestCompile: null,
    latestPreview: null,
    undoSnapshot: null,
    applyingProgrammaticEdit: false,
    suppressUndoClear: false,
    mathematicalEnabled: false,
    editorServicesAvailable: true,
    latestDiagnostics: [],
    sourceCheckTimer: null,
  };

  function readStartupToken() {
    const hash = window.location.hash.startsWith("#") ? window.location.hash.slice(1) : "";
    const params = new URLSearchParams(hash);
    const value = params.get("token");
    if (value) {
      history.replaceState(null, "", window.location.pathname + window.location.search);
    }
    return value;
  }

  function setBanner(text, kind = "neutral") {
    elements.statusBanner.textContent = text;
    elements.statusBanner.classList.remove("is-error", "is-ok");
    if (kind === "error") {
      elements.statusBanner.classList.add("is-error");
    } else if (kind === "ok") {
      elements.statusBanner.classList.add("is-ok");
    }
  }

  function setBadge(badge, text, kind = "neutral") {
    badge.textContent = text;
    badge.className = "badge";
    if (kind === "ok") {
      badge.classList.add("badge-ok");
    } else if (kind === "warn") {
      badge.classList.add("badge-warn");
    } else if (kind === "error") {
      badge.classList.add("badge-err");
    }
  }

  function selectTab(panelName) {
    for (const tab of elements.tabs) {
      const active = tab.dataset.panel === panelName;
      tab.classList.toggle("is-active", active);
      tab.setAttribute("aria-selected", active ? "true" : "false");
    }
    for (const [name, panel] of Object.entries(elements.panels)) {
      const active = name === panelName;
      panel.classList.toggle("is-active", active);
      panel.hidden = !active;
    }
  }

  async function api(path, body, { keepalive = false } = {}) {
    if (!token) {
      return browserApi(path, body);
    }
    const response = await fetch(path, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
      keepalive,
    });
    let payload = null;
    try {
      payload = await response.json();
    } catch {
      throw new Error(`HTTP ${response.status}: non-JSON reply`);
    }
    if (!response.ok) {
      const detail =
        payload && typeof payload.error === "string" ? payload.error : `HTTP ${response.status}`;
      const error = new Error(detail);
      error.status = response.status;
      throw error;
    }
    return payload;
  }

  function enqueueLsp(message) {
    const generation = state.sessionGeneration;
    const session = state.session;
    const task = state.lspQueue.then(async () => {
      if (!session || generation !== state.sessionGeneration) {
        return [];
      }
      const reply = await api("/api/lsp", { session, message });
      if (generation !== state.sessionGeneration) {
        return [];
      }
      return Array.isArray(reply.messages) ? reply.messages : [];
    });
    state.lspQueue = task.catch(() => []);
    return task;
  }

  function lspRequest(method, params) {
    const id = state.rpcId++;
    return enqueueLsp({ jsonrpc: "2.0", id, method, params });
  }

  function lspNotify(method, params) {
    return enqueueLsp({ jsonrpc: "2.0", method, params });
  }

  function normalizeLines(text) {
    return text.replace(/\r\n/g, "\n").replace(/\r/g, "\n").split("\n");
  }

  function compilerToLspPosition(text, line, column) {
    const lines = normalizeLines(text);
    const safeLine = Math.max(1, Math.min(line, lines.length));
    const codePoints = Array.from(lines[safeLine - 1] ?? "");
    const safeColumn = Math.max(1, Math.min(column, codePoints.length + 1));
    const prefix = codePoints.slice(0, safeColumn - 1).join("");
    return { line: safeLine - 1, character: prefix.length };
  }

  function offsetToLspPosition(text, targetOffset) {
    const clamped = Math.max(0, Math.min(targetOffset, text.length));
    const breakPattern = /\r\n|\r|\n/g;
    let line = 0;
    let lineStart = 0;
    for (const match of text.matchAll(breakPattern)) {
      if (match.index >= clamped) {
        break;
      }
      line += 1;
      lineStart = match.index + match[0].length;
    }
    return { line, character: clamped - lineStart };
  }

  function lspPositionToOffset(text, position) {
    const breakPattern = /\r\n|\r|\n/g;
    let currentLine = 0;
    let start = 0;
    for (const match of text.matchAll(breakPattern)) {
      if (currentLine === position.line) {
        const end = match.index;
        return Math.min(start + position.character, end);
      }
      currentLine += 1;
      start = match.index + match[0].length;
    }
    return Math.min(start + position.character, text.length);
  }

  function revealRange(range) {
    const start = range.start;
    const end = range.end ?? range.start;
    if (state.editor && state.monaco) {
      const monacoRange = new state.monaco.Range(
        start.line + 1,
        start.character + 1,
        end.line + 1,
        end.character + 1
      );
      state.editor.setSelection(monacoRange);
      state.editor.revealRangeInCenter(monacoRange);
      state.editor.focus();
      return;
    }
    const startOffset = lspPositionToOffset(state.source, start);
    const endOffset = lspPositionToOffset(state.source, end);
    elements.fallbackEditor.focus();
    elements.fallbackEditor.setSelectionRange(startOffset, endOffset);
    updateCursorStatusFromFallback();
  }

  function clearMonacoOverlays() {
    if (state.editor) {
      state.inlayDecorations = state.editor.deltaDecorations(state.inlayDecorations, []);
      state.semanticDecorations = state.editor.deltaDecorations(state.semanticDecorations, []);
    }
  }

  function clearInspector(
    message = "Select a symbol or place the cursor on an identifier."
  ) {
    elements.symbolsList.replaceChildren();
    elements.symbolCount.textContent = "0";
    elements.hoverOutput.textContent = message;
    elements.referencesList.replaceChildren();
  }

  function clearAuthoring(
    status = "Source changed; run \u201cCheck style & preview\u201d for the current buffer."
  ) {
    state.latestPreview = null;
    elements.authoringList.replaceChildren();
    elements.authoringCount.textContent = "0";
    elements.previewOutput.textContent = "No preview computed for the current source.";
    elements.previewStatus.textContent = status;
    elements.applyPreviewButton.disabled = true;
  }

  function setEditorServicesAvailability(available, reason = null) {
    state.editorServicesAvailable = Boolean(available);
    elements.formatButton.disabled = !state.editorServicesAvailable;
    elements.authoringButton.disabled = !state.editorServicesAvailable;
    elements.typeHintsToggle.disabled = !state.editorServicesAvailable;
    elements.semanticTokensToggle.disabled = !state.editorServicesAvailable;
    if (!state.editorServicesAvailable) {
      clearMonacoOverlays();
      const detail =
        reason ??
        "Dependent mathematical source active: pure-only LSP, Format, lint and binding preview services are disabled.";
      clearInspector(detail);
      clearAuthoring(detail);
      setBadge(
        elements.scopeBadge,
        "Dependent mathematics \u00b7 unqualified elaborator",
        "warn"
      );
    } else {
      setBadge(
        elements.scopeBadge,
        state.mathematicalEnabled
          ? "Pure Nat/bool + LSP \u00b7 dependent math ready"
          : "Pure Nat/bool \u00b7 unqualified prototype",
        "neutral"
      );
    }
  }

  function invalidateStaleOutputs() {
    if (state.sourceCheckTimer !== null) {
      window.clearTimeout(state.sourceCheckTimer);
      state.sourceCheckTimer = null;
    }
    state.latestCompile = null;
    elements.gallinaOutput.textContent = "";
    elements.downloadGallinaButton.disabled = true;
    elements.consoleOutput.textContent =
      "Source changed. Click Evaluate to compute a compile-time value for the current buffer.";
    renderDiagnostics([]);
    clearMonacoOverlays();
    clearInspector("Analyzing current source version\u2026");
    clearAuthoring();
    if (!state.suppressUndoClear) {
      state.undoSnapshot = null;
      elements.undoPreviewButton.disabled = true;
    }
  }

  function scheduleAutomaticSourceCheck() {
    if (state.sourceCheckTimer !== null) {
      window.clearTimeout(state.sourceCheckTimer);
    }
    const expectedVersion = state.version;
    const expectedSource = state.source;
    state.sourceCheckTimer = window.setTimeout(() => {
      state.sourceCheckTimer = null;
      void runAutomaticSourceCheck(expectedVersion, expectedSource);
    }, 180);
  }

  function compilerErrorToDiagnostic(sourceText, error, sourceLabel) {
    const pos = compilerToLspPosition(sourceText, error.line ?? 1, error.column ?? 1);
    return {
      range: { start: pos, end: pos },
      severity: 1,
      code: error.kind ?? "error",
      source: sourceLabel,
      message: error.message ?? "Compilation refused",
    };
  }

  function findingToDiagnostic(sourceText, finding, sourceLabel) {
    const pos = compilerToLspPosition(sourceText, finding.line ?? 1, finding.column ?? 1);
    return {
      range: { start: pos, end: pos },
      severity: 2,
      code: finding.code ?? "VELA105",
      source: sourceLabel,
      message: finding.message ?? "Advisory naming finding",
    };
  }

  async function runAutomaticSourceCheck(expectedVersion, expectedSource) {
    if (expectedVersion !== state.version || expectedSource !== state.source) {
      return;
    }
    try {
      const response = await api("/api/compile", { source: expectedSource });
      if (expectedVersion !== state.version || expectedSource !== state.source) {
        return;
      }
      if (typeof response.editorServices === "boolean") {
        setEditorServicesAvailability(response.editorServices);
      }
      if (response.ok) {
        state.latestCompile = {
          source: expectedSource,
          version: expectedVersion,
          sourceHash: response.sourceHash,
          module: response.module,
          gallina: response.gallina,
        };
        elements.gallinaOutput.textContent = response.gallina;
        elements.downloadGallinaButton.disabled = false;
        if (!response.editorServices) {
          const findings = Array.isArray(response.findings) ? response.findings : [];
          renderDiagnostics(
            findings.map((item) =>
              findingToDiagnostic(expectedSource, item, "vela-math (unqualified)")
            )
          );
        } else {
          renderDiagnostics(state.latestDiagnostics);
          await refreshOverlayDecorations(expectedVersion);
        }
      } else if (!response.editorServices && response.error) {
        renderDiagnostics([
          compilerErrorToDiagnostic(
            expectedSource,
            response.error,
            "vela-math (unqualified)"
          ),
        ]);
      }
    } catch (error) {
      if (expectedVersion !== state.version || expectedSource !== state.source) {
        return;
      }
      setEditorServicesAvailability(
        false,
        `Compiler check unavailable (${error.message}); editor services disabled until a fresh check succeeds.`
      );
      setBadge(elements.connectionBadge, "Service error", "error");
    }
  }

  function renderDiagnostics(diagnostics) {
    elements.diagnosticsList.replaceChildren();
    elements.diagnosticCount.textContent = String(diagnostics.length);
    if (state.model && state.monaco) {
      const markers = diagnostics.map((diag) => ({
        startLineNumber: diag.range.start.line + 1,
        startColumn: diag.range.start.character + 1,
        endLineNumber: (diag.range.end?.line ?? diag.range.start.line) + 1,
        endColumn: Math.max(
          (diag.range.end?.character ?? diag.range.start.character) + 1,
          diag.range.start.character + 2
        ),
        message: diag.message,
        severity:
          diag.severity === 2
            ? state.monaco.MarkerSeverity.Warning
            : state.monaco.MarkerSeverity.Error,
        code: String(diag.code ?? ""),
        source: diag.source ?? "vela-lsp",
      }));
      state.monaco.editor.setModelMarkers(state.model, "vela-lsp", markers);
    }
    if (diagnostics.length === 0) {
      const item = document.createElement("li");
      item.className = "item-row muted";
      item.textContent = "No diagnostics for the current source snapshot.";
      elements.diagnosticsList.append(item);
      return;
    }
    for (const diag of diagnostics) {
      const item = document.createElement("li");
      item.className = "item-row";
      const button = document.createElement("button");
      button.type = "button";
      const line = diag.range.start.line + 1;
      const col = diag.range.start.character + 1;
      button.textContent = `[${diag.code ?? "diag"}] Line ${line}, Col ${col}: ${diag.message}`;
      button.addEventListener("click", () => revealRange(diag.range));
      item.append(button);
      elements.diagnosticsList.append(item);
    }
  }

  function handleLspMessages(messages, expectedVersion) {
    if (expectedVersion !== state.version) {
      return;
    }
    for (const message of messages) {
      if (message.method === "textDocument/publishDiagnostics") {
        const params = message.params ?? {};
        if (typeof params.version === "number" && params.version !== state.version) {
          continue;
        }
        state.latestDiagnostics = Array.isArray(params.diagnostics) ? params.diagnostics : [];
        if (state.editorServicesAvailable) {
          renderDiagnostics(state.latestDiagnostics);
        }
      }
    }
  }

  async function refreshOverlayDecorations(expectedVersion) {
    if (
      expectedVersion !== state.version ||
      !state.session ||
      !state.editorServicesAvailable
    ) {
      return;
    }
    const generation = state.sessionGeneration;
    const lineCount = normalizeLines(state.source).length;
    const fullRange = {
      start: { line: 0, character: 0 },
      end: { line: Math.max(0, lineCount - 1), character: 10000 },
    };

    const [symbolsReply, hintsReply, tokensReply] = await Promise.all([
      lspRequest("textDocument/documentSymbol", {
        textDocument: { uri: DOCUMENT_URI },
      }),
      elements.typeHintsToggle.checked
        ? lspRequest("textDocument/inlayHint", {
            textDocument: { uri: DOCUMENT_URI },
            range: fullRange,
          })
        : Promise.resolve([]),
      elements.semanticTokensToggle.checked
        ? lspRequest("textDocument/semanticTokens/full", {
            textDocument: { uri: DOCUMENT_URI },
          })
        : Promise.resolve([]),
    ]);

    if (
      expectedVersion !== state.version ||
      generation !== state.sessionGeneration ||
      !state.editorServicesAvailable
    ) {
      return;
    }

    const symbolsMsg = symbolsReply.find((item) => "result" in item);
    const symbols = Array.isArray(symbolsMsg?.result) ? symbolsMsg.result : [];
    renderSymbols(symbols, expectedVersion);

    if (state.editor && state.monaco) {
      const hintsMsg = hintsReply.find((item) => "result" in item);
      const hints =
        elements.typeHintsToggle.checked && Array.isArray(hintsMsg?.result)
          ? hintsMsg.result
          : [];
      state.inlayDecorations = state.editor.deltaDecorations(
        state.inlayDecorations,
        hints.map((hint) => ({
          range: new state.monaco.Range(
            hint.position.line + 1,
            hint.position.character + 1,
            hint.position.line + 1,
            hint.position.character + 1
          ),
          options: {
            after: {
              content: String(hint.label ?? ""),
              inlineClassName: "vela-inlay-hint",
            },
          },
        }))
      );

      const tokensMsg = tokensReply.find((item) => "result" in item);
      const data =
        elements.semanticTokensToggle.checked && Array.isArray(tokensMsg?.result?.data)
          ? tokensMsg.result.data
          : [];
      const semanticDecorations = [];
      let line = 0;
      let start = 0;
      for (let idx = 0; idx + 4 < data.length; idx += 5) {
        const deltaLine = data[idx];
        const deltaStart = data[idx + 1];
        const length = data[idx + 2];
        const tokenType = data[idx + 3];
        const modifiers = data[idx + 4];
        line += deltaLine;
        start = deltaLine === 0 ? start + deltaStart : deltaStart;
        const typeClass =
          tokenType === 0
            ? "vela-sem-function"
            : tokenType === 1
              ? "vela-sem-parameter"
              : "vela-sem-variable";
        const declClass = modifiers & 1 ? " vela-sem-declaration" : "";
        semanticDecorations.push({
          range: new state.monaco.Range(line + 1, start + 1, line + 1, start + length + 1),
          options: { inlineClassName: `${typeClass}${declClass}` },
        });
      }
      state.semanticDecorations = state.editor.deltaDecorations(
        state.semanticDecorations,
        semanticDecorations
      );
    }
  }

  function renderSymbols(symbols, expectedVersion) {
    elements.symbolsList.replaceChildren();
    elements.symbolCount.textContent = String(symbols.length);
    if (symbols.length === 0) {
      const empty = document.createElement("li");
      empty.className = "item-row muted";
      empty.textContent =
        "No resolved symbols (source may have a diagnostic or use unsupported syntax).";
      elements.symbolsList.append(empty);
      elements.hoverOutput.textContent =
        "Select a symbol or place the cursor on an identifier.";
      elements.referencesList.replaceChildren();
      return;
    }
    const kindNames = {
      12: "function",
      13: "binding",
      14: "constant",
    };
    for (const symbol of symbols) {
      const item = document.createElement("li");
      item.className = "item-row";
      const button = document.createElement("button");
      button.type = "button";
      const range = symbol.location?.range ?? {
        start: { line: 0, character: 0 },
        end: { line: 0, character: 0 },
      };
      const kindLabel = kindNames[symbol.kind] ?? "symbol";
      button.textContent = `${symbol.name} (${kindLabel}) \u00b7 L${range.start.line + 1}:${range.start.character + 1}`;
      button.addEventListener("click", () => {
        revealRange(range);
        void inspectAtPosition(range.start, expectedVersion);
      });
      item.append(button);
      elements.symbolsList.append(item);
    }
  }

  async function inspectAtPosition(position, expectedVersion = state.version) {
    if (
      !state.session ||
      expectedVersion !== state.version ||
      !state.editorServicesAvailable
    ) {
      return;
    }
    const generation = state.sessionGeneration;
    const [hoverMessages, defMessages, refMessages] = await Promise.all([
      lspRequest("textDocument/hover", {
        textDocument: { uri: DOCUMENT_URI },
        position,
      }),
      lspRequest("textDocument/definition", {
        textDocument: { uri: DOCUMENT_URI },
        position,
      }),
      lspRequest("textDocument/references", {
        textDocument: { uri: DOCUMENT_URI },
        position,
        context: { includeDeclaration: true },
      }),
    ]);

    if (
      expectedVersion !== state.version ||
      generation !== state.sessionGeneration ||
      !state.editorServicesAvailable
    ) {
      return;
    }

    const hover = hoverMessages.find((item) => "result" in item)?.result;
    const definition = defMessages.find((item) => "result" in item)?.result;
    const references = refMessages.find((item) => "result" in item)?.result;

    if (!hover?.contents?.value) {
      elements.hoverOutput.textContent = `No symbol at Line ${position.line + 1}, Col ${position.character + 1}.`;
      elements.referencesList.replaceChildren();
      return;
    }

    elements.hoverOutput.textContent = String(hover.contents.value);
    elements.referencesList.replaceChildren();

    if (definition?.range) {
      const defItem = document.createElement("li");
      defItem.className = "item-row";
      const defBtn = document.createElement("button");
      defBtn.type = "button";
      defBtn.textContent = `Definition \u00b7 Line ${definition.range.start.line + 1}, Col ${definition.range.start.character + 1}`;
      defBtn.addEventListener("click", () => revealRange(definition.range));
      defItem.append(defBtn);
      elements.referencesList.append(defItem);
    }

    const refList = Array.isArray(references) ? references : [];
    for (const ref of refList) {
      if (!ref?.range) {
        continue;
      }
      const item = document.createElement("li");
      item.className = "item-row";
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = `Occurrence \u00b7 Line ${ref.range.start.line + 1}, Col ${ref.range.start.character + 1}`;
      button.addEventListener("click", () => revealRange(ref.range));
      item.append(button);
      elements.referencesList.append(item);
    }
  }

  async function syncSourceChange(newText) {
    state.source = newText;
    state.version += 1;
    const currentVersion = state.version;
    invalidateStaleOutputs();
    scheduleAutomaticSourceCheck();
    try {
      const messages = await lspNotify("textDocument/didChange", {
        textDocument: { uri: DOCUMENT_URI, version: currentVersion },
        contentChanges: [{ text: newText }],
      });
      handleLspMessages(messages, currentVersion);
      await refreshOverlayDecorations(currentVersion);
    } catch (error) {
      if (error.status === 410) {
        await connectLsp("Session expired; reconnected a fresh LSP session.");
      } else {
        setBanner(`Language server update failed: ${error.message}`, "error");
      }
    }
  }

  function applySourceToEditor(newText, { preserveUndo = false } = {}) {
    state.suppressUndoClear = preserveUndo;
    try {
      if (state.model && state.editor) {
        state.applyingProgrammaticEdit = true;
        state.model.setValue(newText);
        state.applyingProgrammaticEdit = false;
      } else {
        elements.fallbackEditor.value = newText;
      }
      void syncSourceChange(newText);
    } finally {
      state.suppressUndoClear = false;
    }
  }

  async function connectLsp(bannerMessage = null) {
    const previous = state.session;
    state.session = null;
    state.sessionGeneration += 1;
    state.lspQueue = Promise.resolve();

    if (previous) {
      try {
        await api("/api/close", { session: previous });
      } catch {
        // Best-effort cleanup of the superseded session.
      }
    }

    try {
      const [capabilities, created] = await Promise.all([
        api("/api/capabilities", {}),
        api("/api/session", {}),
      ]);
      state.mathematicalEnabled = Boolean(capabilities.mathematical);
      state.session = created.session;
      setBadge(
        elements.connectionBadge,
        token ? "Connected (Local Worker)" : "Ready (In-Browser Engine)",
        "ok"
      );
      setEditorServicesAvailability(state.editorServicesAvailable);
      const openVersion = state.version;
      await lspRequest("initialize", { capabilities: {} });
      await lspNotify("initialized", {});
      const opened = await lspNotify("textDocument/didOpen", {
        textDocument: {
          uri: DOCUMENT_URI,
          languageId: "vela",
          version: openVersion,
          text: state.source,
        },
      });
      handleLspMessages(opened, openVersion);
      await refreshOverlayDecorations(openVersion);
      await runAutomaticSourceCheck(openVersion, state.source);
      if (bannerMessage) {
        setBanner(bannerMessage, "ok");
      } else {
        setBanner(
          token
            ? "Connected to local Vela playground worker (Pure + Dependent Mathematics + LSP)."
            : "Vela in-browser compiler, dependent mathematical elaborator, and LSP inspector ready.",
          "ok"
        );
      }
    } catch (error) {
      setBadge(elements.connectionBadge, "Disconnected", "error");
      setEditorServicesAvailability(
        false,
        `Language server connection failed (${error.message}); editor services disabled.`
      );
      setBanner(`Failed to initialize language server: ${error.message}`, "error");
    }
  }

  async function compileSource() {
    const requestedSource = state.source;
    const requestedVersion = state.version;
    setBanner("Compiling current source buffer\u2026");
    try {
      const response = await api("/api/compile", { source: requestedSource });
      if (requestedVersion !== state.version || requestedSource !== state.source) {
        return;
      }
      if (typeof response.editorServices === "boolean") {
        setEditorServicesAvailability(response.editorServices);
      }
      if (!response.ok) {
        state.latestCompile = null;
        elements.gallinaOutput.textContent = "";
        elements.downloadGallinaButton.disabled = true;
        const err = response.error;
        if (!response.editorServices) {
          renderDiagnostics([
            compilerErrorToDiagnostic(
              requestedSource,
              err,
              "vela-math (unqualified)"
            ),
          ]);
        }
        setBanner(
          `Compile refused (${err.kind} at L${err.line}:C${err.column}): ${err.message}`,
          "error"
        );
        selectTab("diagnostics");
        revealRange({
          start: compilerToLspPosition(requestedSource, err.line, err.column),
          end: compilerToLspPosition(requestedSource, err.line, err.column),
        });
        return;
      }
      state.latestCompile = {
        source: requestedSource,
        version: requestedVersion,
        sourceHash: response.sourceHash,
        module: response.module,
        gallina: response.gallina,
      };
      elements.gallinaOutput.textContent = response.gallina;
      elements.downloadGallinaButton.disabled = false;
      const findings = Array.isArray(response.findings) ? response.findings : [];
      if (!response.editorServices) {
        renderDiagnostics(
          findings.map((item) =>
            findingToDiagnostic(requestedSource, item, "vela-math (unqualified)")
          )
        );
      }
      const modeNote = response.editorServices
        ? "pure compiler"
        : `mathematical elaborator (${findings.length} naming warning${findings.length === 1 ? "" : "s"})`;
      setBanner(
        `Compiled module ${response.module} with the ${modeNote} (unqualified prototype; not a Rocq kernel verdict).`,
        "ok"
      );
      selectTab("gallina");
    } catch (error) {
      setEditorServicesAvailability(
        false,
        `Compile request failed (${error.message}); editor services disabled until a fresh check succeeds.`
      );
      setBanner(`Compile request failed: ${error.message}`, "error");
    }
  }

  async function evaluateExpression(event) {
    if (event) {
      event.preventDefault();
    }
    const requestedSource = state.source;
    const requestedVersion = state.version;
    const expression = elements.expressionInput.value;
    const valueType = elements.expressionType.value;
    setBanner(`Evaluating compile-time ${valueType} expression\u2026`);
    try {
      const response = await api("/api/evaluate", {
        source: requestedSource,
        expression,
        valueType,
      });
      if (
        requestedVersion !== state.version ||
        requestedSource !== state.source ||
        expression !== elements.expressionInput.value ||
        valueType !== elements.expressionType.value
      ) {
        return;
      }
      selectTab("console");
      if (!response.ok) {
        const err = response.error;
        elements.consoleOutput.textContent = [
          `Refused (${err.kind}) at Line ${err.line}, Column ${err.column}:`,
          err.message,
        ].join("\n");
        setBanner(`Expression refused (${err.kind}): ${err.message}`, "error");
        return;
      }
      const engineLabel = state.editorServicesAvailable
        ? "pure static evaluator"
        : "dependent mathematical reducer";
      elements.consoleOutput.textContent = [
        `Expression : ${expression}`,
        `Type       : ${response.valueType}`,
        `Value      : ${response.value}`,
        `Note       : Compile-time ${engineLabel} result (unqualified prototype; not native execution or kernel replay).`,
      ].join("\n");
      setBanner(`Compile-time result: ${response.value} : ${response.valueType}`, "ok");
    } catch (error) {
      setBanner(`Evaluation request failed: ${error.message}`, "error");
    }
  }

  async function formatSource() {
    if (!state.session || !state.editorServicesAvailable) {
      return;
    }
    const requestedSource = state.source;
    const requestedVersion = state.version;
    const generation = state.sessionGeneration;
    setBanner("Formatting current source buffer\u2026");
    try {
      const messages = await lspRequest("textDocument/formatting", {
        textDocument: { uri: DOCUMENT_URI },
        options: { tabSize: 4, insertSpaces: true },
      });
      if (
        requestedVersion !== state.version ||
        requestedSource !== state.source ||
        generation !== state.sessionGeneration
      ) {
        return;
      }
      const reply = messages.find((item) => "result" in item || "error" in item);
      if (reply?.error) {
        setBanner(`Formatting refused: ${reply.error.message}`, "error");
        return;
      }
      const edits = Array.isArray(reply?.result) ? reply.result : [];
      if (edits.length === 0) {
        setBanner("No formatting changes (buffer is already canonical or has errors).", "ok");
        return;
      }
      const newText = String(edits[0].newText ?? requestedSource);
      if (newText !== requestedSource) {
        applySourceToEditor(newText);
        setBanner("Formatted buffer with canonical Vela formatter.", "ok");
      }
    } catch (error) {
      setBanner(`Formatting request failed: ${error.message}`, "error");
    }
  }

  async function runAuthoringCheck() {
    if (!state.editorServicesAvailable) {
      setBanner(
        "Authoring lint and explicit-let preview are pure-only services.",
        "error"
      );
      return;
    }
    const requestedSource = state.source;
    const requestedVersion = state.version;
    setBanner("Running advisory style lint and explicit-let preview\u2026");
    try {
      const response = await api("/api/authoring", { source: requestedSource });
      if (requestedVersion !== state.version || requestedSource !== state.source) {
        return;
      }
      selectTab("authoring");
      if (!response.ok) {
        const err = response.error;
        clearAuthoring(`Authoring check refused (${err.kind}): ${err.message}`);
        setBanner(`Authoring check refused (${err.kind}): ${err.message}`, "error");
        return;
      }
      const findings = Array.isArray(response.findings) ? response.findings : [];
      elements.authoringList.replaceChildren();
      elements.authoringCount.textContent = String(findings.length);
      if (findings.length === 0) {
        const item = document.createElement("li");
        item.className = "item-row muted";
        item.textContent = "No advisory lint findings (VELA100\u2013VELA103).";
        elements.authoringList.append(item);
      } else {
        for (const finding of findings) {
          const item = document.createElement("li");
          item.className = "item-row";
          const button = document.createElement("button");
          button.type = "button";
          button.textContent = `[${finding.code}] Line ${finding.line}, Col ${finding.column}: ${finding.message}`;
          const pos = compilerToLspPosition(requestedSource, finding.line, finding.column);
          button.addEventListener("click", () => revealRange({ start: pos, end: pos }));
          item.append(button);
          elements.authoringList.append(item);
        }
      }

      const preview = String(response.bindingPreview ?? requestedSource);
      elements.previewOutput.textContent = preview;
      if (preview !== requestedSource) {
        state.latestPreview = {
          source: requestedSource,
          version: requestedVersion,
          sourceHash: response.sourceHash,
          candidate: preview,
        };
        elements.applyPreviewButton.disabled = false;
        elements.previewStatus.textContent =
          "Candidate explicit-let insertion available for this exact snapshot.";
      } else {
        state.latestPreview = null;
        elements.applyPreviewButton.disabled = true;
        elements.previewStatus.textContent =
          "All local bindings already spell explicit let.";
      }
      setBanner(`Authoring check complete (${findings.length} advisory finding(s)).`, "ok");
    } catch (error) {
      setBanner(`Authoring request failed: ${error.message}`, "error");
    }
  }

  function applyBindingPreview() {
    const preview = state.latestPreview;
    if (
      !preview ||
      preview.version !== state.version ||
      preview.source !== state.source
    ) {
      clearAuthoring("Preview is stale for the current buffer; re-run the authoring check.");
      setBanner("Refused to apply a stale binding preview.", "error");
      return;
    }
    state.undoSnapshot = state.source;
    elements.undoPreviewButton.disabled = false;
    applySourceToEditor(preview.candidate, { preserveUndo: true });
    elements.previewStatus.textContent =
      "Applied explicit-let preview. Use Undo to restore the previous snapshot.";
    setBanner("Applied explicit-let binding preview.", "ok");
  }

  function undoBindingPreview() {
    if (state.undoSnapshot === null) {
      return;
    }
    const previous = state.undoSnapshot;
    state.undoSnapshot = null;
    elements.undoPreviewButton.disabled = true;
    applySourceToEditor(previous);
    setBanner("Restored snapshot from before explicit-let preview.", "ok");
  }

  function triggerDownload(filename, content) {
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.append(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 0);
  }

  function renderSuggestions(suggestions) {
    elements.expressionSuggestions.replaceChildren();
    const label = document.createElement("span");
    label.className = "muted";
    label.textContent = "Try:";
    elements.expressionSuggestions.append(label);
    for (const item of suggestions) {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "suggestion-chip";
      chip.textContent = `${item.expression} : ${item.valueType}`;
      chip.addEventListener("click", () => {
        elements.expressionInput.value = item.expression;
        elements.expressionType.value = item.valueType;
        void evaluateExpression();
      });
      elements.expressionSuggestions.append(chip);
    }
  }

  function loadExample(name, { scrollIntoView = false } = {}) {
    const example = EXAMPLES[name];
    if (!example) {
      return;
    }
    elements.exampleSelect.value = name;
    elements.expressionInput.value = example.expression;
    elements.expressionType.value = example.valueType;
    renderSuggestions(example.suggestions);
    applySourceToEditor(example.source);
    if (scrollIntoView) {
      const playgroundEl = document.getElementById("playground");
      if (playgroundEl) {
        playgroundEl.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }
  }

  function updateCursorStatusFromFallback() {
    const offset = elements.fallbackEditor.selectionStart ?? 0;
    const pos = offsetToLspPosition(state.source, offset);
    elements.cursorStatus.textContent = `Line ${pos.line + 1}, Col ${pos.character + 1}`;
    void inspectAtPosition(pos, state.version);
  }

  function enableFallbackEditor(reason) {
    elements.monacoContainer.hidden = true;
    elements.fallbackEditor.hidden = false;
    elements.fallbackEditor.value = state.source;
    setBadge(elements.editorModeBadge, "Plain-text fallback", "warn");
    setBanner(
      `${reason} Plain-text editing, Compile, Evaluate, Format and Inspector panels remain active.`,
      "error"
    );
  }

  function registerVelaLanguage(monaco) {
    monaco.languages.register({ id: "vela" });
    monaco.languages.setMonarchTokensProvider("vela", {
      keywords: [
        "module",
        "import",
        "public",
        "private",
        "return",
        "let",
        "var",
        "const",
        "if",
        "else",
        "is",
        "match",
        "with",
        "definition",
        "record",
        "union",
        "interface",
        "impl",
        "struct",
        "open",
        "lifts",
        "foreach",
        "while",
        "invariant",
        "decreases",
        "where",
        "theorem",
        "lemma",
        "ensures",
        "requires",
        "restores",
        "proof",
        "calc",
        "assert",
        "by",
        "ghost",
        "tracked",
        "in",
        "ref",
        "out",
        "owned",
        "move",
        "Fn",
        "forall",
        "exists",
      ],
      typeKeywords: [
        "Nat",
        "bool",
        "String",
        "TextBuilder",
        "Vec",
        "Fin",
        "Seq",
        "Span",
        "Slots",
        "Option",
        "Result",
        "Type",
        "Prop",
        "Unit",
        "u8",
        "u16",
        "u32",
        "u64",
        "usize",
        "byte",
        "i8",
        "i16",
        "i32",
        "i64",
      ],
      constants: [
        "true",
        "false",
        "Zero",
        "Succ",
        "VNil",
        "VCons",
        "FZero",
        "FSucc",
        "Some",
        "None",
        "Ok",
        "Err",
      ],
      tokenizer: {
        root: [
          [/\/\/\/.*$/, "comment.doc"],
          [/\/\/.*$/, "comment"],
          [/"""/, { token: "string.quote", next: "@rawString" }],
          [/\$"/, { token: "string.quote", next: "@formatString" }],
          [/"([^"\\]|\\.)*$/, "string.invalid"],
          [/"/, { token: "string.quote", next: "@quotedString" }],
          [/\b[0-9](?:_?[0-9])*\b/, "number"],
          [
            /[A-Za-z_][A-Za-z0-9_]*/,
            {
              cases: {
                "@keywords": "keyword",
                "@typeKeywords": "type.identifier",
                "@constants": "constant.language",
                "@default": "identifier",
              },
            },
          ],
          [/=>|==|!=|<=|>=|&&|\|\||[+\-*/%<>!=]/, "operator"],
          [/[{}()[\],;:]/, "delimiter"],
        ],
        rawString: [
          [/"""+/, { token: "string.quote", next: "@pop" }],
          [/[^"]+/, "string"],
          [/"/, "string"],
        ],
        quotedString: [
          [/[^\\"]+/, "string"],
          [/\\./, "string.escape"],
          [/"/, { token: "string.quote", next: "@pop" }],
        ],
        formatString: [
          [/\{\{|\}\}/, "string.escape"],
          [/\{/, { token: "delimiter.bracket", next: "@formatHole" }],
          [/[^\\"{]+/, "string"],
          [/\\./, "string.escape"],
          [/"/, { token: "string.quote", next: "@pop" }],
        ],
        formatHole: [
          [/\}/, { token: "delimiter.bracket", next: "@pop" }],
          { include: "root" },
        ],
      },
    });

    monaco.editor.defineTheme("vela-night", {
      base: "vs-dark",
      inherit: true,
      rules: [
        { token: "comment.doc", foreground: "7dcfff" },
        { token: "keyword", foreground: "bb9af7" },
        { token: "type.identifier", foreground: "2ac3de" },
        { token: "constant.language", foreground: "ff9e64" },
        { token: "number", foreground: "e0af68" },
      ],
      colors: {
        "editor.background": "#10141c",
      },
    });
  }

  function loadMonaco() {
    return new Promise((resolve, reject) => {
      const loaderScript = document.createElement("script");
      loaderScript.src = `${MONACO_BASE}/vs/loader.js`;
      loaderScript.async = true;
      loaderScript.onload = () => {
        if (!window.require?.config) {
          reject(new Error("Monaco AMD loader unavailable."));
          return;
        }
        window.MonacoEnvironment = {
          getWorkerUrl() {
            const workerSource = [
              `self.MonacoEnvironment = { baseUrl: "${MONACO_BASE}/" };`,
              `importScripts("${MONACO_BASE}/vs/base/worker/workerMain.js");`,
            ].join("\n");
            return `data:text/javascript;charset=utf-8,${encodeURIComponent(workerSource)}`;
          },
        };
        window.require.config({ paths: { vs: `${MONACO_BASE}/vs` } });
        window.require(
          ["vs/editor/editor.main"],
          () => resolve(window.monaco),
          (err) => reject(new Error(err?.message ?? "Monaco module load failed."))
        );
      };
      loaderScript.onerror = () =>
        reject(new Error(`Could not load Monaco ${MONACO_VERSION} from jsDelivr.`));
      document.head.append(loaderScript);
    });
  }

  async function initEditor() {
    elements.fallbackEditor.value = state.source;
    try {
      const monaco = await loadMonaco();
      state.monaco = monaco;
      registerVelaLanguage(monaco);
      state.model = monaco.editor.createModel(
        state.source,
        "vela",
        monaco.Uri.parse(DOCUMENT_URI)
      );
      state.editor = monaco.editor.create(elements.monacoContainer, {
        model: state.model,
        theme: "vela-night",
        automaticLayout: true,
        minimap: { enabled: false },
        fontSize: 13,
        lineNumbersMinChars: 3,
        scrollBeyondLastLine: false,
        tabSize: 4,
        insertSpaces: true,
      });
      setBadge(elements.editorModeBadge, `Monaco ${MONACO_VERSION}`, "ok");

      state.model.onDidChangeContent(() => {
        if (state.applyingProgrammaticEdit) {
          return;
        }
        void syncSourceChange(state.model.getValue());
      });

      state.editor.onDidChangeCursorPosition((event) => {
        const pos = {
          line: event.position.lineNumber - 1,
          character: event.position.column - 1,
        };
        elements.cursorStatus.textContent = `Line ${event.position.lineNumber}, Col ${event.position.column}`;
        void inspectAtPosition(pos, state.version);
      });

      state.editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
        void compileSource();
      });
      state.editor.addCommand(
        monaco.KeyMod.Shift | monaco.KeyMod.Alt | monaco.KeyCode.KeyF,
        () => {
          void formatSource();
        }
      );
    } catch (error) {
      enableFallbackEditor(error.message);
    }
  }

  function wireEvents() {
    for (const tab of elements.tabs) {
      tab.addEventListener("click", () => selectTab(tab.dataset.panel));
    }
    elements.exampleSelect.addEventListener("change", () =>
      loadExample(elements.exampleSelect.value)
    );
    elements.compileButton.addEventListener("click", () => void compileSource());
    elements.formatButton.addEventListener("click", () => void formatSource());
    elements.authoringButton.addEventListener("click", () => void runAuthoringCheck());
    elements.applyPreviewButton.addEventListener("click", () => applyBindingPreview());
    elements.undoPreviewButton.addEventListener("click", () => undoBindingPreview());
    elements.evaluateForm.addEventListener(
      "submit",
      (event) => void evaluateExpression(event)
    );

    elements.downloadSourceButton.addEventListener("click", () => {
      triggerDownload("playground.vela", state.source);
    });
    elements.downloadGallinaButton.addEventListener("click", () => {
      if (state.latestCompile && state.latestCompile.version === state.version) {
        triggerDownload(`${state.latestCompile.module}.v`, state.latestCompile.gallina);
      }
    });

    elements.typeHintsToggle.addEventListener("change", () => {
      void refreshOverlayDecorations(state.version);
    });
    elements.semanticTokensToggle.addEventListener("change", () => {
      void refreshOverlayDecorations(state.version);
    });

    elements.fallbackEditor.addEventListener("input", () => {
      void syncSourceChange(elements.fallbackEditor.value);
    });
    elements.fallbackEditor.addEventListener("click", updateCursorStatusFromFallback);
    elements.fallbackEditor.addEventListener("keyup", updateCursorStatusFromFallback);

    for (const btn of document.querySelectorAll("[data-load-example]")) {
      btn.addEventListener("click", () => {
        const exampleKey = btn.getAttribute("data-load-example");
        if (exampleKey && EXAMPLES[exampleKey]) {
          loadExample(exampleKey, { scrollIntoView: true });
        }
      });
    }

    window.addEventListener("keydown", (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
        event.preventDefault();
        void compileSource();
      } else if (event.shiftKey && event.altKey && event.key.toLowerCase() === "f") {
        event.preventDefault();
        void formatSource();
      }
    });

    window.addEventListener("pagehide", () => {
      if (state.session) {
        void api("/api/close", { session: state.session }, { keepalive: true }).catch(
          () => {}
        );
      }
    });
  }

  async function boot() {
    wireEvents();
    elements.expressionInput.value = EXAMPLES.squares.expression;
    elements.expressionType.value = EXAMPLES.squares.valueType;
    renderSuggestions(EXAMPLES.squares.suggestions);
    await Promise.all([initEditor(), connectLsp()]);
  }

  void boot();
}

if (typeof document !== "undefined") {
  initPlaygroundUi();
}
