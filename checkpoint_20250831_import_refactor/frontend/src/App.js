import React, { useState, useEffect, useCallback, useRef } from 'react';

const Icon = ({ path, className = "w-6 h-6" }) => ( <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className={className}><path strokeLinecap="round" strokeLinejoin="round" d={path} /></svg> );
const StatusBadge = ({ status }) => {
    const statusStr = status ? String(status).toUpperCase().replace(/ /g, '_') : 'DEFAULT';

    const statusMap = {
        'PERSIST_FINISHED': 'bg-green-500/20 text-green-400',
        'SYNC_FINISHED': 'bg-green-500/20 text-green-400',
        'MINERANDO': 'bg-green-500/20 text-green-400',
        'WAIT_FOR_SYNCING': 'bg-yellow-500/20 text-yellow-400',
        'SYNC_STARTED': 'bg-yellow-500/20 text-yellow-400',
        'SINCRONIZANDO': 'bg-yellow-500/20 text-yellow-400',
        'PRUNING_DB': 'bg-blue-500/20 text-blue-400',
        'PRUNNING_DB': 'bg-blue-500/20 text-blue-400',
        'OTIMIZANDO_DB': 'bg-blue-500/20 text-blue-400',
        'OFFLINE': 'bg-red-500/20 text-red-400',
        'ATIVO': 'bg-blue-500/20 text-blue-400',
        'ONLINE': 'bg-green-500/20 text-green-400',
        'NÃO_ENCONTRADO': 'bg-gray-500/20 text-gray-400',
        'DEFAULT': 'bg-gray-500/20 text-gray-400'
    };

    const statusTextMap = {
        'PERSIST_FINISHED': 'Minerando',
        'SYNC_FINISHED': 'Minerando',
        'WAIT_FOR_SYNCING': 'Sincronizando',
        'SYNC_STARTED': 'Sincronizando',
        'PRUNING_DB': 'Otimizando DB',
        'PRUNNING_DB': 'Otimizando DB',
        'OFFLINE': 'Offline',
    };

    const style = statusMap[statusStr] || statusMap['DEFAULT'];
    const text = statusTextMap[statusStr] || status || '...';

    return <span className={`px-2 py-1 text-xs font-medium rounded-full ${style}`}>{text}</span>;
};

const NodeModal = ({ isOpen, onClose, onNodeSaved, project, credentials, nodeToEdit }) => {
    const [node, setNode] = useState({ name: '', ip_address: '', wallet_address: '', vps_provider: '', secondary_ip: '', network: project });
    const isEditMode = nodeToEdit !== null;

    useEffect(() => {
        if (isEditMode) {
            setNode(nodeToEdit);
        } else {
            setNode({ name: '', ip_address: '', wallet_address: '', vps_provider: '', secondary_ip: '', network: project });
        }
    }, [nodeToEdit, project, isEditMode]);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setNode(prev => ({ ...prev, [name]: value }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
                const url = isEditMode ? `/api/nodes/${nodeToEdit.id}` : '/api/nodes/';
        const method = isEditMode ? 'PUT' : 'POST';

        try {
            const response = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json', 'Authorization': credentials },
                body: JSON.stringify(node)
            });
            if (!response.ok) throw new Error(`Falha ao ${isEditMode ? 'editar' : 'adicionar'} o nó.`);
            onNodeSaved();
            onClose();
        } catch (error) {
            console.error(`Erro ao ${isEditMode ? 'editar' : 'adicionar'} nó:`, error);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center z-50">
            <div className="bg-gray-800 p-8 rounded-lg shadow-xl w-full max-w-md">
                <h2 className="text-2xl font-bold mb-6 text-white">{isEditMode ? 'Editar Nó' : 'Adicionar Novo Nó'} ({project.toUpperCase()})</h2>
                <form onSubmit={handleSubmit}>
                    <div className="space-y-4">
                        <input type="text" name="name" placeholder="Nome do Nó" value={node.name} onChange={handleChange} required className="w-full bg-gray-700 text-white p-3 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                        <input type="text" name="ip_address" placeholder="Endereço IP Principal" value={node.ip_address} onChange={handleChange} required className="w-full bg-gray-700 text-white p-3 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                        <input type="text" name="wallet_address" placeholder="Endereço da Carteira" value={node.wallet_address} onChange={handleChange} required className="w-full bg-gray-700 text-white p-3 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                        <input type="text" name="vps_provider" placeholder="Provedor VPS" value={node.vps_provider} onChange={handleChange} required className="w-full bg-gray-700 text-white p-3 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                        <input type="text" name="secondary_ip" placeholder="IP Secundário (Opcional)" value={node.secondary_ip} onChange={handleChange} className="w-full bg-gray-700 text-white p-3 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                    </div>
                    <div className="flex justify-end space-x-4 mt-8">
                        <button type="button" onClick={onClose} className="py-2 px-4 bg-gray-600 hover:bg-gray-500 rounded-md text-white font-semibold">Cancelar</button>
                        <button type="submit" className="py-2 px-4 bg-indigo-600 hover:bg-indigo-500 rounded-md text-white font-semibold">{isEditMode ? 'Salvar' : 'Adicionar'}</button>
                    </div>
                </form>
            </div>
        </div>
    );
};

