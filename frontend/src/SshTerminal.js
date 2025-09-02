import React, { useEffect, useRef, useState } from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import useWebSocket from 'react-use-websocket';
import '@xterm/xterm/css/xterm.css';

const SshTerminal = ({ nodeIp, onDisconnect, credentials }) => {
    const terminalRef = useRef(null);
    const xtermRef = useRef(null);
    const fitAddonRef = useRef(null);
    const [connectionError, setConnectionError] = useState(null);
    const [isConnecting, setIsConnecting] = useState(true);
    const [authStatus, setAuthStatus] = useState('connecting');

    const getWebSocketUrl = () => {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        // Remove query parameter authentication for now
        return `${protocol}//${host}/ws/ssh/${nodeIp}`;
    };

    const { sendMessage, lastMessage, readyState } = useWebSocket(
        getWebSocketUrl(),
        {
            onOpen: () => {
                console.log('WebSocket connection established, sending auth...');
                setAuthStatus('authenticating');
                // Send authentication immediately after connection
                if (credentials) {
                    const authMessage = JSON.stringify({
                        type: 'auth',
                        credentials: credentials
                    });
                    console.log('Sending auth message:', authMessage);
                    sendMessage(authMessage);
                } else {
                    console.error('No credentials available for WebSocket auth');
                    setConnectionError('Credenciais não disponíveis para autenticação');
                    setAuthStatus('error');
                }
            },
            onClose: (event) => {
                console.log('WebSocket connection closed', event);
                setIsConnecting(false);
                if (event.code === 1008) {
                    setConnectionError('Erro de autenticação: Verifique suas credenciais.');
                } else if (event.code !== 1000) {
                    setConnectionError('Conexão SSH perdida. Verifique a conectividade com o servidor.');
                }
                if (onDisconnect) {
                    onDisconnect();
                }
            },
            onError: (event) => {
                console.error('WebSocket error:', event);
                setIsConnecting(false);
                setConnectionError('Erro de conexão WebSocket. Verifique a configuração do servidor.');
            },
            shouldReconnect: () => false, // Don't auto-reconnect on errors
        }
    );

    useEffect(() => {
        if (xtermRef.current || !terminalRef.current || connectionError) {
            return;
        }

        const term = new Terminal({
            cursorBlink: true,
            convertEol: true,
            fontSize: 14,
            fontFamily: 'Consolas, "Liberation Mono", Menlo, Courier, monospace',
        });
        const fitAddon = new FitAddon();

        xtermRef.current = term;
        fitAddonRef.current = fitAddon;

        term.loadAddon(fitAddon);
        term.open(terminalRef.current);
        fitAddon.fit();

        // Show connection status
        if (isConnecting) {
            term.write('\r\nConectando ao servidor SSH...\r\n');
        }

        term.onData((data) => {
            if (sendMessage && readyState === 1) { // Only send if WebSocket is open
                sendMessage(data);
            }
        });

        return () => {
            if (xtermRef.current) {
                xtermRef.current.dispose();
                xtermRef.current = null;
            }
        };
    }, [sendMessage, connectionError, isConnecting, readyState]);

    useEffect(() => {
        if (lastMessage !== null && xtermRef.current) {
            const data = lastMessage.data;
            
            // Check if this is an authentication success message
            if (data.includes('Autenticação bem-sucedida') || data.includes('Iniciando conexão SSH')) {
                console.log('Authentication successful, SSH connecting...');
                setAuthStatus('ssh-connecting');
                setIsConnecting(false);
                setConnectionError(null);
            }
            
            // Check if SSH connection is established (look for shell prompt or login messages)
            if (data.includes('$') || data.includes('#') || data.includes('Welcome') || data.includes('login:')) {
                console.log('SSH connection established successfully!');
                setAuthStatus('connected');
                setIsConnecting(false);
                setConnectionError(null);
            }
            
            // Check for error messages
            if (data.includes('ERRO:')) {
                console.error('SSH error received:', data);
                setConnectionError('Erro de conexão SSH: Verifique as credenciais e conectividade.');
                setIsConnecting(false);
                setAuthStatus('error');
            }
            
            xtermRef.current.write(data);
        }
    }, [lastMessage]);

    useEffect(() => {
        const handleResize = () => {
            if (fitAddonRef.current) {
                fitAddonRef.current.fit();
            }
        };
        window.addEventListener('resize', handleResize);
        // Fit on initial render
        const timeoutId = setTimeout(() => handleResize(), 100);

        return () => {
            window.removeEventListener('resize', handleResize);
            clearTimeout(timeoutId);
        };
    }, []);

    // Show error state
    if (connectionError) {
        return (
            <div className="flex flex-col items-center justify-center h-full text-white">
                <div className="bg-red-500/20 text-red-400 p-4 rounded-lg mb-4 max-w-md text-center">
                    <h3 className="font-semibold mb-2">Erro de Conexão SSH</h3>
                    <p className="text-sm">{connectionError}</p>
                </div>
                <button 
                    onClick={onDisconnect}
                    className="bg-gray-600 hover:bg-gray-500 text-white px-4 py-2 rounded-md"
                >
                    Voltar
                </button>
            </div>
        );
    }

    // Show loading state
    if (isConnecting) {
        const statusMessages = {
            'connecting': 'Conectando ao WebSocket...',
            'authenticating': 'Autenticando usuário...',
            'ssh-connecting': 'Conectando ao servidor SSH...',
            'error': 'Erro de conexão'
        };
        
        return (
            <div className="flex flex-col items-center justify-center h-full text-white">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white mb-4"></div>
                <p>{statusMessages[authStatus] || 'Conectando ao servidor SSH...'}</p>
                <p className="text-sm text-gray-400 mt-2">Node: {nodeIp}</p>
            </div>
        );
    }

    return <div ref={terminalRef} style={{ width: '100%', height: '100%' }} />;
};

export default SshTerminal;
