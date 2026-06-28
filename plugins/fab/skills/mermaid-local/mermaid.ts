/**
 * mermaid.ts — Local Mermaid diagram validator and renderer.
 *
 * Usage:
 *   echo 'graph TD; A-->B' | bun mermaid.ts validate
 *   bun mermaid.ts validate < diagram.mmd
 *   bun mermaid.ts render diagram.mmd output.png
 *   bun mermaid.ts render diagram.mmd output.svg
 *   echo 'graph TD; A-->B' | bun mermaid.ts render - output.png
 */

import { execSync } from "child_process";
import { existsSync, readFileSync, writeFileSync, mkdirSync } from "fs";
import { basename, resolve, extname } from "path";

const MERMAID_VERSION = "11";
const SCRIPT_DIR = resolve(import.meta.dir);
const CACHE_DIR = resolve(SCRIPT_DIR, ".cache");

// Ensure cache dir
if (!existsSync(CACHE_DIR)) mkdirSync(CACHE_DIR, { recursive: true });

const MERMAID_JS_PATH = resolve(CACHE_DIR, `mermaid.${MERMAID_VERSION}.min.js`);

async function ensureMermaid() {
  if (existsSync(MERMAID_JS_PATH)) return;
  console.error(`Downloading mermaid v${MERMAID_VERSION}...`);
  const url = `https://cdn.jsdelivr.net/npm/mermaid@${MERMAID_VERSION}/dist/mermaid.min.js`;
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`Failed to download mermaid: ${resp.status}`);
  const js = await resp.text();
  writeFileSync(MERMAID_JS_PATH, js);
  console.error(`Cached to ${MERMAID_JS_PATH}`);
}

function readInput(inputPath: string): string {
  if (inputPath === "-") {
    return readFileSync("/dev/stdin", "utf-8");
  }
  const abs = resolve(inputPath);
  if (!existsSync(abs)) {
    console.error(`File not found: ${abs}`);
    process.exit(1);
  }
  return readFileSync(abs, "utf-8");
}

const HTML_TEMPLATE = (mermaidJs: string, diagram: string, theme: string) => `
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body { margin: 0; padding: 20px; background: white; }
  .mermaid { font-family: sans-serif; }
  .error { color: red; font-family: monospace; white-space: pre-wrap; }
</style>
</head>
<body>
<div id="container">
  <pre class="mermaid">${diagram.replace(/</g, "&lt;").replace(/>/g, "&gt;")}</pre>
</div>
<div id="error" class="error"></div>
<script>
${mermaidJs}
</script>
<script>
  mermaid.initialize({
    startOnLoad: true,
    theme: '${theme}',
    securityLevel: 'loose',
    suppressErrors: false,
    logLevel: 'error',
  });

  // Capture parse errors
  const origError = console.error;
  const errors = [];
  console.error = function(...args) {
    errors.push(args.join(' '));
    origError.apply(console, args);
  };

  window.__mermaidErrors = errors;
  window.__mermaidReady = false;

  mermaid.run({ querySelector: '.mermaid' }).then(() => {
    window.__mermaidReady = true;
  }).catch(err => {
    errors.push(err.message || String(err));
    window.__mermaidReady = true;
  });
</script>
</body>
</html>
`;

async function validate(diagram: string): Promise<boolean> {
  const { chromium } = await import("playwright");
  const mermaidJs = readFileSync(MERMAID_JS_PATH, "utf-8");
  const html = HTML_TEMPLATE(mermaidJs, diagram, "default");

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  try {
    await page.setContent(html, { waitUntil: "load" });

    // Wait for mermaid to finish rendering
    await page.waitForFunction(() => (window as any).__mermaidReady === true, {
      timeout: 10000,
    });

    const errors: string[] = await page.evaluate(
      () => (window as any).__mermaidErrors || [],
    );

    // Also check if mermaid actually produced SVG
    const svgCount = await page.locator("svg").count();

    if (errors.length > 0 && svgCount === 0) {
      console.log("INVALID:");
      for (const e of errors) {
        console.log("  " + e.split("\n")[0]);
      }
      return false;
    }

    if (svgCount === 0) {
      console.log("INVALID: no SVG produced (syntax error or empty diagram)");
      return false;
    }

    console.log("VALID");
    return true;
  } catch (e: any) {
    // If page.setContent fails, it's likely a syntax error
    const msg = e?.message || String(e);
    if (msg.includes("Parse error") || msg.includes("error")) {
      console.log("INVALID:");
      console.log("  " + msg.split("\n")[0]);
      return false;
    }
    console.log("INVALID: " + msg.split("\n")[0]);
    return false;
  } finally {
    await browser.close();
  }
}

