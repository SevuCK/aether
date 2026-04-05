# Operations & Deployment Strategy (OPERATIONS.md)

## 1. Introduction & DevOps Philosophy

Due to Aether's strictly decentralized Peer-to-Peer (P2P) architecture and its reliance on the Tor network for routing, the application does not require centralized backend servers, relay nodes, or external databases. Consequently, classical IT operations and server maintenance are not applicable.

In the context of Aether, "Operations" encompasses the automated Quality Assurance (CI/CD pipeline), the secure compilation and distribution of the software to the end-user (Release Management), and the lifecycle management of the product (End-of-Life planning). Our operational processes are designed to uphold the project's core principle of "Security by Design".

## 2. Continuous Integration (CI) & Supply Chain Security

To prevent human error and ensure that every commit meets our strict security and quality standards, we utilize **GitHub Actions** as our centralized CI/CD platform.

### 2.1 Quality Gates and Automated Testing

Every accepted Pull Request to the `main` branch triggers a comprehensive CI pipeline. Code is only eligible for merging if it passes the following automated quality gates:

* **Linting & Formatting:** Enforced via `Pylint` (Backend) and `ESLint`/`Prettier` (Frontend) to maintain clean code standards.
* **Test Execution:** Execution of the `pytest` and `Jest` suites. The pipeline fails if the backend test coverage drops below **70%**.
* **Static Application Security Testing (SAST):** `SonarQube` scans the codebase. The pipeline immediately halts if any critical or high-severity vulnerabilities are detected.

### 2.2 Supply Chain Security

Given the severe threat model of our target audience (e.g., investigative journalists), securing third-party dependencies is paramount. We employ **Dependabot** to continuously monitor all `npm` and `pip` dependencies for known vulnerabilities (CVEs). Vulnerable dependencies automatically trigger a security alert and generate a PR for dependency patching.

## 3. Continuous Deployment (CD) & Release Management

The build and distribution processes are entirely automated to ensure reproducible builds and eliminate manual tampering risks during the compilation phase.

### 3.1 Automated Packaging Process

Aether's primary target environments are security- and privacy-focused operating systems (e.g., Tails OS, Whonix). Therefore, official releases are exclusively targeted for **GNU/Linux**.

The automated CD pipeline is triggered when a developer pushes a new version tag (e.g., `v1.0.0`) to the `main` branch:

1. **Archive Generation:** The pipeline bundles the frontend and backend components into a single `.tar.gz` archive.

### 3.2 Cryptographic Signing Strategy

To protect users against supply-chain attacks (e.g., compromised GitHub servers), all releases are cryptographically signed.

* **Current Automation (Beta Phase):** During the current project phase, the CI/CD pipeline automatically signs the release tags and the generated `.tar.gz` archives using a dedicated GPG key stored in GitHub Secrets.
* **Future Transition (Production Maturity):** As the project matures and reaches a larger user base, the signing process will transition to an "offline signing" model. Automated CI/CD signing will be disabled, and core maintainers will download the release artifacts, verify them, and sign the release archives locally to futher increase security.

## 4. Delivery and Update Procedure

Standard automatic background updates are considered a security risk in high-threat environments, as they can be exploited to silently push malicious payloads to targeted users.

Aether **does not** perform silent auto-updates, make background update checks, or display update notification banners. Users must proactively check for new releases, download the updated `.tar.gz` archive, verify its GPG signature, and follow the standard installation procedure to install the new version.

## 5. Installation and Startup Procedure

Because Aether relies on Python and Node.js, the application is not compiled into a standalone binary executable. Installation and operation workflows are identical for all users: simply execute the provided installation and startup scripts.

If you require a fully manual installation, you can follow this step-by-step procedure:

```
* Download code *
(Using the provided signed archive or by cloning the repo)

* Install npm (if not already installed) *
sudo apt update -y && sudo apt install npm -y

* Install docker (if not already installed) *
curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh && sudo usermod -aG docker $USER && newgrp docker

* build container (cwd = aether project root) *
docker build --no-cache -t aether .

* get npm packages (cwd = src-frontend) *
npm install

* End of install *

* start frontend (cwd = src-frontend) *
cd src-frontend && AETHER_API_PORT=5000 npm run dev

* start backend (cwd = aether project root) *
docker run -p 5000:5000 --name aether-client aether

* End of startup *
```

## 6. End-of-Life (EOL) & Sunset Strategy

A decentralized application poses a unique challenge: there are no central servers to shut down. Even if active development ceases, users could theoretically continue using Aether indefinitely. However, unpatched cryptographic libraries or outdated Tor daemons eventually become critical security vulnerabilities.

To responsibly manage the project's End-of-Life, the following Sunset Strategy is defined:

1. **Repository Archiving:** The GitHub repository will be set to "Read-Only / Archived", and the `README.md` will be updated with a prominent "ABANDONED / EOL" security warning.
2. **Final Sunset Release:** A final update will be published. This version will hardcode a permanent, un-dismissible warning banner in the Graphical User Interface: *"Software EOL: This software no longer receives security updates. Continued use poses a severe security risk."*
3. **Data Offboarding:** The final release notes and documentation will guide users to utilize the **Export Encrypted Backup (UC-10)** feature. This allows users to securely extract their cryptographic identity and contact lists before permanently deleting the Aether client from their machines.
