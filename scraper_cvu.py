import pymupdf as fitz
import re
import json
from pathlib import Path



CONFIG = {

    "incluir_fecha_nacimiento": False,

    "incluir_genero": False,

    "incluir_curp": False,

    "incluir_rfc": False,

    "incluir_celular": False,

    "incluir_telefono_casa": False,

    "incluir_correo_personal": False,

    "incluir_telefono_trabajo": True,

    "incluir_correo_laboral": True
}


PATRONES_SENSIBLES = {

    "fecha_nacimiento":
        r"(?im)^Fecha de nacimiento\s*:\s*.*$",

    "genero":
        r"(?im)^G[eé]nero\s*:\s*.*$",

    "curp":
        r"(?im)^CURP\s*:\s*.*$",

    "rfc":
        r"(?im)^R\.?F\.?C\.?\s*:\s*.*$",

    "celular":
        r"(?im)^Celular\s*:\s*.*$",

    "telefono_casa":
        r"(?im)^Casa\s*:\s*.*$",

    "correo_personal":
        r"(?im)^Personal\s*:\s*.*$"
}

def extraer_publicaciones(texto):

    inicio = texto.find(
        "Artículo"
    )

    if inicio == -1:

        return []

    bloque = texto[inicio:]

    patron = re.compile(

        r"(?ms)^"
        r"(\d{4}-\d{2}-\d{2})"
        r"\s+"
        r"(.+?)"

        r"(?="
        r"^\d{4}-\d{2}-\d{2}\s"
        r"|\Z)"
    )

    publicaciones = []

    for fecha, contenido in (
        patron.findall(bloque)
    ):

        lineas = [

            x.strip()

            for x in (
                contenido.splitlines()
            )

            if x.strip()
        ]

        if not lineas:

            continue

        texto_bloque = "\n".join(
            lineas
        )

        if "Autor(es):" in texto_bloque:

            titulo, resto = (
                texto_bloque.split(
                    "Autor(es):",
                    1
                )
            )

            titulo = " ".join(
                titulo.split()
            )

        else:

            titulo = lineas[0]

            resto = "\n".join(
                lineas[1:]
            )

        autores = buscar_primero(

            r"^(.+?)"
            r"(?=\n|REVISTA:)",

            resto,

            re.I | re.M
        )

        revista = buscar_primero(

            r"REVISTA:\s*(.+?)"
            r"(?="
            r"\nDIRECCION ELECTR[ÓO]NICA:"
            r"|\nPROP[ÓO]SITO:"
            r"|\Z)",

            texto_bloque,

            re.I | re.M | re.S
        )

        url = buscar_primero(

            r"DIRECCION "
            r"ELECTR[ÓO]NICA:"
            r"\s*(https?://\S+)",

            texto_bloque,

            re.I | re.M
        )

        publicaciones.append({

            "fecha":
                fecha,

            "titulo":
                titulo,

            "autores":
                autores,

            "revista":
                revista,

            "url":
                url
        })

    return publicaciones

def filtrar_datos_personales(texto):

    resultado = texto

    mapa = {

        "fecha_nacimiento":
            "incluir_fecha_nacimiento",

        "genero":
            "incluir_genero",

        "curp":
            "incluir_curp",

        "rfc":
            "incluir_rfc",

        "celular":
            "incluir_celular",

        "telefono_casa":
            "incluir_telefono_casa",

        "correo_personal":
            "incluir_correo_personal"
    }

    for campo, opcion in mapa.items():

        if not CONFIG[opcion]:

            resultado = re.sub(
                PATRONES_SENSIBLES[campo],
                "",
                resultado
            )

    if not CONFIG[
        "incluir_telefono_trabajo"
    ]:

        resultado = re.sub(
            r"(?im)^Trabajo\s*:\s*.*$",
            "",
            resultado
        )

    if not CONFIG[
        "incluir_correo_laboral"
    ]:

        resultado = re.sub(

            r"(?im)^(Laboral|Registro.*?)"
            r"\s*:\s*\S+@\S+.*$",

            "",

            resultado
        )

    return re.sub(
        r"\n{3,}",
        "\n\n",
        resultado
    ).strip()

