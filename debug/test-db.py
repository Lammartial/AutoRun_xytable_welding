import pandas as pd
from dbcon import srcEngine, SSession
# this import is only needed if connection has to be changed
from dbcon import load_config_yaml_file, createInternalSession

#
# Test porstgres connections
#
print("\nTest POSTGRES connection:\n","-"*80,"\n")

period = "month"
uuid = "90C77C1F8F2911E7813900A0453037A7"  # gn_mains 

result = None
with srcEngine.connect() as srcConnection:
    #
    # Pandas RUELZ!!!
    #
    result = pd.read_sql(
        f'''
        SELECT
            date_trunc('{period}', ma."Timestamp") as e_period,
            max(ma."Ea_pos") as e_pos,
            max(ma."Ea_neg") as e_neg
        FROM measure.m_acenergy as ma
            WHERE ma."ref_component"=UUID('{uuid}')
            GROUP by e_period
            ORDER by e_period ASC
        ''',
        con=srcConnection,
    )
    print(result)

#
# Test MS-SQL connection
#
print("\nTest MSSQL connection:\n","-"*80,"\n")

msrcEngine, mSSession = createInternalSession(load_config_yaml_file("config_mssql"), echo=True)

result = None
with msrcEngine.connect() as msrcConnection:
    result = pd.read_sql(
        f'''
        SELECT
            *
        FROM ORDER_T as ot
            ORDER by ot.Number ASC
        ''',
        con=msrcConnection,
    )
    print(result)



print("\nDONE.")