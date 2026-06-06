import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { DATA_DIR, STATE_FILE, log } from "./lib.mjs";

const HOOK = "toggle";

// "on" unless the state file explicitly says "off" (matches isDisabled).
function currentState() {
  try {
    return readFileSync(STATE_FILE, "utf8").trim() === "off" ? "off" : "on";
  } catch {
    return "on"; // no file yet => enabled
  }
}

function setState(state) {
  mkdirSync(DATA_DIR, { recursive: true });
  writeFileSync(STATE_FILE, state + "\n");
}

const arg = (process.argv[2] || "").trim().toLowerCase();
const before = currentState();

let next;
if (arg === "on" || arg === "off") {
  next = arg;
} else if (arg === "" || arg === "toggle") {
  next = before === "on" ? "off" : "on";
} else if (arg === "status") {
  next = before; // report only, no change
} else {
  console.log(`plainly: unknown argument "${arg}". Use on, off, or status.`);
  log({ hook: HOOK, action: "error", stage: "bad-arg", arg });
  process.exit(0);
}

if (arg !== "status" && next !== before) {
  setState(next);
}

const verb = arg === "status" ? "is" : "is now";
console.log(`plainly ${verb} ${next.toUpperCase()}.`);

log({
  hook: HOOK,
  action: arg === "status" ? "status" : "set",
  before,
  after: next,
});
