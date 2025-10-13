from enums import ChecklistItemDocKindEnum

CLIENT_COMPLEXITY_CHECKLIST = { #defines intake checklist items based on client complexity
    "simple": [ChecklistItemDocKindEnum.T4, ChecklistItemDocKindEnum.id], #simple requires t4 and id
    "average": [ChecklistItemDocKindEnum.T4, ChecklistItemDocKindEnum.id, ChecklistItemDocKindEnum.receipt, ChecklistItemDocKindEnum.receipt], #average requires t4, id and 2 receipts
    "complex": [ChecklistItemDocKindEnum.T4, ChecklistItemDocKindEnum.id, ChecklistItemDocKindEnum.receipt, ChecklistItemDocKindEnum.receipt, ChecklistItemDocKindEnum.receipt, ChecklistItemDocKindEnum.receipt, ChecklistItemDocKindEnum.receipt]
}

T4_KEYWORDS = [
    "t4",
    "statementofremunerationpaid",
    "etatdelaremunerationpayee",
]

ID_KEYWORDS = [
    "licence",
    "permis",
    "passport"
]

RECEIPT_KEYWORDS = [
    "receipt",
    "invoice",
    "total",
    "bill"
]