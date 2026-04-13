'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const TRANSFORM_PATH = process.env.TRANSFORM_PATH
  || path.join(__dirname, '../../plugin/src/transform.js');
const TEST_DATA_PATH = process.env.TEST_DATA_PATH
  || path.join(__dirname, 'data/sample.json');

// ---------------------------------------------------------------------------
// Load and sandbox transform.js
// ---------------------------------------------------------------------------
function runTransform(input) {
  const code = fs.readFileSync(TRANSFORM_PATH, 'utf-8');

  const sandbox = {
    Date,
    Array,
    Object,
    String,
    Number,
    Boolean,
    RegExp,
    Math,
    JSON,
    console,
    parseInt,
    parseFloat,
    isNaN,
    isFinite,
    undefined,
  };

  vm.createContext(sandbox);
  vm.runInContext(code, sandbox);
  return vm.runInContext('transform(__input__)', Object.assign(sandbox, { __input__: input }));
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------
async function main() {
  let testData;
  try {
    testData = JSON.parse(fs.readFileSync(TEST_DATA_PATH, 'utf-8'));
  } catch (e) {
    console.error(`Cannot load test data from ${TEST_DATA_PATH}: ${e.message}`);
    process.exit(1);
  }

  // Support single input object or array of named test cases:
  // [{ "name": "case 1", "input": { ... } }, ...]
  const cases = Array.isArray(testData)
    ? testData
    : [{ name: 'default', input: testData }];

  let failed = 0;

  for (const tc of cases) {
    const name = tc.name || 'unnamed';
    const input = tc.input !== undefined ? tc.input : tc;

    try {
      const result = runTransform(input);
      console.log(`\n✓ ${name}`);
      console.log(JSON.stringify(result, null, 2));
    } catch (e) {
      console.error(`\n✗ ${name}: ${e.message}`);
      failed++;
    }
  }

  if (failed > 0) {
    console.error(`\n${failed} case(s) failed`);
    process.exit(1);
  }

  console.log('\nAll cases passed');
}

main().catch(err => {
  console.error(`Fatal: ${err.message}`);
  process.exit(1);
});
