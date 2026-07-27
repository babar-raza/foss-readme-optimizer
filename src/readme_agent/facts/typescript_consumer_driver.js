"use strict";

const crypto = require("crypto");
const fs = require("fs");
const path = require("path");
const childProcess = require("child_process");

const RESULT_PREFIX = "README_AGENT_TYPESCRIPT_CONSUMER=";
const workspace = process.cwd();
const config = JSON.parse(
  fs.readFileSync(path.join(workspace, ".readme-agent-typescript-config.json"), "utf8"),
);

function run(argv, cwd = workspace) {
  const result = childProcess.spawnSync(argv[0], argv.slice(1), {
    cwd,
    encoding: "utf8",
    env: { HOME: "/tmp", PATH: process.env.PATH },
  });
  return {
    argv,
    returnCode: result.status === null ? 1 : result.status,
    stdout: (result.stdout || "").slice(0, 12000),
    stderr: (result.stderr || "").slice(0, 12000),
  };
}

function sha256File(file) {
  return crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
}

function extract(archive, destination) {
  fs.mkdirSync(destination, { recursive: true });
  const result = run(["tar", "-xzf", archive, "--strip-components=1", "-C", destination]);
  if (result.returnCode !== 0) {
    throw new Error(`cannot extract ${archive}: ${result.stderr}`);
  }
}

function copyTree(source, destination) {
  fs.cpSync(source, destination, { recursive: true, force: true });
}

function relativeDeclaration(file, packageRoot) {
  return path.relative(packageRoot, file).split(path.sep).join("/");
}

function declarationKind(ts, declaration) {
  if (ts.isClassDeclaration(declaration)) return "class";
  if (ts.isInterfaceDeclaration(declaration)) return "interface";
  if (ts.isTypeAliasDeclaration(declaration)) return "type_alias";
  if (ts.isEnumDeclaration(declaration)) return "enum";
  if (ts.isFunctionDeclaration(declaration)) return "function";
  if (ts.isVariableDeclaration(declaration)) return "variable";
  if (ts.isMethodDeclaration(declaration) || ts.isMethodSignature(declaration)) return "method";
  if (
    ts.isPropertyDeclaration(declaration) ||
    ts.isPropertySignature(declaration) ||
    ts.isGetAccessorDeclaration(declaration) ||
    ts.isSetAccessorDeclaration(declaration)
  ) {
    return "property";
  }
  if (ts.isEnumMember(declaration)) return "enum_member";
  return null;
}

function isPublic(ts, declaration, name) {
  if (!name || name.startsWith("_") || name.startsWith("#")) return false;
  const flags = ts.getCombinedModifierFlags(declaration);
  return !(flags & ts.ModifierFlags.Private) && !(flags & ts.ModifierFlags.Protected);
}

function symbolType(checker, symbol, declaration) {
  try {
    return checker
      .typeToString(
      checker.getTypeOfSymbolAtLocation(symbol, declaration),
      declaration,
      1,
      )
      .slice(0, 500);
  } catch {
    return null;
  }
}

