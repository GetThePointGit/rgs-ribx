from __future__ import annotations

from pathlib import Path

import pandas as pd
from lxml import etree

from rgs_ribx.errors import (
    XML_FILE_NOT_FOUND,
    XML_MISSING_ZA,
    XML_NO_OBJECTS,
    XML_SYNTAX_ERROR,
    XML_UNKNOWN_OBJECT_TYPE,
    XML_WRONG_ROOT,
    create_error_warning_df,
)

GML_NS = "http://www.opengis.net/gml"
NAMESPACES = {"gml": GML_NS}

# Mapping van ZB_ tag-suffix naar object type prefix en beschrijving
OBJECT_TYPE_MAP = {
    "A": ("A", "inspectie_leiding"),
    "C": ("C", "inspectie_put"),
    "E": ("E", "inspectie_reiniging_kolk"),
    "G": ("G", "reiniging_leiding"),
    "J": ("J", "reiniging_put"),
    "L": ("L", "stortbon_reiniging"),
    "M": ("M", "calamiteit_reiniging"),
    "N": ("N", "stagnatie_reiniging"),
    "Q": ("Q", "reiniging_drainageleiding"),
    "S": ("S", "reiniging_drainageput"),
}

OBSERVATION_COLUMNS = [
    "_object_code",
    "_object_idx",
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "G",
    "H",
    "I",
    "J",
    "K",
    "M",
    "N",
    "O",
]
OBSERVATION_COLUMNS_SET = set(OBSERVATION_COLUMNS)


# Per object-prefix: het attribuut waarin RIBX-DRAINAGE de toelichting bij een
# Z-waarde meegeeft. Spec (RIBX-DRAINAGE p.8): "Toelichting staat bij het
# element als attribuut met dezelfde code als het algemene opmerkingenveld
# (drainageleiding: QDE)." Voorbeeld: <QCK QDE="Drain">Z</QCK> levert
# QCK="Z" en QCK_toelichting="Drain" op in de pandas-rij.
TOELICHTING_ATTR_BY_PREFIX = {
    "A": "ADE",
    "C": "CDE",
    "E": "EDE",
    "G": "GDE",
    "J": "JDE",
    "Q": "QDE",
    "S": "SDE",
}


def _extract_element_value(element):
    """Extraheer de waarde uit een XML element, inclusief GML geometrie."""
    # todo: is dit het meest efficient of kan dit beter bij de velden waar je het überhaupt verwacht? Deze functie wordt vaak aangeroepen in een bestand.
    # Check voor geneste gml:Point
    gml_point = element.find(f"{{{GML_NS}}}Point")
    if gml_point is not None:
        pos = gml_point.find(f"{{{GML_NS}}}pos")
        if pos is not None and pos.text:
            return pos.text.strip()
        return None

    # Check voor geneste gml:LineString
    gml_ls = element.find(f"{{{GML_NS}}}LineString")
    if gml_ls is not None:
        pos_list = gml_ls.find(f"{{{GML_NS}}}posList")
        if pos_list is not None and pos_list.text:
            return pos_list.text.strip()
        return None

    return element.text.strip() if element.text else None


def _parse_object(zb_element, object_prefix):
    """Parse een ZB_* element naar een dict met header-velden en een lijst van observaties (ZC).

    Voor velden met tekstwaarde 'Z' (Anders) en een attribuut ``<prefix>DE``
    (bijv. ``<QCK QDE="Drain">Z</QCK>``) wordt de attribuutwaarde als sibling-
    kolom ``<tag>_toelichting`` opgenomen — conform RIBX-DRAINAGE p.8.

    Parameters
    ----------
    zb_element : lxml.etree._Element
        Het ZB_* element dat één object representeert.
    object_prefix : str
        De één-letter object-prefix (Q/S/A/C/E/G/J/...). Bepaalt welke
        attribuut-key (``<prefix>DE``) als toelichting bij een Z-waarde wordt
        uitgelezen.

    Returns
    -------
    tuple
        ``(header: dict, observations: list[dict])``. ``header`` bevat tag→
        waarde en optioneel ``<tag>_toelichting`` voor Z-waarden met DE-attr.
    """
    header = {}
    observations = []

    toelichting_attr = TOELICHTING_ATTR_BY_PREFIX.get(object_prefix)

    for child in zb_element:
        if not isinstance(child.tag, str):
            continue
        tag = etree.QName(child).localname

        if tag == "ZC":
            obs = {}
            for zc_child in child:
                if not isinstance(zc_child.tag, str):
                    continue
                obs[etree.QName(zc_child).localname] = zc_child.text.strip() if zc_child.text else None
            observations.append(obs)
        else:
            value = _extract_element_value(child)
            header[tag] = value

            # Z-waarde + <prefix>DE-attribuut → toelichting in sibling-kolom.
            # Strikt: tekstvergelijking op exact 'Z' (case-sensitive), zoals
            # de codelijst-conventie voor "Anders".
            if value == "Z" and toelichting_attr is not None and toelichting_attr in child.attrib:
                header[f"{tag}_toelichting"] = child.attrib[toelichting_attr]

    return header, observations


