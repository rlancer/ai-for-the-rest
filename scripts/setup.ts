#!/usr/bin/env bun
/**
 * Cross-platform setup script (runs after shell bootstrap installs bun)
 * Handles: mise tools, uv tools, bun globals, shell profiles
 * Post-setup configuration (AI tools, SSH keys) is handled by aftr
 */

import { $ } from "bun";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "fs";
import { homedir } from "os";
import { join } from "path";

const isWindows = process.platform === "win32";
const home = homedir();

// Colors for console output
const cyan = (s: string) => `\x1b[36m${s}\x1b[0m`;
const yellow = (s: string) => `\x1b[33m${s}\x1b[0m`;
const green = (s: string) => `\x1b[32m${s}\x1b[0m`;
const gray = (s: string) => `\x1b[90m${s}\x1b[0m`;

// Helper to strip BOM (Byte Order Mark) from file content
function stripBom(content: string): string {
  // Remove UTF-8 BOM if present
  if (content.charCodeAt(0) === 0xfeff) {
    return content.slice(1);
  }
  return content;
}

// Helper to check if a command exists
async function commandExists(cmd: string): Promise<boolean> {
  try {
    if (isWindows) {
      await $`where ${cmd}`.quiet();
    } else {
      await $`which ${cmd}`.quiet();
    }
    return true;
  } catch {
    return false;
  }
}

// Load config - check multiple locations for local vs remote execution
const scriptDir = import.meta.dir;

interface Config {
  mise_tools: string[];
  uv_tools: string[];
  bun_global?: string[];
}

function loadConfig(): Config {
  // Try standard repo layout first
  const repoConfigPath = join(scriptDir, "..", "config", "config.json");
  if (existsSync(repoConfigPath)) {
    return JSON.parse(readFileSync(repoConfigPath, "utf-8"));
  }

  // Try config dir next to script (for remote execution temp dir)
  const localConfigPath = join(scriptDir, "config", "config.json");
  if (existsSync(localConfigPath)) {
    return JSON.parse(readFileSync(localConfigPath, "utf-8"));
  }

  throw new Error(`config.json not found in ${repoConfigPath} or ${localConfigPath}`);
}

const config = loadConfig();

// Install mise tools
async function installMiseTools() {
  console.log(yellow("\nInstalling mise tools..."));

  // Trust the global mise config if it exists
  const miseConfigDir = isWindows
    ? join(home, ".config", "mise")
    : join(home, ".config", "mise");
  const miseGlobalConfig = join(miseConfigDir, "config.toml");

  if (existsSync(miseGlobalConfig)) {
    try {
      await $`mise trust ${miseGlobalConfig}`.quiet();
    } catch {
      // Trust might fail if config doesn't need trusting, that's ok
    }
  }

  for (const tool of config.mise_tools) {
    const toolName = tool.replace(/@.*/, "");
    try {
      const result = await $`mise list ${toolName}`.quiet().text();
      if (result && !result.includes("(missing)")) {
        console.log(gray(`  ${toolName} already installed via mise`));
      } else {
        throw new Error("not installed");
      }
    } catch {
      console.log(gray(`  Installing ${tool}...`));
      try {
        // Use mise install instead of mise use for initial installation
        // mise use -g can fail on Windows with exit code 53 due to config file issues
        await $`mise install ${tool}`.quiet();
        await $`mise use -g ${tool}`.quiet();
        console.log(green(`  ${toolName} installed successfully`));
      } catch (err: unknown) {
        const error = err as { exitCode?: number; stderr?: string };
        console.log(yellow(`  Warning: Failed to install ${tool} via mise (exit code: ${error.exitCode || 'unknown'})`));
        console.log(gray(`  You can manually install later with: mise use -g ${tool}`));
        // Continue with other tools instead of failing completely
      }
    }
  }
}

// Get the uv command (installed globally via package manager)
function getUvCommand(): string {
  return "uv";
}

// Helper to sleep for a given number of milliseconds
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// Check if a uv tool is installed and working
async function checkUvToolHealth(tool: string): Promise<"healthy" | "corrupted" | "not_installed"> {
  const toolDir = isWindows
    ? join(home, "AppData", "Roaming", "uv", "tools", tool)
    : join(home, ".local", "share", "uv", "tools", tool);

  // Check if tool directory exists
  if (!existsSync(toolDir)) {
    return "not_installed";
  }

  // Tool directory exists, check if it actually runs
  try {
    await $`${tool} --version`.quiet();
    return "healthy";
  } catch {
    // Tool exists but can't run - corrupted installation
    return "corrupted";
  }
}

