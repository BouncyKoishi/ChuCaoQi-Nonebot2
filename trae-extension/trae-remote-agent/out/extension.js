"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const http = __importStar(require("http"));
let server = null;
let outputChannel;
function activate(context) {
    outputChannel = vscode.window.createOutputChannel('Trae Remote Agent');
    outputChannel.appendLine('Trae Remote Agent is activating...');
    outputChannel.show(true);
    outputChannel.appendLine('=== Searching for Trae/AI related commands ===');
    searchRelevantCommands();
    const listCommandsCmd = vscode.commands.registerCommand('traeRemote.listCommands', () => {
        searchRelevantCommands();
        vscode.window.showInformationMessage('Commands listed in output channel');
    });
    const startServerCmd = vscode.commands.registerCommand('traeRemote.startServer', () => {
        startHttpServer(context);
    });
    const stopServerCmd = vscode.commands.registerCommand('traeRemote.stopServer', () => {
        stopHttpServer();
    });
    const testBuilderCmd = vscode.commands.registerCommand('traeRemote.testBuilder', async () => {
        await testBuilderAccess();
    });
    const deepSearchCmd = vscode.commands.registerCommand('traeRemote.deepSearch', async () => {
        await deepSearchCommands();
    });
    const testTraeCmd = vscode.commands.registerCommand('traeRemote.testTraeCommands', async () => {
        await testTraeSpecificCommands();
    });
    const testAgentCmd = vscode.commands.registerCommand('traeRemote.testAgentCommands', async () => {
        await testAgentSessionCommands();
    });
    context.subscriptions.push(listCommandsCmd, startServerCmd, stopServerCmd, testBuilderCmd, deepSearchCmd, testTraeCmd, testAgentCmd);
    outputChannel.appendLine('Trae Remote Agent activated successfully!');
}
async function searchRelevantCommands() {
    const cmds = await vscode.commands.getCommands(true);
    outputChannel.appendLine(`\nTotal commands: ${cmds.length}`);
    const keywords = [
        'trae', 'builder', 'chat', 'ai', 'agent',
        'copilot', 'assistant', 'sidebar', 'panel',
        'llm', 'model', 'generate', 'complete', 'solo'
    ];
    const categorized = {};
    keywords.forEach(k => categorized[k] = []);
    for (const cmd of cmds) {
        const lowerCmd = cmd.toLowerCase();
        for (const keyword of keywords) {
            if (lowerCmd.includes(keyword)) {
                categorized[keyword].push(cmd);
                break;
            }
        }
    }
    for (const keyword of keywords) {
        if (categorized[keyword].length > 0) {
            outputChannel.appendLine(`\n=== ${keyword.toUpperCase()} Related (${categorized[keyword].length}) ===`);
            categorized[keyword].forEach(cmd => outputChannel.appendLine(`  ${cmd}`));
        }
    }
}
async function testTraeSpecificCommands() {
    outputChannel.appendLine('\n=== Testing Trae Specific Commands ===');
    const cmds = await vscode.commands.getCommands(true);
    const traeCmds = cmds.filter(c => c.toLowerCase().includes('trae'));
    outputChannel.appendLine(`Found ${traeCmds.length} trae commands`);
    for (const cmd of traeCmds) {
        try {
            outputChannel.appendLine(`Trying: ${cmd}`);
            await vscode.commands.executeCommand(cmd);
            outputChannel.appendLine(`  ✓ Success!`);
            await new Promise(r => setTimeout(r, 300));
        }
        catch (error) {
            const errorMsg = error instanceof Error ? error.message : String(error);
            outputChannel.appendLine(`  ✗ ${errorMsg}`);
        }
    }
}
async function testAgentSessionCommands() {
    outputChannel.appendLine('\n=== Testing Agent Session Commands ===');
    const cmds = await vscode.commands.getCommands(true);
    const agentCmds = cmds.filter(c => c.toLowerCase().includes('agent') ||
        c.toLowerCase().includes('ai-chat') ||
        c.toLowerCase().includes('aichat'));
    outputChannel.appendLine(`Found ${agentCmds.length} agent/ai-chat commands`);
    for (const cmd of agentCmds) {
        try {
            outputChannel.appendLine(`Trying: ${cmd}`);
            await vscode.commands.executeCommand(cmd);
            outputChannel.appendLine(`  ✓ Success!`);
            await new Promise(r => setTimeout(r, 300));
        }
        catch (error) {
            const errorMsg = error instanceof Error ? error.message : String(error);
            outputChannel.appendLine(`  ✗ ${errorMsg}`);
        }
    }
}
async function deepSearchCommands() {
    outputChannel.appendLine('\n=== Deep Search for Trae/AI Commands ===');
    const cmds = await vscode.commands.getCommands(true);
    const patterns = [
        /^trae/i, /^ai/i, /chat/i, /builder/i, /agent/i,
        /copilot/i, /assistant/i, /sidebar/i, /panel.*chat/i,
        /workbench\.view/i, /workbench\.action\.(open|show)/i,
        /generate/i, /complete/i, /llm/i, /solo/i
    ];
    const matched = new Set();
    for (const cmd of cmds) {
        for (const pattern of patterns) {
            if (pattern.test(cmd)) {
                matched.add(cmd);
                break;
            }
        }
    }
    outputChannel.appendLine(`\nFound ${matched.size} potentially relevant commands:`);
    const sorted = Array.from(matched).sort();
    sorted.forEach(cmd => outputChannel.appendLine(`  ${cmd}`));
    outputChannel.appendLine('\n=== Testing workbench.view commands ===');
    const viewCommands = cmds.filter(c => c.startsWith('workbench.view'));
    for (const cmd of viewCommands.slice(0, 20)) {
        try {
            outputChannel.appendLine(`Trying: ${cmd}`);
            await vscode.commands.executeCommand(cmd);
            outputChannel.appendLine(`  ✓ Success!`);
            await new Promise(r => setTimeout(r, 300));
        }
        catch (error) {
            const errorMsg = error instanceof Error ? error.message : String(error);
            outputChannel.appendLine(`  ✗ ${errorMsg}`);
        }
    }
}
async function testBuilderAccess() {
    outputChannel.appendLine('\n=== Testing Builder/Chat Access ===');
    const cmds = await vscode.commands.getCommands(true);
    const testPatterns = [
        'trae', 'builder', 'chat', 'ai', 'agent',
        'copilot', 'assistant', 'sidebar', 'panel', 'solo'
    ];
    const testCommands = cmds.filter(c => {
        const lower = c.toLowerCase();
        return testPatterns.some(p => lower.includes(p));
    });
    outputChannel.appendLine(`Found ${testCommands.length} commands to test`);
    const results = [];
    for (const cmd of testCommands) {
        try {
            outputChannel.appendLine(`Trying: ${cmd}`);
            await vscode.commands.executeCommand(cmd);
            outputChannel.appendLine(`  ✓ Success!`);
            results.push({ cmd, success: true });
            await new Promise(r => setTimeout(r, 200));
        }
        catch (error) {
            const errorMsg = error instanceof Error ? error.message : String(error);
            outputChannel.appendLine(`  ✗ ${errorMsg}`);
            results.push({ cmd, success: false, error: errorMsg });
        }
    }
    outputChannel.appendLine('\n=== Summary ===');
    const successful = results.filter(r => r.success);
    const failed = results.filter(r => !r.success);
    outputChannel.appendLine(`Successful: ${successful.length}`);
    successful.forEach(r => outputChannel.appendLine(`  ✓ ${r.cmd}`));
    outputChannel.appendLine(`\nFailed: ${failed.length}`);
    vscode.window.showInformationMessage(`Test complete: ${successful.length} succeeded, ${failed.length} failed`);
}
function startHttpServer(context) {
    if (server) {
        vscode.window.showWarningMessage('Server is already running');
        return;
    }
    const config = vscode.workspace.getConfiguration('traeRemote');
    const port = config.get('port', 8765);
    server = http.createServer(async (req, res) => {
        const sendJson = (data, status = 200) => {
            res.writeHead(status, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify(data));
        };
        try {
            if (req.method === 'GET' && req.url === '/health') {
                sendJson({ status: 'ok', timestamp: new Date().toISOString() });
            }
            else if (req.method === 'GET' && req.url === '/commands') {
                const commands = await vscode.commands.getCommands(true);
                sendJson({ commands, count: commands.length });
            }
            else if (req.method === 'GET' && req.url?.startsWith('/commands/search/')) {
                const query = decodeURIComponent(req.url.replace('/commands/search/', ''));
                const cmds = await vscode.commands.getCommands(true);
                const filtered = cmds.filter(c => c.toLowerCase().includes(query.toLowerCase()));
                sendJson({ query, results: filtered, count: filtered.length });
            }
            else if (req.method === 'POST' && req.url === '/command') {
                let body = '';
                req.on('data', chunk => { body += chunk; });
                req.on('end', async () => {
                    try {
                        const data = JSON.parse(body);
                        outputChannel.appendLine(`\nReceived command: ${JSON.stringify(data)}`);
                        const result = await handleCommand(data);
                        sendJson(result);
                    }
                    catch (error) {
                        const errorMsg = error instanceof Error ? error.message : String(error);
                        sendJson({ error: errorMsg }, 500);
                    }
                });
            }
            else if (req.method === 'POST' && req.url === '/chat') {
                let body = '';
                req.on('data', chunk => { body += chunk; });
                req.on('end', async () => {
                    try {
                        const data = JSON.parse(body);
                        outputChannel.appendLine(`\nReceived chat request: ${JSON.stringify(data)}`);
                        const result = await handleChatRequest(data);
                        sendJson(result);
                    }
                    catch (error) {
                        const errorMsg = error instanceof Error ? error.message : String(error);
                        sendJson({ error: errorMsg }, 500);
                    }
                });
            }
            else if (req.method === 'POST' && req.url === '/ai-command') {
                let body = '';
                req.on('data', chunk => { body += chunk; });
                req.on('end', async () => {
                    try {
                        const data = JSON.parse(body);
                        outputChannel.appendLine(`\nReceived AI command: ${JSON.stringify(data)}`);
                        const result = await handleAICommand(data);
                        sendJson(result);
                    }
                    catch (error) {
                        const errorMsg = error instanceof Error ? error.message : String(error);
                        sendJson({ error: errorMsg }, 500);
                    }
                });
            }
            else {
                sendJson({
                    error: 'Not found',
                    endpoints: [
                        'GET /health',
                        'GET /commands',
                        'GET /commands/search/{q}',
                        'POST /command',
                        'POST /chat',
                        'POST /ai-command'
                    ]
                }, 404);
            }
        }
        catch (error) {
            const errorMsg = error instanceof Error ? error.message : String(error);
            sendJson({ error: errorMsg }, 500);
        }
    });
    server.listen(port, () => {
        outputChannel.appendLine(`HTTP Server started on port ${port}`);
        vscode.window.showInformationMessage(`Trae Remote Server started on port ${port}`);
    });
}
function stopHttpServer() {
    if (server) {
        server.close();
        server = null;
        outputChannel.appendLine('HTTP Server stopped');
        vscode.window.showInformationMessage('Trae Remote Server stopped');
    }
    else {
        vscode.window.showWarningMessage('Server is not running');
    }
}
async function handleCommand(data) {
    const { command, args = [] } = data;
    outputChannel.appendLine(`Executing command: ${command} with args: ${JSON.stringify(args)}`);
    try {
        const result = await vscode.commands.executeCommand(command, ...args);
        outputChannel.appendLine(`Command result: ${JSON.stringify(result)}`);
        return { success: true, result };
    }
    catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        outputChannel.appendLine(`Command failed: ${errorMsg}`);
        return { success: false, error: errorMsg };
    }
}
async function handleChatRequest(data) {
    const { message, context } = data;
    outputChannel.appendLine(`Chat message: ${message}`);
    const cmds = await vscode.commands.getCommands(true);
    const chatRelatedCmds = cmds.filter(c => {
        const lower = c.toLowerCase();
        return lower.includes('chat') || lower.includes('trae') || lower.includes('ai');
    });
    return {
        success: false,
        error: 'No direct chat API available',
        availableCommands: chatRelatedCmds
    };
}
async function handleAICommand(data) {
    const { action, payload } = data;
    outputChannel.appendLine(`AI Command: ${action}, Payload: ${JSON.stringify(payload)}`);
    const cmds = await vscode.commands.getCommands(true);
    const aiCmds = cmds.filter(c => {
        const lower = c.toLowerCase();
        return lower.includes('ai') || lower.includes('agent') || lower.includes('chat') || lower.includes('trae');
    });
    switch (action) {
        case 'list':
            return { success: true, commands: aiCmds };
        case 'open_chat':
            const chatCmds = [
                'workbench.panel.chat.view.ai-chat.newSession',
                'workbench.action.chat.open',
                'workbench.view.chat',
                'workbench.action.chat.openInSidebar'
            ];
            for (const cmd of chatCmds) {
                if (cmds.includes(cmd)) {
                    try {
                        await vscode.commands.executeCommand(cmd);
                        return { success: true, openedWith: cmd };
                    }
                    catch (e) {
                        outputChannel.appendLine(`Failed ${cmd}: ${e}`);
                    }
                }
            }
            return { success: false, error: 'Could not open chat panel' };
        case 'open_agent':
            const agentCmds = cmds.filter(c => c.toLowerCase().includes('agent') &&
                (c.includes('open') || c.includes('focus') || c.includes('view')));
            for (const cmd of agentCmds) {
                try {
                    await vscode.commands.executeCommand(cmd);
                    return { success: true, openedWith: cmd };
                }
                catch (e) {
                    outputChannel.appendLine(`Failed ${cmd}: ${e}`);
                }
            }
            return { success: false, error: 'Could not open agent panel' };
        default:
            return { success: false, error: 'Unknown action' };
    }
}
function deactivate() {
    stopHttpServer();
    outputChannel.appendLine('Trae Remote Agent deactivated');
}
//# sourceMappingURL=extension.js.map