const Sidebar = ({ activeProject, setActiveProject, isSidebarOpen, setSidebarOpen }) => {
    const menuItems = [
        { id: 'nkn', name: 'NKN', icon: <Icon path="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" /> },
        { id: 'sentinel', name: 'Sentinel', icon: <Icon path="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" /> },
        { id: 'mysterium', name: 'Mysterium', icon: <Icon path="M15.042 21.672L13.684 16.6m0 0l-2.51 2.225.569-9.47 5.227 7.917-3.286-.672zm-7.518-.267A8.25 8.25 0 1120.25 10.5M8.288 14.212A5.25 5.25 0 1117.25 10.5" /> },
    ];
    return (
        <aside className={`fixed inset-y-0 left-0 bg-gray-900 text-gray-300 flex-col z-30 w-64 transform transition-transform duration-300 ease-in-out ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'} md:relative md:translate-x-0 md:flex md:flex-shrink-0`}>
            <div className="h-20 flex items-center justify-center border-b border-gray-800">
                <Icon path="M6.429 9.75L2.25 12l4.179 2.25m0-4.5l5.571 3 5.571-3m-11.142 0L2.25 7.5 12 2.25l9.75 5.25-3.75 2.016" className="w-8 h-8 text-indigo-500" />
                <h1 className="text-xl font-bold ml-2">NodeMon</h1>
            </div>
            <nav className="flex-1 px-4 py-6">
                <ul>
                    {menuItems.map(item => (
                        <li key={item.id}>
                                                        <button onClick={(e) => { e.preventDefault(); setActiveProject(item.id); setSidebarOpen(false); }} className={`flex items-center px-4 py-3 my-1 rounded-lg transition-colors duration-200 w-full ${activeProject === item.id ? 'bg-indigo-600 text-white' : 'hover:bg-gray-800'}`}>
                                <span className="mr-3">{item.icon}</span>
                                {item.name}
                            </button>
                        </li>
                    ))}
                </ul>
            </nav>
        </aside>
    );
};

