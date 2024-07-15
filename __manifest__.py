{
    "name": "Impuestos extras en pedidos",
    "version": "17.0.1.0.1",
    "category": "Sales",
    "installable": True,
    "application": False,
    "summary": "Impuestos extras en pedidos",
    "depends": ["product","sale","account"],
    "data": [
        "security/ir.model.access.csv",
        "views/sale.xml",
        "wizard/wizard_view.xml",
        ],
}