function serializeSymbol(ts, checker, symbol, exportName, packageRoot, includeMembers) {
  const target = symbol.flags & ts.SymbolFlags.Alias ? checker.getAliasedSymbol(symbol) : symbol;
  const declarations = target.getDeclarations() || symbol.getDeclarations() || [];
  const declaration = declarations[0];
  if (!declaration) return [];
  const kind = declarationKind(ts, declaration);
  if (!kind || !isPublic(ts, declaration, exportName)) return [];
  const sourceFile = declaration.getSourceFile();
  const line = sourceFile.getLineAndCharacterOfPosition(declaration.getStart()).line + 1;
  const rows = [
    {
      qualifiedName: exportName,
      exportName,
      memberName: null,
      kind,
      declarationPath: relativeDeclaration(sourceFile.fileName, packageRoot),
      sourceLine: line,
      typeText: symbolType(checker, target, declaration),
      readonly: Boolean(ts.getCombinedModifierFlags(declaration) & ts.ModifierFlags.Readonly),
      compilerResolved: true,
    },
  ];
  const members = includeMembers ? declaration.members || [] : [];
  for (const member of members) {
    const memberName = member.name && member.name.getText(sourceFile).replace(/^["']|["']$/g, "");
    const memberKind = declarationKind(ts, member);
    if (!memberKind || !isPublic(ts, member, memberName)) continue;
    const memberSymbol = checker.getSymbolAtLocation(member.name);
    const memberLine = sourceFile.getLineAndCharacterOfPosition(member.getStart()).line + 1;
    rows.push({
      qualifiedName: `${exportName}.${memberName}`,
      exportName,
      memberName,
      kind: memberKind,
      declarationPath: relativeDeclaration(sourceFile.fileName, packageRoot),
      sourceLine: memberLine,
      typeText: memberSymbol ? symbolType(checker, memberSymbol, member) : null,
      readonly: Boolean(ts.getCombinedModifierFlags(member) & ts.ModifierFlags.Readonly),
      compilerResolved: true,
    });
  }
  return rows;
}

function emit(payload, exitCode) {
  process.stdout.write(`${RESULT_PREFIX}${JSON.stringify(payload)}\n`);
  process.exit(exitCode);
}

const toolchainRoot = path.join(workspace, ".readme-agent-toolchain");
const archives = path.join(workspace, ".readme-agent-toolchain-archives");
for (const artifact of config.toolchain.artifacts) {
  const archive = path.join(archives, artifact.filename);
  if (sha256File(archive) !== artifact.sha256) {
    throw new Error(`toolchain archive hash mismatch: ${artifact.filename}`);
  }
  let destination;
  if (artifact.name === "typescript") {
    destination = path.join(toolchainRoot, "node_modules", "typescript");
  } else if (artifact.name === "@types/node") {
    destination = path.join(toolchainRoot, "node_modules", "@types", "node");
  } else {
    destination = path.join(toolchainRoot, "node_modules", artifact.name);
  }
  extract(archive, destination);
}

const tsc = path.join(toolchainRoot, "node_modules", "typescript", "bin", "tsc");
const typeRoots = path.join(toolchainRoot, "node_modules", "@types");
const build = run(["node", tsc, "-p", config.package.buildConfigPath, "--typeRoots", typeRoots]);
if (build.returnCode !== 0) {
  emit({ accepted: false, build, diagnostics: [build.stdout, build.stderr], symbols: [] }, 30);
}

const packageRoot = path.join(workspace, ".readme-agent-built-package");
fs.mkdirSync(packageRoot, { recursive: true });
fs.copyFileSync(path.join(workspace, "package.json"), path.join(packageRoot, "package.json"));
copyTree(
  path.join(workspace, config.package.outputRoot),
  path.join(packageRoot, config.package.outputRoot),
);
const archivePath = path.join(workspace, ".readme-agent-built-package.tgz");
const packed = run(
  [
    "tar",
    "--sort=name",
    "--mtime=@0",
    "--owner=0",
    "--group=0",
    "-czf",
    archivePath,
    "-C",
    packageRoot,
    ".",
  ],
  workspace,
);
if (packed.returnCode !== 0) {
  emit({ accepted: false, build, packed, diagnostics: [packed.stderr], symbols: [] }, 31);
}

const consumerRoot = path.join(workspace, ".readme-agent-consumer");
const installedRoot = path.join(consumerRoot, "node_modules", ...config.package.packageName.split("/"));
fs.mkdirSync(installedRoot, { recursive: true });
const installed = run(["tar", "-xzf", archivePath, "-C", installedRoot]);
if (installed.returnCode !== 0) {
  emit({ accepted: false, build, packed, installed, diagnostics: [installed.stderr], symbols: [] }, 32);
}
fs.writeFileSync(path.join(consumerRoot, "consumer.ts"), config.example.code);
fs.writeFileSync(
  path.join(consumerRoot, "tsconfig.json"),
  JSON.stringify({
    compilerOptions: {
      target: "ES2020",
      module: "node16",
      moduleResolution: "node16",
      strict: true,
      noEmit: true,
      skipLibCheck: true,
      typeRoots: [typeRoots],
    },
    files: ["consumer.ts"],
  }),
);
const compile = run(["node", tsc, "-p", "tsconfig.json"], consumerRoot);

const ts = require(path.join(toolchainRoot, "node_modules", "typescript", "lib", "typescript.js"));
const consumerFile = path.join(consumerRoot, "consumer.ts");
const options = {
  target: ts.ScriptTarget.ES2020,
  module: ts.ModuleKind.Node16,
  moduleResolution: ts.ModuleResolutionKind.Node16,
  strict: true,
  noEmit: true,
  skipLibCheck: true,
  typeRoots: [typeRoots],
};
const program = ts.createProgram([consumerFile], options);
const checker = program.getTypeChecker();
const resolved = ts.resolveModuleName(
  config.example.importSpecifier,
  consumerFile,
  options,
  ts.sys,
).resolvedModule;
let symbols = [];
if (resolved) {
  const sourceFile = program.getSourceFile(resolved.resolvedFileName);
  const moduleSymbol = sourceFile && checker.getSymbolAtLocation(sourceFile);
  if (moduleSymbol) {
    const requiredRoots = new Set(
      config.example.requiredSymbols.map((name) => name.split(".", 1)[0]),
    );
    for (const exported of checker.getExportsOfModule(moduleSymbol)) {
      const exportName = exported.getName();
      symbols.push(
        ...serializeSymbol(
          ts,
          checker,
          exported,
          exportName,
          installedRoot,
          requiredRoots.has(exportName),
        ),
      );
    }
  }
}
symbols = symbols.sort((left, right) => left.qualifiedName.localeCompare(right.qualifiedName));
const available = new Set(symbols.map((item) => item.qualifiedName));
const missingSymbols = config.example.requiredSymbols.filter((name) => !available.has(name));
const diagnostics = ts
  .getPreEmitDiagnostics(program)
  .map((diagnostic) => ts.flattenDiagnosticMessageText(diagnostic.messageText, "\n").slice(0, 1000))
  .slice(0, 50);
const accepted =
  compile.returnCode === 0 && diagnostics.length === 0 && Boolean(resolved) && missingSymbols.length === 0;
emit(
  {
    accepted,
    build,
    packed,
    installed,
    compile,
    compilerVersion: ts.version,
    builtArtifactSha256: sha256File(archivePath),
    resolvedDeclarationPath: resolved
      ? relativeDeclaration(resolved.resolvedFileName, installedRoot)
      : null,
    symbols,
    missingSymbols,
    diagnostics,
  },
  accepted ? 0 : 33,
);
