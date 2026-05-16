# ElectronSafeUpdater — code-level analysis

ElectronSafeUpdater (npm package `safeupdater`, published by Doyensec) is a "secure Electron updater reference implementation." Despite TypeScript-style typings (`src/index.d.ts:1`), the implementation is ESM JavaScript, not TypeScript. Only macOS is wired up; everything else throws at startup (`src/index.js:26-28`).

## 1. Architecture overview

There is **no `main/`, `renderer/`, `preload/` Electron-app skeleton** — this is a library consumed by a host Electron main process. The entry point `start({getApp, getMainWindow, logger, canRunSilently})` (`src/index.js:17`) is invoked from the host's main process and constructs a platform-specific `Updater` subclass. The package is dual-published ESM + CJS via `esbuild` bundling with `electron` and `config` marked external (`package.json:27-29`).

Runtime dependencies of note: `@noble/ed25519` for signatures, `electron-store` for cross-launch state, `electron-updater` (listed but unused — see §5), `got` for HTTP, `config` for the public key and feed URL, `js-yaml` (transitively, used via `parseYaml`).

The host application supplies the BrowserWindow; the only window the library creates itself is the version-picker modal in `getUserVersion` (`src/common.js:271-282`).

## 2. Module / file layout

- `src/index.js` — public entry, platform gate, "install on next launch" replay logic.
- `src/common.js` — the abstract `Updater` base class (~1100 lines) holding the entire update FSM: polling, version checks, download, signature verify, install handoff, retry/rollback.
- `src/macos.js` — `MacOSUpdater extends Updater`; delegates installation to Electron's built-in Squirrel.Mac `autoUpdater`.
- `src/signature.js` — Ed25519 sign/verify of a `sha256(file)-version` message.
- `src/downloadandverify.js` — generic "fetch + sibling `.sig` + verify" helper for manifest files.
- `src/got.js` — HTTPS agent factory with optional pinned CA.
- `src/preload.cjs` — 13-line preload exposing two IPC functions over `contextBridge`.
- `src/input.html` — version-picker UI loaded into the modal BrowserWindow.
- `util/` — `pathAndDir.js` (path-traversal guard, temp/cache layout), `curve.js` (noble-ed25519 wrapper), `version.js` (channel detection), `isPathInside.js`, `errors.js`.
- `tools/` — `generateKeys.js` (Ed25519 keypair), `sign.js` (CLI signer), `server.py` (HTTPS test server), `example.main.js` (sample host).
- `tests/integration/` — three Vitest specs covering signature roundtrip, `downloadAndVerify` happy/fail paths, and tempdir/integrity helpers.
- `config/default.json` — declares `updatesPublicKey`, pinned `certificateAuthority`, `updatesUrl`, `allowInsecureTLS` (`config/default.json:1-7`).

## 3. Code-signing verification

**This is single-platform Ed25519, not OS-native code signing.** There is no call to `codesign`, `spctl`, `WinVerifyTrust`, `signtool`, or `osslsigncode` anywhere in the tree.

The verification primitive is in `src/signature.js`:

```js
// src/signature.js:25-30
async function generateMessage(updatePackagePath, version) {
    const hash = await _getFileHash(updatePackagePath);              // SHA-256
    const messageString = `${Buffer.from(hash).toString('hex')}-${version}`;
    return Buffer.from(messageString);
}
```

`verifySignature(file, version, sig, pubkey)` (`src/signature.js:42-45`) calls `ed.verify` via the wrapper at `util/curve.js:20`. Note the message is the ASCII string `"<hex_sha256>-<version>"`, not raw bytes — the version is bound into the signature, which blocks naive rollback of a payload across versions.

Call sites:
1. **Update payload verification** in `Updater.#doDownloadAndInstall` (`src/common.js:519-533`). The public key is loaded from app config (`config.get('updatesPublicKey')` at `src/common.js:516`), not from a TOFU file. Failure throws and the cache is deliberately *not* cleared, to avoid redownload loops (`src/common.js:527-532`).
2. **Manifest verification** for every fetched YAML/JSON via `downloadAndVerify` (`src/downloadandverify.js:58-67`) which calls `verifySignature(filePath, "version", signature, publicKey)` at `src/downloadandverify.js:137-142`. **Bug worth flagging:** the literal string `"version"` is hard-coded as the version-bind value (`src/downloadandverify.js:139`), so manifest signatures are not actually bound to any release version — only the payload's are.

