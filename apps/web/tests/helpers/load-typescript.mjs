import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import { dirname } from "node:path";
import ts from "typescript";

const nodeRequire = createRequire(import.meta.url);

export function loadTypescriptModule(url) {
  const filename = url.pathname;
  const source = readFileSync(url, "utf8");
  const output = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
      esModuleInterop: true
    },
    fileName: filename
  }).outputText;
  const loadedModule = { exports: {} };
  const execute = new Function("exports", "require", "module", "__filename", "__dirname", output);
  execute(loadedModule.exports, nodeRequire, loadedModule, filename, dirname(filename));
  return loadedModule.exports;
}
