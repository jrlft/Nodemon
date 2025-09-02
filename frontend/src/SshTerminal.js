import React, { useEffect, useRef } from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import useWebSocket from 'react-use-websocket';
import '@xterm/xterm/css/xterm.css';

const SshTerminal = ({ nodeIp, onDisconnect }) => {
    const terminalRef = useRef(null);
    const xtermRef = useRef(null);
    const fitAddonRef = useRef(null);

    const getWebSocketUrl = () => {
        const host = window.location.host;
        return `wss://${host}/ws/ssh/${nodeIp}`;
    };

    const { sendMessage, lastMessage } = useWebSocket(getWebSocketUrl(), {
        onOpen: () => {
            console.log('WebSocket connection established');
        },
        onClose: () => {
            console.log('WebSocket connection closed');
            if (onDisconnect) {
                onDisconnect();
            }
        },
        onError: (event) => {
            console.error('WebSocket error:', event);
        },
    });

    useEffect(() => {
        if (xtermRef.current || !terminalRef.current) {
            return;
        }

        const term = new Terminal({
            cursorBlink: true,
            convertEol: true,
        });
        const fitAddon = new FitAddon();

        xtermRef.current = term;
        fitAddonRef.current = fitAddon;

        term.loadAddon(fitAddon);
        term.open(terminalRef.current);
        fitAddon.fit();

        term.onData((data) => {
            sendMessage(data);
        });

        return () => {
            term.dispose();
            xtermRef.current = null;
        };
    }, [sendMessage]);

    useEffect(() => {
        if (lastMessage !== null) {
            xtermRef.current?.write(lastMessage.data);
        }
    }, [lastMessage]);

    useEffect(() => {
        const handleResize = () => {
            fitAddonRef.current?.fit();
        };
        window.addEventListener('resize', handleResize);
        // Fit on initial render
        setTimeout(() => handleResize(), 100); 

        return () => {
            window.removeEventListener('resize', handleResize);
        };
    }, []);

    return <div ref={terminalRef} style={{ width: '100%', height: '100%' }} />;
};

export default SshTerminal;