// Install uv tools
async function installUvTools() {
  console.log(yellow("\nInstalling uv tools..."));

  // uv is installed globally via package manager (scoop/brew)
  const uvCmd = getUvCommand();

  for (const tool of config.uv_tools) {
    const health = await checkUvToolHealth(tool);

    // Handle corrupted installations by uninstalling first
    if (health === "corrupted") {
      console.log(yellow(`  ${tool} installation appears corrupted, reinstalling...`));
      try {
        await $`${uvCmd} tool uninstall ${tool}`.quiet();
        await sleep(1000); // Wait for filesystem to settle
        console.log(gray(`    Uninstalled corrupted ${tool}`));
      } catch {
        // If uninstall fails, try to remove the directory manually on Windows
        if (isWindows) {
          const toolDir = join(home, "AppData", "Roaming", "uv", "tools", tool);

          // First, try to kill any python processes using this tool's directory
          console.log(gray(`    Checking for processes locking ${tool}...`));
          try {
            const result = await $`pwsh -NoProfile -Command "Get-Process python* -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '${toolDir}*' } | Select-Object -ExpandProperty Id"`.quiet().text();
            const pids = result.trim().split("\n").filter((p) => p.trim());
            if (pids.length > 0) {
              console.log(gray(`    Killing ${pids.length} process(es) locking ${tool}...`));
              for (const pid of pids) {
                try {
                  await $`pwsh -NoProfile -Command "Stop-Process -Id ${pid.trim()} -Force"`.quiet();
                } catch {
                  // Process might have already exited
                }
              }
              await sleep(1000); // Wait for processes to terminate
            }
          } catch {
            // Ignore errors when checking for processes
          }

          console.log(gray(`    Attempting to remove ${tool} directory...`));
          try {
            await $`pwsh -NoProfile -Command "Remove-Item -Recurse -Force '${toolDir}'"`.quiet();
            await sleep(1000);
          } catch {
            console.log(yellow(`    Could not remove ${tool} directory automatically`));
          }
        }
      }
    }

    const action = health === "healthy" ? "Upgrading" : "Installing";
    console.log(gray(`  ${action} ${tool}...`));

    let success = false;
    let lastError: { exitCode?: number; stderr?: string } | undefined;

    // On Windows, upgrading can fail due to locked files. Try up to 3 times with delays.
    const maxAttempts = isWindows && health === "healthy" ? 3 : 1;

    for (let attempt = 1; attempt <= maxAttempts && !success; attempt++) {
      try {
        if (attempt > 1) {
          console.log(gray(`    Retry attempt ${attempt}/${maxAttempts}...`));
          // On retry, try uninstalling first
          if (attempt === 2) {
            console.log(gray(`    Trying to uninstall first...`));
            try {
              await $`${uvCmd} tool uninstall ${tool}`.quiet();
              await sleep(1000);
            } catch {
              // Uninstall might fail too, continue anyway
            }
          }
        }

        // Use --upgrade to install or upgrade existing tools
        // Use --force when reinstalling after corruption to overwrite stale executables
        const forceFlag = health === "corrupted" ? "--force" : "";
        if (forceFlag) {
          await $`${uvCmd} tool install --upgrade --force ${tool}`;
        } else {
          await $`${uvCmd} tool install --upgrade ${tool}`;
        }
        console.log(green(`  ${tool} ${health === "healthy" ? "upgraded" : "installed"} successfully`));
        success = true;
      } catch (err: unknown) {
        lastError = err as { exitCode?: number; stderr?: string };
        if (attempt < maxAttempts) {
          // Wait before retrying to allow file locks to release
          await sleep(2000);
        }
      }
    }

    if (!success && lastError) {
      console.log(yellow(`  Warning: Failed to ${action.toLowerCase()} ${tool} via uv (exit code: ${lastError.exitCode || 'unknown'})`));
      if (isWindows) {
        console.log(gray(`  This may be due to locked files. Close any terminals using ${tool} and try:`));
        console.log(gray(`    uv tool uninstall ${tool}`));
        console.log(gray(`    uv tool install ${tool}`));
      } else {
        console.log(gray(`  You can manually install later with: uv tool install --upgrade ${tool}`));
      }
    }
  }
}

// Install bun global packages (if any configured)
async function installBunGlobals() {
  if (config.bun_global && config.bun_global.length > 0) {
    console.log(yellow("\nInstalling bun global packages..."));

    for (const pkg of config.bun_global) {
      // Extract command name from package (last part after /)
      const cmdName = pkg.split("/").pop()!;
      if (await commandExists(cmdName)) {
        console.log(gray(`  ${pkg} already installed`));
      } else {
        console.log(gray(`  Installing ${pkg}...`));
        await $`bun install -g ${pkg}`;
      }
    }
  } else {
    console.log(gray("\nNo bun global packages configured (AI tools will be set up via aftr)"));
  }
}

