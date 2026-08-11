// Owns the Python backend subprocess: finding the right interpreter,
// spawning it as `python -m server.main`, and polling until it's
// actually answering HTTP requests.

const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const http = require('http');
const { dialog } = require('electron');

const SERVER_PORT = 8000;
const SERVER_URL = `http://localhost:${SERVER_PORT}/`;

// ---------------------------------------------------------------------
// NOTE — dependency-free packaging:
// This spawns a Python interpreter to run the `server` package, which
// means the machine running the packaged app still needs Python 3 +
// the package's dependencies installed.
// ---------------------------------------------------------------------
function resolvePythonCommand(serverDir) {
  // Explicit override always wins.
  if (process.env.PYTHON_BIN) {
    return { command: process.env.PYTHON_BIN, args: ['-m', 'server.main'] };
  }

  // Look for a uv/venv-style .venv there and prefer its
  // interpreter, since that's where the project's actual dependencies
  // (aiohttp, etc.) are installed, not on system PATH.
  const projectRoot = path.join(serverDir, '..');
  const venvPython = process.platform === 'win32'
    ? path.join(projectRoot, '.venv', 'Scripts', 'python.exe')
    : path.join(projectRoot, '.venv', 'bin', 'python');

  if (fs.existsSync(venvPython)) {
    console.log(`[main] Using project venv interpreter: ${venvPython}`);
    return { command: venvPython, args: ['-m', 'server.main'] };
  }

  const fallback = process.platform === 'win32' ? 'python' : 'python3';
  console.log(`[main] No .venv found at ${projectRoot} — falling back to '${fallback}' on PATH`);
  return { command: fallback, args: ['-m', 'server.main'] };
}

class PythonServer {
  constructor() {
    this.process = null;
  }

  // cwd must be the directory that directly contains the `server`
  // package folder (i.e. gui/), since `-m server.main` resolves the
  // package relative to the current working directory.
  start(serverDir = __dirname) {
    const { command, args } = resolvePythonCommand(serverDir);

    this.process = spawn(command, args, { cwd: serverDir, env: process.env });

    this.process.stdout.on('data', d => console.log(`[server] ${d}`.trimEnd()));
    this.process.stderr.on('data', d => console.error(`[server] ${d}`.trimEnd()));

    this.process.on('error', err => {
      dialog.showErrorBox(
        'Could not start backend',
        `Failed to launch "${command} ${args.join(' ')}".\n\n${err.message}\n\n` +
        `Make sure Python 3 and its dependencies (fastapi, uvicorn, etc.) are ` +
        `installed and on PATH, or set the PYTHON_BIN environment variable to ` +
        `the interpreter to use.`
      );
    });

    this.process.on('exit', code => {
      console.log(`Python server exited with code ${code}`);
    });
  }

  stop() {
    if (this.process) this.process.kill();
  }

  waitUntilReady({ timeoutMs = 15000, intervalMs = 250 } = {}) {
    const start = Date.now();
    return new Promise((resolve, reject) => {
      const tryOnce = () => {
        const req = http.get(SERVER_URL, res => {
          res.resume();
          resolve();
        });
        req.on('error', () => {
          if (Date.now() - start > timeoutMs) {
            reject(new Error(`No response from ${SERVER_URL} within ${timeoutMs}ms`));
          } else {
            setTimeout(tryOnce, intervalMs);
          }
        });
      };
      tryOnce();
    });
  }
}

module.exports = { PythonServer, SERVER_URL, SERVER_PORT };