def extraer_titulos_academicos(
    texto
):

    bloque = buscar_primero(

        r"T[ií]tulos acad[eé]micos\s*\n"
        r"(.+?)"
        r"(?=\nProductividad "
        r"acad[eé]mica|\Z)",

        texto,

        re.I | re.M | re.S
    )

    if not bloque:

        return []

    titulos = []

    partes = re.split(

        r"(?=^\d{4}-\d{2}-\d{2}\s)",

        bloque,

        flags=re.M
    )

    for parte in partes:

        parte = " ".join(
            parte.split()
        )

        if re.match(

            r"^\d{4}-\d{2}-\d{2}",

            parte
        ):

            titulos.append(
                parte
            )

    return titulos


def extraer_texto_pdf(ruta_pdf):
    documento = fitz.open(ruta_pdf)

    paginas = []

    for pagina in documento:
        paginas.append(
            pagina.get_text("text")
        )

    documento.close()

    return "\n".join(paginas)

def limpiar_texto(texto):

    texto = texto.replace(
        "\u00a0",
        " "
    )

    texto = re.sub(
        r"[ \t]+",
        " ",
        texto
    )

    texto = re.sub(
        r"\n{3,}",
        "\n\n",
        texto
    )

    return texto.strip()


def buscar_primero(
    patron,
    texto,
    flags=re.I | re.M
):

    coincidencia = re.search(
        patron,
        texto,
        flags
    )

    if coincidencia:

        return coincidencia.group(
            1
        ).strip()

    return None

def extraer_datos_generales(texto):

    datos = {}

    nombre = buscar_primero(

        r"^(.+?)\s+Curriculum\s*:",

        texto
    )

    resumen = buscar_primero(

        r"Resumen biogr[aá]fico\s*\n"
        r"(.+?)"
        r"(?=\nInformación de contacto|"
        r"\nAdscripciones)",

        texto,

        re.I | re.M | re.S
    )

    if nombre:

        datos["nombre"] = (
            nombre.title()
        )

    if resumen:

        datos[
            "resumen_biografico"
        ] = resumen

    if CONFIG[
        "incluir_telefono_trabajo"
    ]:

        telefono = buscar_primero(

            r"^Trabajo\s*:\s*(.+)$",

            texto
        )

        if telefono:

            datos[
                "telefono_trabajo"
            ] = telefono

    return datos



texto = extraer_texto_pdf("CVU.pdf")
texto_limpio = limpiar_texto(texto)

texto_publico = filtrar_datos_personales(texto_limpio)


datos_generales = (extraer_datos_generales(texto_limpio))


print("Caracteres extraídos:", len(texto))

print(texto[:2000])
print(texto_limpio[:2000])
print(texto_publico[:2000])

with open("cvu_completo.txt", "w", encoding="utf-8") as archivo:
    archivo.write(texto)


with open("profesor_publico.txt","w",encoding="utf-8") as archivo:
    archivo.write(texto_publico)

print("Se generó cvu_completo.txt")

print(datos_generales)
titulos = (
    extraer_titulos_academicos(
        texto_limpio
    )
)

for titulo in titulos:

    print(titulo)


    publicaciones = (
    extraer_publicaciones(
        texto_limpio
    )
)

print(
    "Publicaciones detectadas:",
    len(publicaciones)
)


for publicacion in publicaciones:

    print(
        publicacion["fecha"],
        "-",
        publicacion["titulo"]
    )

    datos_profesor = {
        "fuente": {
            "archivo": "CVU.pdf"
        },
        "profesor": extraer_datos_generales(texto_limpio),
        "titulos_academicos": extraer_titulos_academicos(texto_limpio),
        "publicaciones": extraer_publicaciones(texto_limpio),
        "texto_publico_completo": texto_publico,
    }

    with open(
        "profesor.json",
        "w",
        encoding="utf-8"
    ) as archivo:
        json.dump(
            datos_profesor,
            archivo,
            ensure_ascii=False,
            indent=4
        )

with open(
    "profesor_publico.txt",
    "w",
    encoding="utf-8"
) as archivo:

    archivo.write(
        texto_publico
    )