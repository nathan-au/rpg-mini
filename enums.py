from enum import Enum

#enums/enumerations set the options that are variable can be like a Python drop-down menu. Each enum we need for models must be defined here first

class ClientComplexityEnum(str, Enum): #enum for client complexity
    simple = "simple" #simple client
    average = "average" #average client
    complex = "complex" #complex client

class IntakeStatusEnum(str, Enum): #intake status can either be open or done
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