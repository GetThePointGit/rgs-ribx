"""RIBX tag -> concept constants, taken from drainworks save_to_sewerage.py.

Only the subset needed to build the geometry/topology model is included.
"""

# Object reference (code) fields.
REF_FIELDS = {"A": "AAA", "C": "CAA", "G": "GAA", "J": "JAA", "Q": "QAA", "S": "SAA", "E": "EAA"}

# Date fields (YYYY-MM-DD).
DATE_FIELDS = {"A": "ABF", "C": "CBF", "G": "GBF", "J": "JBF", "Q": "QBF", "S": "SBF", "E": "EBF"}

# Pipe node references.
NODE1_FIELDS = {"A": "AAD", "G": "GAD", "Q": "QAD"}
NODE2_FIELDS = {"A": "AAF", "G": "GAF", "Q": "QAF"}

# Geometry fields.
PIPE_GEOM_FIELDS = {"A": "AXY", "G": "GXY", "Q": "QXY"}
NODE1_GEOM_FIELDS = {"A": "AAE", "G": "GAE", "Q": "QAE"}
NODE2_GEOM_FIELDS = {"A": "AAG", "G": "GAG", "Q": "QAG"}
MANHOLE_GEOM_FIELDS = {"C": "CAB", "J": "JAB", "S": "SAB", "E": "EAB"}

# Pipe attributes (inspection pipe ZB_A).
PIPE_SHAPE_FIELD = "ACA"
PIPE_DIAMETER_FIELD = "ACB"
PIPE_WIDTH_FIELD = "ACC"
PIPE_MATERIAL_FIELD = "ACD"
PIPE_SEWERAGE_TYPE_FIELD = "ACJ"
PIPE_BOB1_FIELD = "ACR"
PIPE_BOB2_FIELD = "ACS"

# Manhole attributes (inspection manhole ZB_C).
MANHOLE_NODE_TYPE_FIELD = "CAR"
MANHOLE_GROUND_LEVEL_FIELD = "CAS"

# Observation columns (ZC) -> Observation attribute.
OBSERVATION_FIELD_MAP = {
    "A": "code",
    "B": "char1",
    "C": "char2",
    "O": "char3",
    "D": "quant1",
    "E": "quant2",
    "F": "remarks",
    "G": "clock1",
    "H": "clock2",
    "I": "distance",
    "J": "traject_location",
    "M": "photo_ref",
    "N": "video_ref",
}
