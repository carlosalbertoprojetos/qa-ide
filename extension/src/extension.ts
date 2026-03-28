import * as path from "path";
import * as vscode from "vscode";
import axios from "axios";

const BACKEND_BASE_URL = "http://127.0.0.1:8000";
const MAX_CODE_LENGTH = 25000;
const PASS_ICON = "\u2714";
const FAIL_ICON = "\u2716";
let outputChannel: vscode.OutputChannel;

type FullAuditAttempt = {
  attempt: number;
  success: boolean;
  output: string;
  errors: string;
  corrected: boolean;
};

type FullAuditResult = {
  success: boolean;
  auto_corrected: boolean;
  total_attempts: number;
  attempts: FullAuditAttempt[];
};

type FullAuditResponsePayload = {
  plan: string;
  tests: string;
  result: FullAuditResult;
  fixed_tests: string;
  history_path: string;
  created_at: string;
};

type HistoryEntry = {
  filePath: string;
  fileName: string;
  modifiedAt: number;
};

export function activate(context: vscode.ExtensionContext) {
  outputChannel = vscode.window.createOutputChannel("QA IDE");

  const auditCommand = vscode.commands.registerCommand("qa.audit", async () => {
    const document = getActiveDocument();
    if (!document) {
      return;
    }

    const code = getDocumentCode(document);
    if (!code) {
      return;
    }

    try {
      await vscode.window.withProgress(
        {
          location: vscode.ProgressLocation.Notification,
          title: "QA IDE: Analisando codigo...",
          cancellable: false,
        },
        async () => {
          const response = await axios.post(
            `${BACKEND_BASE_URL}/audit`,
            {
              code,
              filePath: document.uri.fsPath,
            },
            {
              timeout: 20000,
            }
          );

          const analysis = response?.data?.analysis;
          if (!analysis || typeof analysis !== "string") {
            throw new Error("Resposta invalida do servidor de auditoria.");
          }

          outputChannel.clear();
          outputChannel.appendLine("QA IDE - Auditoria de codigo");
          outputChannel.appendLine(`Arquivo: ${document.uri.fsPath}`);
          outputChannel.appendLine("");
          outputChannel.appendLine(analysis);
          outputChannel.show(true);
        }
      );

      vscode.window.showInformationMessage("Auditoria concluida. Veja o painel QA IDE.");
    } catch (error: unknown) {
      vscode.window.showErrorMessage(`Falha na auditoria: ${getErrorMessage(error)}`);
    }
  });

  const generateTestsCommand = vscode.commands.registerCommand("qa.generateTests", async () => {
    const document = getActiveDocument();
    if (!document) {
      return;
    }

    if (document.isUntitled) {
      vscode.window.showErrorMessage("Salve o arquivo antes de gerar testes.");
      return;
    }

    if (path.extname(document.fileName).toLowerCase() !== ".py") {
      vscode.window.showErrorMessage("A geracao automatica de testes esta disponivel apenas para arquivos Python.");
      return;
    }

    const sourceName = path.basename(document.fileName);
    const sourceStem = path.parse(sourceName).name;
    if (sourceStem.startsWith("test_")) {
      vscode.window.showWarningMessage("O arquivo atual ja parece ser um teste pytest.");
      return;
    }

    const code = getDocumentCode(document);
    if (!code) {
      return;
    }

    const testFileName = `test_${sourceStem}.py`;
    const targetPath = path.join(path.dirname(document.fileName), testFileName);
    const targetUri = vscode.Uri.file(targetPath);

    if (await fileExists(targetUri)) {
      vscode.window.showWarningMessage(`O arquivo de teste ja existe: ${targetPath}`);
      return;
    }

    try {
      await vscode.window.withProgress(
        {
          location: vscode.ProgressLocation.Notification,
          title: "QA IDE: Gerando testes...",
          cancellable: false,
        },
        async () => {
          const response = await axios.post(
            `${BACKEND_BASE_URL}/generate-tests`,
            { code, filename: sourceName },
            { timeout: 30000 }
          );

          const tests = response?.data?.tests;
          if (!tests || typeof tests !== "string") {
            throw new Error("Resposta invalida do servidor de testes.");
          }

          await vscode.workspace.fs.writeFile(targetUri, Buffer.from(tests, "utf8"));
        }
      );

      const createdDocument = await vscode.workspace.openTextDocument(targetUri);
      await vscode.window.showTextDocument(createdDocument, { preview: false });
      vscode.window.showInformationMessage(`Testes gerados com sucesso em: ${targetPath}`);
    } catch (error: unknown) {
      vscode.window.showErrorMessage(`Falha ao gerar testes: ${getErrorMessage(error)}`);
    }
  });

  const runTestsCommand = vscode.commands.registerCommand("qa.runTests", async () => {
    const projectPath = getProjectPath();
    if (!projectPath) {
      return;
    }

    try {
      await vscode.window.withProgress(
        {
          location: vscode.ProgressLocation.Notification,
          title: "QA IDE: Rodando testes...",
          cancellable: false,
        },
        async () => {
          const response = await axios.post(
            `${BACKEND_BASE_URL}/run-tests`,
            { path: projectPath },
            { timeout: 180000 }
          );

          const success = response?.data?.success;
          const output = response?.data?.output;
          const errors = response?.data?.errors;
          if (typeof success !== "boolean" || typeof output !== "string" || typeof errors !== "string") {
            throw new Error("Resposta invalida do servidor de execucao de testes.");
          }

          showTestRunResults(projectPath, success, output, errors);
        }
      );
    } catch (error: unknown) {
      vscode.window.showErrorMessage(`Falha ao rodar testes: ${getErrorMessage(error)}`);
    }
  });

  const fullAuditCommand = vscode.commands.registerCommand("qa.fullAudit", async () => {
    const document = getActiveDocument();
    if (!document) {
      return;
    }

    const targetFileName = getFullAuditFilename(document);
    if (!targetFileName) {
      return;
    }

    const code = getDocumentCode(document);
    if (!code) {
      return;
    }

    try {
      await vscode.window.withProgress(
        {
          location: vscode.ProgressLocation.Notification,
          title: "QA IDE: Rodando auditoria completa inteligente...",
          cancellable: false,
        },
        async () => {
          const response = await axios.post(
            `${BACKEND_BASE_URL}/full-audit`,
            { code, filename: targetFileName },
            { timeout: 180000 }
          );

          if (!isFullAuditResponsePayload(response?.data)) {
            throw new Error("Resposta invalida do servidor de auditoria completa.");
          }

          showFullAuditResults(targetFileName, response.data);
        }
      );
    } catch (error: unknown) {
      vscode.window.showErrorMessage(`Falha na auditoria completa: ${getErrorMessage(error)}`);
    }
  });

  const openLatestHistoryCommand = vscode.commands.registerCommand("qa.openLatestHistory", async () => {
    const projectPath = getProjectPath();
    if (!projectPath) {
      return;
    }

    const historyDir = path.join(projectPath, ".qa_audit_history");
    const latestHistory = await getLatestHistoryFile(historyDir);
    if (!latestHistory) {
      vscode.window.showWarningMessage(`Nenhum historico encontrado em: ${historyDir}`);
      return;
    }

    const historyUri = vscode.Uri.file(latestHistory);
    const historyDocument = await vscode.workspace.openTextDocument(historyUri);
    await vscode.window.showTextDocument(historyDocument, { preview: false });
    vscode.window.showInformationMessage(`Historico mais recente aberto: ${latestHistory}`);
  });

  const browseHistoryCommand = vscode.commands.registerCommand("qa.browseHistory", async () => {
    const projectPath = getProjectPath();
    if (!projectPath) {
      return;
    }

    const historyDir = path.join(projectPath, ".qa_audit_history");
    const historyEntries = await getHistoryEntries(historyDir);
    if (historyEntries.length === 0) {
      vscode.window.showWarningMessage(`Nenhum historico encontrado em: ${historyDir}`);
      return;
    }

    const selection = await vscode.window.showQuickPick(
      historyEntries.map((entry) => ({
        label: entry.fileName,
        description: formatHistoryTimestamp(entry.modifiedAt),
        detail: entry.filePath,
        entry,
      })),
      {
        placeHolder: "Selecione um historico de auditoria para abrir",
        matchOnDescription: true,
        matchOnDetail: true,
      }
    );

    if (!selection) {
      return;
    }

    const historyUri = vscode.Uri.file(selection.entry.filePath);
    const historyDocument = await vscode.workspace.openTextDocument(historyUri);
    await vscode.window.showTextDocument(historyDocument, { preview: false });
    vscode.window.showInformationMessage(`Historico aberto: ${selection.entry.filePath}`);
  });

  context.subscriptions.push(
    auditCommand,
    generateTestsCommand,
    runTestsCommand,
    fullAuditCommand,
    openLatestHistoryCommand,
    browseHistoryCommand,
    outputChannel
  );
}

