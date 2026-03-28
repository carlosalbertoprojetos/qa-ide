cat > src/extension.ts << 'EOF'
import * as vscode from 'vscode';
import axios from 'axios';
import * as fs from 'fs';
import * as path from 'path';
import { exec } from 'child_process';

export function activate(context: vscode.ExtensionContext) {

    let disposable = vscode.commands.registerCommand('qa.auditProject', async () => {

        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders) {
            vscode.window.showErrorMessage("Abra um projeto.");
            return;
        }

        const basePath = workspaceFolders[0].uri.fsPath;

        const files = await vscode.workspace.findFiles('**/*.py', '**/node_modules/**');

        let missingTests: string[] = [];

        for (const file of files) {
            const filePath = file.fsPath;
            const dir = path.dirname(filePath);
            const name = path.basename(filePath);

            const testFile = path.join(dir, `test_${name}`);

            if (!fs.existsSync(testFile)) {
                missingTests.push(filePath);
            }
        }

        if (missingTests.length === 0) {
            vscode.window.showInformationMessage("Sem pendências de testes.");
            return;
        }

        for (const filePath of missingTests) {

            const code = fs.readFileSync(filePath, 'utf-8');

            try {
                const response = await axios.post('http://localhost:8000/generate-tests', {
                    file_path: filePath,
                    code: code
                });

                const testCode = response.data.tests;

                const testPath = path.join(
                    path.dirname(filePath),
                    `test_${path.basename(filePath)}`
                );

                fs.writeFileSync(testPath, testCode);

            } catch (err) {
                console.error(err);
            }
        }

        vscode.window.showInformationMessage("Testes gerados. Executando pytest...");

        exec('pytest', { cwd: basePath }, (error, stdout, stderr) => {
            if (error) {
                vscode.window.showErrorMessage("Testes falharam. Verifique.");
                console.log(stderr);
                return;
            }

            vscode.window.showInformationMessage("Testes passaram com sucesso!");
            console.log(stdout);
        });

    });

    context.subscriptions.push(disposable);
}

export function deactivate() {}
EOF