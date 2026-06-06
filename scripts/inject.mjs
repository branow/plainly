import { readFileSync } from "node:fs";
import { join } from "node:path";
import { parseStdin, isDisabled, log } from "./lib.mjs";

const HOOK = "inject";

const input = parseStdin(HOOK);
const session = input.session_id || "unknown";

if (isDisabled(HOOK)) {
  log({ hook: HOOK, session, action: "skip", reason: "disabled" });
  process.exit(0);
}

const promptPath = join(
  process.env.CLAUDE_PLUGIN_ROOT || "",
  "prompt",
  "plainly.md",
);

let text;
try {
  text = readFileSync(promptPath, "utf8");
} catch (e) {
  log({
    hook: HOOK,
    session,
    action: "error",
    stage: "read-prompt",
    error: e.message,
    code: e.code,
    path: promptPath,
  });
  process.exit(0);
}

process.stdout.write(text);

log({
  hook: HOOK,
  session,
  action: "inject",
  bytes: text.length,
  source: input.source,
});
