"""
Flask backend for the Planar Graph Editor.
All mutating endpoints return the full serialised graph state.
"""
from flask import Flask, jsonify, request, render_template
from backend.graph_state import GraphManager

app = Flask(__name__)
gm = GraphManager()


# ── Page ───────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


# ── Graph state ────────────────────────────────────────────────────────

@app.route('/api/graph', methods=['GET'])
def get_graph():
    return jsonify(gm.serialize())


@app.route('/api/reset', methods=['POST'])
def reset_graph():
    gm.reset()
    return jsonify(gm.serialize())


# ── Vertices ───────────────────────────────────────────────────────────

@app.route('/api/vertices', methods=['POST'])
def add_vertex():
    data = request.get_json()
    x, y = float(data['x']), float(data['y'])
    gm.add_vertex(x, y)
    return jsonify(gm.serialize())


@app.route('/api/vertices/<int:vid>', methods=['DELETE'])
def remove_vertex(vid):
    if not gm.remove_vertex(vid):
        return jsonify({'error': 'Vertex not found'}), 404
    return jsonify(gm.serialize())


# ── Edges ──────────────────────────────────────────────────────────────

@app.route('/api/edges', methods=['POST'])
def add_edge():
    data = request.get_json()
    u_id, v_id = int(data['u_id']), int(data['v_id'])
    eid = gm.add_edge(u_id, v_id)
    if eid is None:
        return jsonify({'error': 'Cannot add edge (duplicate or invalid)'}), 400
    return jsonify(gm.serialize())


@app.route('/api/edges/<int:eid>', methods=['DELETE'])
def remove_edge(eid):
    if not gm.remove_edge(eid):
        return jsonify({'error': 'Edge not found'}), 404
    return jsonify(gm.serialize())


# ── Templates ──────────────────────────────────────────────────────────

@app.route('/api/templates/grid', methods=['POST'])
def insert_grid():
    data = request.get_json()
    rows = max(2, int(data.get('rows', 3)))
    cols = max(2, int(data.get('cols', 3)))
    spacing = max(10.0, float(data.get('spacing', 100)))
    origin_x = float(data.get('origin_x', 0))
    origin_y = float(data.get('origin_y', 0))
    gm.insert_grid(rows, cols, spacing, origin_x, origin_y)
    return jsonify(gm.serialize())


if __name__ == '__main__':
    app.run(debug=True, port=5000)
