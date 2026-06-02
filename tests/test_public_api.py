def test_top_level_imports():
    import rgs_ribx

    assert hasattr(rgs_ribx, "build_from_ribx")
    assert hasattr(rgs_ribx, "compute_lost_capacity")
    assert hasattr(rgs_ribx, "MeasurementPoint")
    assert hasattr(rgs_ribx, "Pipe")
    assert hasattr(rgs_ribx, "Manhole")
