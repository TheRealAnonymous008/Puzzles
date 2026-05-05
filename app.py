"""
app.py – Flask web server for the puzzle editor.

REST API
--------
GET  /api/state
POST /api/grid/add_cell            {row, col}
POST /api/grid/remove_cell         {row, col}
POST /api/symbol/place             {row, col, symbol_type, ...params}
POST /api/symbol/remove            {row, col}
GET  /api/symbols/registry
POST /api/rule/add                 {rule_type, params}
POST /api/rule/remove              {index}
GET  /api/rules/registry
POST /api/player/set_value         {row, col, value}
POST /api/player/clear_value       {row, col}
POST /api/player/clear_all
POST /api/player/validate          -> violations
POST /api/lines/add_segment        {from_row, from_col, to_row, to_col}
POST /api/lines/remove_segment     {from_row, from_col, to_row, to_col}
POST /api/lines/clear
GET  /api/solve
POST /api/load                     {state: ...}
GET  /api/export
"""
import sys
import os

from flask import Flask, jsonify, request, send_from_directory

sys.path.insert(0, os.path.dirname(__file__))

from puzzle_engine._ import * 

app = Flask(__name__, static_folder="static", static_url_path="")

# ---------------------------------------------------------------------------
# Single in-memory state
# ---------------------------------------------------------------------------
_state = PuzzleState()
for _r in range(4):
    for _c in range(4):
        _state.add_cell(_r, _c)

_solver_domain = list(range(1, 10))
_solver_max_solutions = 2


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _state_response():
    d = _state.to_dict()
    bb = _state.grid.bounding_box()
    d["bounding_box"] = {"min_row": bb[0], "min_col": bb[1],
                         "max_row": bb[2], "max_col": bb[3]}
    violations = _state.check_rules()
    d["violations"] = [
        {"rule_id": v.rule_id, "message": v.message,
         "cells": [list(c) for c in v.cells]}
        for v in violations
    ]
    d["is_solved"] = len(violations) == 0
    return jsonify(d)


def _err(msg: str, code: int = 400):
    return jsonify({"error": msg}), code


# ---------------------------------------------------------------------------
# Static
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

@app.get("/api/state")
def get_state():
    return _state_response()


@app.post("/api/load")
def load_state():
    global _state
    data = request.get_json(force=True)
    if "state" not in data:
        return _err("Missing 'state' key")
    try:
        _state = PuzzleState.from_dict(data["state"])
    except Exception as e:
        return _err(str(e))
    return _state_response()


@app.get("/api/export")
def export_state():
    return jsonify(_state.to_dict())


# ---------------------------------------------------------------------------
# Grid
# ---------------------------------------------------------------------------

@app.post("/api/grid/add_cell")
def add_cell():
    d = request.get_json(force=True)
    try:
        _state.add_cell(int(d["row"]), int(d["col"]))
    except Exception as e:
        return _err(str(e))
    return _state_response()


@app.post("/api/grid/remove_cell")
def remove_cell():
    d = request.get_json(force=True)
    try:
        _state.remove_cell(int(d["row"]), int(d["col"]))
    except Exception as e:
        return _err(str(e))
    return _state_response()


# ---------------------------------------------------------------------------
# Symbols
# ---------------------------------------------------------------------------

@app.get("/api/symbols/registry")
def symbols_registry():
    result = []
    for stype in SymbolRegistry.all_types():
        cls = SymbolRegistry.get(stype)
        result.append({"symbol_type": stype, "description": cls.__doc__ or ""})
    return jsonify(result)


@app.post("/api/symbol/place")
def place_symbol():
    d = request.get_json(force=True)
    row, col = int(d["row"]), int(d["col"])
    stype = d.get("symbol_type", "number")
    sym_cls = SymbolRegistry.get(stype)
    if sym_cls is None:
        return _err(f"Unknown symbol type: {stype}")
    try:
        sym = sym_cls.from_dict({k: v for k, v in d.items()
                                 if k not in ("row", "col", "symbol_type")})
        _state.place_symbol(row, col, sym)
    except Exception as e:
        return _err(str(e))
    return _state_response()


@app.post("/api/symbol/remove")
def remove_symbol():
    d = request.get_json(force=True)
    _state.remove_symbol(int(d["row"]), int(d["col"]))
    return _state_response()


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------

@app.get("/api/rules/registry")
def rules_registry():
    return jsonify(RuleRegistry.schema())


@app.post("/api/rule/add")
def add_rule():
    d = request.get_json(force=True)
    rtype = d.get("rule_type")
    params = d.get("params", {})
    rule_cls = RuleRegistry.get(rtype)
    if rule_cls is None:
        return _err(f"Unknown rule type: {rtype}")
    try:
        rule = rule_cls.from_params(params)
        _state.add_rule(rule)
    except Exception as e:
        return _err(str(e))
    return _state_response()


@app.post("/api/rule/remove")
def remove_rule():
    d = request.get_json(force=True)
    _state.remove_rule(int(d["index"]))
    return _state_response()


# ---------------------------------------------------------------------------
# Player values
# ---------------------------------------------------------------------------

@app.post("/api/player/set_value")
def set_player_value():
    d = request.get_json(force=True)
    try:
        val = d.get("value")
        if val is not None:
            try:
                val = int(val)
            except (TypeError, ValueError):
                pass
        _state.set_player_value(int(d["row"]), int(d["col"]), val)
    except Exception as e:
        return _err(str(e))
    return _state_response()


@app.post("/api/player/clear_value")
def clear_player_value():
    d = request.get_json(force=True)
    _state.clear_player_value(int(d["row"]), int(d["col"]))
    return _state_response()


@app.post("/api/player/clear_all")
def clear_all_player_values():
    _state.clear_all_player_values()
    return _state_response()


@app.post("/api/player/validate")
def validate():
    violations = _state.check_rules()
    return jsonify({
        "is_solved": len(violations) == 0,
        "violations": [
            {"rule_id": v.rule_id, "message": v.message,
             "cells": [list(c) for c in v.cells]}
            for v in violations
        ],
    })


# ---------------------------------------------------------------------------
# Lines
# ---------------------------------------------------------------------------

@app.post("/api/lines/add_segment")
def lines_add_segment():
    d = request.get_json(force=True)
    try:
        _state.add_line_segment(
            int(d["from_row"]), int(d["from_col"]),
            int(d["to_row"]),   int(d["to_col"]),
        )
    except Exception as e:
        return _err(str(e))
    return _state_response()


@app.post("/api/lines/remove_segment")
def lines_remove_segment():
    d = request.get_json(force=True)
    _state.remove_line_segment(
        int(d["from_row"]), int(d["from_col"]),
        int(d["to_row"]),   int(d["to_col"]),
    )
    return _state_response()


@app.post("/api/lines/clear")
def lines_clear():
    _state.clear_all_lines()
    return _state_response()


# ---------------------------------------------------------------------------
# Solver
# ---------------------------------------------------------------------------

@app.get("/api/solve")
def solve():
    domain_param = request.args.get("domain")
    max_sol = int(request.args.get("max_solutions", _solver_max_solutions))
    if domain_param:
        try:
            domain = [int(x) for x in domain_param.split(",")]
        except ValueError:
            return _err("domain must be comma-separated integers")
    else:
        domain = _solver_domain
    solver = Solver(domain=domain, max_solutions=max(1, min(max_sol, 100)))
    result = solver.solve(_state)
    return jsonify(result.to_dict())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Puzzle Editor running at http://localhost:5050")
    app.run(debug=True, port=5050)