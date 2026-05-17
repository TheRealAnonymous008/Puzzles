"""
GraphManager: A planar graph manager with DCEL-style face computation.

Manages vertices, edges, and automatically computes planar faces using
a half-edge angular-sort algorithm. Supports isolated vertices natively.
"""
import math


class GraphManager:
    def __init__(self):
        self.vertices = {}   # vid → {id, x, y}
        self.edges = {}      # eid → {id, u_id, v_id}
        self._adj = {}       # vid → {neighbor_vid: eid}
        self._nv = 0
        self._ne = 0

    def reset(self):
        self.__init__()

    # ── Vertex operations ─────────────────────────────────────────────

    def add_vertex(self, x, y):
        vid = self._nv
        self._nv += 1
        self.vertices[vid] = {'id': vid, 'x': float(x), 'y': float(y)}
        self._adj[vid] = {}
        return vid

    def remove_vertex(self, vid):
        if vid not in self.vertices:
            return False
        for nid in list(self._adj[vid]):
            eid = self._adj[vid][nid]
            self._adj[nid].pop(vid, None)
            if eid in self.edges:
                del self.edges[eid]
        del self._adj[vid]
        del self.vertices[vid]
        return True

    def find_vertex_near(self, x, y, eps=0.5):
        for vid, v in self.vertices.items():
            if math.hypot(v['x'] - x, v['y'] - y) < eps:
                return vid
        return None

    # ── Edge operations ────────────────────────────────────────────────

    def add_edge(self, u_id, v_id):
        if u_id not in self.vertices or v_id not in self.vertices:
            return None
        if u_id == v_id:
            return None
        if v_id in self._adj.get(u_id, {}):
            return None  # already exists
        eid = self._ne
        self._ne += 1
        self.edges[eid] = {'id': eid, 'u_id': u_id, 'v_id': v_id}
        self._adj[u_id][v_id] = eid
        self._adj[v_id][u_id] = eid
        return eid

    def remove_edge(self, eid):
        if eid not in self.edges:
            return False
        e = self.edges[eid]
        self._adj[e['u_id']].pop(e['v_id'], None)
        self._adj[e['v_id']].pop(e['u_id'], None)
        del self.edges[eid]
        return True

    def edge_between(self, u_id, v_id):
        return self._adj.get(u_id, {}).get(v_id)

    # ── Grid template ──────────────────────────────────────────────────

    def insert_grid(self, rows, cols, spacing, origin_x, origin_y):
        vids = {}
        for r in range(rows):
            for c in range(cols):
                x = origin_x + c * spacing
                y = origin_y + r * spacing
                vid = self.add_vertex(x, y)
                vids[(r, c)] = vid
        for r in range(rows):
            for c in range(cols - 1):
                self.add_edge(vids[(r, c)], vids[(r, c + 1)])
        for r in range(rows - 1):
            for c in range(cols):
                self.add_edge(vids[(r, c)], vids[(r + 1, c)])

    # ── Face computation ───────────────────────────────────────────────

    def compute_faces(self):
        """
        Compute interior planar faces using half-edge angular-sort algorithm.

        For each directed half-edge (u→v), the next half-edge in the face cycle
        is (v→w) where w is the CW-predecessor of u in the sorted outgoing edges
        of v. Interior faces are identified by a positive signed area (shoelace
        formula in SVG coordinates where y increases downward).
        """
        verts = self.vertices
        edges = self.edges

        if len(edges) < 2:
            return []

        # Vertices with degree >= 2 can form faces
        # Build outgoing neighbours per vertex, sorted by CCW angle
        outgoing = {}
        for vid in verts:
            nbrs = list(self._adj[vid].keys())
            if len(nbrs) < 2:
                continue  # degree-1 vertices can't bound faces
            vx, vy = verts[vid]['x'], verts[vid]['y']
            nbrs.sort(key=lambda n: math.atan2(
                verts[n]['y'] - vy, verts[n]['x'] - vx))
            outgoing[vid] = nbrs

        if not outgoing:
            return []

        # Build next half-edge map:  (u,v) → (v,w)
        next_he = {}
        for vid, nbrs in outgoing.items():
            n = len(nbrs)
            for i, nid in enumerate(nbrs):
                # half-edge that ARRIVES at vid from nid
                # next in face cycle = depart vid toward CW-prev of nid around vid
                w = nbrs[(i - 1) % n]
                next_he[(nid, vid)] = (vid, w)

        # Trace face cycles
        visited = set()
        faces = []
        fid = 0

        for start in next_he:
            if start in visited:
                continue
            cycle = []
            cur = start
            while cur not in visited:
                visited.add(cur)
                cycle.append(cur[0])
                cur = next_he.get(cur)
                if cur is None:
                    break

            if len(cycle) < 3:
                continue

            # Signed area (shoelace) — positive = interior in SVG (y-down)
            area = 0.0
            n = len(cycle)
            for i in range(n):
                x1 = verts[cycle[i]]['x']
                y1 = verts[cycle[i]]['y']
                x2 = verts[cycle[(i + 1) % n]]['x']
                y2 = verts[cycle[(i + 1) % n]]['y']
                area += x1 * y2 - x2 * y1

            if area > 0:  # interior face
                faces.append({'id': fid, 'vertex_ids': cycle})
                fid += 1

        return faces

    # ── Serialisation ──────────────────────────────────────────────────

    def serialize(self):
        verts = self.vertices
        adj = self._adj

        vertices_out = []
        for vid, v in verts.items():
            neighbors = list(adj.get(vid, {}).keys())
            vertices_out.append({
                'id': vid,
                'x': v['x'],
                'y': v['y'],
                'degree': len(neighbors),
                'adjacent': neighbors,
            })

        edges_out = []
        for eid, e in self.edges.items():
            u = verts[e['u_id']]
            v = verts[e['v_id']]
            length = math.hypot(v['x'] - u['x'], v['y'] - u['y'])
            edges_out.append({
                'id': eid,
                'u_id': e['u_id'],
                'v_id': e['v_id'],
                'length': round(length, 2),
            })

        faces_out = self.compute_faces()
        # Enrich faces: compute area and edge count
        for face in faces_out:
            vids = face['vertex_ids']
            n = len(vids)
            area = 0.0
            for i in range(n):
                x1, y1 = verts[vids[i]]['x'], verts[vids[i]]['y']
                x2, y2 = verts[vids[(i+1) % n]]['x'], verts[vids[(i+1) % n]]['y']
                area += x1 * y2 - x2 * y1
            face['area'] = round(abs(area) / 2, 2)
            face['edge_count'] = n

        return {
            'vertices': vertices_out,
            'edges': edges_out,
            'faces': faces_out,
        }
