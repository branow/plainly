import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

const configDir = process.env.CLAUDE_CONFIG_DIR || join(homedir(), ".claude");
const state = join(configDir, "plainly.state");
try {
  if (readFileSync(state, "utf8").trim() === "off") process.exit(0);
} catch {}

const prompt = join(process.env.CLAUDE_PLUGIN_ROOT, "prompt", "plainly.md");
process.stdout.write(readFileSync(prompt, "utf8"));