// Configure shell profiles
async function configureProfiles() {
  console.log(yellow("\nConfiguring shell profiles..."));

  if (isWindows) {
    const profileContent = `
# Add uv tools to PATH
$env:PATH = "$env:USERPROFILE\\.local\\bin;" + $env:PATH

# Initialize starship prompt
Invoke-Expression (&starship init powershell)

# Initialize mise
mise activate pwsh | Out-String | Invoke-Expression
`;

    // PowerShell Core profile
    const pwshProfileDir = join(home, "Documents", "PowerShell");
    const pwshProfile = join(pwshProfileDir, "Microsoft.PowerShell_profile.ps1");

    if (!existsSync(pwshProfileDir)) {
      mkdirSync(pwshProfileDir, { recursive: true });
    }

    if (!existsSync(pwshProfile)) {
      writeFileSync(pwshProfile, profileContent, "utf-8");
      console.log(gray("  Created PowerShell Core profile"));
    } else {
      const existing = stripBom(readFileSync(pwshProfile, "utf-8"));
      if (!existing.includes(".local\\bin")) {
        // Rewrite entire file in UTF-8 to avoid encoding issues when appending
        writeFileSync(pwshProfile, existing + profileContent, "utf-8");
        console.log(gray("  Updated PowerShell Core profile"));
      } else {
        console.log(gray("  PowerShell Core profile already configured"));
      }
    }

    // Note: We only configure PowerShell Core (pwsh), not Windows PowerShell.
    // Windows PowerShell is only used for bootstrapping (setup.ps1) and doesn't need
    // starship/mise integration.
  } else {
    // macOS/Linux - configure zsh
    const profileContent = `
# Add uv tools to PATH
export PATH="$HOME/.local/bin:$PATH"

# Initialize mise
eval "$(mise activate zsh)"

# Initialize starship prompt
eval "$(starship init zsh)"
`;

    const zshrc = join(home, ".zshrc");

    if (!existsSync(zshrc)) {
      writeFileSync(zshrc, profileContent, "utf-8");
      console.log(gray("  Created .zshrc"));
    } else {
      const existing = stripBom(readFileSync(zshrc, "utf-8"));
      if (!existing.includes(".local/bin")) {
        // Rewrite entire file in UTF-8 to avoid encoding issues when appending
        writeFileSync(zshrc, existing + profileContent, "utf-8");
        console.log(gray("  Updated .zshrc"));
      } else {
        console.log(gray("  .zshrc already configured"));
      }
    }
  }
}

// Show instructions for completing setup
async function showNextSteps() {
  console.log(cyan("\n=== Next Steps ==="));
  console.log(yellow("\nTo complete your setup, run the following commands:\n"));

  if (isWindows) {
    console.log(gray("1. Open a new Windows Terminal or PowerShell window"));
    console.log(gray("   (This loads your updated profile with mise and PATH)"));
    console.log();
    console.log(green("2. Run: aftr setup"));
    console.log(gray("   This will prompt you to select AI CLI tools and configure SSH keys"));
  } else {
    console.log(gray("1. Open a new terminal window (iTerm2, Terminal.app, etc.)"));
    console.log(gray("   (This loads your updated profile with mise and PATH)"));
    console.log();
    console.log(green("2. Run: aftr setup"));
    console.log(gray("   This will prompt you to select AI CLI tools and configure SSH keys"));
  }

  console.log();
  console.log(gray("Or, for non-interactive setup with defaults:"));
  console.log(green("   aftr setup --non-interactive"));
  console.log();
}

// Show installation summary
async function showSummary() {
  console.log(cyan("\n=== Installation Summary ==="));

  console.log(yellow("\nMise tools:"));
  try {
    const miseList = await $`mise list`.text();
    miseList.split("\n").forEach((line) => {
      if (line.trim()) console.log(gray(`  ${line}`));
    });
  } catch {
    console.log(gray("  (unable to list)"));
  }

  console.log(yellow("\nUV tools:"));
  try {
    // uv is installed globally via package manager
    const uvCmd = getUvCommand();
    const uvList = await $`${uvCmd} tool list`.text();
    uvList.split("\n").forEach((line) => {
      if (line.trim()) console.log(gray(`  ${line}`));
    });
  } catch {
    console.log(gray("  (unable to list)"));
  }
}

// Main
async function main() {
  console.log(cyan("Continuing setup with bun..."));

  await installMiseTools();
  await installUvTools();
  await installBunGlobals();
  await configureProfiles();
  await showSummary();
  await showNextSteps();

  console.log(green("Base setup complete!"));
  console.log(gray("Follow the steps above to finish configuring your environment.\n"));
}

main().catch((err) => {
  console.error("Setup failed:", err);
  process.exit(1);
});
