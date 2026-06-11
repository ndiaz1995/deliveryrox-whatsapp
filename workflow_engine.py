"""
🔧 Workflow Engine - Serializador Visual → Ejecutable
Convierte el formato del editor visual (nodos + conexiones) 
al formato que el bot ejecuta (start_node + nodes dict).
"""

from typing import Dict, List, Any


def serialize_workflow(visual_nodes: List[dict], connections: List[dict]) -> dict:
    """
    Convierte nodos visuales y conexiones a formato ejecutable del bot.
    
    Args:
        visual_nodes: Lista de nodos del editor visual
        connections: Lista de conexiones {from, fromPort, to}
    
    Returns:
        {"start_node": str, "nodes": {node_id: node_config}}
    """
    executable = {}
    
    # Encontrar nodo de inicio (tipo 'start' o el primero)
    start_node = None
    for node in visual_nodes:
        if node.get('type') == 'start':
            start_node = node['id']
            break
    if not start_node and visual_nodes:
        start_node = visual_nodes[0]['id']
    
    # Construir diccionario de conexiones: (from_node, from_port) -> to_node
    conn_map = {}
    for conn in connections:
        key = (conn.get('from'), conn.get('fromPort', 'out'))
        conn_map[key] = conn.get('to')
    
    # Procesar cada nodo
    for node in visual_nodes:
        node_id = node['id']
        node_type = node.get('type', 'message')
        config = {
            "type": node_type,
            "content": node.get('content', '')
        }
        
        if node_type == 'message':
            # Buscar siguiente nodo
            next_node = conn_map.get((node_id, 'out')) or conn_map.get((node_id, 'out1'))
            if next_node:
                config['next'] = next_node
        
        elif node_type == 'options':
            # Cada opción tiene su propio next
            options = []
            for i, opt in enumerate(node.get('outputs', [])):
                port_id = opt.get('id', f'out{i+1}')
                next_node = conn_map.get((node_id, port_id))
                options.append({
                    "id": opt.get('id', f'opt_{i}'),
                    "label": opt.get('label', f'Opción {i+1}'),
                    "next": next_node
                })
            config['options'] = options
        
        elif node_type == 'input':
            config['save_as'] = node.get('saveAs', 'response')
            next_node = conn_map.get((node_id, 'out')) or conn_map.get((node_id, 'out1'))
            if next_node:
                config['next'] = next_node
        
        elif node_type == 'condition':
            config['condition'] = node.get('conditionType', 'yes_no')
            # Para condiciones, buscamos puertos de salida
            outputs = node.get('outputs', [])
            if len(outputs) >= 1:
                next_true = conn_map.get((node_id, outputs[0].get('id', 'out1')))
                if next_true:
                    config['next_true'] = next_true
            if len(outputs) >= 2:
                next_false = conn_map.get((node_id, outputs[1].get('id', 'out2')))
                if next_false:
                    config['next_false'] = next_false
            # Fallback: si solo hay una conexión, es next_true
            if 'next_true' not in config:
                next_node = conn_map.get((node_id, 'out')) or conn_map.get((node_id, 'out1'))
                if next_node:
                    config['next_true'] = next_node
        
        elif node_type == 'action':
            config['action'] = node.get('actionType', 'create_order')
            next_node = conn_map.get((node_id, 'out')) or conn_map.get((node_id, 'out1'))
            if next_node:
                config['next'] = next_node
        
        elif node_type == 'start':
            # El nodo start es igual a message pero marca el inicio
            next_node = conn_map.get((node_id, 'out')) or conn_map.get((node_id, 'out1'))
            if next_node:
                config['next'] = next_node
        
        executable[node_id] = config
    
    return {
        "start_node": start_node,
        "nodes": executable
    }


