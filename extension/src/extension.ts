import * as vscode from 'vscode';
import axios from 'axios';
import * as fs from 'fs';
import * as path from 'path';

export function activate(context: vscode.ExtensionContext) {

    const disposable = vscode.commands.registerCommand('qa.auditProject', async () => {

        try {
            const workspaceFolders = vscode.workspace.workspaceFolders;

            if (!workspaceFolders) {
                vscode.window.showErrorMessage("Abra um projeto primeiro.");
                return;
            }

            const files = await vscode.workspace.findFiles('**/*.py', '**/node_modules/**');

            let missingTests: vscode.Uri[] = [];

            for (const file of files) {
                const filePath = file.fsPath;
                const dir = path.dirname(filePath);
                const name = path.basename(filePath);

                const testFile = path.join(dir, `test_${name}`);

                if (!fs.existsSync(testFile)) {
                    missingTests.push(file);
                }
            }

            if (missingTests.length === 0) {
                vscode.window.showInformationMessage("Tudo coberto com testes.");
                return;
            }

            const pick = await vscode.window.showQuickPick(
                missingTests.map(f => f.fsPath),
                { placeHolder: "Selecione arquivo para gerar teste" }
            );

            if (!pick) return;

            const code = fs.readFileSync(pick, 'utf-8');

            vscode.window.showInformationMessage("Gerando testes...");

            const response = await axios.post('http://localhost:8000/generate-tests', {
                file_path: pick,
                code: code
            });

            const testCode = response.data.tests;

            const testPath = path.join(
                path.dirname(pick),
                `test_${path.basename(pick)}`
            );

            fs.writeFileSync(testPath, testCode);

            vscode.window.showInformationMessage(`Teste criado: ${testPath}`);

        } catch (error: any) {
            vscode.window.showErrorMessage("Erro: " + error.message);
        }

    });

    context.subscriptions.push(disposable);
}

export function deactivate() {}