def ribx_to_pandas(ribx_path: Path | str):
    """Read RIBX file and convert to pandas DataFrames.

    The dataframes contain all (processed) columns for objects and observations.
    For the objects the tags will be used as columns.

    Parameters:
    ribx_path (Path | str): Path to the RIBX file

    Returns:
    tuple: A tuple containing three elements:
        - objects (dict): dictionary with as key object type (e.g. 'A', 'C') and as value a DataFrame
        - observations (dict): dictionary with as key object type and as value a DataFrame with observation data
        - errors_and_warnings (DataFrame): DataFrame with error/warning messages
    """
    errors = []
    ribx_path = Path(ribx_path)

    # --- Stap 1: XML validatie ---
    if not ribx_path.exists():
        errors.append(
            {
                "level": "error",
                "line_nr": None,
                "value": str(ribx_path),
                "code": XML_FILE_NOT_FOUND,
                "message": f"Bestand niet gevonden: {ribx_path}",
            }
        )
        return {}, {}, create_error_warning_df(errors)

    try:
        # remove_comments=True: XML comments worden niet bewaard in de tree, zodat
        # de per-object `_ribx_content` (gebruikt voor de md5 hash) deterministisch
        # is over bestanden met/zonder comments.
        # remove_blank_text=True: stript insignificant whitespace (tabs, spaties,
        # newlines tussen elementen) zodat etree.tostring() altijd dezelfde compacte
        # output geeft ongeacht de oorspronkelijke indentatie van het bronbestand.
        parser = etree.XMLParser(remove_comments=True, remove_blank_text=True)
        tree = etree.parse(str(ribx_path), parser)
    except etree.XMLSyntaxError as e:
        errors.append(
            {
                "level": "error",
                "line_nr": e.lineno,
                "value": str(e),
                "code": XML_SYNTAX_ERROR,
                "message": f"Ongeldige XML: {e}",
            }
        )
        return {}, {}, create_error_warning_df(errors)

    root = tree.getroot()

    # Controleer root element
    root_tag = etree.QName(root).localname if root.prefix else root.tag
    if root_tag != "DATA":
        errors.append(
            {
                "level": "error",
                "line_nr": 1,
                "value": root_tag,
                "code": XML_WRONG_ROOT,
                "message": f"Root element moet 'DATA' zijn, gevonden: '{root_tag}'",
            }
        )
        return {}, {}, create_error_warning_df(errors)

    # Lees ZA metadata
    # todo: moeten we ZA nog opslaan in de database. Moeten we validatie laten afhangen van dit element?
    za = root.find("ZA")
    if za is None:
        errors.append(
            {
                "level": "warning",
                "line_nr": None,
                "value": None,
                "code": XML_MISSING_ZA,
                "message": "ZA metadata element ontbreekt",
            }
        )

    # --- Stap 2: Omzetten naar pandas DataFrames ---
    objects = {}
    observations = {}

    for child in root:
        if not isinstance(child.tag, str):
            continue
        tag = etree.QName(child).localname

        if not tag.startswith("ZB_"):
            continue

        suffix = tag[3:]  # e.g. 'A', 'C', 'E', etc.
        if suffix not in OBJECT_TYPE_MAP:
            errors.append(
                {
                    "level": "warning",
                    "line_nr": child.sourceline,
                    "value": tag,
                    "code": XML_UNKNOWN_OBJECT_TYPE,
                    "message": f"Onbekend objecttype: {tag}",
                }
            )
            continue

        prefix, _beschrijving = OBJECT_TYPE_MAP[suffix]

        header, obs_list = _parse_object(child, prefix)

        # Voeg toe aan objects dict
        if suffix not in objects:
            objects[suffix] = []
            observations[suffix] = []

        obj_idx = len(objects[suffix])
        # Gebruik het eerste veld als object code (bijv. AAA, CAA, EAA, etc.)
        code_field = f"{prefix}AA"
        object_code = header.get(code_field)

        header["_source_line"] = child.sourceline
        header["_ribx_content"] = etree.tostring(child, encoding="unicode", pretty_print=False)
        objects[suffix].append(header)

        # Voeg observaties toe met referentie naar het object
        for obs in obs_list:
            obs["_object_code"] = object_code
            obs["_object_idx"] = obj_idx
            observations[suffix].append(obs)

    # Converteer lijsten naar DataFrames
    for suffix in list(objects.keys()):
        objects[suffix] = pd.DataFrame(objects[suffix])
        if observations[suffix]:
            obs_df = pd.DataFrame(observations[suffix])
            # Voeg ontbrekende standaard kolommen toe in één keer
            missing = OBSERVATION_COLUMNS_SET - set(obs_df.columns)
            if missing:
                obs_df = obs_df.reindex(columns=[*obs_df.columns, *missing])
            observations[suffix] = obs_df
        else:
            observations[suffix] = pd.DataFrame(columns=OBSERVATION_COLUMNS)

    if not objects:
        errors.append(
            {
                "level": "warning",
                "line_nr": None,
                "value": None,
                "code": XML_NO_OBJECTS,
                "message": "Geen objecten gevonden in het RIBX bestand",
            }
        )

    return objects, observations, create_error_warning_df(errors)
