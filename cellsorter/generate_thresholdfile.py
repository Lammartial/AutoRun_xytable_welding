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


pyodbc.lowercase = False
conn = pyodbc.connect(
    r"Driver={Microsoft Access Driver (*.mdb, *.accdb)};" +
    r"Dbq=C:\Projekte\V-Kong\Teststand-Deployment\Python_Libs\rrc\sampledata\MG1T.accdb;")
cur = conn.cursor()

tables = [i.table_name for i in cur.tables(tableType="Table")]
print(tables)

#df = pd.read_sql_table(tables[0], conn)
#print(df)
cols = ["Cellsn","Bin_Number","Ir","Ocv","TestTime","Batchid","TestResult"]
cur.execute(f"SELECT {','.join(cols)} FROM {tables[0]}");
data = cur.fetchall()
df = pd.DataFrame.from_records(data, columns=cols)
#df.replace(-10000.0, np.nan, inplace=True)
df = df.loc[~((df["Ir"] == -10000) | (df["Ocv"] == -10000))]
print(df)
print(df.describe())

# while True:
#     row = cur.fetchone()
#     if row is None:
#         break
#     print(row)
# #     print (u"ID: {1} {2} Atk:{3} Def:{4} HP:{5} BP:{6} Species: {7} {8}".format(
# #         row.get("Number"), row.get("ID"), row.get("Name"), row.get("Atk"),
# #         row.get("Def"), row.get("HP"), row.get("BP"), row.get("Species"), row.get("Special") ))
# # cur.close()
# # conn.close()