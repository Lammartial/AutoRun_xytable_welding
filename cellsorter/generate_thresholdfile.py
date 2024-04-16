from re import I
from itertools import chain
import pyodbc
import pandas as pd
import numpy as np


#
# You need to install the 64bit ODBC Microsoft Access Driver 2016
# Download the file from Microsoft as "AccessDatabaseEngine_x64".
#
# How to install 64-bit Microsoft Access database engine alongside 32-bit Microsoft Office?
# it may throw an error that alongside the 32bit version its not possible to install.
# Then:
#   run "AccessDatabaseEngine_x64.exe /quiet"
#
# then with regedit as admin,
#
#   delete or rename the mso.dll registry value in the following registry key:
#     HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Office\14.0\Common\FilesPaths
#     HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Office\16.0\Common\FilesPaths
#
# (from https://www.autodesk.com/support/technical/article/caas/sfdcarticles/sfdcarticles/How-to-install-64-bit-Microsoft-Database-Drivers-alongside-32-bit-Microsoft-Office.html)
#


pyodbc.lowercase = False
with pyodbc.connect(
    r"Driver={Microsoft Access Driver (*.mdb, *.accdb)};" +
    r"Dbq=C:\Projekte\V-Kong\Teststand-Deployment\Python_Libs\rrc\sampledata\MG1T.accdb;") as conn:
    with conn.cursor() as cur:

        tables = [i.table_name for i in cur.tables(tableType="Table")]
        print("Tables:", tables)

        #df = pd.read_sql_table(tables[0], conn)
        #print(df)
        cols = ["Cellsn","Bin_Number","Ir","Ocv","TestTime","Batchid","TestResult"]
        cur.execute(f"SELECT {','.join(cols)} FROM {tables[0]}");
        data = cur.fetchall()

#cur.close()
#conn.close()


df = pd.DataFrame.from_records(data, columns=cols)
#df.replace(-10000.0, np.nan, inplace=True)
df = df.astype({"Bin_Number": "int64", "Ir": "float64", "Ocv": "float64",})
df = df.loc[~((df["Ir"] == -10000) | (df["Ocv"] == -10000))]
print(df)
print(df.describe())

range_ocv = df["Ocv"].max() - df["Ocv"].min()
avg_ocv = df["Ocv"].mean()
median_ocv = df["Ocv"].median()
mode_ocv = df["Ocv"].mode()
print(f"Ocv: Mean={avg_ocv},Median={median_ocv},Mode={mode_ocv}")

range_ir = df["Ir"].max() - df["Ir"].min()
avg_ir = df["Ir"].mean()
median_ir = df["Ir"].median()
mode_ir = df["Ir"].mode()
print(f"Ir: Mean={avg_ir},Median={median_ir},Mode={mode_ir}")


print("\n\n Cellsorter Range Tool:\n","="*25)

print("Bin numbers used:", sorted(df["Bin_Number"].unique()))
print(f"Range Ocv: {range_ocv}, Ir: {range_ir}")


print("Created ranges:")
# 2x5mV - avg + 2x5 mV
#  1xmO - avg + 1 mOhm

sort_ocv = [avg_ocv + 0.005 * n for n in range(-2,2)]
sort_ocv = sort_ocv[:2] + [avg_ocv] + sort_ocv[2:]
print(sort_ocv)

sort_ir = [avg_ir + 0.005 * n for n in range(-1,1)]
sort_ir = [sort_ir[0], avg_ir, sort_ir[-1]]
print(sort_ir)

# make 4 ranges for Ocv
ocv_ranges = []
for previous, current in zip(sort_ocv, sort_ocv[1:]):
    ocv_ranges.append((previous, current))
    print(f"[{previous}..{current}]")

# make two ranges for Ir
ir_ranges = []
for previous, current in zip(sort_ir, sort_ir[1:]):
    ir_ranges.append((previous, current))
    print(f"[{previous}..{current}]")

# create a 2d array in numpy
#slots = list(zip(ir_ranges, ocv_ranges))
#slots = list(filter(lambda i: i is not None, chain.from_iterable(zip(ocv_ranges, ir_ranges))))
slots = []
for n in ocv_ranges:
    for m in ir_ranges:
        slots.append((n,m))
print("\n\n", len(slots), slots)

print("\nDONE.")
