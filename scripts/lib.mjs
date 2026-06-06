import {
  readFileSync,
  writeFileSync,
  appendFileSync,
  mkdirSync,
  statSync,
} from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

const CONFIG_DIR =
  process.env.CLAUDE_CONFIG_DIR || join(homedir(), ".claude");

// Per-plugin persistent dir managed by Claude Code
// (~/.claude/plugins/data/<id>/). CLAUDE_PLUGIN_DATA is provided to plugin
// hooks; the fallback keeps the scripts working when run outside the plugin
// runtime, e.g. in tests.
export const DATA_DIR =
  process.env.CLAUDE_PLUGIN_DATA ||
  join(CONFIG_DIR, "plugins", "data", "plainly-plainly");

export const STATE_FILE = join(DATA_DIR, "plainly.state");

const LOG_FILE = join(DATA_DIR, "plainly.log");
const LOG_MAX_BYTES = 1024 * 1024; // safety cap on runaway log growth

function metricsFile(sessionId) {
  return join(DATA_DIR, `metrics-${sessionId}.json`);
}

// Create the data dir if missing. Returns true on success.
function ensureDir() {
  try {
    mkdirSync(DATA_DIR, { recursive: true });
    return true;
  } catch {
    return false;
  }
}

// Append one JSON line to the log. Never throws: if the log file itself
// can't be written, fall back to stderr so the failure is still visible in
// hook debug output instead of vanishing silently.
export function log(entry) {
  try {
    ensureDir();

    const record = { ts: new Date().toISOString(), ...entry };
    const line = JSON.stringify(record) + "\n";

    let size = 0;
    try {
      size = statSync(LOG_FILE).size;
    } catch {
      // No log file yet; size stays 0.
    }

    if (size >= LOG_MAX_BYTES) {
      trimAndAppend(line);
    } else {
      appendFileSync(LOG_FILE, line);
    }
  } catch (e) {
    try {
      process.stderr.write(`plainly: log write failed: ${e.message}\n`);
    } catch {
      // Nothing left to do.
    }
  }
}

// Over the cap: keep the most recent half of the log and drop the oldest
// half, then append the new line. Bounds the file without losing recent
// history.
function trimAndAppend(line) {
  const data = readFileSync(LOG_FILE, "utf8");
  let kept = data.slice(Math.floor(data.length / 2));

  // The slice likely starts mid-line; drop that partial line so every
  // remaining line stays valid JSON.
  const firstNewline = kept.indexOf("\n");
  kept = firstNewline >= 0 ? kept.slice(firstNewline + 1) : "";

  writeFileSync(LOG_FILE, kept + line);
}

// Record a failure to the log. Used by the file helpers below.
function logError(hook, stage, e, extra = {}) {
  log({
    hook,
    action: "error",
    stage,
    error: e && e.message,
    code: e && e.code,
    ...extra,
  });
}

// Raw hook payload from stdin (fd 0).
export function readStdin(hook) {
  try {
    return readFileSync(0, "utf8");
  } catch (e) {
    logError(hook, "read-stdin", e);
    return "";
  }
}

// Parsed hook payload. Returns {} if stdin is missing or not valid JSON.
export function parseStdin(hook) {
  const raw = readStdin(hook);
  try {
    return JSON.parse(raw || "{}");
  } catch (e) {
    logError(hook, "parse-stdin", e, {
      rawLen: raw.length,
      rawHead: raw.slice(0, 200),
    });
    return {};
  }
}

// True only when the toggle file explicitly holds "off". A missing file
// (ENOENT) means plainly is on, so that case is not logged as an error.
export function isDisabled(hook) {
  try {
    return readFileSync(STATE_FILE, "utf8").trim() === "off";
  } catch (e) {
    if (e.code !== "ENOENT") {
      logError(hook, "read-state", e);
    }
    return false;
  }
}

// Words of human-facing prose, with fenced and inline code removed.
export function countProseWords(text) {
  if (!text) return 0;

  const prose = String(text)
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/`[^`]*`/g, " ")
    .trim();

  return prose ? prose.split(/\s+/).filter(Boolean).length : 0;
}

// Per-session metrics live in metrics-<sessionId>.json with the shape:
//   { counts: number[], lastNudgeAt: number }
// `counts` is the prose word count of each chat reply, in order. `lastNudgeAt`
// is the counts index at which the last reminder was injected, used for the
// cooldown. A brand-new session has no file yet.

// Read a session's metrics. Returns a fresh default when the file does not
// exist (new session) or cannot be parsed.
export function loadMetrics(sessionId, hook) {
  try {
    return JSON.parse(readFileSync(metricsFile(sessionId), "utf8"));
  } catch (e) {
    if (e.code !== "ENOENT") {
      logError(hook, "load-metrics", e, { session: sessionId });
    }
    return { counts: [], lastNudgeAt: -999 };
  }
}

// Write a session's metrics back to disk.
export function saveMetrics(sessionId, data, hook) {
  if (!ensureDir()) {
    const e = { message: "could not create data dir" };
    logError(hook, "save-metrics", e, { session: sessionId });
    return;
  }

  try {
    writeFileSync(metricsFile(sessionId), JSON.stringify(data));
  } catch (e) {
    logError(hook, "save-metrics", e, { session: sessionId });
  }
}