After the in-process Ed25519 check passes, macOS installation is delegated to Electron's `autoUpdater.checkForUpdates()` / `quitAndInstall()` (`src/macos.js:98, 48`), which on Squirrel.Mac performs the OS-level codesign check on the swapped-in `.app` bundle. So the design is **two-layer**: app-controlled Ed25519 over the ZIP, then Squirrel.Mac's `SecStaticCodeCheckValidity` on the unpacked bundle. There is no Windows Authenticode or Linux ed25519 code path despite the README listing both (`README.md:228`).

## 4. IPC threat model

Preload surface (`src/preload.cjs:6-14`) is intentionally tiny:

```js
contextBridge.exposeInMainWorld('api', {
    onSetPromptText: (callback) => ipcRenderer.on('set-prompt-text', ...),
    sendUserInput: (data) => ipcRenderer.send('user-input', data)
});
```

`ipcMain` channels registered by the library:
- `updater/force-update` via `ipcMain.handle` in the `Updater` constructor (`src/common.js:195`) — invokable from any renderer with no auth.
- `start-update` via `ipcMain.handleOnce`, re-registered each cycle (`src/common.js:352-353`).
- `user-input` via `ipcMain.once`, scoped to a single version-picker window (`src/common.js:315`) and cleaned up by `ipcMain.removeAllListeners('user-input')` (`src/common.js:286`).

The internal version-picker window enforces the hardened defaults:
```js
// src/common.js:277-281
webPreferences: {
    nodeIntegration: false,
    contextIsolation: true,
    preload: path.join(__dirname, 'preload.cjs'),
}
```
`sandbox: true` is *not* set, and there is no `webSecurity` or CSP meta tag in `src/input.html`. The host app's main window is created and hardened by the host, not by this package — the bundled `tools/example.main.js:65-72` actually shows a *bad* example with no `contextIsolation` and `openDevTools()` left on.

**Threat-model gap:** `updater/force-update` and `start-update` have no sender-frame validation (no `event.senderFrame` check), so any compromised renderer or sub-frame can trigger an update install cycle.

## 5. Update protocol

**Not TUF.** The feed is a flat layout under `config.updatesUrl` (`util/pathAndDir.js:106`):

- `/<channel>-mac.yml` — top-level update-check manifest (`util/pathAndDir.js:163-169`), channel derived from prerelease tag (`util/version.js:73-94`: `staging`, `alpha`, `axolotl`, `beta`, `latest`).
- `/releases/versions.json` — global version list (`util/pathAndDir.js:98`), signed by `versions.json.sig` (`src/common.js:1079`).
- `/releases/<version>/<version>.yml` — per-version manifest (`util/pathAndDir.js:102`).
- `<asset>.sig` — sibling Ed25519 signature, hex-encoded, fetched as text and `Buffer.from(text, 'hex')` (`src/downloadandverify.js:108-117`).

YAML is parsed under `FAILSAFE_SCHEMA` to block js-yaml tag-based RCE (`src/util.js:177-181`). Asset filenames are restricted to `^[A-Za-z0-9.-]+$` (`src/util.js:187-189`), and every download target is validated with `validatePath`→`isPathInside` before write (`src/common.js:816-818`, `util/pathAndDir.js:46-54`, `util/isPathInside.js:3-15`).

Transport: HTTPS via `got` with a custom `https.Agent`. `getGotOptions()` reads a CA bundle from `config.certificateAuthority` and uses `rejectUnauthorized: !allowInsecureTLS` (`src/got.js:32-44`). Default config pins a CA placeholder (`config/default.json:3`). The `allowInsecureTLS` escape hatch exists (`src/got.js:19`) — risk if mis-set.

Compatibility: `electron-updater` is listed in deps (`package.json:46`) but never imported. Actual install on macOS reuses Electron's built-in Squirrel.Mac `autoUpdater` via a local `file://` feed:

```js
// src/macos.js:84-96
const feedPath = join(tempDir, 'feed.json');
await writeFile(feedPath, JSON.stringify({ url: updateUrl }));
autoUpdater.setFeedURL({ url: pathToFileURL(feedPath).href, serverType: 'json' });
autoUpdater.checkForUpdates();
```

