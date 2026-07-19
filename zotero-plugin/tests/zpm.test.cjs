const assert = require("node:assert/strict");
const test = require("node:test");

const {
  zpmCreatorName,
  zpmTrimOutput,
} = require("../zpm.js");

test("creator names prefer the family name and degrade safely", () => {
  assert.equal(zpmCreatorName({ firstName: "Ada", lastName: "Lovelace" }), "Lovelace");
  assert.equal(zpmCreatorName({ name: "CERN" }), "CERN");
  assert.equal(zpmCreatorName({ firstName: "Plato" }), "Plato");
});

test("process output is bounded before display", () => {
  assert.equal(zpmTrimOutput("  ready  "), "ready");
  assert.match(zpmTrimOutput("x".repeat(13000)), /output truncated/);
});
