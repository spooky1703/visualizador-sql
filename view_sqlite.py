#!/usr/bin/env python3
"""
view_sqlite.py - Servidor HTTP minimal para explorar un archivo SQLite (.db)
Uso: python3 view_sqlite.py ruta/a/tu.db
Abre: http://localhost:8000
"""
import sqlite3
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote

DB_PATH = sys.argv[1] if len(sys.argv) > 1 else "riego.db"
HOST = "127.0.0.1"
PORT = 8000
ROW_LIMIT = 2000  # límite de filas a mostrar por tabla

def get_tables(conn):
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;")
    return [r[0] for r in cur.fetchall()]

def get_table_head(conn, table, limit=ROW_LIMIT):
    cur = conn.cursor()
    try:
        cur.execute(f"PRAGMA table_info('{table}')")
        cols = [r[1] for r in cur.fetchall()]
        cur.execute(f"SELECT * FROM '{table}' LIMIT ?", (limit,))
        rows = cur.fetchall()
        return cols, rows
    except Exception as e:
        return [], [("ERROR", str(e))]

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        conn = sqlite3.connect(DB_PATH)
        try:
            if parsed.path in ("/", "/index.html"):
                tables = get_tables(conn)
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(self.render_index(tables).encode("utf-8"))
            elif parsed.path == "/table":
                table = qs.get("name", [""])[0]
                table = unquote(table)
                cols, rows = get_table_head(conn, table)
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(self.render_table(table, cols, rows).encode("utf-8"))
            else:
                self.send_response(404)
                self.end_headers()
        finally:
            conn.close()

    def render_index(self, tables):
        html = f"""<!doctype html>
<html>
<head><meta charset="utf-8"><title>SQLite Viewer - {DB_PATH}</title>
<style>
body{{font-family:system-ui,Segoe UI,Roboto,Arial;margin:20px}}
a{{text-decoration:none;color:#0366d6}}
table{{border-collapse:collapse;width:100%;max-width:1200px}}
th,td{{border:1px solid #ddd;padding:6px 8px;font-size:14px}}
th{{background:#f6f8fa;text-align:left}}
.header{{margin-bottom:14px}}
.small{{color:#555;font-size:13px}}
</style>
</head><body>
<div class="header"><h2>SQLite Viewer</h2><div class="small">Archivo: {DB_PATH}</div></div>
<h3>Tablas</h3>
<ul>
"""
        if not tables:
            html += "<li><em>No se encontraron tablas.</em></li>"
        else:
            for t in tables:
                html += f'<li><a href="/table?name={t}">{t}</a></li>'
        html += "</ul><hr><div class='small'>Servidor sencillo - solo lectura. Presiona F5 para recargar.</div></body></html>"
        return html

    def render_table(self, table, cols, rows):
        html = f"""<!doctype html>
<html>
<head><meta charset="utf-8"><title>Tabla {table}</title>
<style>body{{font-family:system-ui,Segoe UI,Roboto,Arial;margin:20px}}a{{text-decoration:none}}table{{border-collapse:collapse;width:100%;max-width:1400px}}th,td{{border:1px solid #ddd;padding:6px 8px;font-size:13px}}th{{background:#f6f8fa}}</style>
</head><body>
<a href="/">← Volver</a>
<h2>Tabla: {table}</h2>
"""
        if not cols:
            html += "<p><em>Sin columnas o ocurrió un error.</em></p>"
        else:
            html += "<table><thead><tr>"
            for c in cols:
                html += f"<th>{c}</th>"
            html += "</tr></thead><tbody>"
            if not rows:
                html += "<tr><td colspan='100%'><em>Sin filas</em></td></tr>"
            else:
                for r in rows:
                    html += "<tr>"
                    for v in r:
                        html += f"<td>{(v if v is not None else '')}</td>"
                    html += "</tr>"
            html += "</tbody></table>"
            if len(rows) >= ROW_LIMIT:
                html += f"<p class='small'>Mostrando las primeras {ROW_LIMIT} filas. Para ver más, modifica ROW_LIMIT en el script.</p>"
        html += "<hr><div class='small'>Solo lectura - SQLite</div></body></html>"
        return html

if __name__ == "__main__":
    print(f"Iniciando servidor para '{DB_PATH}' en http://{HOST}:{PORT} ...")
    server = HTTPServer((HOST, PORT), SimpleHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDetenido.")
        server.server_close()
