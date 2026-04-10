from melvil import operators, panels


def test_operator_classes_defined():
    assert hasattr(operators, "classes")
    assert len(operators.classes) > 0


def test_panel_classes_defined():
    assert hasattr(panels, "classes")
    assert len(panels.classes) > 0


def test_operator_bl_idname():
    from melvil.operators import MELVIL_OT_hello

    assert MELVIL_OT_hello.bl_idname == "melvil.hello"


def test_panel_space_type():
    from melvil.panels import MELVIL_PT_main

    assert MELVIL_PT_main.bl_space_type == "VIEW_3D"
