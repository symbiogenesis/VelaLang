// SPDX-License-Identifier: Apache-2.0
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const [grammarPath, textmatePath, onigurumaPath, fixturePath] = process.argv.slice(2);
const textmate = require(path.join(textmatePath, 'release/main.js'));
const oniguruma = require(path.join(onigurumaPath, 'release/main.js'));
const wasm = fs.readFileSync(path.join(onigurumaPath, 'release/onig.wasm'));
await oniguruma.loadWASM(wasm.buffer.slice(wasm.byteOffset, wasm.byteOffset + wasm.byteLength));
const registry = new textmate.Registry({
  onigLib: Promise.resolve({
    createOnigScanner(patterns) { return new oniguruma.OnigScanner(patterns); },
    createOnigString(value) { return new oniguruma.OnigString(value); }
  }),
  loadGrammar: async () => textmate.parseRawGrammar(fs.readFileSync(grammarPath, 'utf8'), grammarPath)
});
const grammar = await registry.loadGrammar('source.vela');
const cases = JSON.parse(fs.readFileSync(fixturePath, 'utf8'));
const observations = [];
for (const fixture of cases) {
  let state = textmate.INITIAL;
  let offset = 0;
  const spans = [];
  for (const line of fixture.source.split('\n')) {
    const result = grammar.tokenizeLine(line, state, 100);
    if (result.stoppedEarly) throw new Error('TextMate tokenization budget exhausted');
    for (const token of result.tokens) {
      spans.push({start: offset + token.startIndex, end: offset + token.endIndex, scopes: token.scopes});
    }
    state = result.ruleStack;
    offset += line.length + 1;
  }
  const assertions = [];
  for (const expected of fixture.scopes) {
    const index = fixture.source.indexOf(expected.text);
    if (index < 0) throw new Error('Expected text absent from fixture');
    const span = spans.find(item => item.start <= index && item.end > index);
    if (!span || !span.scopes.includes(expected.scope)) {
      throw new Error(`${fixture.name}: ${expected.text}: expected ${expected.scope}; got ${JSON.stringify(span)}`);
    }
    assertions.push({text: expected.text, utf16Offset: index, scope: expected.scope});
  }
  observations.push({name: fixture.name, assertions, spans});
}
console.log(JSON.stringify({engine: 'vscode-textmate', version: '9.2.0', observations}));
