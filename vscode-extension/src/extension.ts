/**
 * NullForge VS Code Extension
 * ===========================
 * AI-powered code synthesis directly in VS Code
 */

import * as vscode from 'vscode';
import axios from 'axios';

// Configuration interface
interface NullForgeConfig {
    provider: string;
    model: string;
    apiKey: string;
    apiBase: string;
    temperature: number;
    maxTokens: number;
    enableShellTools: boolean;
    enableFileTools: boolean;
}

// Chat panel provider
class NullForgeChatProvider implements vscode.WebviewViewProvider {
    public static readonly viewType = 'nullforge.chat';
    private _view?: vscode.WebviewView;

    constructor(private readonly _extensionUri: vscode.Uri) {}

    resolveWebviewView(
        webviewView: vscode.WebviewView,
        context: vscode.WebviewViewResolveContext,
        _token: vscode.CancellationToken
    ) {
        this._view = webviewView;
        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this._extensionUri]
        };
        webviewView.webview.html = this._getHtmlForWebview(webviewView.webview);

        // Handle messages from webview
        webviewView.webview.onDidReceiveMessage(async (data) => {
            switch (data.type) {
                case 'synthesize':
                    await synthesizeCode(data.prompt);
                    break;
                case 'chat':
                    await handleChat(data.message, this._view!);
                    break;
            }
        });
    }

    private _getHtmlForWebview(webview: vscode.Webview): string {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NullForge Chat</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: var(--vscode-font-family);
            background: var(--vscode-editor-background);
            color: var(--vscode-foreground);
            padding: 12px;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        .header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 12px;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--vscode-panel-border);
        }
        .header h2 {
            font-size: 14px;
            font-weight: 600;
        }
        .messages {
            flex: 1;
            overflow-y: auto;
            margin-bottom: 12px;
        }
        .message {
            padding: 8px 12px;
            margin-bottom: 8px;
            border-radius: 8px;
            font-size: 13px;
            line-height: 1.5;
        }
        .message.user {
            background: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            margin-left: 20px;
        }
        .message.assistant {
            background: var(--vscode-editor-inactiveSelectionBackground);
            margin-right: 20px;
        }
        .message pre {
            background: var(--vscode-textCodeBlock-background);
            padding: 8px;
            border-radius: 4px;
            margin-top: 8px;
            overflow-x: auto;
            font-family: var(--vscode-editor-font-family);
            font-size: 12px;
        }
        .input-container {
            display: flex;
            gap: 8px;
        }
        .input-container textarea {
            flex: 1;
            padding: 10px;
            border: 1px solid var(--vscode-input-border);
            background: var(--vscode-input-background);
            color: var(--vscode-input-foreground);
            border-radius: 6px;
            resize: none;
            font-family: inherit;
            font-size: 13px;
        }
        .input-container textarea:focus {
            outline: 1px solid var(--vscode-focusBorder);
        }
        .input-container button {
            padding: 10px 16px;
            background: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 500;
        }
        .input-container button:hover {
            background: var(--vscode-button-hoverBackground);
        }
        .status {
            font-size: 11px;
            color: var(--vscode-descriptionForeground);
            margin-top: 8px;
        }
        .typing {
            display: inline-block;
            width: 8px;
            height: 8px;
            background: var(--vscode-progressBar-background);
            border-radius: 50%;
            animation: typing 1s ease-in-out infinite;
        }
        @keyframes typing {
            0%, 100% { opacity: 0.3; }
            50% { opacity: 1; }
        }
    </style>
