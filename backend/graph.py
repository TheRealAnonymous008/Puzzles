import math
from typing import List, Optional, Tuple

EPS = 1e-9


class PlanarGraph:
    class _Vertex:
        __slots__ = ('id', 'x', 'y', 'incident_edge')

        def __init__(self, vid: int, x: float, y: float):
            self.id = vid
            self.x = x
            self.y = y
            self.incident_edge: Optional['PlanarGraph._HalfEdge'] = None

        def __hash__(self):
            return hash(self.id)

        def __eq__(self, other):
            return isinstance(other, PlanarGraph._Vertex) and self.id == other.id

    class _HalfEdge:
        __slots__ = ('id', 'origin', 'twin', 'next', 'prev', 'face')

        def __init__(self, hid: int):
            self.id = hid
            self.origin: Optional['PlanarGraph._Vertex'] = None
            self.twin: Optional['PlanarGraph._HalfEdge'] = None
            self.next: Optional['PlanarGraph._HalfEdge'] = None
            self.prev: Optional['PlanarGraph._HalfEdge'] = None
            self.face: Optional['PlanarGraph._Face'] = None

    class _Face:
        __slots__ = ('id', 'half_edge')

        def __init__(self, fid: int):
            self.id = fid
            self.half_edge: Optional['PlanarGraph._HalfEdge'] = None

    def __init__(self):
        self._vertices = {}
        self._halfedges = {}
        self._faces = {}
        self._next_vid = 0
        self._next_heid = 0
        self._next_fid = 0
        self._boundary_vertex_ids = set()
        self._boundary_edge_ids = set()
        self._boundary_face_ids = set()
        self._outer_face_id = None
        self._create_bounding_box()

    def _create_bounding_box(self):
        B = 1e6
        v0 = self._add_vertex_raw(-B, -B)
        v1 = self._add_vertex_raw(B, -B)
        v2 = self._add_vertex_raw(B, B)
        v3 = self._add_vertex_raw(-B, B)

        he0 = self._add_halfedge_raw()
        he1 = self._add_halfedge_raw()
        he2 = self._add_halfedge_raw()
        he3 = self._add_halfedge_raw()
        he0t = self._add_halfedge_raw()
        he1t = self._add_halfedge_raw()
        he2t = self._add_halfedge_raw()
        he3t = self._add_halfedge_raw()

        he0.origin = v0
        he0t.origin = v1
        he1.origin = v1
        he1t.origin = v2
        he2.origin = v2
        he2t.origin = v3
        he3.origin = v3
        he3t.origin = v0

        he0.twin = he0t; he0t.twin = he0
        he1.twin = he1t; he1t.twin = he1
        he2.twin = he2t; he2t.twin = he2
        he3.twin = he3t; he3t.twin = he3

        he0.next = he1; he1.prev = he0
        he1.next = he2; he2.prev = he1
        he2.next = he3; he3.prev = he2
        he3.next = he0; he0.prev = he3

        he0t.next = he3t; he3t.prev = he0t
        he3t.next = he2t; he2t.prev = he3t
        he2t.next = he1t; he1t.prev = he2t
        he1t.next = he0t; he0t.prev = he1t

        interior = self._add_face_raw()
        outer = self._add_face_raw()

        for he in (he0, he1, he2, he3):
            he.face = interior
        for he in (he0t, he1t, he2t, he3t):
            he.face = outer

        interior.half_edge = he0
        outer.half_edge = he0t

        v0.incident_edge = he0
        v1.incident_edge = he1
        v2.incident_edge = he2
        v3.incident_edge = he3

        self._outer_face_id = outer.id
        self._boundary_vertex_ids.update({v0.id, v1.id, v2.id, v3.id})
        self._boundary_edge_ids.update({he0.id, he1.id, he2.id, he3.id,
                                        he0t.id, he1t.id, he2t.id, he3t.id})
        self._boundary_face_ids.add(outer.id)

    def _add_vertex_raw(self, x: float, y: float) -> '_Vertex':
        v = PlanarGraph._Vertex(self._next_vid, x, y)
        self._vertices[v.id] = v
        self._next_vid += 1
        return v

    def _add_halfedge_raw(self) -> '_HalfEdge':
        he = PlanarGraph._HalfEdge(self._next_heid)
        self._halfedges[he.id] = he
        self._next_heid += 1
        return he

    def _add_face_raw(self) -> '_Face':
        f = PlanarGraph._Face(self._next_fid)
        self._faces[f.id] = f
        self._next_fid += 1
        return f

    def add_vertex(self, x: float, y: float) -> '_Vertex':
        v = PlanarGraph._Vertex(self._next_vid, x, y)
        self._vertices[v.id] = v
        self._next_vid += 1
        face = self._locate_face(x, y)
        return v

    def _locate_face(self, x: float, y: float) -> '_Face':
        for face in self._faces.values():
            if face.id in self._boundary_face_ids:
                continue
            if face.half_edge is not None and self._point_in_face(x, y, face):
                return face
        return None

    def _point_in_face(self, x: float, y: float, face: '_Face') -> bool:
        he = face.half_edge
        if he is None:
            return False
        start = he
        poly = []
        while True:
            poly.append((he.origin.x, he.origin.y))
            he = he.next
            if he is start:
                break
        return self._point_in_polygon(x, y, poly)

    @staticmethod
    def _point_in_polygon(x: float, y: float, poly: List[Tuple[float, float]]) -> bool:
        inside = False
        n = len(poly)
        j = n - 1
        for i in range(n):
            xi, yi = poly[i]
            xj, yj = poly[j]
            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        return inside

    def get_vertices(self) -> List['_Vertex']:
        return [v for v in self._vertices.values() if v.id not in self._boundary_vertex_ids]

    def get_edges(self) -> List[Tuple['_HalfEdge', '_HalfEdge']]:
        visited = set()
        edges = []
        for he in self._halfedges.values():
            if he.id in self._boundary_edge_ids or he.twin.id in self._boundary_edge_ids:
                continue
            if he.id not in visited and he.twin.id not in visited:
                visited.add(he.id)
                visited.add(he.twin.id)
                edges.append((he, he.twin))
        return edges

    def get_faces(self) -> List['_Face']:
        return [f for f in self._faces.values() if f.id not in self._boundary_face_ids]

    def adjacent_vertices(self, v: '_Vertex') -> List['_Vertex']:
        if v.incident_edge is None:
            return []
        adj = []
        he = v.incident_edge
        while True:
            neighbor = he.twin.origin
            if neighbor.id not in self._boundary_vertex_ids:
                adj.append(neighbor)
            he = he.twin.next
            if he is v.incident_edge:
                break
        return adj

    def incident_edges(self, v: '_Vertex') -> List[Tuple['_HalfEdge', '_HalfEdge']]:
        if v.incident_edge is None:
            return []
        edges = []
        he = v.incident_edge
        while True:
            if he.id not in self._boundary_edge_ids and he.twin.id not in self._boundary_edge_ids:
                if he.id < he.twin.id:
                    edges.append((he, he.twin))
                else:
                    edges.append((he.twin, he))
            he = he.twin.next
            if he is v.incident_edge:
                break
        return edges

    def incident_faces(self, v: '_Vertex') -> List['_Face']:
        if v.incident_edge is None:
            return []
        faces = []
        he = v.incident_edge
        while True:
            face = he.face
            if face is not None and face.id not in self._boundary_face_ids:
                faces.append(face)
            he = he.twin.next
            if he is v.incident_edge:
                break
        return faces

    def add_edge(self, u: '_Vertex', v: '_Vertex') -> None:
        if u.id not in self._vertices or v.id not in self._vertices:
            return
        if self._find_halfedge(u, v) is not None:
            return
        events = self._collect_intersections(u, v)
        vertices_on_segment = self._process_events(u, v, events)
        self._insert_chain(vertices_on_segment)

    def _find_halfedge(self, u: '_Vertex', v: '_Vertex') -> Optional['_HalfEdge']:
        if u.incident_edge is None:
            return None
        he = u.incident_edge
        while True:
            if he.twin.origin is v:
                return he
            he = he.twin.next
            if he is u.incident_edge:
                break
        return None

    def _collect_intersections(self, u: '_Vertex', v: '_Vertex'):
        events = []
        ux, uy = u.x, u.y
        vx, vy = v.x, v.y
        for he in self._halfedges.values():
            if he.id in self._boundary_edge_ids or he.twin.id in self._boundary_edge_ids:
                continue
            if he.id > he.twin.id:
                continue
            a = he.origin
            b = he.twin.origin
            if a is u or a is v or b is u or b is v:
                continue
            inter = self._segment_intersection(ux, uy, vx, vy, a.x, a.y, b.x, b.y)
            if inter is None:
                continue
            ix, iy, t = inter
            if self._distance_point_segment(ix, iy, ux, uy, vx, vy) > EPS:
                continue
            if self._distance_point_segment(ix, iy, a.x, a.y, b.x, b.y) > EPS:
                continue
            events.append((ix, iy, t, he))
        for endpoint, param in [(u, 0.0), (v, 1.0)]:
            for he in self._halfedges.values():
                if he.id in self._boundary_edge_ids or he.twin.id in self._boundary_edge_ids:
                    continue
                if he.id > he.twin.id:
                    continue
                if he.origin is endpoint or he.twin.origin is endpoint:
                    continue
                dist = self._distance_point_segment(endpoint.x, endpoint.y,
                                                    he.origin.x, he.origin.y,
                                                    he.twin.origin.x, he.twin.origin.y)
                if dist < EPS:
                    events.append((endpoint.x, endpoint.y, param, he))
        return events

    @staticmethod
    def _segment_intersection(x1, y1, x2, y2, x3, y3, x4, y4):
        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denom) < EPS:
            return None
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom
        if -EPS <= t <= 1 + EPS and -EPS <= u <= 1 + EPS:
            ix = x1 + t * (x2 - x1)
            iy = y1 + t * (y2 - y1)
            return ix, iy, t
        return None

    @staticmethod
    def _distance_point_segment(px, py, x1, y1, x2, y2):
        dx = x2 - x1
        dy = y2 - y1
        if abs(dx) < EPS and abs(dy) < EPS:
            return math.hypot(px - x1, py - y1)
        t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
        if t < 0:
            return math.hypot(px - x1, py - y1)
        elif t > 1:
            return math.hypot(px - x2, py - y2)
        projx = x1 + t * dx
        projy = y1 + t * dy
        return math.hypot(px - projx, py - projy)

    def _process_events(self, u: '_Vertex', v: '_Vertex', events):
        ux, uy = u.x, u.y
        vx, vy = v.x, v.y
        points = [(ux, uy, 0.0, u)]
        point_to_vertex = {(ux, uy): u}
        for (ix, iy, t, he) in events:
            key = (round(ix / EPS) * EPS, round(iy / EPS) * EPS)
            if key in point_to_vertex:
                continue
            existing = self._find_vertex_at(ix, iy)
            if existing is not None:
                point_to_vertex[key] = existing
                points.append((ix, iy, t, existing))
            else:
                new_v = self._add_vertex_raw(ix, iy)
                point_to_vertex[key] = new_v
                points.append((ix, iy, t, new_v))
        points.sort(key=lambda p: p[2])
        dedup = []
        for px, py, t, vert in points:
            if vert is u or vert is v:
                dedup.append(vert)
                continue
            if dedup and (dedup[-1] is vert):
                continue
            dedup.append(vert)
        if dedup[-1] is not v:
            dedup.append(v)
        vertices_order = []
        seen = set()
        for vert in dedup:
            if vert.id not in seen:
                seen.add(vert.id)
                vertices_order.append(vert)
        if vertices_order[0] is not u:
            vertices_order.insert(0, u)
        if vertices_order[-1] is not v:
            vertices_order.append(v)
        for (ix, iy, t, he) in events:
            key = (round(ix / EPS) * EPS, round(iy / EPS) * EPS)
            vert = point_to_vertex.get(key)
            if vert is None:
                continue
            self._split_edge_at_vertex(he, vert)
        return vertices_order

    def _find_vertex_at(self, x: float, y: float) -> Optional['_Vertex']:
        for v in self._vertices.values():
            if abs(v.x - x) < EPS and abs(v.y - y) < EPS:
                return v
        return None

    def _split_edge_at_vertex(self, he: '_HalfEdge', new_vert: '_Vertex'):
        if he.origin is new_vert or he.twin.origin is new_vert:
            return
        he1 = self._add_halfedge_raw()
        he2 = self._add_halfedge_raw()
        he1_twin = self._add_halfedge_raw()
        he2_twin = self._add_halfedge_raw()
        he1.origin = he.origin
        he1_twin.origin = new_vert
        he2.origin = new_vert
        he2_twin.origin = he.twin.origin
        he1.twin = he1_twin; he1_twin.twin = he1
        he2.twin = he2_twin; he2_twin.twin = he2
        face_left = he.face
        face_right = he.twin.face
        he1.face = face_left; he2.face = face_left
        he1_twin.face = face_right; he2_twin.face = face_right
        he1.next = he2; he2.prev = he1
        he2.next = he.next; he.next.prev = he2
        he1.prev = he.prev; he.prev.next = he1
        he1_twin.next = he.twin.next; he.twin.next.prev = he1_twin
        he2_twin.next = he1_twin; he1_twin.prev = he2_twin
        he2_twin.prev = he.twin.prev; he.twin.prev.next = he2_twin
        if face_left.half_edge is he:
            face_left.half_edge = he1
        if face_right.half_edge is he.twin:
            face_right.half_edge = he1_twin
        if he.origin.incident_edge is he:
            he.origin.incident_edge = he1
        if he.twin.origin.incident_edge is he.twin:
            he.twin.origin.incident_edge = he2_twin
        new_vert.incident_edge = he2
        del self._halfedges[he.id]
        del self._halfedges[he.twin.id]

    def _insert_chain(self, verts: List['_Vertex']):
        for i in range(len(verts) - 1):
            a = verts[i]
            b = verts[i + 1]
            if a is b:
                continue
            if self._find_halfedge(a, b) is not None:
                continue
            self._add_edge_inside_face(a, b)

    def _add_edge_inside_face(self, a: '_Vertex', b: '_Vertex'):
        face = self._common_face(a, b)
        if face is None:
            return
        h1 = self._boundary_halfedge_from(a, face)
        h2 = self._boundary_halfedge_from(b, face)
        if h1 is None or h2 is None:
            return
        new_he = self._add_halfedge_raw()
        new_twin = self._add_halfedge_raw()
        new_he.origin = a
        new_twin.origin = b
        new_he.twin = new_twin; new_twin.twin = new_he
        new_he.face = face
        new_twin.face = self._add_face_raw()
        new_face = new_twin.face
        prev_h1 = h1.prev
        prev_h2 = h2.prev
        prev_h1.next = new_he; new_he.prev = prev_h1
        new_he.next = h2; h2.prev = new_he
        prev_h2.next = new_twin; new_twin.prev = prev_h2
        new_twin.next = h1; h1.prev = new_twin
        he = h1
        while True:
            he.face = new_face
            he = he.next
            if he is h2:
                break
        new_face.half_edge = h1
        if face.half_edge is h1:
            face.half_edge = new_he

    def _common_face(self, a: '_Vertex', b: '_Vertex') -> Optional['_Face']:
        if a.incident_edge is None and b.incident_edge is None:
            return None
        if a.incident_edge is None:
            return b.incident_edge.face if b.incident_edge else None
        if b.incident_edge is None:
            return a.incident_edge.face
        he_start = a.incident_edge
        he = he_start
        while True:
            if he.face is not None and he.face.id not in self._boundary_face_ids:
                he2 = b.incident_edge
                while True:
                    if he2.face is he.face:
                        return he.face
                    he2 = he2.twin.next
                    if he2 is b.incident_edge:
                        break
            he = he.twin.next
            if he is he_start:
                break
        return None

    def _boundary_halfedge_from(self, v: '_Vertex', face: '_Face') -> Optional['_HalfEdge']:
        if v.incident_edge is None:
            return None
        he = v.incident_edge
        while True:
            if he.face is face:
                return he
            he = he.twin.next
            if he is v.incident_edge:
                break
        return None

    def remove_vertex(self, v: '_Vertex') -> None:
        if v.id in self._boundary_vertex_ids:
            return
        while v.incident_edge is not None:
            he = v.incident_edge
            if he.id in self._boundary_edge_ids or he.twin.id in self._boundary_edge_ids:
                break
            self._remove_edge(he)
        if v.id in self._vertices:
            del self._vertices[v.id]

    def _remove_edge(self, he: '_HalfEdge') -> None:
        twin = he.twin
        face_left = he.face
        face_right = twin.face
        a = he.prev
        b = he.next
        c = twin.prev
        d = twin.next
        a.next = d; d.prev = a
        c.next = b; b.prev = c
        if face_left.half_edge is he:
            face_left.half_edge = b if b.face is face_left else a
        if face_right.half_edge is twin:
            face_right.half_edge = d if d.face is face_right else c
        if he.origin.incident_edge is he:
            he.origin.incident_edge = d if d.origin is he.origin else a
        if twin.origin.incident_edge is twin:
            twin.origin.incident_edge = b if b.origin is twin.origin else c
        for h in self._halfedges.values():
            if h.face is face_right:
                h.face = face_left
        if face_right.id in self._faces:
            del self._faces[face_right.id]
        del self._halfedges[he.id]
        del self._halfedges[twin.id]