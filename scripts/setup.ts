#!/usr/bin/env bun
/**
 * Cross-platform setup script (runs after shell bootstrap installs bun)
 * Handles: mise tools, bun globals, shell profiles, SSH key setup
 */

import { $ } from "bun";
import { existsSync, mkdirSync, readFileSync, writeFileSync, appendFileSync, chmodSync } from "fs";
import { homedir } from "os";
import { join } from "path";
import * as readline from "readline";

const isWindows = process.platform === "win32";
const home = homedir();

// Colors for console output
const cyan = (s: string) => `\x1b[36m${s}\x1b[0m`;
const yellow = (s: string) => `\x1b[33m${s}\x1b[0m`;
const green = (s: string) => `\x1b[32m${s}\x1b[0m`;
const gray = (s: string) => `\x1b[90m${s}\x1b[0m`;
const white = (s: string) => `\x1b[37m${s}\x1b[0m`;

// Helper to prompt user for input
function prompt(question: string): Promise<string> {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });
  return new Promise((resolve) => {
    rl.question(question, (answer) => {
      rl.close();
      resolve(answer);
    });
  });
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
  bun_global: string[];
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

// Install bun global packages
async function installBunGlobals() {
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
}

// Configure shell profiles
async function configureProfiles() {
  console.log(yellow("\nConfiguring shell profiles..."));

  if (isWindows) {
    const profileContent = `
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
    } else if (!readFileSync(pwshProfile, "utf-8").includes("starship init")) {
      appendFileSync(pwshProfile, profileContent);
      console.log(gray("  Updated PowerShell Core profile"));
    } else {
      console.log(gray("  PowerShell Core profile already configured"));
    }

    // Windows PowerShell profile
    const winPsProfileDir = join(home, "Documents", "WindowsPowerShell");
    const winPsProfile = join(winPsProfileDir, "Microsoft.PowerShell_profile.ps1");

    if (!existsSync(winPsProfileDir)) {
      mkdirSync(winPsProfileDir, { recursive: true });
    }

    if (!existsSync(winPsProfile)) {
      writeFileSync(winPsProfile, profileContent, "utf-8");
      console.log(gray("  Created Windows PowerShell profile"));
    } else if (!readFileSync(winPsProfile, "utf-8").includes("starship init")) {
      appendFileSync(winPsProfile, profileContent);
      console.log(gray("  Updated Windows PowerShell profile"));
    } else {
      console.log(gray("  Windows PowerShell profile already configured"));
    }
  } else {
    // macOS/Linux - configure zsh
    const profileContent = `
# Initialize mise
eval "$(mise activate zsh)"

# Initialize starship prompt
eval "$(starship init zsh)"
`;

    const zshrc = join(home, ".zshrc");

    if (!existsSync(zshrc)) {
      writeFileSync(zshrc, profileContent, "utf-8");
      console.log(gray("  Created .zshrc"));
    } else if (!readFileSync(zshrc, "utf-8").includes("starship init")) {
      appendFileSync(zshrc, profileContent);
      console.log(gray("  Updated .zshrc"));
    } else {
      console.log(gray("  .zshrc already configured"));
    }
  }
}

// SSH key setup
async function setupSSHKey() {
  console.log(cyan("\n=== SSH Key Setup ==="));

  const sshDir = join(home, ".ssh");
  const sshKeyPath = join(sshDir, "id_ed25519");
  const sshPubKeyPath = `${sshKeyPath}.pub`;

  const response = await prompt("Would you like to set up an SSH key for GitHub? (Y/n) ");

  if (response === "" || response.toLowerCase().startsWith("y")) {
    if (existsSync(sshPubKeyPath)) {
      console.log(green("\nExisting SSH key found!"));
    } else {
      console.log(yellow("\nGenerating new SSH key (ed25519)..."));

      // Create .ssh directory if it doesn't exist
      if (!existsSync(sshDir)) {
        mkdirSync(sshDir, { recursive: true });
        if (!isWindows) {
          chmodSync(sshDir, 0o700);
        }
      }

      const email = await prompt("Enter your email for the SSH key: ");
      if (email) {
        await $`ssh-keygen -t ed25519 -C ${email} -f ${sshKeyPath} -N ""`;
        console.log(green("SSH key generated!"));
      } else {
        console.log(yellow("No email provided, skipping SSH key generation."));
      }
    }

    // Display the public key if it exists
    if (existsSync(sshPubKeyPath)) {
      const pubKey = readFileSync(sshPubKeyPath, "utf-8").trim();
      console.log(cyan("\n============================================================"));
      console.log(yellow("Your SSH public key (copy this to GitHub):"));
      console.log(cyan("============================================================"));
      console.log();
      console.log(white(pubKey));
      console.log();
      console.log(cyan("============================================================"));
      console.log(yellow("\nTo add this key to GitHub:"));
      console.log(gray("  1. Go to https://github.com/settings/keys"));
      console.log(gray("  2. Click 'New SSH key'"));
      console.log(gray("  3. Paste the key above and save"));
    }
  } else {
    console.log(gray("Skipping SSH key setup."));
  }
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

  console.log(yellow("\nBun global packages:"));
  try {
    const bunList = await $`bun pm ls -g`.text();
    bunList.split("\n").forEach((line) => {
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
  await installBunGlobals();
  await configureProfiles();
  await showSummary();
  await setupSSHKey();

  console.log(green("\nSetup complete!"));
}

main().catch((err) => {
  console.error("Setup failed:", err);
  process.exit(1);
});