async function render(
  diagram: string,
  outputPath: string,
  theme: string = "default",
): Promise<void> {
  const { chromium } = await import("playwright");
  const mermaidJs = readFileSync(MERMAID_JS_PATH, "utf-8");
  const html = HTML_TEMPLATE(mermaidJs, diagram, theme);

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  try {
    await page.setContent(html, { waitUntil: "load" });

    await page.waitForFunction(() => (window as any).__mermaidReady === true, {
      timeout: 15000,
    });

    const errors: string[] = await page.evaluate(
      () => (window as any).__mermaidErrors || [],
    );
    const svgCount = await page.locator("svg").count();

    if (errors.length > 0 && svgCount === 0) {
      console.error("Cannot render — diagram has errors:");
      for (const e of errors) console.error("  " + e.split("\n")[0]);
      process.exit(1);
    }

    const ext = extname(outputPath).toLowerCase();
    const absOutput = resolve(outputPath);

    if (ext === ".svg") {
      // Extract SVG directly from DOM
      const svg = await page.locator("svg").first().innerHTML();
      const svgFull = `<svg xmlns="http://www.w3.org/2000/svg" ${svg}>`;
      // Get the full outerHTML
      const outerSvg = await page.evaluate(() => {
        const svg = document.querySelector("svg");
        return svg ? svg.outerHTML : "";
      });
      writeFileSync(absOutput, outerSvg);
      console.log(`SVG written to ${absOutput}`);
    } else {
      // PNG screenshot
      const svgEl = await page.locator("svg").first();
      const box = await svgEl.boundingBox();
      if (!box) {
        console.error("Could not get SVG bounding box");
        process.exit(1);
      }

      // Add some padding
      const padding = 20;
      await page.setViewportSize({
        width: Math.ceil(box.width + padding * 2),
        height: Math.ceil(box.height + padding * 2),
      });

      await page.screenshot({
        path: absOutput,
        clip: {
          x: box.x - padding,
          y: box.y - padding,
          width: box.width + padding * 2,
          height: box.height + padding * 2,
        },
        type: "png",
      });
      console.log(
        `PNG written to ${absOutput} (${Math.ceil(box.width)}x${Math.ceil(box.height)}px)`,
      );
    }
  } finally {
    await browser.close();
  }
}

// ── CLI ──────────────────────────────────────────────────────────────────────

const args = process.argv.slice(2);
const command = args[0];

if (!command || (command !== "validate" && command !== "render")) {
  console.log("Usage:");
  console.log("  bun mermaid.ts validate [file.mmd | -]");
  console.log(
    "  bun mermaid.ts render <file.mmd | -> <output.png|svg> [--theme dark|default|forest|neutral]",
  );
  process.exit(1);
}

await ensureMermaid();

if (command === "validate") {
  const inputPath = args[1] || "-";
  const diagram = readInput(inputPath);
  const ok = await validate(diagram);
  process.exit(ok ? 0 : 1);
}

if (command === "render") {
  const inputPath = args[1];
  const outputPath = args[2];
  const themeIdx = args.indexOf("--theme");
  const theme = themeIdx >= 0 ? args[themeIdx + 1] : "default";

  if (!inputPath || !outputPath) {
    console.error(
      "Usage: bun mermaid.ts render <input.mmd|-> <output.png|svg>",
    );
    process.exit(1);
  }

  const diagram = readInput(inputPath);
  await render(diagram, outputPath, theme);
}