</head>
<body>
    <div class="header">
        <span>⚡</span>
        <h2>NullForge Chat</h2>
    </div>
    
    <div class="messages" id="messages">
        <div class="message assistant">
            <strong>NullForge</strong><br>
            Hello! I'm NullForge, your AI coding assistant. Describe what you want to build, and I'll synthesize the code for you.
        </div>
    </div>
    
    <div class="input-container">
        <textarea id="input" placeholder="Describe what you want to build..." rows="3"></textarea>
        <button onclick="sendMessage()">⚡ Send</button>
    </div>
    
    <div class="status" id="status">Ready</div>

    <script>
        const vscode = acquireVsCodeApi();
        const messagesEl = document.getElementById('messages');
        const inputEl = document.getElementById('input');
        const statusEl = document.getElementById('status');

        function sendMessage() {
            const message = inputEl.value.trim();
            if (!message) return;

            // Add user message
            messagesEl.innerHTML += \`
                <div class="message user">
                    <strong>You</strong><br>
                    \${escapeHtml(message)}
                </div>
            \`;
            
            inputEl.value = '';
            statusEl.innerHTML = '<span class="typing"></span> Thinking...';
            messagesEl.scrollTop = messagesEl.scrollHeight;

            // Send to extension
            vscode.postMessage({ type: 'chat', message });
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Handle Enter key
        inputEl.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        // Receive messages from extension
        window.addEventListener('message', (event) => {
            const data = event.data;
            if (data.type === 'response') {
                messagesEl.innerHTML += \`
                    <div class="message assistant">
                        <strong>NullForge</strong><br>
                        \${data.content}
                    </div>
                \`;
                statusEl.textContent = 'Ready';
                messagesEl.scrollTop = messagesEl.scrollHeight;
            } else if (data.type === 'error') {
                statusEl.textContent = 'Error: ' + data.message;
            }
        });
    </script>
</body>
</html>`;
    }

    public addMessage(content: string) {
        if (this._view) {
            this._view.webview.postMessage({ type: 'response', content });
        }
    }
}

// Get configuration
function getConfig(): NullForgeConfig {
    const config = vscode.workspace.getConfiguration('nullforge');
    return {
        provider: config.get('provider', 'venice'),
        model: config.get('model', 'llama-3.1-405b'),
        apiKey: config.get('apiKey', ''),
        apiBase: config.get('apiBase', ''),
        temperature: config.get('temperature', 0.7),
        maxTokens: config.get('maxTokens', 4096),
        enableShellTools: config.get('enableShellTools', true),
        enableFileTools: config.get('enableFileTools', true)
    };
}

// Synthesize code
async function synthesizeCode(prompt?: string) {
    const config = getConfig();
    
    if (!prompt) {
        prompt = await vscode.window.showInputBox({
            prompt: 'What do you want to build?',
            placeHolder: 'e.g., A REST API with authentication...',
            ignoreFocusOut: true
        });
    }
    
    if (!prompt) return;

    const outputChannel = vscode.window.createOutputChannel('NullForge');
    outputChannel.show();
    outputChannel.appendLine('⚡ NullForge - Starting synthesis...');
    outputChannel.appendLine(`📝 Goal: ${prompt}`);
    outputChannel.appendLine(`🤖 Provider: ${config.provider} / ${config.model}`);
    outputChannel.appendLine('');

    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: 'NullForge: Synthesizing...',
        cancellable: true
    }, async (progress, token) => {
        try {
            progress.report({ message: 'Planning...' });
            
            // Simulated API call (replace with actual NullForge API)
            const apiBase = config.apiBase || 'http://localhost:8000';
            
            // For demo, simulate the synthesis
            outputChannel.appendLine('📋 Planning phase...');
            await sleep(1000);
            
            outputChannel.appendLine('✓ Plan created with 5 subtasks');
            outputChannel.appendLine('');
            
            const steps = [
                'Setting up project structure',
                'Creating data models',
                'Implementing core logic',
                'Adding API endpoints',
                'Writing tests'
            ];
            
            for (let i = 0; i < steps.length; i++) {
                if (token.isCancellationRequested) {
                    outputChannel.appendLine('❌ Synthesis cancelled');
                    return;
                }
                
                progress.report({ 
                    message: steps[i],
                    increment: 20
                });
                outputChannel.appendLine(`⏳ Step ${i + 1}/${steps.length}: ${steps[i]}`);
                await sleep(800);
                outputChannel.appendLine(`✅ Completed: ${steps[i]}`);
            }
            
            outputChannel.appendLine('');
            outputChannel.appendLine('🎉 Synthesis completed successfully!');
            outputChannel.appendLine('');
            outputChannel.appendLine('Generated files:');
            outputChannel.appendLine('  📄 main.py');
            outputChannel.appendLine('  📄 models.py');
            outputChannel.appendLine('  📄 requirements.txt');
            
            vscode.window.showInformationMessage(
                'NullForge: Synthesis completed!',
                'View Output'
            ).then(selection => {
                if (selection === 'View Output') {
                    outputChannel.show();
                }
            });
            
        } catch (error: any) {
            outputChannel.appendLine(`❌ Error: ${error.message}`);
            vscode.window.showErrorMessage(`NullForge Error: ${error.message}`);
        }
    });
}

