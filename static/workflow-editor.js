/**
 * 🎨 D'MAR Workflow Editor
 * Editor visual de flujos tipo n8n con canvas 2D.
 * Fondo blanco, partículas sutiles, nodos arrastrables, conexiones bezier.
 */

class WorkflowEditor {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.canvas = document.createElement('canvas');
        this.ctx = this.canvas.getContext('2d');
        this.container.appendChild(this.canvas);
        
        // Estado
        this.nodes = [];
        this.connections = [];
        this.selectedNode = null;
        this.dragging = null;
        this.connecting = null;
        this.hoverNode = null;
        this.hoverPort = null;
        
        // Cámara
        this.camera = { x: 0, y: 0, zoom: 1 };
        this.isPanning = false;
        this.panStart = { x: 0, y: 0 };
        this.cameraStart = { x: 0, y: 0 };
        
        // Partículas
        this.particles = this._initParticles(60);
        
        // Tipos de nodos
        this.nodeTypes = {
            start: { label: 'Inicio', color: '#495057', icon: '🏁', textColor: '#fff' },
            message: { label: 'Mensaje', color: '#00bcd4', icon: '💬', textColor: '#fff' },
            input: { label: 'Pregunta', color: '#28a745', icon: '❓', textColor: '#fff' },
            options: { label: 'Menú', color: '#ffc107', icon: '☰', textColor: '#333' },
            condition: { label: 'Condición', color: '#9c27b0', icon: '⚡', textColor: '#fff' },
            action: { label: 'Acción', color: '#f44336', icon: '⚙️', textColor: '#fff' }
        };
        
        // Config visual
        this.nodeWidth = 200;
        this.nodeHeaderHeight = 32;
        this.portRadius = 6;
        this.gridSize = 20;
        
