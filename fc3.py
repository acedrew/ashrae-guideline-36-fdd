import argparse
import os

import pandas as pd

from faults import FaultConditionThree
from reports import FaultCodeThreeReport

# python 3.10 on Windows 10
# py .\fc3.py -i ./ahu_data/hvac_random_fake_data/fc2_3_fake_data1.csv -o fake1_ahu_fc3_report

parser = argparse.ArgumentParser(add_help=False)
args = parser.add_argument_group("Options")

args.add_argument(
    "-h", "--help", action="help", help="Show this help message and exit."
)
args.add_argument("-i", "--input", required=True, type=str, help="CSV File Input")
args.add_argument(
    "-o", "--output", required=True, type=str, help="Word File Output Name"
)
"""
FUTURE 
 * incorporate an arg for SI units 
 * °C on temp sensors
 * piping pressure sensor PSI conversion
 * air flow CFM conversion
 * AHU duct static pressure "WC

args.add_argument('--use-SI-units', default=False, action='store_true')
args.add_argument('--no-SI-units', dest='use-SI-units', action='store_false')
"""
args = parser.parse_args()


OUTDOOR_DEGF_ERR_THRES = 5.
MIX_DEGF_ERR_THRES = 5.
RETURN_DEGF_ERR_THRES = 2.


_fc3 = FaultConditionThree(
    OUTDOOR_DEGF_ERR_THRES,
    MIX_DEGF_ERR_THRES,
    RETURN_DEGF_ERR_THRES,
    "mat",
    "rat",
    "oat",
)
_fc3_report = FaultCodeThreeReport(
    OUTDOOR_DEGF_ERR_THRES,
    MIX_DEGF_ERR_THRES,
    RETURN_DEGF_ERR_THRES,
    "mat",
    "rat",
    "oat",
)


df = pd.read_csv(args.input, index_col="Date", parse_dates=True).rolling("5T").mean()

start = df.head(1).index.date
print("Dataset start: ", start)

end = df.tail(1).index.date
print("Dataset end: ", end)

for col in df.columns:
    print("df column: ", col, "- max len: ", df[col].size)

df["fc3_flag"] = _fc3.apply(df)

df2 = df.copy().dropna()

print(df2.columns)
print(df2.fc3_flag)
document = _fc3_report.create_report(args.output, df2)
path = os.path.join(os.path.curdir, "final_report")
if not os.path.exists(path):
    os.makedirs(path)
document.save(os.path.join(path, f"{args.output}.docx"))