export function deactivate() {
  outputChannel?.dispose();
}

function getActiveDocument(): vscode.TextDocument | undefined {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    vscode.window.showErrorMessage("Abra um arquivo antes de executar este comando.");
    return undefined;
  }

  return editor.document;
}

function getDocumentCode(document: vscode.TextDocument): string | undefined {
  const code = document.getText().trim();
  if (!code) {
    vscode.window.showErrorMessage("O arquivo atual esta vazio.");
    return undefined;
  }

  return code.length > MAX_CODE_LENGTH ? code.slice(0, MAX_CODE_LENGTH) : code;
}

function getFullAuditFilename(document: vscode.TextDocument): string | undefined {
  if (document.isUntitled) {
    if (document.languageId !== "python") {
      vscode.window.showErrorMessage("A auditoria completa inteligente exige um arquivo Python ou um editor Python sem salvar.");
      return undefined;
    }

    return "untitled.py";
  }

  const fileName = path.basename(document.fileName);
  if (path.extname(fileName).toLowerCase() !== ".py") {
    vscode.window.showErrorMessage("A auditoria completa inteligente esta disponivel apenas para arquivos Python.");
    return undefined;
  }

  return fileName;
}

function getProjectPath(): string | undefined {
  const editor = vscode.window.activeTextEditor;
  if (editor) {
    const folder = vscode.workspace.getWorkspaceFolder(editor.document.uri);
    if (folder) {
      return folder.uri.fsPath;
    }

    if (!editor.document.isUntitled) {
      return path.dirname(editor.document.fileName);
    }
  }

  const firstWorkspaceFolder = vscode.workspace.workspaceFolders?.[0];
  if (firstWorkspaceFolder) {
    return firstWorkspaceFolder.uri.fsPath;
  }

  vscode.window.showErrorMessage("Abra uma pasta ou um arquivo do projeto antes de rodar os testes.");
  return undefined;
}

