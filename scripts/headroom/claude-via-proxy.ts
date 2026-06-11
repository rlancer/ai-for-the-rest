#!/usr/bin/env bun
// Launches Claude Code routed through the Headroom context proxy.
//
//   1. Ensures the proxy container is running and healthy (starts it if not).
//   2. Sets ANTHROPIC_BASE_URL so the claude CLI talks to the proxy.
//   3. Launches `claude`, forwarding any extra args (e.g. `--version`).
//
// Used by the `claude` mise task. All trailing args from
// `mise run claude -- ...` arrive here in process.argv and are forwarded
// verbatim to the claude CLI.

import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HOST_PORT = 8787;
const scriptDir = dirname(fileURLToPath(import.meta.url));

// Args after the script path are forwarded to the claude CLI.
const forwarded = process.argv.slice(2);

// Ensure the proxy is up (no-op if already running and healthy).
const ensure = Bun.spawn(
  ["bun", join(scriptDir, "headroom-proxy.ts"), "--ensure-only"],
  { stdout: "inherit", stderr: "inherit" },
);
if ((await ensure.exited) !== 0) {
  console.error("error: failed to ensure the Headroom proxy is running.");
  process.exit(1);
}

const baseUrl = `http://127.0.0.1:${HOST_PORT}`;
console.log(`ANTHROPIC_BASE_URL=${baseUrl}`);

// Launch claude, inheriting stdio so it stays fully interactive, and forward
// every extra arg verbatim.
const claude = Bun.spawn(["claude", ...forwarded], {
  stdin: "inherit",
  stdout: "inherit",
  stderr: "inherit",
  env: { ...process.env, ANTHROPIC_BASE_URL: baseUrl },
});

process.exit(await claude.exited);
