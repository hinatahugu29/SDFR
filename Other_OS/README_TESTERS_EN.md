# SDF.R V15.9.8.1 Mac/Linux Test Build - Tester Guide

This test build (V15.9.8.1) is an initial test build compiled for macOS (Apple Silicon) and Linux based on the Windows version.
We kindly ask our testers to install and verify the add-on according to the following guidelines and report any issues or status updates.

---

## 1. Testing Verification Items (What to Check)

Please follow the steps below to verify if the add-on's basic features work correctly on your OS.

1. **Add-on Installation and Activation**
   - Install the provided ZIP file (`SDF_R_15_9_8_1_MAC.zip` or `SDF_R_15_9_8_1_LINUX.zip`) as-is in Blender.
   - Check if you can activate the add-on by checking the checkbox without any initialization errors or warnings.
2. **GPU Engine Initialization Logs**
   - Open the Blender system console (or terminal) and verify if the following logs are displayed:
     - `SDF.R: --- Initializing GPU Engine (V15.9.8.1) ---`
     - `SDF.R: GPU Engine Ready!`
3. **Basic Mesh Generation and Real-Time Synchronization**
   - Create a new SDF mesh in the 3D viewport.
   - Add primitives (Sphere, Box, Torus, etc.) and verify if the mesh deforms smoothly in real-time as you translate, rotate, or scale them.
   - Verify if changing the Smoothness value causes any mesh tearing, holes, or boundary corruption.
4. **Resolution Durability & Stability Test**
   - Increase the Resolution value to `128` or `256` and check if it causes extreme lag, freezing, or a crash (forced termination of Blender).
5. **Deactivation and Uninstallation**
   - Check if you can clean-uninstall the add-on by unchecking the checkbox and clicking "Remove".

---

## 2. Troubleshooting (Common Issues & Solutions)

### macOS Specific: Bypassing Gatekeeper (Block on Execution)
Since the macOS binary (`rust_gpu_sdf.so`) built in the CI environment (GitHub Actions) is not digitally signed by Apple, the macOS Gatekeeper security system might block it from loading, showing a warning: "developer cannot be verified".

**【Bypassing Steps】**
1. When the block warning dialog appears, click "Cancel".
2. Open macOS **"System Settings"** > **"Privacy & Security"**.
3. Scroll down and look for a message saying: `"rust_gpu_sdf.so" was blocked from use because it is not from an identified developer.` Click **"Open Anyway"**.
4. Return to Blender and try enabling the add-on checkbox again.

### Python Import / Circular Dependency Errors
In older test versions, when Blender attempted to load the add-on from a temporary directory (e.g., during `exec_legacy`), errors like `RuntimeError: attempted relative import with no known parent package` could occur. While this build implements fallbacks to prevent this, please report console log details to developers if you still encounter errors.

### GPU Initialization Errors
SDF.R uses WebGPU (wgpu) to compute meshes on the GPU. If your graphics drivers are outdated (especially on Linux) or if GPU initialization fails, the add-on may freeze on startup or Blender may crash. Please report your OS version and GPU model in such cases.

---

## 3. Bug Report Template

If you encounter any bugs or behavior issues, please copy the template below, fill in the details as much as possible, and report it to us.

### 📋 Report Template
```text
[OS Version] (e.g., macOS Sequoia 15.0 / Ubuntu 22.04 LTS)
[CPU & GPU Model] (e.g., Apple M2 / Intel Core i7 + RTX 4070)
[Blender Version] (e.g., Blender 4.2.1 LTS / Blender 5.1.0 Alpha)
[ZIP File Name Used] (e.g., SDF_R_15_9_8_1_MAC.zip)
[Issue Description]
(e.g., When enabling the add-on, the checkbox does not turn on and an error is displayed in the console)

[Steps to Reproduce]
1. 
2. 
3. 

[Blender Console Logs (Error Message)]
*Please copy and paste the full error traceback text from the console.

[Screenshots or Videos] (if possible)
```

### 💡 How to Open Blender System Console
- **macOS / Linux**: You need to launch Blender from the Terminal. Open Terminal, drag and drop the Blender binary path (e.g., `/Applications/Blender.app/Contents/MacOS/Blender`), and hit enter. Error tracebacks will be printed in real-time in the terminal window when errors occur.