async function fileExists(uri: vscode.Uri): Promise<boolean> {
  try {
    await vscode.workspace.fs.stat(uri);
    return true;
  } catch {
    return false;
  }
}

async function getLatestHistoryFile(historyDir: string): Promise<string | undefined> {
  const entries = await getHistoryEntries(historyDir);
  return entries[0]?.filePath;
}

async function getHistoryEntries(historyDir: string): Promise<HistoryEntry[]> {
  const historyUri = vscode.Uri.file(historyDir);
  try {
    const entries = await vscode.workspace.fs.readDirectory(historyUri);
    const jsonFiles = entries
      .filter(([name, fileType]) => fileType === vscode.FileType.File && name.toLowerCase().endsWith(".json"))
      .map(([name]) => path.join(historyDir, name));

    const stats = await Promise.all(
      jsonFiles.map(async (filePath) => {
        const stat = await vscode.workspace.fs.stat(vscode.Uri.file(filePath));
        return {
          filePath,
          fileName: path.basename(filePath),
          modifiedAt: stat.mtime,
        };
      })
    );

    stats.sort((left, right) => right.modifiedAt - left.modifiedAt);
    return stats;
  } catch {
    return [];
  }
}

function formatHistoryTimestamp(timestamp: number): string {
  return new Date(timestamp).toLocaleString();
}

function isFullAuditResult(value: unknown): value is FullAuditResult {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Partial<FullAuditResult>;
  return (
    typeof candidate.success === "boolean" &&
    typeof candidate.auto_corrected === "boolean" &&
    typeof candidate.total_attempts === "number" &&
    Array.isArray(candidate.attempts)
  );
}