const Dashboard = ({ project, credentials, setSidebarOpen }) => {
    const [nodes, setNodes] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [globalStat, setGlobalStat] = useState({ label: '...', value: '...' });
    const [isModalOpen, setModalOpen] = useState(false);
    const [nodeToEdit, setNodeToEdit] = useState(null);
    const [selectedNodes, setSelectedNodes] = useState([]);
    const fileInputRef = useRef(null);
    const [currentPage, setCurrentPage] = useState(1);
    const [itemsPerPage, setItemsPerPage] = useState(200);

    const fetchNodes = useCallback(async () => {
        setLoading(true);
        try {
                        const response = await fetch(`/api/nodes/?network=${project}`, { headers: { 'Authorization': credentials } });
            if (response.status === 401) throw new Error("Não autorizado. A API requer autenticação.");
            if (!response.ok) throw new Error(`API de nós retornou: ${response.status}`);
            const data = await response.json();
            setNodes(data);
        } catch (e) {
            setError(e.message);
            setNodes([]);
        } finally {
            setLoading(false);
        }
    }, [project, credentials]);

    const fetchGlobalStat = useCallback(async () => {
        try {
                        const response = await fetch(`/api/status/global/${project}`, { headers: { 'Authorization': credentials } });
            if (response.ok) {
                const data = await response.json();
                setGlobalStat(data);
            }
        } catch (e) {
            console.error("Erro ao buscar status global:", e);
        }
    }, [project, credentials]);

        const handleRefresh = useCallback(() => {
        fetchNodes();
        fetchGlobalStat();
    }, [fetchNodes, fetchGlobalStat]);

    const handleFileUpload = async (event) => {
        const file = event.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        try {
                        const response = await fetch('/api/nodes/upload-csv/', {
                method: 'POST',
                headers: { 'Authorization': credentials },
                body: formData,
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Falha ao importar o CSV.');
            }

            const result = await response.json();
            alert(result.message);
            handleRefresh();
        } catch (error) {
            console.error("Erro ao importar CSV:", error);
            alert(`Erro ao importar: ${error.message}`);
        }
    };

        useEffect(() => {
        handleRefresh();
        const interval = setInterval(handleRefresh, 60000);
        return () => clearInterval(interval);
    }, [handleRefresh]);

    const handleOpenModal = (node = null) => {
        setNodeToEdit(node);
        setModalOpen(true);
    };

    const handleCloseModal = () => {
        setModalOpen(false);
        setNodeToEdit(null);
    };

    const handleNodeSaved = () => {
        handleCloseModal();
        handleRefresh();
    };

    const handleDeleteNode = async (nodeId) => {
        if (window.confirm("Tem certeza que deseja excluir este nó?")) {
            try {
                                const response = await fetch(`/api/nodes/${nodeId}`, { method: 'DELETE', headers: { 'Authorization': credentials } });
                if (!response.ok) throw new Error("Falha ao excluir o nó.");
                handleRefresh();
            } catch (error) {
                console.error("Erro ao excluir nó:", error);
            }
        }
    };

    const handleSelectNode = (nodeId) => {
        setSelectedNodes(prev => prev.includes(nodeId) ? prev.filter(id => id !== nodeId) : [...prev, nodeId]);
    };

    const handleSelectAllNodes = (e) => {
        if (e.target.checked) {
            setSelectedNodes(currentNodes.map(node => node.id));
        } else {
            setSelectedNodes([]);
        }
    };

    const handleDeleteSelected = async () => {
        if (window.confirm(`Tem certeza que deseja excluir os ${selectedNodes.length} nós selecionados?`)) {
            try {
                                const response = await fetch('/api/nodes/delete-multiple', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'Authorization': credentials },
                    body: JSON.stringify({ node_ids: selectedNodes })
                });
                if (!response.ok) throw new Error("Falha ao excluir os nós selecionados.");
                setSelectedNodes([]);
                handleRefresh();
            } catch (error) {
                console.error("Erro ao excluir nós selecionados:", error);
            }
        }
    };

    const projectTitle = { nkn: "Nós da Rede NKN", sentinel: "Nós da Rede Sentinel", mysterium: "Nós da Rede Mysterium" };

    const indexOfLastNode = currentPage * itemsPerPage;
    const indexOfFirstNode = indexOfLastNode - itemsPerPage;
    const currentNodes = nodes.slice(indexOfFirstNode, indexOfLastNode);
    const totalPages = Math.ceil(nodes.length / itemsPerPage);

    return (
        <main className="flex-1 p-4 sm:p-8 bg-gray-800 text-gray-100 overflow-y-auto">
            <NodeModal isOpen={isModalOpen} onClose={handleCloseModal} onNodeSaved={handleNodeSaved} project={project} credentials={credentials} nodeToEdit={nodeToEdit} />
            <header className="mb-8">
                <div className="flex justify-between items-center flex-wrap gap-4">
                    <div className="flex items-center">
                        <button className="md:hidden mr-4 text-gray-400 hover:text-white" onClick={() => setSidebarOpen(true)}>
                            <Icon path="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
                        </button>
                        <h2 className="text-2xl sm:text-3xl font-bold">{projectTitle[project]}</h2>
                    </div>
                    <div className="flex items-center bg-gray-900 px-4 py-2 rounded-lg">
                        <span className="text-sm text-gray-400 mr-2">{globalStat.label}:</span>
                        <span className="text-lg font-semibold text-green-400">{globalStat.value}</span>
                    </div>
                </div>
            </header>
            <div className="flex flex-wrap gap-4 items-center justify-between mb-6">
                <div className="flex flex-wrap gap-2">
                    <input type="file" ref={fileInputRef} accept=".csv" style={{ display: 'none' }} onChange={handleFileUpload} />
                    <button onClick={() => fileInputRef.current.click()} className="flex items-center bg-gray-700 hover:bg-gray-600 text-white font-semibold py-2 px-4 rounded-lg text-sm"><Icon path="M12 16.5V9.75m0 0l-3.75 3.75M12 9.75l3.75 3.75M3.75 6.75h16.5" className="w-5 h-5 mr-2" />Importar CSV</button>
                    <button onClick={() => handleOpenModal()} className="flex items-center bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-2 px-4 rounded-lg text-sm"><Icon path="M12 4.5v15m7.5-7.5h-15" className="w-5 h-5 mr-2" />Adicionar Nó</button>
                    <button onClick={handleRefresh} className="flex items-center bg-gray-700 hover:bg-gray-600 text-white font-semibold py-2 px-4 rounded-lg text-sm"><Icon path="M16.023 9.348h4.992v-.001a.75.75 0 01.75.75c0 .414-.336.75-.75.75h-4.992v.001a.75.75 0 01-.75-.75c0-.414.336-.75.75-.75zM4.477 9.348a.75.75 0 01.75.75v8.175a.75.75 0 01-1.5 0V10.1a.75.75 0 01.75-.75zM12 6.75a.75.75 0 01.75.75v11.5a.75.75 0 01-1.5 0V7.5a.75.75 0 01.75-.75zM17.25 9.348a.75.75 0 01.75.75v5.175a.75.75 0 01-1.5 0V10.1a.75.75 0 01.75-.75z" className="w-5 h-5 mr-2" />Atualizar</button>
                    {selectedNodes.length > 0 && (
                        <button onClick={handleDeleteSelected} className="flex items-center bg-red-600 hover:bg-red-500 text-white font-bold py-2 px-4 rounded-lg text-sm"><Icon path="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" className="w-5 h-5 mr-2" />Excluir ({selectedNodes.length})</button>
                    )}
                </div>
                <div className="flex items-center space-x-2 sm:space-x-4">
                    <span className="text-sm text-gray-400 hidden sm:inline">Itens por página:</span>
                    <select 
                        value={itemsPerPage} 
                        onChange={(e) => { setItemsPerPage(Number(e.target.value)); setCurrentPage(1); }}
                        className="bg-gray-700 text-white p-2 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
                    >
                        <option value={100}>100</option>
                        <option value={200}>200</option>
                        <option value={500}>500</option>
                        <option value={1000}>1000</option>
                    </select>
                    <span className="text-sm text-gray-400">
                        {indexOfFirstNode + 1}-{Math.min(indexOfLastNode, nodes.length)} de {nodes.length}
                    </span>
                    <div className="flex space-x-1">
                        <button 
                            onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))} 
                            disabled={currentPage === 1}
                            className="p-2 bg-gray-700 hover:bg-gray-600 rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            <Icon path="M15.75 19.5L8.25 12l7.5-7.5" className="w-5 h-5" />
                        </button>
                        <button 
                            onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                            disabled={currentPage === totalPages || totalPages === 0}
                            className="p-2 bg-gray-700 hover:bg-gray-600 rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            <Icon path="M8.25 4.5l7.5 7.5-7.5 7.5" className="w-5 h-5" />
                        </button>
                    </div>
                </div>
            </div>
            <div className="bg-gray-900 rounded-lg shadow-lg overflow-hidden">
                {/* Card View for Mobile */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 md:hidden p-4">
                    {loading && <div className="text-center p-8 col-span-full">A carregar...</div>}
                    {error && <div className="text-center p-8 text-red-400 col-span-full">{error}</div>}
                    {!loading && !error && nodes.length === 0 && (<div className="text-center p-12 text-gray-500 col-span-full">Nenhum nó encontrado. Adicione um nó ou importe um ficheiro CSV.</div>)}
                    {!loading && !error && currentNodes.map(node => (
                        <div key={node.id} className="bg-gray-800 p-4 rounded-lg shadow-lg space-y-3">
                            <div className="flex justify-between items-start">
                                <h3 className="font-bold text-base text-white truncate">{node.name}</h3>
                                <StatusBadge status={node.status} />
                            </div>
                            <div className="text-sm text-gray-400 space-y-1">
                                <p><span className="font-semibold text-gray-300">IP:</span> {node.ip_address}</p>
                                <p><span className="font-semibold text-gray-300">Provedor:</span> {node.vps_provider}</p>
                                <p><span className="font-semibold text-gray-300">Bloco:</span> {node.currentBlock ? node.currentBlock.toLocaleString() : 'N/A'}</p>
                            </div>
                            <div className="text-xs text-gray-500 font-mono truncate">
                                {node.wallet_address}
                            </div>
                            <div className="flex justify-end items-center space-x-2 pt-2">
                                <input type="checkbox" checked={selectedNodes.includes(node.id)} onChange={() => handleSelectNode(node.id)} className="w-4 h-4 text-indigo-600 bg-gray-700 border-gray-600 rounded focus:ring-indigo-500" />
                                <button onClick={() => handleOpenModal(node)} className="font-medium text-indigo-400 hover:underline"><Icon path="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" className="w-5 h-5" /></button>
                                <button onClick={() => handleDeleteNode(node.id)} className="font-medium text-red-500 hover:underline"><Icon path="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" className="w-5 h-5" /></button>
                            </div>
                        </div>
                    ))}
                </div>
                {/* Table View for Desktop */}
                <div className="overflow-x-auto hidden md:block">
                    <table className="w-full text-sm text-left text-gray-400">
                        <thead className="text-xs text-gray-300 uppercase bg-gray-800/50">
                            <tr>
                                <th scope="col" className="p-4"><input type="checkbox" onChange={handleSelectAllNodes} checked={nodes.length > 0 && selectedNodes.length === currentNodes.length} className="w-4 h-4 text-indigo-600 bg-gray-700 border-gray-600 rounded focus:ring-indigo-500" /></th>
                                <th scope="col" className="px-6 py-3">Nome do Nó</th>
                                <th scope="col" className="px-6 py-3">IP / Localização</th>
                                <th scope="col" className="px-6 py-3 hidden lg:table-cell">IP Secundário</th>
                                <th scope="col" className="px-6 py-3 hidden lg:table-cell">Provedor / Carteira</th>
                                <th scope="col" className="px-6 py-3">Status</th>
                                <th scope="col" className="px-6 py-3 text-right">Bloco / Info</th>
                                <th scope="col" className="px-6 py-3 text-right hidden md:table-cell">Última Atualização</th>
                                <th scope="col" className="px-6 py-3 text-center">Ações</th>
                            </tr>
                        </thead>
                        <tbody>
                            {loading && <tr><td colSpan="9" className="text-center p-8">A carregar...</td></tr>}
                            {error && <tr><td colSpan="9" className="text-center p-8 text-red-400">{error}</td></tr>}
                            {!loading && !error && nodes.length === 0 && (<tr><td colSpan="9" className="text-center p-12 text-gray-500">Nenhum nó encontrado. Adicione um nó ou importe um ficheiro CSV.</td></tr>)}
                            {!loading && !error && currentNodes.map(node => (
                                <tr key={node.id} className="border-b border-gray-800 hover:bg-gray-800/60">
                                    <td className="w-4 p-4"><input type="checkbox" checked={selectedNodes.includes(node.id)} onChange={() => handleSelectNode(node.id)} className="w-4 h-4 text-indigo-600 bg-gray-700 border-gray-600 rounded focus:ring-indigo-500" /></td>
                                    <td className="px-6 py-4 font-medium text-white whitespace-nowrap">{node.name}</td>
                                    <td className="px-6 py-4"><div>{node.ip_address}</div><div className="text-xs text-gray-500">{node.location}</div></td>
                                    <td className="px-6 py-4 hidden lg:table-cell">{node.secondary_ip || 'N/A'}</td>
                                    <td className="px-6 py-4 hidden lg:table-cell"><div>{node.vps_provider}</div><div className="text-xs text-gray-500 font-mono truncate max-w-xs">{node.wallet_address}</div></td>
                                    <td className="px-6 py-4"><StatusBadge status={node.status} /></td>
                                    <td className="px-6 py-4 text-right font-mono">{node.currentBlock ? node.currentBlock.toLocaleString() : 'N/A'}</td>
                                    <td className="px-6 py-4 text-right hidden md:table-cell">{new Date(node.lastUpdate).toLocaleString()}</td>
                                    <td className="px-6 py-4 text-center">
                                        <div className="flex items-center justify-center space-x-2">
                                            <button onClick={() => handleOpenModal(node)} className="font-medium text-indigo-400 hover:underline"><Icon path="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" className="w-5 h-5" /></button>
                                            <button onClick={() => handleDeleteNode(node.id)} className="font-medium text-red-500 hover:underline"><Icon path="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" className="w-5 h-5" /></button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </main>
    );
};

const Login = ({ onLogin, error }) => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');

    const handleSubmit = (e) => {
        e.preventDefault();
        onLogin(username, password);
    };

    return (
        <div className="flex items-center justify-center h-screen bg-gray-900">
            <div className="w-full max-w-md p-8 space-y-8 bg-gray-800 rounded-lg shadow-lg">
                <div className="flex justify-center">
                    <Icon path="M6.429 9.75L2.25 12l4.179 2.25m0-4.5l5.571 3 5.571-3m-11.142 0L2.25 7.5 12 2.25l9.75 5.25-3.75 2.016" className="w-10 h-10 text-indigo-500" />
                    <h1 className="text-3xl font-bold ml-3 text-white">NodeMon</h1>
                </div>
                <form onSubmit={handleSubmit} className="space-y-6">
                    <input
                        type="text"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        placeholder="Usuário"
                        required
                        autoComplete="username"
                        className="w-full px-4 py-3 bg-gray-700 text-white border border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                    <input
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="Senha"
                        required
                        autoComplete="current-password"
                        className="w-full px-4 py-3 bg-gray-700 text-white border border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                    {error && <p className="text-red-500 text-sm text-center">{error}</p>}
                    <button type="submit" className="w-full py-3 px-4 font-semibold text-white bg-indigo-600 rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-gray-800 focus:ring-indigo-500">
                        Entrar
                    </button>
                </form>
            </div>
        </div>
    );
};

export default function App() {
    const [credentials, setCredentials] = useState(null);
    const [authError, setAuthError] = useState('');
    const [activeProject, setActiveProject] = useState('nkn');
    const [isSidebarOpen, setSidebarOpen] = useState(false);

    const handleLogin = async (username, password) => {
        const tempCredentials = 'Basic ' + btoa(`${username}:${password}`);
        try {
                        const response = await fetch('/api/nodes/', {
                headers: { 'Authorization': tempCredentials }
            });
            if (response.ok) {
                setCredentials(tempCredentials);
                setAuthError('');
            } else {
                setAuthError('Credenciais inválidas.');
            }
        } catch (error) {
            setAuthError('Erro ao conectar à API.');
        }
    };

    if (!credentials) {
        return <Login onLogin={handleLogin} error={authError} />;
    }

    return (
        <div className="flex h-screen bg-gray-800 font-sans">
            <Sidebar activeProject={activeProject} setActiveProject={setActiveProject} isSidebarOpen={isSidebarOpen} setSidebarOpen={setSidebarOpen} />
            <div className="flex-1 flex flex-col overflow-hidden">
                <Dashboard project={activeProject} credentials={credentials} setSidebarOpen={setSidebarOpen} />
            </div>
        </div>
    );
}
