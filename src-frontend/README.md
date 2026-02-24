# Project Setup & Overview

This project is a desktop chat application built using a **Web-Hybrid Architecture**.

## Architecture Overview

We use a "Two-Headed" structure where the UI and the System logic run in separate processes:

* **Frontend (The Renderer):** Built with **SvelteKit** + **Vite**.
    * *Location:* `src/`
    * *Role:* Handles all UI, Chat Logic, and State Management.
* **Backend (The Main Process):** Built with **Electron** (Node.js).
    * *Location:* `electron.js` (Root)
    * *Role:* Creates the OS window, handles system menus, and manages the application lifecycle.

**Tools Used:**
* **Concurrent.ly:** Runs the Vite server and Electron process simultaneously.
* **Wait-on:** Ensures Electron doesn't launch until Vite is ready.
* **Cross-env:** Sets environment variables (like `NODE_ENV`) across Windows/Linux/Mac.

---

## Local Development Setup

Follow these steps to set up a fresh environment.

### 1. System Prerequisites

* **Node.js (v20+):** [Download Here](https://nodejs.org/)
* **OS Specifics:**
    * **Windows:** No special requirements.
    * **macOS:** Xcode Command Line Tools (`xcode-select --install`).
    * **Linux / WSL (Ubuntu):** You **must** install the GUI libraries required by Electron. Run this command:

```bash
# Required for Ubuntu 24.04+ / WSL
sudo apt-get update && sudo apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2t64 \
    libgtk-3-0
```

### 2. Installation

Clone the repository and install the Node dependencies:

```bash
git clone [https://github.com/YourUsername/your-repo-name.git](https://github.com/YourUsername/your-repo-name.git)
cd your-repo-name
npm install
```

### 3. Running the App

Start the development environment. This will launch the Vite local server and open the Electron desktop window.

```bash
npm run dev
```

* **Hot Reloading:** Saving any file in `src/` will instantly update the running app window.

---

## 🛠 Common Setup Issues

If `npm run dev` fails on a fresh setup, check these common environment issues:

**1. "Error loading shared libraries: libnspr4.so" (Linux/WSL)**
* **Cause:** Your Linux environment is missing the desktop GUI dependencies.
* **Fix:** Run the `sudo apt-get install...` command listed in the Prerequisites section.

**2. Black Screen or "DRI3 / libEGL" Errors**
* **Cause:** Your graphics drivers (WSLg) are failing to initialize hardware acceleration.
* **Fix:** Force the app to use software rendering:
    ```bash
    LIBGL_ALWAYS_SOFTWARE=1 npm run dev
    ```