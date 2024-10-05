aspect_colors = {
    "ordo": "D5D4EC",
    "terra": "56C000",
    "aqua": "3CD4FC",
    "permutatio": "578357",
    "vitreus": "80FFFF",
    "victus": "DE0005",
    "metallum": "B5B5CD",
    "sano": "FF2F34",
    "tempus": "B68CFF",
    "iter": "E0585B",
    "mortuus": "887788",
    "herba": "01AC00",
    "limus": "01F800",
    "bestia": "9F6409",
    "caelum": "5E74CF",
    "spiritus": "EBEBFB",
    "magneto": "C0C0C0",
    "aequalitas": "EEF0EA",
    "corpus": "EE478D",
    "humanus": "FFD7C0",
    "instrumentum": "4040EE",
    "perfodio": "DCD2D8",
    "luxuria": "FFC1CE",
    "tutamen": "00C0C0",
    "machina": "8080A0",
    "gloria": "FFE980",
    "messis": "E1B371",
    "lucrum": "E6BE44",
    "electrum": "C0EEEE",
    "tabernus": "4C8569",
    "pannus": "EAEAC2",
    "fabrico": "809D80",
    "meto": "EEAD82",
    "nebrisum": "EEEE7E",
    "perditio": "404040",
    "ignis": "FF5A01",
    "aer": "FFFF7E",
    "potentia": "C0FFFF",
    "gelum": "E1FFFF",
    "motus": "CDCCF4",
    "venenum": "89F000",
    "vacuos": "888888",
    "lux": "FFF663",
    "tempestas": "FFFFFF",
    "vinculum": "9A8080",
    "volatus": "E7E7D7",
    "praecantatio": "9700C0",
    "primordium": "F7F7DB",
    "radio": "C0FFC0",
    "fames": "9A0305",
    "arbor": "876531",
    "tenebrae": "222222",
    "vitium": "800080",
    "infernus": "FF0000",
    "exanimis": "3A4000",
    "auram": "FFC0FF",
    "superbia": "9639FF",
    "cognitio": "FFC2B3",
    "gula": "D59C46",
    "sensus": "0FD9FF",
    "astrum": "2D2C2B",
    "alienis": "805080",
    "strontio": "EEC2B3",
    "desidia": "6E6E6E",
    "invidia": "00BA00",
    "vesania": "1B122C",
    "telum": "C05050",
    "ira": "870404",
    "terminus": "B90000",
}


def hex_to_rgb(hex_color):
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


rgb_to_aspect_map = {
    name: hex_to_rgb(hex_code) for name, hex_code in aspect_colors.items()
}


def rgb_to_aspect(rgb_color):
    for name, rgb in rgb_to_aspect_map.items():
        if rgb == rgb_color:
            return name
    return None
