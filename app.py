# app.py
import os, tempfile, io
from flask import Flask, request, render_template, send_file, Response
from werkzeug.utils import secure_filename
from parser_presupuesto import parse_pdf
import xlsxwriter  # lo trae XlsxWriter

ALLOWED_EXT = {".pdf"}
MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

COLUMNS = [
    'seccion','seccion_nombre','subseccion','subseccion_nombre','clave',
    'descripcion','unidad','cantidad','precio_unitario','total','titulo','fecha','archivo'
]

def build_xlsx_bytes(rows):
    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {'in_memory': True})
    ws = wb.add_worksheet('BD')

    # encabezados
    for j, h in enumerate(COLUMNS):
        ws.write(0, j, h)

    # filas
    for i, r in enumerate(rows, start=1):
        for j, k in enumerate(COLUMNS):
            ws.write(i, j, '' if r.get(k) is None else r.get(k))

    wb.close()
    buf.seek(0)
    return buf

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/convertir", methods=["POST"])
def convertir():
    try:
        if "files" not in request.files:
            return Response("No se envió ningún archivo.", status=400)

        files = request.files.getlist("files")
        if not files:
            return Response("No se envió ningún archivo.", status=400)

        all_rows = []

        with tempfile.TemporaryDirectory() as tmpdir:
            for f in files:
                filename = secure_filename(f.filename or "")
                ext = os.path.splitext(filename)[1].lower()
                if ext not in ALLOWED_EXT:
                    return Response(f"Extensión no permitida: {filename}", status=400)

                pdf_path = os.path.join(tmpdir, filename)
                f.save(pdf_path)

                rows, _ = parse_pdf(pdf_path)
                all_rows.extend(rows)

        if not all_rows:
            return Response("No se extrajo ninguna partida. Revisa el formato de tus PDFs.", status=400)

        xlsx_buffer = build_xlsx_bytes(all_rows)
        return send_file(
            xlsx_buffer,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="presupuesto_bd.xlsx",
        )

    except Exception as e:
        app.logger.exception("Fallo en /convertir")
        return Response(f"Error interno procesando tus archivos: {e}", status=500)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
