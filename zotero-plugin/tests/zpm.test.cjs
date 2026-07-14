const assert = require("node:assert/strict");
const test = require("node:test");

const {
  zpmCommandArguments,
  zpmCreatorName,
  zpmTrimOutput,
} = require("../zpm.js");

test("creator names prefer the family name and degrade safely", () => {
  assert.equal(zpmCreatorName({ firstName: "Ada", lastName: "Lovelace" }), "Lovelace");
  assert.equal(zpmCreatorName({ name: "CERN" }), "CERN");
  assert.equal(zpmCreatorName({ firstName: "Plato" }), "Plato");
});

test("plugin export arguments preserve values without shell interpolation", () => {
  assert.deepEqual(
    zpmCommandArguments(
      "/tmp/request with spaces.json",
      "A;NOT-A-COMMAND",
      "/Users/Test/Research Projects",
      true,
      "bundle",
    ),
    [
      "plugin-export",
      "/tmp/request with spaces.json",
      "A;NOT-A-COMMAND",
      "--output",
      "/Users/Test/Research Projects",
      "--annotation-layout",
      "bundle",
      "--annotations",
    ],
  );
});

test("process output is bounded before display", () => {
  assert.equal(zpmTrimOutput("  ready  "), "ready");
  assert.match(zpmTrimOutput("x".repeat(13000)), /output truncated/);
});
