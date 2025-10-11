from enum import Enum


class ClientComplexityEnum(str, Enum):
    simple = "simple"
    average = "average"
    complex = "complex"

class IntakeStatusEnum(str, Enum):
    open = "open"
    done = "done"

class ChecklistItemDocKindEnum(str, Enum):
    T4 = "T4"
    receipt = "receipt"
    id = "id"

class ChecklistItemStatusEnum(str, Enum):
    missing = "missing"
    received = "received"

class DocumentDocKindEnum(str, Enum):
    T4 = "T4"
    receipt = "receipt"
    id = "id"
    unknown = "unknown"