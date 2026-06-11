#!/usr/bin/env bun
// Starts the Headroom context proxy in a container.
//
// Image: ghcr.io/chopratejas/headroom:latest
//   - ENTRYPOINT is `headroom proxy`; default CMD `--host 0.0.0.0 --port 8787`.
//   - The proxy binds 0.0.0.0:8787 inside the container; we publish that to
//     127.0.0.1:8787 on the host.
//
// A stable container name + `--rm` means a re-run cleanly replaces any stale
// container. With `--ensure-only`, this is a no-op when the container is already
// running and healthy (used by the launcher so `mise run claude` is fast).
//
// Cross-platform: runs under WSL/Linux (native podman or docker) and on the
// podman-machine setup on Windows. The container engine is auto-detected.
//
// Usage:
//   bun headroom-proxy.ts                # (re)start the proxy
//   bun headroom-proxy.ts --ensure-only  # start only if not already healthy

const IMAGE = "ghcr.io/chopratejas/headroom:latest";
const NAME = "headroom-proxy";
const HOST_PORT = 8787;
const HEALTH_URL = `http://127.0.0.1:${HOST_PORT}/health`;

const ensureOnly = process.argv.includes("--ensure-only");

/** Run a command, capturing output; never throws. */
async function run(
  cmd: string[],
  opts: { quiet?: boolean } = {},
): Promise<{ code: number; stdout: string; stderr: string }> {
  const proc = Bun.spawn(cmd, {
    stdout: opts.quiet ? "pipe" : "inherit",
    stderr: opts.quiet ? "pipe" : "inherit",
  });
  const [stdout, stderr] = await Promise.all([
    opts.quiet ? new Response(proc.stdout).text() : Promise.resolve(""),
    opts.quiet ? new Response(proc.stderr).text() : Promise.resolve(""),
  ]);
  const code = await proc.exited;
  return { code, stdout, stderr };
}

/** Capture-only run that returns trimmed stdout (or "" on failure). */
async function capture(cmd: string[]): Promise<string> {
  const { code, stdout } = await run(cmd, { quiet: true });
  return code === 0 ? stdout.trim() : "";
}

function die(msg: string): never {
  console.error(`error: ${msg}`);
  process.exit(1);
}

/** Find the container engine on PATH: podman first, then docker. */
async function detectEngine(): Promise<string> {
  for (const engine of ["podman", "docker"]) {
    if (await capture([engine, "--version"])) return engine;
  }
  die(
    "no container engine found. Install podman or docker and ensure it is on PATH.",
  );
}

/**
 * Ensure the engine's daemon/VM is reachable.
 * For podman on Windows/mac this may be a `podman machine`; on native Linux/WSL
 * there is no machine, so we only try to start it if `machine list` shows one.
 */
async function ensureEngineReachable(engine: string): Promise<void> {
  if ((await capture([engine, "info", "--format", "{{.Host.Os}}"])) || (await capture([engine, "info"]))) {
    return; // daemon already reachable
  }

  if (engine === "podman") {
    // Only podman has the `machine` concept (Windows/mac). On native Linux this
    // returns nothing, so we skip straight to the error below.
    const machines = await capture([engine, "machine", "list", "--format", "{{.Name}}"]);
    if (machines) {
      console.log("podman machine not reachable; starting it (~30s)...");
      const { code } = await run([engine, "machine", "start"]);
      if (code === 0) return;
      die("failed to start the podman machine. Run `podman machine start` manually and retry.");
    }
  }

  die(
    `${engine} daemon is not reachable. Start it (e.g. \`sudo service docker start\` or \`podman machine start\`) and retry.`,
  );
}

/**
 * Ensure the image is present locally, pulling it (with visible progress) if
 * not. On a first run the image is not cached, and an implicit pull during
 * `run -d` happens silently — on a slow connection this looks like a hang and
 * eats into the health-check window. Pulling up front separates "downloading"
 * from "starting up" so each gets its own time budget and visible feedback.
 */
async function ensureImagePresent(engine: string): Promise<void> {
  // `image inspect` only succeeds for a fully-pulled image (a half-finished
  // pull from an aborted run won't satisfy it), so this also forces a retry of
  // an incomplete download rather than treating it as present.
  const present = await capture([engine, "image", "inspect", IMAGE]);
  if (present) return;

  console.log(
    `Pulling Headroom image '${IMAGE}' (first run; this is a large image and can take several minutes — waiting for the full download)...`,
  );
  // No timeout here: `run` blocks until the pull fully completes, however long
  // that takes, streaming the engine's pull progress to the terminal.
  const { code } = await run([engine, "pull", IMAGE]);
  if (code !== 0) die(`${engine} pull failed (exit ${code}). Check your network and retry.`);
}

async function isProxyHealthy(): Promise<boolean> {
  try {
    const res = await fetch(HEALTH_URL, {
      signal: AbortSignal.timeout(2000),
    });
    return res.status === 200;
  } catch {
    return false;
  }
}

async function isContainerRunning(engine: string): Promise<boolean> {
  const out = await capture([
    engine,
    "ps",
    "--filter",
    `name=^${NAME}$`,
    "--format",
    "{{.Names}}",
  ]);
  return out.split("\n").includes(NAME);
}

async function main() {
  const engine = await detectEngine();
  await ensureEngineReachable(engine);

  if (ensureOnly && (await isContainerRunning(engine)) && (await isProxyHealthy())) {
    console.log(`Headroom proxy already healthy at ${HEALTH_URL}`);
    process.exit(0);
  }

  // Pull the image up front so the download has its own time budget (and
  // visible progress) separate from the health-check window below.
  await ensureImagePresent(engine);

  // Remove any stale container so the fresh `run` cannot collide with it.
  await run([engine, "rm", "-f", NAME], { quiet: true });

  console.log(`Starting Headroom proxy container '${NAME}' on 127.0.0.1:${HOST_PORT} ...`);
  const { code } = await run([
    engine,
    "run",
    "-d",
    "--rm",
    "--name",
    NAME,
    "-p",
    `127.0.0.1:${HOST_PORT}:${HOST_PORT}`,
    IMAGE,
    "--host",
    "0.0.0.0",
    "--port",
    String(HOST_PORT),
  ]);
  if (code !== 0) die(`${engine} run failed (exit ${code}).`);

  // Wait for the health endpoint to return 200. The image is already pulled by
  // this point, so this window only covers container startup — but a cold start
  // (engine paging in the freshly-pulled image, proxy initializing) can still
  // take longer than a warm one, so give it a generous budget.
  const HEALTH_TIMEOUT_MS = 90_000;
  process.stdout.write("Waiting for proxy to become healthy");
  const deadline = Date.now() + HEALTH_TIMEOUT_MS;
  while (Date.now() < deadline) {
    if (await isProxyHealthy()) {
      console.log(`\nHeadroom proxy is healthy at ${HEALTH_URL}`);
      process.exit(0);
    }
    process.stdout.write(".");
    await Bun.sleep(500);
  }

  console.log("");
  die(
    `proxy did not become healthy within ${HEALTH_TIMEOUT_MS / 1000}s. Check logs: ${engine} logs ${NAME}`,
  );
}

main();
