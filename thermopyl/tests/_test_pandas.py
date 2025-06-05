def test_build_pandas_dataframe():
    tmpdir = tempfile.mkdtemp()
    try:
        filenames = [get_fn("je8006138.xml")]
        data, compounds = build_pandas_dataframe(filenames)

        # Debugging output to understand what was parsed
        print("\n=== DEBUG OUTPUT ===")
        print(f"Parsed {len(data)} records")
        print(f"DataFrame columns: {list(data.columns)}")
        print(f"Compound entries: {len(compounds)}")
        print(f"First few entries:\n{data.head()}")
        print("=== END DEBUG OUTPUT ===\n")

        # Write and read data to confirm persistence and structure
        data.to_hdf(os.path.join(tmpdir, 'data.h5'), key='data')
        compounds.to_hdf(os.path.join(tmpdir, 'compound_name_to_formula.h5'), key='data') 
        df = pandas_dataframe(thermoml_path=tmpdir)
        assert not df.empty
    finally:
        shutil.rmtree(tmpdir)
        
def test_parsed_content_correctness():
    filenames = [get_fn("je8006138.xml")]
    data, compounds = build_pandas_dataframe(filenames)
    
    print("\n=== Columns in parsed DataFrame ===\n")
    print(list(data.columns))
    print("\n=== Data ===\n")
    print(data.head(3))
    
    assert not data.empty
    assert "prop_Viscosity, Pa*s" in data.columns

    # Confirm viscosity column exists
    assert "prop_Viscosity, Pa*s" in data.columns

    # Find a known value (e.g., T=293.15, x=0.5005)
    subset = data[
        (data["var_Temperature, K"] == 293.15) &
        (data["var_Mole fraction_3"] == 0.5005)
    ]

    assert not subset.empty
    value = subset.iloc[0]["prop_Viscosity, Pa*s"]
    assert abs(value - 0.003881) < 1e-6