That is, after Ed25519 passes, the library writes a Squirrel feed pointing at the local ZIP and lets Squirrel.Mac swap the bundle.

## 6. Attack-surface reduction

What the design explicitly does:
- `nodeIntegration: false` + `contextIsolation: true` on the only window it creates (`src/common.js:278-279`).
- YAML `FAILSAFE_SCHEMA` (`src/util.js:178`).
- Asset-filename allowlist regex (`src/util.js:187`).
- Path-traversal guard on every write target (`util/pathAndDir.js:46-54`).
- Per-process temp dir with `mode: 0o700` and UUIDv4 name (`util/pathAndDir.js:71-73`).
- Pinned CA + `rejectUnauthorized: true` by default (`src/got.js:33-44`).
- Refusal to run on Mac App Store builds or unpackaged dev (`src/index.js:67`).
- Polling jitter `now + rand*POLL_INTERVAL` to avoid thundering-herd hits on the feed server (`src/common.js:400-404`).

What it does **not** do: no CSP meta in `input.html`, no `sandbox: true`, no `webSecurity` setting, no `setPermissionRequestHandler`, no `will-navigate`/`new-window` blocking, no sender-frame check on `ipcMain` handlers, no certificate-pinning beyond CA-bundle pinning, no rollback floor for the *update* path (only for the *downgrade* path via `minDowngradeVersion` at `src/common.js:740-746`).

## 7. Privilege separation

Install always runs as the invoking user — there is no helper binary, no `SMJobBless`, no `AuthorizationExecuteWithPrivileges`. The macOS swap is delegated wholly to Electron's `autoUpdater.quitAndInstall()` (`src/macos.js:48`), which uses Squirrel.Mac's `ShipIt` helper. ShipIt runs as the user and replaces the `.app` bundle in place; this means the app must live somewhere user-writable (`/Applications` requires the install to have been done with admin rights originally and Squirrel.Mac will fail on read-only volumes — handled here only by a string-match on the error message at `src/macos.js:40-41`).

The "install on next launch" flow (`src/index.js:46-58`) persists `installOnNextLaunch` + `updateFeedUrl` to `electron-store`. On the next start, before the new `Updater` is even constructed, it re-points `autoUpdater` at the cached feed URL and calls `quitAndInstall()` immediately. Because `electron-store` is just JSON in `userData`, a local attacker who can write that JSON can substitute the `updateFeedUrl` — but the resulting payload still has to pass Squirrel.Mac codesign verification, so this is bounded.

## 8. Tests / threat scenarios

Three Vitest integration files; no unit tests for `common.js`'s FSM. Scenarios covered:
- Ed25519 sign+verify roundtrip with disk-loaded keys (`tests/integration/signature.integration.test.js:47-58`).
- `downloadAndVerify` happy paths for text/JSON/buffer, and explicit `signature verification fails → throws` (`tests/integration/downloadAndVerify.integration.test.js:58-70`).
- SHA-512 integrity helper positive + negative (`tests/integration/util.integration.test.js:54-67`), tempdir creation/cleanup.

What is **not** tested: TLS pinning behaviour, path-traversal rejection, the `installOnNextLaunch` replay, downgrade floor enforcement, IPC handler authorization, malformed YAML, manifest version-binding (which would catch the `"version"` literal bug noted in §3).

## 9. What's genuinely novel at the code level

The reusable pattern is the **two-layer signature model**: app-managed Ed25519 (vendor-controlled key) signs `sha256(payload)||"-"||version`, *and* the OS code-signing trust chain runs on the bundle at install time via Squirrel.Mac. This decouples the auto-update trust root from the platform CA / Developer-ID world, so a stolen Apple Developer ID alone isn't enough to push an update and the vendor's offline Ed25519 key alone isn't enough to bypass macOS Gatekeeper. The second reusable idea is the `downloadAndVerify` shape (`src/downloadandverify.js:23`) — every fetched control file (versions list, per-version YAML) is paired with a sibling `.sig` and refused on mismatch, so the manifest can't be substituted out-of-band even if the CDN is compromised. The path-traversal+filename-regex+`FAILSAFE_SCHEMA` triple in `util/pathAndDir.js:46`, `src/util.js:187`, and `src/util.js:178` is a tight, copyable hardening template for any updater that deserializes server-supplied manifests.