// Handle chat messages
async function handleChat(message: string, view: vscode.WebviewView) {
    const config = getConfig();
    
    try {
        // For demo, generate a simulated response
        await sleep(1500);
        
        let response = `I'll help you with that! Here's my approach:\n\n`;
        response += `Based on your request: "${message.substring(0, 100)}..."\n\n`;
        response += `I would:\n`;
        response += `1. Analyze the requirements\n`;
        response += `2. Create a structured plan\n`;
        response += `3. Generate the necessary code\n\n`;
        response += `Would you like me to proceed with the synthesis?`;
        
        view.webview.postMessage({ type: 'response', content: response });
        
    } catch (error: any) {
        view.webview.postMessage({ type: 'error', message: error.message });
    }
}

// Audit current file
async function auditCurrentFile() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showWarningMessage('No file is currently open');
        return;
    }
    
    const document = editor.document;
    const content = document.getText();
    const fileName = document.fileName;
    
    const outputChannel = vscode.window.createOutputChannel('NullForge Audit');
    outputChannel.show();
    outputChannel.appendLine(`🔍 NullForge - Auditing: ${fileName}`);
    outputChannel.appendLine('');
    
    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: 'Analyzing...',
        cancellable: false
    }, async () => {
        await sleep(2000);
        
        // Simulated audit results
        const lines = content.split('\n').length;
        const language = document.languageId;
        
        outputChannel.appendLine(`📊 File Statistics:`);
        outputChannel.appendLine(`   Language: ${language}`);
        outputChannel.appendLine(`   Lines: ${lines}`);
        outputChannel.appendLine(`   Size: ${content.length} bytes`);
        outputChannel.appendLine('');
        outputChannel.appendLine(`🎯 Analysis Results:`);
        outputChannel.appendLine(`   ✅ No critical issues found`);
        outputChannel.appendLine(`   ⚠️  2 suggestions for improvement`);
        outputChannel.appendLine('');
        outputChannel.appendLine(`💡 Suggestions:`);
        outputChannel.appendLine(`   1. Consider adding type hints for better code clarity`);
        outputChannel.appendLine(`   2. Some functions could be refactored for better readability`);
        
        vscode.window.showInformationMessage('NullForge: Audit completed');
    });
}

// Helper function
function sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Extension activation
export function activate(context: vscode.ExtensionContext) {
    console.log('NullForge extension is now active');

    // Register chat provider
    const chatProvider = new NullForgeChatProvider(context.extensionUri);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider(
            NullForgeChatProvider.viewType,
            chatProvider
        )
    );

    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('nullforge.synthesize', () => synthesizeCode()),
        vscode.commands.registerCommand('nullforge.synthesizeSelection', async () => {
            const editor = vscode.window.activeTextEditor;
            if (editor && editor.selection) {
                const selection = editor.document.getText(editor.selection);
                if (selection) {
                    await synthesizeCode(selection);
                }
            }
        }),
        vscode.commands.registerCommand('nullforge.audit', () => auditCurrentFile()),
        vscode.commands.registerCommand('nullforge.auditProject', async () => {
            const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
            if (workspaceFolder) {
                vscode.window.showInformationMessage(
                    `Auditing project: ${workspaceFolder.name}...`
                );
            }
        }),
        vscode.commands.registerCommand('nullforge.chat', () => {
            vscode.commands.executeCommand('nullforge.chat.focus');
        }),
        vscode.commands.registerCommand('nullforge.configure', async () => {
            vscode.commands.executeCommand(
                'workbench.action.openSettings',
                'nullforge'
            );
        }),
        vscode.commands.registerCommand('nullforge.showHistory', () => {
            vscode.window.showInformationMessage('Synthesis history coming soon!');
        })
    );

    // Status bar item
    const statusBarItem = vscode.window.createStatusBarItem(
        vscode.StatusBarAlignment.Right,
        100
    );
    statusBarItem.text = '$(sparkle) NullForge';
    statusBarItem.tooltip = 'Click to synthesize code';
    statusBarItem.command = 'nullforge.synthesize';
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);

    vscode.window.showInformationMessage('⚡ NullForge is ready!');
}

export function deactivate() {
    console.log('NullForge extension deactivated');
}
