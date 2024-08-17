import sqlite3
import pandas as pd
from rdflib import Graph, Namespace

from open_fdd.air_handling_unit.faults.fault_condition_one import FaultConditionOne

PERCENTAGE_COLS_TO_CONVERT = [
    "Supply_Fan_VFD_Speed_Sensor",  # BRICK formatted column name
]

# Minimal config dict just for fc1
config_dict = {
    "INDEX_COL_NAME": "timestamp",
    "DUCT_STATIC_COL": "Supply_Air_Static_Pressure_Sensor",
    "DUCT_STATIC_SETPOINT_COL": "Supply_Air_Static_Pressure_Setpoint",
    "SUPPLY_VFD_SPEED_COL": "Supply_Fan_VFD_Speed_Sensor",
    "VFD_SPEED_PERCENT_ERR_THRES": 0.05,
    "VFD_SPEED_PERCENT_MAX": 0.99,
    "DUCT_STATIC_INCHES_ERR_THRES": 0.1,
    "TROUBLESHOOT_MODE": False,
    "ROLLING_WINDOW_SIZE": 10,
}


def load_rdf_graph(file_path):
    print("Loading RDF graph...")
    g = Graph()
    g.parse(file_path, format="turtle")
    return g


def run_sparql_query(graph):
    print("Running SPARQL query...")
    query = """
    PREFIX brick: <https://brickschema.org/schema/Brick#>
    PREFIX ref: <https://brickschema.org/schema/Reference#>

    SELECT ?sensor ?sensorType WHERE {
        ?sensor a ?sensorType .
        FILTER (?sensorType IN (brick:Supply_Air_Static_Pressure_Sensor, brick:Supply_Air_Static_Pressure_Setpoint, brick:Supply_Fan_VFD_Speed_Sensor))
    }
    """
    return graph.query(query)


def extract_sensor_data(query_result):
    print("SPARQL query completed. Checking results...")
    sensor_data = {}
    for row in query_result:
        sensor_type = str(row.sensorType).split("#")[-1]
        sensor_data[sensor_type] = row.sensor
        print(f"Found sensor: {sensor_type} -> {row.sensor}")
    return sensor_data


def retrieve_timeseries_data(sensor_data, conn):
    dfs = []
    for sensor_type, sensor_uri in sensor_data.items():
        sensor_id = sensor_uri.split("/")[-1]
        print(f"Querying SQLite for sensor: {sensor_id} of type: {sensor_type}")
        sql_query = """
        SELECT timestamp, value
        FROM TimeseriesData
        WHERE sensor_name = ?
        """
        df_sensor = pd.read_sql_query(sql_query, conn, params=(sensor_id,))

        if df_sensor.empty:
            print(
                f"No data found for sensor: {sensor_type} with sensor_id: {sensor_id}"
            )
        else:
            print(
                f"Data found for sensor: {sensor_type}, number of records: {len(df_sensor)}"
            )
            df_sensor = df_sensor.rename(columns={"value": sensor_type})
            dfs.append(df_sensor)

    return dfs


def combine_dataframes(dfs):
    if not dfs:
        print("No data found for any sensors.")
        return None

    print("Combining DataFrames...")
    df_combined = dfs[0].set_index("timestamp")
    for df in dfs[1:]:
        df_combined = pd.merge(
            df_combined, df.set_index("timestamp"), left_index=True, right_index=True
        )

    print("The df is combined successfully.")
    return df_combined


def convert_floats(df, columns):
    # This data has floats between 0.0 and 100.0
    # so we need to convert to 0.0 and 1.0 ranges
    for column in columns:
        df[column] = df[column] / 100.0

    print(df.head())
    return df


def run_fault_one(config_dict, df):
    fc1 = FaultConditionOne(config_dict)
    df = fc1.apply(df)
    print(f"Total faults detected: {df['fc1_flag'].sum()}")
    return df


def update_fault_flags_in_db(df, conn):
    cursor = conn.cursor()

    update_data = [
        (int(row["fc1_flag"]), index, "Supply_Fan_VFD_Speed_Sensor")
        for index, row in df.iterrows()
    ]

    cursor.executemany(
        """
    UPDATE TimeseriesData
    SET fc1_flag = ?
    WHERE timestamp = ? AND sensor_name = ?
    """,
        update_data,
    )

    conn.commit()
    print("Database updated with fault flags.")


def main():
    # Step 1: Load the RDF graph from the Turtle file
    g = load_rdf_graph("brick_model_with_timeseries.ttl")

    # Step 2: Run SPARQL query to find sensors
    rdf_result = run_sparql_query(g)

    # Step 3: Extract sensor data from SPARQL query result
    sensor_data = extract_sensor_data(rdf_result)

    # Step 4: Connect to SQLite database
    print("Connecting to SQLite database...")
    conn = sqlite3.connect("brick_timeseries.db")

    # Step 5: Retrieve timeseries data from the database
    dfs = retrieve_timeseries_data(sensor_data, conn)

    # Step 6: Combine the retrieved dataframes
    df_combined = combine_dataframes(dfs)
    print(df_combined.columns)

    if df_combined is not None:
        # Step 7: Convert analog outputs to floats
        df_combined = convert_floats(df_combined, PERCENTAGE_COLS_TO_CONVERT)

        # Step 8: Run fault condition one
        df_combined = run_fault_one(config_dict, df_combined)

        # Step 9: Write the fault flags back to the database
        update_fault_flags_in_db(df_combined, conn)

        print("columns: \n", df_combined.columns)

    # Close the database connection
    conn.close()


if __name__ == "__main__":
    main()