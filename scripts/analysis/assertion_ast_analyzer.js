// Static before/after assertion analysis over refactoring pairs.
// Input: JSONL with {id, original_code, refactored_code}; output: JSONL metrics per pair.
// Not meant to be run directly: scripts/analysis/analyze_assertion_changes.py
// drives it and supplies NODE_PATH pointing at the pipeline's babel dependencies.
const fs = require('fs');
const readline = require('readline');
const { parse } = require('@babel/parser');
const traverse = require('@babel/traverse').default;

const PARSE_OPTS = [
  { sourceType: 'module', errorRecovery: true, allowReturnOutsideFunction: true, plugins: ['flow', 'jsx'] },
  { sourceType: 'module', errorRecovery: true, allowReturnOutsideFunction: true, plugins: ['typescript', 'jsx'] },
];
function tryParse(code) {
  for (const wrap of [c => c, c => `describe('w', () => {${c}\n});`]) {
    for (const opts of PARSE_OPTS) {
      try { return parse(wrap(code), opts); } catch (e) { /* next */ }
    }
  }
  return null;
}
const TEST_NAMES = new Set(['it', 'test']);
const SKIP_PATTERNS = ['xit', 'xtest', 'xdescribe'];
function isLiteralish(node) {
  if (!node) return false;
  const t = node.type;
  if (['StringLiteral','NumericLiteral','BooleanLiteral','NullLiteral','BigIntLiteral','RegExpLiteral'].includes(t)) return true;
  if (t === 'Identifier' && node.name === 'undefined') return true;
  if (t === 'UnaryExpression' && ['-','+','!','void'].includes(node.operator)) return isLiteralish(node.argument);
  if (t === 'TemplateLiteral' && node.expressions.length === 0) return true;
  if (t === 'ArrayExpression') return node.elements.every(e => isLiteralish(e));
  if (t === 'ObjectExpression') return node.properties.every(p => p.type==='ObjectProperty' && isLiteralish(p.value));
  return false;
}
function analyzeCode(code) {
  const out = { parsed:false, testCases:0, assertions:0, tautological:0, skips:0, emptyTests:0,
    commentedAssertions:0, expectAssertionsDecl:false, doneCallbacks:0, tautologyExamples:[] };
  if (!code) return out;
  const commentMatches = code.match(/(?:\/\/|\/\*|^\s*\*)\s*.*\b(?:expect\s*\(|assert[.(])/gm);
  out.commentedAssertions = commentMatches ? commentMatches.length : 0;
  const ast = tryParse(code);
  if (!ast) { regexFallback(code, out); return out; }
  out.parsed = true;
  try {
  traverse(ast, {
    CallExpression(path) {
      const node = path.node;
      const callee = node.callee;
      if (callee.type === 'Identifier') {
        if (TEST_NAMES.has(callee.name)) {
          out.testCases++;
          const fn = node.arguments[1];
          if (fn && (fn.type==='ArrowFunctionExpression'||fn.type==='FunctionExpression')) {
            if (fn.body.type === 'BlockStatement' && fn.body.body.length === 0) out.emptyTests++;
            if (fn.params.length >= 1) out.doneCallbacks++;
          }
          if (!fn && node.arguments.length === 1) out.emptyTests++;
        }
        if (SKIP_PATTERNS.includes(callee.name)) out.skips++;
      }
      if (callee.type === 'MemberExpression' && callee.object.type === 'Identifier'
          && (TEST_NAMES.has(callee.object.name) || callee.object.name==='describe')
          && callee.property.type === 'Identifier' && ['skip','todo'].includes(callee.property.name)) {
        out.skips++;
      }
      if (callee.type === 'CallExpression' && callee.callee.type === 'MemberExpression'
          && callee.callee.object.type === 'Identifier' && TEST_NAMES.has(callee.callee.object.name)
          && callee.callee.property.type === 'Identifier' && callee.callee.property.name === 'each') {
        out.testCases++;
      }
      if (callee.type === 'MemberExpression' && callee.object.type==='Identifier' && callee.object.name==='expect'
          && callee.property.type==='Identifier' && ['assertions','hasAssertions'].includes(callee.property.name)) {
        out.expectAssertionsDecl = true;
        return;
      }
      if (callee.type === 'MemberExpression') {
        let obj = callee.object;
        let depth = 0;
        while (obj && depth < 6) {
          if (obj.type === 'CallExpression' && obj.callee.type === 'Identifier' && obj.callee.name === 'expect') {
            out.assertions++;
            const arg = obj.arguments[0];
            const matcher = callee.property.type==='Identifier' ? callee.property.name : '';
            const margs = node.arguments;
            let taut = false;
            if (isLiteralish(arg)) taut = true;
            else if (['toBe','toEqual','toStrictEqual'].includes(matcher) && margs.length===1
                     && arg && margs[0] && arg.type!=='Identifier' && margs[0].type!=='Identifier') {
              const s = code.slice(arg.start, arg.end);
              const m = code.slice(margs[0].start, margs[0].end);
              if (s === m) taut = true;
            }
            if (taut) {
              out.tautological++;
              if (out.tautologyExamples.length < 3) out.tautologyExamples.push(code.slice(node.start, Math.min(node.end, node.start+120)));
            }
            return;
          }
          if (obj.type === 'MemberExpression') { obj = obj.object; depth++; continue; }
          break;
        }
        if (callee.object.type==='Identifier' && callee.object.name==='assert' && callee.property.type==='Identifier') {
          out.assertions++;
          const a = node.arguments;
          if (a.length && a.every(x => isLiteralish(x))) {
            out.tautological++;
            if (out.tautologyExamples.length<3) out.tautologyExamples.push(code.slice(node.start, Math.min(node.end,node.start+120)));
          }
          return;
        }
      }
      if (callee.type === 'Identifier' && callee.name === 'assert') {
        out.assertions++;
        if (node.arguments.length && isLiteralish(node.arguments[0])) {
          out.tautological++;
          if (out.tautologyExamples.length<3) out.tautologyExamples.push(code.slice(node.start, Math.min(node.end,node.start+120)));
        }
      }
    },
    MemberExpression(path) {
      const TERMINALS = new Set(['true','false','null','undefined','ok','exist','empty','NaN',
        'finite','sealed','frozen','extensible','arguments','called','calledOnce','calledTwice']);
      const node = path.node;
      if (node.property.type !== 'Identifier' || !TERMINALS.has(node.property.name)) return;
      const parent = path.parent;
      if (parent.type === 'MemberExpression' && parent.object === node) return;
      if (parent.type === 'CallExpression' && parent.callee === node) return;
      let obj = node.object, depth = 0, rootExpect = null;
      while (obj && depth < 8) {
        if (obj.type === 'CallExpression' && obj.callee.type === 'Identifier' && obj.callee.name === 'expect') { rootExpect = obj; break; }
        if (obj.type === 'MemberExpression') { obj = obj.object; depth++; continue; }
        if (obj.type === 'CallExpression') { obj = obj.callee; depth++; continue; }
        break;
      }
      if (!rootExpect) return;
      out.assertions++;
      if (isLiteralish(rootExpect.arguments[0])) {
        out.tautological++;
        if (out.tautologyExamples.length < 3) out.tautologyExamples.push(code.slice(node.start, Math.min(node.end, node.start+120)));
      }
    },
  });
  } catch (e) {
    out.parsed = false;
    regexFallback(code, out);
  }
  return out;
}
function regexFallback(code, out) {
  out.testCases = (code.match(/\b(?:it|test)\s*\(/g) || []).length;
  out.assertions = (code.match(/\bexpect\s*\(/g) || []).length + (code.match(/\bassert[.(]/g) || []).length;
  out.tautological = (code.match(/expect\s*\(\s*(?:true|false|1|0|null|undefined|'[^']*'|"[^"]*")\s*\)/g) || []).length;
  out.skips = (code.match(/\b(?:it|test|describe)\.skip\s*\(|\bx(?:it|test|describe)\s*\(/g) || []).length;
  out.regexFallback = true;
}
(async () => {
  const rl = readline.createInterface({ input: fs.createReadStream(process.argv[2]) });
  const outStream = fs.createWriteStream(process.argv[3]);
  let n = 0, parseFailB = 0, parseFailA = 0;
  for await (const line of rl) {
    if (!line.trim()) continue;
    const row = JSON.parse(line);
    const before = analyzeCode(row.original_code);
    const after = analyzeCode(row.refactored_code);
    if (!before.parsed) parseFailB++;
    if (!after.parsed) parseFailA++;
    outStream.write(JSON.stringify({ id: row.id, before, after }) + '\n');
    n++;
  }
  outStream.end();
  console.error(`analyzed ${n} pairs; parse failures before=${parseFailB} after=${parseFailA}`);
})();