def deserialize_workflow(executable: dict) -> dict:
    """
    Convierte formato ejecutable a formato visual (para cargar en el editor).
    
    Returns:
        {"nodes": [...], "connections": [...]}
    """
    start_node = executable.get('start_node', '')
    nodes = executable.get('nodes', {})
    
    visual_nodes = []
    connections = []
    
    # Posiciones iniciales en espiral
    positions = _generate_positions(len(nodes))
    pos_idx = 0
    
    for node_id, config in nodes.items():
        node_type = config.get('type', 'message')
        x, y = positions[pos_idx] if pos_idx < len(positions) else (100 + pos_idx * 50, 100)
        pos_idx += 1
        
        # Determinar outputs según tipo
        outputs = []
        if node_type == 'options' and config.get('options'):
            for i, opt in enumerate(config['options']):
                outputs.append({
                    "id": opt.get('id', f'out{i+1}'),
                    "label": opt.get('label', f'Opción {i+1}')
                })
                if opt.get('next'):
                    connections.append({
                        "from": node_id,
                        "fromPort": opt.get('id', f'out{i+1}'),
                        "to": opt['next']
                    })
        elif node_type == 'condition':
            outputs.append({"id": "out1", "label": "Sí / True"})
            outputs.append({"id": "out2", "label": "No / False"})
            if config.get('next_true'):
                connections.append({"from": node_id, "fromPort": "out1", "to": config['next_true']})
            if config.get('next_false'):
                connections.append({"from": node_id, "fromPort": "out2", "to": config['next_false']})
        else:
            outputs.append({"id": "out1", "label": "Siguiente"})
            if config.get('next'):
                connections.append({"from": node_id, "fromPort": "out1", "to": config['next']})
        
        visual_nodes.append({
            "id": node_id,
            "type": node_type,
            "label": _get_node_label(node_type, node_id),
            "content": config.get('content', ''),
            "x": x,
            "y": y,
            "width": 180,
            "height": _calc_node_height(node_type, len(outputs)),
            "outputs": outputs,
            "saveAs": config.get('save_as'),
            "conditionType": config.get('condition'),
            "actionType": config.get('action')
        })
    
    return {"nodes": visual_nodes, "connections": connections}


def _generate_positions(count: int) -> List[tuple]:
    """Genera posiciones en espiral para nodos."""
    positions = []
    x, y = 100, 100
    dx, dy = 220, 0
    step = 0
    steps_per_side = 1
    
    for i in range(count):
        positions.append((x, y))
        x += dx
        y += dy
        step += 1
        if step >= steps_per_side:
            step = 0
            dx, dy = -dy, dx  # Rotar 90°
            if dy == 0:
                steps_per_side += 1
    
    return positions


def _get_node_label(node_type: str, node_id: str) -> str:
    labels = {
        'start': 'Inicio',
        'message': 'Mensaje',
        'input': 'Pregunta',
        'options': 'Menú',
        'condition': 'Condición',
        'action': 'Acción'
    }
    return labels.get(node_type, node_id)


def _calc_node_height(node_type: str, output_count: int) -> int:
    base = 80
    if node_type == 'options':
        base = 55 + (output_count * 30)
    elif node_type == 'condition':
        base = 100
    return max(base, 80)


def validate_workflow(executable: dict) -> tuple:
    """
    Valida que un workflow ejecutable sea correcto.
    
    Returns:
        (is_valid: bool, error_message: str)
    """
    if not executable.get('start_node'):
        return False, "Falta el nodo de inicio"
    
    nodes = executable.get('nodes', {})
    if not nodes:
        return False, "El workflow no tiene nodos"
    
    if executable['start_node'] not in nodes:
        return False, f"El nodo de inicio '{executable['start_node']}' no existe"
    
    # Verificar que no hay nodos huérfanos (que no sean alcanzables)
    # y que todas las referencias a 'next' existen
    for node_id, config in nodes.items():
        next_nodes = []
        if config.get('next'):
            next_nodes.append(config['next'])
        if config.get('next_true'):
            next_nodes.append(config['next_true'])
        if config.get('next_false'):
            next_nodes.append(config['next_false'])
        for opt in config.get('options', []):
            if opt.get('next'):
                next_nodes.append(opt['next'])
        
        for next_id in next_nodes:
            if next_id not in nodes:
                return False, f"El nodo '{node_id}' referencia a '{next_id}' que no existe"
    
    return True, "Workflow válido"