function isFullAuditResponsePayload(value: unknown): value is FullAuditResponsePayload {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Partial<FullAuditResponsePayload>;
  return (
    typeof candidate.plan === "string" &&
    typeof candidate.tests === "string" &&
    isFullAuditResult(candidate.result) &&
    typeof candidate.fixed_tests === "string" &&
    typeof candidate.history_path === "string" &&
    typeof candidate.created_at === "string"
  );
}

function showTestRunResults(projectPath: string, success: boolean, output: string, errors: string): void {
  outputChannel.clear();
  outputChannel.appendLine("QA IDE - Execucao de Testes");
  outputChannel.appendLine(`Projeto: ${projectPath}`);
  outputChannel.appendLine(`Status Geral: ${success ? `${PASS_ICON} testes passaram` : `${FAIL_ICON} testes falharam`}`);
  outputChannel.appendLine("");
  outputChannel.appendLine("Resultado:");
  outputChannel.appendLine(output);

  if (errors.trim()) {
    outputChannel.appendLine("");
    outputChannel.appendLine("Erros Principais:");
    outputChannel.appendLine(highlightErrors(errors));
  }

  outputChannel.show(true);

  const message = success
    ? `${PASS_ICON} Testes executados com sucesso em: ${projectPath}`
    : `${FAIL_ICON} Falhas encontradas na execucao dos testes em: ${projectPath}`;

  if (success) {
    void vscode.window.showInformationMessage(message);
  } else {
    void vscode.window.showWarningMessage(message);
  }
}

function showFullAuditResults(filename: string, payload: FullAuditResponsePayload): void {
  outputChannel.clear();
  outputChannel.appendLine("QA IDE - Auditoria Completa Inteligente");
  outputChannel.appendLine(`Arquivo: ${filename}`);
  outputChannel.appendLine(`Status Final: ${payload.result.success ? PASS_ICON : FAIL_ICON}`);
  outputChannel.appendLine(`Total de Tentativas: ${payload.result.total_attempts}`);
  outputChannel.appendLine(`Autocorrecao: ${payload.result.auto_corrected ? "sim" : "nao"}`);
  outputChannel.appendLine(`Executado em: ${payload.created_at}`);
  outputChannel.appendLine(`Historico salvo em: ${payload.history_path}`);
  outputChannel.appendLine("");
  outputChannel.appendLine("Plano do Planner:");
  outputChannel.appendLine(payload.plan);
  outputChannel.appendLine("");
  outputChannel.appendLine("Testes Gerados:");
  outputChannel.appendLine(payload.tests);
  outputChannel.appendLine("");
  outputChannel.appendLine("Historico Estruturado de Tentativas:");

  for (const attempt of payload.result.attempts) {
    outputChannel.appendLine(
      `${attempt.success ? PASS_ICON : FAIL_ICON} Tentativa ${attempt.attempt} | corrigido: ${attempt.corrected ? "sim" : "nao"}`
    );
    outputChannel.appendLine("Saida:");
    outputChannel.appendLine(attempt.output || "(sem saida)");
    if (attempt.errors.trim()) {
      outputChannel.appendLine("Erros:");
      outputChannel.appendLine(highlightErrors(attempt.errors));
    }
    outputChannel.appendLine("");
  }

  outputChannel.appendLine("Testes Finais / Corrigidos:");
  outputChannel.appendLine(payload.fixed_tests);
  outputChannel.show(true);

  const message = payload.result.success
    ? `${PASS_ICON} Auditoria completa concluida. Historico salvo em: ${payload.history_path}`
    : `${FAIL_ICON} Auditoria completa finalizou com falhas. Historico salvo em: ${payload.history_path}`;

  if (payload.result.success) {
    void vscode.window.showInformationMessage(message);
  } else {
    void vscode.window.showWarningMessage(message);
  }
}

function highlightErrors(errors: string): string {
  return errors
    .split(/\r?\n/)
    .filter((line) => line.trim().length > 0)
    .map((line) => `${FAIL_ICON} ${line}`)
    .join("\n");
}

function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    return typeof detail === "string" ? detail : error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return String(error);
}