        this._bindEvents();
        this._resize();
        this._animate();
    }
    
    // ========== INICIALIZACIÓN ==========
    
    _initParticles(count) {
        const particles = [];
        for (let i = 0; i < count; i++) {
            particles.push({
                x: Math.random() * 2000,
                y: Math.random() * 2000,
                vx: (Math.random() - 0.5) * 0.15,
                vy: (Math.random() - 0.5) * 0.15,
                radius: Math.random() * 2 + 0.5,
                alpha: Math.random() * 0.04 + 0.01
            });
        }
        return particles;
    }
    
    _bindEvents() {
        window.addEventListener('resize', () => this._resize());
        this.canvas.addEventListener('mousedown', e => this._onMouseDown(e));
        this.canvas.addEventListener('mousemove', e => this._onMouseMove(e));
        this.canvas.addEventListener('mouseup', e => this._onMouseUp(e));
        this.canvas.addEventListener('wheel', e => this._onWheel(e), { passive: false });
        this.canvas.addEventListener('dblclick', e => this._onDoubleClick(e));
    }
    
    _resize() {
        const rect = this.container.getBoundingClientRect();
        this.canvas.width = rect.width;
        this.canvas.height = rect.height;
        this.render();
    }
    
    // ========== COORDENADAS ==========
    
    _screenToWorld(sx, sy) {
        return {
            x: (sx - this.canvas.width / 2) / this.camera.zoom - this.camera.x,
            y: (sy - this.canvas.height / 2) / this.camera.zoom - this.camera.y
        };
    }
    
    _worldToScreen(wx, wy) {
        return {
            x: (wx + this.camera.x) * this.camera.zoom + this.canvas.width / 2,
            y: (wy + this.camera.y) * this.camera.zoom + this.canvas.height / 2
        };
    }
    
    // ========== RENDER ==========
    
    _animate() {
        this._updateParticles();
        this.render();
        requestAnimationFrame(() => this._animate());
    }
    
    _updateParticles() {
        for (const p of this.particles) {
            p.x += p.vx;
            p.y += p.vy;
            if (p.x < -500) p.x = 2500;
            if (p.x > 2500) p.x = -500;
            if (p.y < -500) p.y = 2500;
            if (p.y > 2500) p.y = -500;
        }
    }
    
    render() {
        const ctx = this.ctx;
        const w = this.canvas.width;
        const h = this.canvas.height;
        
        // Fondo blanco
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, w, h);
        
        ctx.save();
        
        // Aplicar cámara
        ctx.translate(w / 2, h / 2);
        ctx.scale(this.camera.zoom, this.camera.zoom);
        ctx.translate(this.camera.x, this.camera.y);
        
        // Grid
        this._renderGrid(ctx);
        
        // Partículas
        this._renderParticles(ctx);
        
        // Conexiones
        this._renderConnections(ctx);
        
        // Línea temporal de conexión
        if (this.connecting) {
            this._renderConnectingLine(ctx);
        }
        
        // Nodos
        this._renderNodes(ctx);
        
        ctx.restore();
    }
    
    _renderGrid(ctx) {
        const size = this.gridSize;
        const left = -this.camera.x - this.canvas.width / (2 * this.camera.zoom);
        const right = -this.camera.x + this.canvas.width / (2 * this.camera.zoom);
        const top = -this.camera.y - this.canvas.height / (2 * this.camera.zoom);
        const bottom = -this.camera.y + this.canvas.height / (2 * this.camera.zoom);
        
        const startX = Math.floor(left / size) * size;
        const startY = Math.floor(top / size) * size;
        const endX = Math.ceil(right / size) * size;
        const endY = Math.ceil(bottom / size) * size;
        
        ctx.fillStyle = '#e9ecef';
        for (let x = startX; x <= endX; x += size) {
            for (let y = startY; y <= endY; y += size) {
                ctx.beginPath();
                ctx.arc(x, y, 1, 0, Math.PI * 2);
                ctx.fill();
            }
        }
    }
    
    _renderParticles(ctx) {
        for (const p of this.particles) {
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(0, 188, 212, ${p.alpha})`;
            ctx.fill();
        }
    }
    
    _renderConnections(ctx) {
        for (const conn of this.connections) {
            const fromNode = this.nodes.find(n => n.id === conn.from);
            const toNode = this.nodes.find(n => n.id === conn.to);
            if (!fromNode || !toNode) continue;
            
            const fromPos = this._getOutputPortPos(fromNode, conn.fromPort);
            const toPos = this._getInputPortPos(toNode);
            
            this._drawBezier(ctx, fromPos, toPos, '#adb5bd', 2);
        }
    }
    
    _renderConnectingLine(ctx) {
        const fromNode = this.nodes.find(n => n.id === this.connecting.nodeId);
        if (!fromNode) return;
        
        const fromPos = this._getOutputPortPos(fromNode, this.connecting.portId);
        const mouseWorld = this._screenToWorld(this.connecting.mouseX, this.connecting.mouseY);
        
        ctx.setLineDash([5, 5]);
        this._drawBezier(ctx, fromPos, mouseWorld, '#00bcd4', 2);
        ctx.setLineDash([]);
    }
    
    _drawBezier(ctx, from, to, color, width) {
        const midX = (from.x + to.x) / 2;
        ctx.beginPath();
        ctx.moveTo(from.x, from.y);
        ctx.bezierCurveTo(midX, from.y, midX, to.y, to.x, to.y);
        ctx.strokeStyle = color;
        ctx.lineWidth = width;
        ctx.stroke();
        
        // Flecha
        const angle = Math.atan2(to.y - from.y, to.x - from.x);
        const arrowLen = 10;
        ctx.beginPath();
        ctx.moveTo(to.x, to.y);
        ctx.lineTo(to.x - arrowLen * Math.cos(angle - 0.5), to.y - arrowLen * Math.sin(angle - 0.5));
        ctx.lineTo(to.x - arrowLen * Math.cos(angle + 0.5), to.y - arrowLen * Math.sin(angle + 0.5));
        ctx.closePath();
        ctx.fillStyle = color;
        ctx.fill();
    }
    
    _renderNodes(ctx) {
        for (const node of this.nodes) {
            const info = this.nodeTypes[node.type];
            const isSelected = this.selectedNode?.id === node.id;
            const isHovered = this.hoverNode?.id === node.id;
            
            // Sombra
            if (isSelected || isHovered) {
                ctx.shadowColor = info.color + '40';
                ctx.shadowBlur = 15;
                ctx.shadowOffsetY = 4;
            }
            
            // Fondo del nodo
            ctx.fillStyle = '#ffffff';
            ctx.strokeStyle = isSelected ? info.color : '#dee2e6';
            ctx.lineWidth = isSelected ? 2.5 : 1.5;
            this._roundRect(ctx, node.x, node.y, node.width, node.height, 12);
            ctx.fill();
            ctx.stroke();
            
            ctx.shadowColor = 'transparent';
            ctx.shadowBlur = 0;
            ctx.shadowOffsetY = 0;
            
            // Header
            ctx.fillStyle = info.color;
            this._roundRectTop(ctx, node.x, node.y, node.width, this.nodeHeaderHeight, 12);
            ctx.fill();
            
            ctx.fillStyle = info.textColor;
            ctx.font = 'bold 12px Segoe UI, sans-serif';
            ctx.textBaseline = 'middle';
            ctx.fillText(`${info.icon} ${node.label}`, node.x + 10, node.y + this.nodeHeaderHeight / 2);
            
            // Body - contenido
            ctx.fillStyle = '#495057';
            ctx.font = '11px Segoe UI, sans-serif';
            const content = node.content || '';
            const lines = content.split('\n').slice(0, 3);
            let textY = node.y + this.nodeHeaderHeight + 14;
            for (const line of lines) {
                const truncated = line.length > 28 ? line.substring(0, 28) + '...' : line;
                ctx.fillText(truncated, node.x + 12, textY);
                textY += 15;
            }
            
            // Puertos de salida
            const outputs = node.outputs || [{ id: 'out1', label: 'Siguiente' }];
            let portY = node.y + node.height - 10 - (outputs.length * 18);
            for (const output of outputs) {
                const isPortHovered = this.hoverPort?.nodeId === node.id && this.hoverPort?.portId === output.id;
                
                // Punto
                ctx.beginPath();
                ctx.arc(node.x + node.width, portY, isPortHovered ? 8 : this.portRadius, 0, Math.PI * 2);
                ctx.fillStyle = isPortHovered ? info.color : '#adb5bd';
                ctx.fill();
                
                // Label
                ctx.fillStyle = '#868e96';
                ctx.font = '10px Segoe UI, sans-serif';
                ctx.textAlign = 'right';
                ctx.fillText(output.label, node.x + node.width - 14, portY + 3);
                ctx.textAlign = 'left';
                
                portY += 18;
            }
            
            // Puerto de entrada
            ctx.beginPath();
            ctx.arc(node.x, node.y + this.nodeHeaderHeight / 2, this.portRadius, 0, Math.PI * 2);
            ctx.fillStyle = isHovered ? info.color : '#adb5bd';
            ctx.fill();
        }
    }
    
    _roundRect(ctx, x, y, w, h, r) {
        ctx.beginPath();
        ctx.moveTo(x + r, y);
        ctx.lineTo(x + w - r, y);
        ctx.quadraticCurveTo(x + w, y, x + w, y + r);
        ctx.lineTo(x + w, y + h - r);
        ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
        ctx.lineTo(x + r, y + h);
        ctx.quadraticCurveTo(x, y + h, x, y + h - r);
        ctx.lineTo(x, y + r);
        ctx.quadraticCurveTo(x, y, x + r, y);
        ctx.closePath();
    }
    
    _roundRectTop(ctx, x, y, w, h, r) {
        ctx.beginPath();
        ctx.moveTo(x + r, y);
        ctx.lineTo(x + w - r, y);
        ctx.quadraticCurveTo(x + w, y, x + w, y + r);
        ctx.lineTo(x + w, y + h);
        ctx.lineTo(x, y + h);
        ctx.lineTo(x, y + r);
        ctx.quadraticCurveTo(x, y, x + r, y);
        ctx.closePath();
    }
    
    _getOutputPortPos(node, portId) {
        const outputs = node.outputs || [{ id: 'out1' }];
        const idx = outputs.findIndex(o => o.id === portId);
        const portIdx = idx >= 0 ? idx : 0;
        const outputsCount = outputs.length;
        const startY = node.y + node.height - 10 - (outputsCount * 18) + (portIdx * 18);
        return { x: node.x + node.width, y: startY };
    }
    
    _getInputPortPos(node) {
        return { x: node.x, y: node.y + this.nodeHeaderHeight / 2 };
    }
    
    // ========== EVENTOS ==========
    
    _onMouseDown(e) {
        const rect = this.canvas.getBoundingClientRect();
        const sx = e.clientX - rect.left;
        const sy = e.clientY - rect.top;
        const world = this._screenToWorld(sx, sy);
        
        // Verificar si hizo clic en un puerto de salida
        const port = this._getPortAt(world.x, world.y);
        if (port) {
            this.connecting = {
                nodeId: port.nodeId,
                portId: port.portId,
                mouseX: sx,
                mouseY: sy
            };
            return;
        }
        
        // Verificar si hizo clic en un nodo
        const node = this._getNodeAt(world.x, world.y);
        if (node) {
            this.dragging = {
                node: node,
                offsetX: world.x - node.x,
                offsetY: world.y - node.y
            };
            this.selectNode(node.id);
            return;
        }
        
        // Panning del canvas
        this.isPanning = true;
        this.panStart = { x: sx, y: sy };
        this.cameraStart = { ...this.camera };
        this.selectedNode = null;
        this._onSelectNode(null);
    }
    
    _onMouseMove(e) {
        const rect = this.canvas.getBoundingClientRect();
        const sx = e.clientX - rect.left;
        const sy = e.clientY - rect.top;
        const world = this._screenToWorld(sx, sy);
        
        // Actualizar línea temporal de conexión
        if (this.connecting) {
            this.connecting.mouseX = sx;
            this.connecting.mouseY = sy;
        }
        
        // Drag de nodo
        if (this.dragging) {
            this.dragging.node.x = world.x - this.dragging.offsetX;
            this.dragging.node.y = world.y - this.dragging.offsetY;
        }
        
        // Panning
        if (this.isPanning) {
            this.camera.x = this.cameraStart.x + (sx - this.panStart.x) / this.camera.zoom;
            this.camera.y = this.cameraStart.y + (sy - this.panStart.y) / this.camera.zoom;
        }
        
        // Hover
        this.hoverNode = this._getNodeAt(world.x, world.y);
        this.hoverPort = this._getPortAt(world.x, world.y);
    }
    
    _onMouseUp(e) {
        const rect = this.canvas.getBoundingClientRect();
        const sx = e.clientX - rect.left;
        const sy = e.clientY - rect.top;
        const world = this._screenToWorld(sx, sy);
        
        // Finalizar conexión
        if (this.connecting) {
            const targetNode = this._getNodeAt(world.x, world.y);
            if (targetNode && targetNode.id !== this.connecting.nodeId) {
                // Eliminar conexión existente desde este puerto
                this.connections = this.connections.filter(
                    c => !(c.from === this.connecting.nodeId && c.fromPort === this.connecting.portId)
                );
                // Crear nueva conexión
                this.connections.push({
                    from: this.connecting.nodeId,
                    fromPort: this.connecting.portId,
                    to: targetNode.id
                });
            }
            this.connecting = null;
        }
        
        this.dragging = null;
        this.isPanning = false;
    }
    
    _onWheel(e) {
        e.preventDefault();
        const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
        const newZoom = Math.max(0.3, Math.min(3, this.camera.zoom * zoomFactor));
        this.camera.zoom = newZoom;
    }
    
    _onDoubleClick(e) {
        const rect = this.canvas.getBoundingClientRect();
        const world = this._screenToWorld(e.clientX - rect.left, e.clientY - rect.top);
        const node = this._getNodeAt(world.x, world.y);
        if (node && confirm(`¿Eliminar nodo "${node.label}"?`)) {
            this.deleteNode(node.id);
        }
    }
    
    _getNodeAt(x, y) {
        for (let i = this.nodes.length - 1; i >= 0; i--) {
            const n = this.nodes[i];
            if (x >= n.x && x <= n.x + n.width && y >= n.y && y <= n.y + n.height) {
                return n;
            }
        }
        return null;
    }
    
    _getPortAt(x, y) {
        for (const node of this.nodes) {
            const outputs = node.outputs || [{ id: 'out1' }];
            let portY = node.y + node.height - 10 - (outputs.length * 18);
            for (const output of outputs) {
                const dx = x - (node.x + node.width);
                const dy = y - portY;
                if (dx * dx + dy * dy <= 100) {
                    return { nodeId: node.id, portId: output.id };
                }
                portY += 18;
            }
        }
        return null;
    }
    
    // ========== API PÚBLICA ==========
    
    addNode(type) {
        const info = this.nodeTypes[type];
        const id = 'node_' + Date.now() + '_' + Math.floor(Math.random() * 1000);
        
        // Posición centrada en la vista actual
        const centerWorld = this._screenToWorld(this.canvas.width / 2, this.canvas.height / 2);
        
        const node = {
            id: id,
            type: type,
            label: info.label,
            content: type === 'message' || type === 'start' ? 'Escribe tu mensaje...' : '',
            x: centerWorld.x - this.nodeWidth / 2,
            y: centerWorld.y - 40,
            width: this.nodeWidth,
            height: 100,
            outputs: type === 'options' ? [{ id: 'out1', label: 'Opción 1' }] : [{ id: 'out1', label: 'Siguiente' }],
            saveAs: type === 'input' ? 'respuesta' : undefined,
            conditionType: type === 'condition' ? 'yes_no' : undefined,
            actionType: type === 'action' ? 'create_order' : undefined
        };
        
        if (type === 'options') node.height = 130;
        if (type === 'condition') node.height = 110;
        
        this.nodes.push(node);
        this.selectNode(id);
    }
    
    deleteNode(id) {
        this.nodes = this.nodes.filter(n => n.id !== id);
        this.connections = this.connections.filter(c => c.from !== id && c.to !== id);
        if (this.selectedNode?.id === id) {
            this.selectedNode = null;
            this._onSelectNode(null);
        }
    }
    
    selectNode(id) {
        this.selectedNode = this.nodes.find(n => n.id === id) || null;
        this._onSelectNode(this.selectedNode);
    }
    
    updateNode(id, key, value) {
        const node = this.nodes.find(n => n.id === id);
        if (!node) return;
        node[key] = value;
        if (key === 'content' && node.type === 'options') {
            // Recalcular altura
            const lines = (value || '').split('\n').length;
            node.height = Math.max(130, 70 + lines * 12 + (node.outputs?.length || 1) * 18);
        }
    }
    
    updateOption(nodeId, index, value) {
        const node = this.nodes.find(n => n.id === nodeId);
        if (node && node.outputs && node.outputs[index]) {
            node.outputs[index].label = value;
        }
    }
    
    addOption(nodeId) {
        const node = this.nodes.find(n => n.id === nodeId);
        if (!node || node.type !== 'options') return;
        const newIdx = (node.outputs || []).length + 1;
        node.outputs.push({ id: 'out' + newIdx, label: 'Opción ' + newIdx });
        node.height += 18;
    }
    
    // ========== SERIALIZACIÓN ==========
    
    toJSON() {
        return {
            nodes: this.nodes.map(n => ({
                id: n.id,
                type: n.type,
                label: n.label,
                content: n.content,
                x: n.x,
                y: n.y,
                width: n.width,
                height: n.height,
                outputs: n.outputs,
                saveAs: n.saveAs,
                conditionType: n.conditionType,
                actionType: n.actionType
            })),
            connections: this.connections
        };
    }
    
    fromJSON(data) {
        this.nodes = (data.nodes || []).map(n => ({
            ...n,
            outputs: n.outputs || [{ id: 'out1', label: 'Siguiente' }]
        }));
        this.connections = data.connections || [];
        this.selectedNode = null;
    }
    
    save() {
        const visual = this.toJSON();
        fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ visual: visual })
        })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                alert('Flujo guardado correctamente');
            } else {
                alert('Error: ' + (data.error || 'Unknown'));
            }
        })
        .catch(err => alert('Error de red: ' + err));
    }
    
    load() {
        fetch('/api/config')
            .then(r => r.json())
            .then(data => {
                const visual = data.visual;
                if (visual && visual.nodes && visual.nodes.length > 0) {
                    this.fromJSON(visual);
                } else {
                    // Crear flujo por defecto
                    this._createDefaultFlow();
                }
            })
            .catch(() => this._createDefaultFlow());
    }
    
    _createDefaultFlow() {
        this.nodes = [
            { id: 'welcome', type: 'start', label: 'Bienvenida', content: '🛵 ¡Bienvenido a D\'MAR!\n¿Qué necesitas?', x: 100, y: 200, width: 200, height: 100, outputs: [{id:'out1',label:'Siguiente'}] },
            { id: 'menu', type: 'options', label: 'Menú Principal', content: '¿De qué tipo es tu delivery?', x: 400, y: 150, width: 200, height: 150, outputs: [{id:'out1',label:'🍕 Comida'},{id:'out2',label:'📦 Objeto'},{id:'out3',label:'🚗 Personas'}] },
            { id: 'ask_food', type: 'input', label: 'Qué comida', content: '🍕 ¿Qué comida quieres pedir?', x: 750, y: 50, width: 200, height: 90, outputs: [{id:'out1',label:'Siguiente'}], saveAs: 'item' },
            { id: 'ask_address', type: 'input', label: 'Dirección', content: '📍 ¿A qué dirección te lo llevamos?', x: 1050, y: 50, width: 200, height: 90, outputs: [{id:'out1',label:'Siguiente'}], saveAs: 'address' },
            { id: 'create_order', type: 'action', label: 'Crear Pedido', content: '📝 Crear pedido en sistema', x: 1350, y: 50, width: 200, height: 90, outputs: [{id:'out1',label:'Siguiente'}], actionType: 'create_order' },
            { id: 'confirm', type: 'message', label: 'Confirmación', content: '🎉 ¡Pedido creado!\n#{{order_code}}\n📍 {{address}}\n🍕 {{item}}', x: 1650, y: 50, width: 200, height: 120, outputs: [] }
        ];
        this.connections = [
            { from: 'welcome', fromPort: 'out1', to: 'menu' },
            { from: 'menu', fromPort: 'out1', to: 'ask_food' },
            { from: 'ask_food', fromPort: 'out1', to: 'ask_address' },
            { from: 'ask_address', fromPort: 'out1', to: 'create_order' },
            { from: 'create_order', fromPort: 'out1', to: 'confirm' }
        ];
        this.camera = { x: -500, y: -50, zoom: 0.85 };
    }
    
    reset() {
        if (confirm('¿Restaurar flujo por defecto?')) {
            this._createDefaultFlow();
        }
    }
}

// Exportar para uso global
window.WorkflowEditor = WorkflowEditor;
