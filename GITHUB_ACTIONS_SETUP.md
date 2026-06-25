# GitHub Actions setup for SDF.R cross-platform builds

This workspace is already prepared with a workflow:

- `.github/workflows/build-sdf-r-v15-9-8-1-cross-platform.yml`

That workflow builds:

- `Rust-GPU-SDF-V15.9.8.1_MAC`
- `Rust-GPU-SDF-V15.9.8.1_LINUX`

and uploads ZIP artifacts from GitHub-hosted macOS and Linux runners.

## 1. Create a GitHub repository

Create an empty repository on GitHub first.

Example:

- Repository name: `blender-sdf-r`
- Visibility: private or public

## 2. Connect this local repo to GitHub

Replace the URL below with your repository URL.

```powershell
git remote add origin https://github.com/YOUR_NAME/YOUR_REPO.git
git push -u origin master
```

If `origin` already exists, use:

```powershell
git remote set-url origin https://github.com/YOUR_NAME/YOUR_REPO.git
git push -u origin master
```

## 3. Open GitHub Actions

After pushing:

1. Open the GitHub repository in the browser.
2. Open the `Actions` tab.
3. Select `Build SDF.R V15.9.8.1 Cross Platform`.
4. Click `Run workflow`.

The workflow can also start automatically when files under these paths are pushed:

- `.github/workflows/build-sdf-r-v15-9-8-1-cross-platform.yml`
- `Rust-GPU-SDF-V15.9.8.1_MAC/**`
- `Rust-GPU-SDF-V15.9.8.1_LINUX/**`

## 4. Download build artifacts

When the workflow finishes, open the workflow run and download:

- `SDF_R_15_9_8_1_MAC`
- `SDF_R_15_9_8_1_LINUX`

Those artifacts contain:

- `SDF_R_15_9_8_1_MAC.zip`
- `SDF_R_15_9_8_1_LINUX.zip`

## 5. Hand off for testing

Send each ZIP to a tester on the matching OS and ask them to verify:

- ZIP installs in Blender
- enabling the addon succeeds
- GPU warm-up starts
- simple preview and bake works

## Notes

- This repository currently has no Git remote configured yet.
- Local `target/`, generated ZIPs, and native binaries are ignored by `.gitignore`.
- If Linux build fails because of missing system packages, update the Linux workflow step that installs apt dependencies.
