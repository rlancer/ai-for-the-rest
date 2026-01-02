#!/usr/bin/env bun
/**
 * Publish script for aftr package
 * Bumps version, commits, tags, and pushes to trigger CI/CD
 */

import { $ } from "bun";
import { readFileSync, writeFileSync } from "fs";
import { join } from "path";

const scriptDir = import.meta.dir;
const pyprojectPath = join(scriptDir, "..", "packages", "cli", "pyproject.toml");

// Colors for console output
const cyan = (s: string) => `\x1b[36m${s}\x1b[0m`;
const yellow = (s: string) => `\x1b[33m${s}\x1b[0m`;
const green = (s: string) => `\x1b[32m${s}\x1b[0m`;
const red = (s: string) => `\x1b[31m${s}\x1b[0m`;
const gray = (s: string) => `\x1b[90m${s}\x1b[0m`;

type BumpType = "patch" | "minor" | "major";

function parseVersion(version: string): [number, number, number] {
  const [major, minor, patch] = version.split(".").map(Number);
  return [major, minor, patch];
}

function bumpVersion(version: string, bumpType: BumpType): string {
  const [major, minor, patch] = parseVersion(version);

  switch (bumpType) {
    case "major":
      return `${major + 1}.0.0`;
    case "minor":
      return `${major}.${minor + 1}.0`;
    case "patch":
      return `${major}.${minor}.${patch + 1}`;
    default:
      throw new Error(`Invalid bump type: ${bumpType}`);
  }
}

function getCurrentVersion(): string {
  const content = readFileSync(pyprojectPath, "utf-8");
  const match = content.match(/version = "([^"]+)"/);

  if (!match) {
    throw new Error("Could not find version in pyproject.toml");
  }

  return match[1];
}

function updateVersion(newVersion: string) {
  const content = readFileSync(pyprojectPath, "utf-8");
  const updated = content.replace(
    /version = "[^"]+"/,
    `version = "${newVersion}"`
  );
  writeFileSync(pyprojectPath, updated, "utf-8");
}

async function checkGitStatus(): Promise<boolean> {
  try {
    const status = await $`git status --porcelain`.text();
    return status.trim().length === 0;
  } catch {
    return false;
  }
}

async function main() {
  const args = process.argv.slice(2);

  if (args.length === 0) {
    console.log(cyan("Usage: mise run publish <patch|minor|major>"));
    console.log(gray("\nExamples:"));
    console.log(gray("  mise run publish patch  # 0.1.0 -> 0.1.1"));
    console.log(gray("  mise run publish minor  # 0.1.0 -> 0.2.0"));
    console.log(gray("  mise run publish major  # 0.1.0 -> 1.0.0"));
    process.exit(1);
  }

  const bumpType = args[0] as BumpType;

  if (!["patch", "minor", "major"].includes(bumpType)) {
    console.log(red(`Invalid bump type: ${bumpType}`));
    console.log(gray("Must be one of: patch, minor, major"));
    process.exit(1);
  }

  // Check git status
  const isClean = await checkGitStatus();
  if (!isClean) {
    console.log(red("Error: Working directory has uncommitted changes"));
    console.log(gray("Please commit or stash your changes first"));
    process.exit(1);
  }

  // Get current version and calculate new version
  const currentVersion = getCurrentVersion();
  const newVersion = bumpVersion(currentVersion, bumpType);

  console.log(cyan("\n=== Publishing aftr ==="));
  console.log(gray(`Current version: ${currentVersion}`));
  console.log(yellow(`New version: ${newVersion}`));
  console.log();

  // Update version in pyproject.toml
  console.log(gray("Updating pyproject.toml..."));
  updateVersion(newVersion);
  console.log(green("✓ Version updated"));

  // Git operations
  console.log(gray("\nCommitting changes..."));
  await $`git add ${pyprojectPath}`;
  await $`git commit -m ${"Bump aftr version to " + newVersion}`;
  console.log(green("✓ Changes committed"));

  console.log(gray(`\nCreating tag v${newVersion}...`));
  await $`git tag -a ${"v" + newVersion} -m ${"Release v" + newVersion}`;
  console.log(green("✓ Tag created"));

  console.log(gray("\nPushing to GitHub..."));
  await $`git push origin main`;
  await $`git push origin ${"v" + newVersion}`;
  console.log(green("✓ Pushed to GitHub"));

  console.log(green("\n✓ Successfully published v" + newVersion));
  console.log(cyan("\nGitHub Actions will now:"));
  console.log(gray("  1. Run tests"));
  console.log(gray("  2. Build the package"));
  console.log(gray("  3. Publish to PyPI"));
  console.log(gray("  4. Create a GitHub release"));
  console.log();
  console.log(gray("Check workflow status at:"));
  console.log(gray("  https://github.com/rlancer/ai-for-the-rest/actions/workflows/publish.yml"));
  console.log();
}

main().catch((err) => {
  console.error(red("\nPublish failed:"), err.message);
  process.exit(1);
});
