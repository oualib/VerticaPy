"""
(c)  Copyright  [2018-2023]  OpenText  or one of its
affiliates.  Licensed  under  the   Apache  License,
Version 2.0 (the  "License"); You  may  not use this
file except in compliance with the License.

You may obtain a copy of the License at:
http://www.apache.org/licenses/LICENSE-2.0

Unless  required  by applicable  law or  agreed to in
writing, software  distributed  under the  License is
distributed on an  "AS IS" BASIS,  WITHOUT WARRANTIES
OR CONDITIONS OF ANY KIND, either express or implied.
See the  License for the specific  language governing
permissions and limitations under the License.
"""

#
#
# Modules
#
# Standard Python Modules
import os, math, shutil, re, time, decimal, warnings, datetime, inspect, csv
from typing import Union, Literal, overload

# VerticaPy Modules
import vertica_python
import verticapy as vp
from verticapy.utils._decorators import (
    save_verticapy_logs,
    check_minimum_version,
)
from verticapy.utils._toolbox import *
from verticapy.jupyter._javascript import datatables_repr
from verticapy.errors import *
from .parsers.csv import read_csv

# Other Modules
import pandas as pd

# IPython - Optional
try:
    from IPython.display import HTML, display, Markdown
except:
    pass

#
# Utilities Functions
#


def create_schema(
    schema: str, raise_error: bool = False,
):
    """
Creates a new schema.

Parameters
----------
schema: str
    Schema name.
raise_error: bool, optional
    If the schema couldn't be created, the function raises an error.

Returns
-------
bool
    True if the schema was successfully created, False otherwise.
    """
    try:
        executeSQL(f"CREATE SCHEMA {schema};", title="Creating the new schema.")
        return True
    except:
        if raise_error:
            raise
        return False


def create_table(
    table_name: str,
    dtype: dict,
    schema: str = "",
    temporary_table: bool = False,
    temporary_local_table: bool = True,
    genSQL: bool = False,
    raise_error: bool = False,
):
    """
Creates a new table using the input columns' names and data types.

Parameters
----------
table_name: str, optional
    The final table name.
dtype: dict
    Dictionary of the user types. Each key represents a column name and each
    value represents its data type. 
    Example: {"age": "int", "name": "varchar"}
schema: str, optional
    Schema name.
temporary_table: bool, optional
    If set to True, a temporary table will be created.
temporary_local_table: bool, optional
    If set to True, a temporary local table will be created. The parameter 
    'schema' must be empty, otherwise this parameter is ignored.
genSQL: bool, optional
    If set to True, the SQL code for creating the final table will be 
    generated but not executed.
raise_error: bool, optional
    If the relation couldn't be created, raises the entire error.

Returns
-------
bool
    True if the table was successfully created, False otherwise.
    """
    # -#
    if schema.lower() == "v_temp_schema":
        schema = ""
        temporary_local_table = True
    if schema:
        input_relation = quote_ident(schema) + "." + quote_ident(table_name)
    else:
        input_relation = quote_ident(table_name)
    temp = "TEMPORARY " if temporary_table else ""
    if not (schema):
        temp = "LOCAL TEMPORARY " if temporary_local_table else ""
    dtype_str = [f"{quote_ident(column)} {dtype[column]}" for column in dtype]
    dtype_str = ", ".join(dtype_str)
    on_commit = " ON COMMIT PRESERVE ROWS" if temp else ""
    query = f"CREATE {temp}TABLE {input_relation}({dtype_str}){on_commit};"
    if genSQL:
        return query
    try:
        executeSQL(query, title="Creating the new table.")
        return True
    except:
        if raise_error:
            raise
        return False


def create_verticapy_schema():
    """
Creates a schema named 'verticapy' used to store VerticaPy extended models.
    """
    sql = "CREATE SCHEMA IF NOT EXISTS verticapy;"
    executeSQL(sql, title="Creating VerticaPy schema.")
    sql = """CREATE TABLE IF NOT EXISTS verticapy.models (model_name VARCHAR(128), 
                                                          category VARCHAR(128), 
                                                          model_type VARCHAR(128), 
                                                          create_time TIMESTAMP, 
                                                          size INT);"""
    executeSQL(sql, title="Creating the models table.")
    sql = """CREATE TABLE IF NOT EXISTS verticapy.attr (model_name VARCHAR(128), 
                                                        attr_name VARCHAR(128), 
                                                        value VARCHAR(65000));"""
    executeSQL(sql, title="Creating the attr table.")


def drop(
    name: str = "",
    method: Literal["table", "view", "model", "geo", "text", "auto", "schema"] = "auto",
    raise_error: bool = False,
    **kwds,
):
    """
Drops the input relation. This can be a model, view, table, text index,
schema, or geo index.

Parameters
----------
name: str, optional
    Relation name. If empty, it will drop all VerticaPy temporary 
    elements.
method / relation_type: str, optional
    Method used to drop.
        auto   : identifies the table/view/index/model to drop. 
                 It will never drop an entire schema unless the 
                 method is set to 'schema'.
        model  : drops the input model.
        table  : drops the input table.
        view   : drops the input view.        
        geo    : drops the input geo index.
        text   : drops the input text index.
        schema : drops the input schema.
raise_error: bool, optional
    If the object couldn't be dropped, this function raises an error.

Returns
-------
bool
    True if the relation was dropped, False otherwise.
    """
    # -#
    if "relation_type" in kwds and method == "auto":
        method = kwds["relation_type"]
    schema, relation = schema_relation(name)
    schema, relation = schema[1:-1], relation[1:-1]
    if not (name):
        method = "temp"
    if method == "auto":
        fail, end_conditions = False, False
        result = executeSQL(
            query=f"""
            SELECT 
                /*+LABEL('utilities.drop')*/ * 
            FROM columns 
            WHERE table_schema = '{schema}' 
                AND table_name = '{relation}'""",
            print_time_sql=False,
            method="fetchrow",
        )
        if not (result):
            result = executeSQL(
                query=f"""
                SELECT 
                    /*+LABEL('utilities.drop')*/ * 
                FROM view_columns 
                WHERE table_schema = '{schema}' 
                    AND table_name = '{relation}'""",
                print_time_sql=False,
                method="fetchrow",
            )
        elif not (end_conditions):
            method = "table"
            end_conditions = True
        if not (result):
            try:
                result = executeSQL(
                    query=f"""
                    SELECT 
                        /*+LABEL('utilities.drop')*/ model_type 
                    FROM verticapy.models 
                    WHERE LOWER(model_name) = '{quote_ident(name).lower()}'""",
                    print_time_sql=False,
                    method="fetchrow",
                )
            except:
                result = []
        elif not (end_conditions):
            method = "view"
            end_conditions = True
        if not (result):
            result = executeSQL(
                query=f"""
                SELECT 
                    /*+LABEL('utilities.drop')*/ * 
                FROM models 
                WHERE schema_name = '{schema}' 
                    AND model_name = '{relation}'""",
                print_time_sql=False,
                method="fetchrow",
            )
        elif not (end_conditions):
            method = "model"
            end_conditions = True
        if not (result):
            result = executeSQL(
                query=f"""
                SELECT 
                    /*+LABEL('utilities.drop')*/ * 
                FROM 
                    (SELECT STV_Describe_Index () OVER ()) x  
                WHERE name IN ('{schema}.{relation}',
                               '{relation}',
                               '\"{schema}\".\"{relation}\"',
                               '\"{relation}\"',
                               '{schema}.\"{relation}\"',
                               '\"{schema}\".{relation}')""",
                print_time_sql=False,
                method="fetchrow",
            )
        elif not (end_conditions):
            method = "model"
            end_conditions = True
        if not (result):
            try:
                executeSQL(
                    query=f"""
                        SELECT 
                            /*+LABEL(\'utilities.drop\')*/ * 
                        FROM "{schema}"."{relation}" LIMIT 0;""",
                    print_time_sql=False,
                )
                method = "text"
            except:
                fail = True
        elif not (end_conditions):
            method = "geo"
            end_conditions = True
        if fail:
            if raise_error:
                raise MissingRelation(
                    f"No relation / index / view / model named '{name}' was detected."
                )
            return False
    query = ""
    if method == "model":
        model_type = kwds["model_type"] if "model_type" in kwds else None
        try:
            result = executeSQL(
                query=f"""
                    SELECT 
                        /*+LABEL('utilities.drop')*/ model_type 
                    FROM verticapy.models 
                    WHERE LOWER(model_name) = '{quote_ident(name).lower()}'""",
                print_time_sql=False,
                method="fetchfirstelem",
            )
            is_in_verticapy_schema = True
            if not (model_type):
                model_type = result
        except:
            is_in_verticapy_schema = False
        if (
            model_type
            in (
                "DBSCAN",
                "LocalOutlierFactor",
                "CountVectorizer",
                "KernelDensity",
                "AutoDataPrep",
                "KNeighborsRegressor",
                "KNeighborsClassifier",
                "NearestCentroid",
            )
            or is_in_verticapy_schema
        ):
            if model_type in ("DBSCAN", "LocalOutlierFactor"):
                drop(name, method="table")
            elif model_type == "CountVectorizer":
                drop(name, method="text")
                if is_in_verticapy_schema:
                    res = executeSQL(
                        query=f"""
                            SELECT 
                                /*+LABEL('utilities.drop')*/ value 
                            FROM verticapy.attr 
                            WHERE LOWER(model_name) = '{quote_ident(name).lower()}' 
                                AND attr_name = 'countvectorizer_table'""",
                        print_time_sql=False,
                        method="fetchrow",
                    )
                    if res and res[0]:
                        drop(res[0], method="table")
            elif model_type == "KernelDensity":
                table_name = name.replace('"', "") + "_KernelDensity_Map"
                drop(table_name, method="table")
                model_name = name.replace('"', "") + "_KernelDensity_Tree"
                drop(model_name, method="model")
            elif model_type == "AutoDataPrep":
                drop(name, method="table")
            if is_in_verticapy_schema:
                executeSQL(
                    query=f"""
                        DELETE /*+LABEL('utilities.drop')*/ 
                        FROM verticapy.models 
                        WHERE LOWER(model_name) = '{quote_ident(name).lower()}';""",
                    title="Deleting vModel.",
                )
                executeSQL("COMMIT;", title="Commit.")
                executeSQL(
                    query=f"""
                        DELETE /*+LABEL('utilities.drop')*/ 
                        FROM verticapy.attr 
                        WHERE LOWER(model_name) = '{quote_ident(name).lower()}';""",
                    title="Deleting vModel attributes.",
                )
                executeSQL("COMMIT;", title="Commit.")
        else:
            query = f"DROP MODEL {name};"
    elif method == "table":
        query = f"DROP TABLE {name};"
    elif method == "view":
        query = f"DROP VIEW {name};"
    elif method == "geo":
        query = f"SELECT STV_Drop_Index(USING PARAMETERS index ='{name}') OVER ();"
    elif method == "text":
        query = f"DROP TEXT INDEX {name};"
    elif method == "schema":
        query = f"DROP SCHEMA {name} CASCADE;"
    if query:
        try:
            executeSQL(query, title="Deleting the relation.")
            result = True
        except:
            if raise_error:
                raise
            result = False
    elif method == "temp":
        sql = """SELECT /*+LABEL('utilities.drop')*/
                    table_schema, table_name 
                 FROM columns 
                 WHERE LOWER(table_name) LIKE '%_verticapy_tmp_%' 
                 GROUP BY 1, 2;"""
        all_tables = result = executeSQL(sql, print_time_sql=False, method="fetchall")
        for elem in all_tables:
            table = format_schema_table(
                elem[0].replace('"', '""'), elem[1].replace('"', '""')
            )
            drop(table, method="table")
        sql = """SELECT /*+LABEL('utilities.drop')*/
                    table_schema, table_name 
                 FROM view_columns 
                 WHERE LOWER(table_name) LIKE '%_verticapy_tmp_%' 
                 GROUP BY 1, 2;"""
        all_views = executeSQL(sql, print_time_sql=False, method="fetchall")
        for elem in all_views:
            view = format_schema_table(
                elem[0].replace('"', '""'), elem[1].replace('"', '""')
            )
            drop(view, method="view")
        result = True
    else:
        result = True
    return result


def get_data_types(
    expr: str = "",
    column: str = "",
    table_name: str = "",
    schema: str = "public",
    usecols: list = [],
):
    """
Returns customized relation columns and the respective data types.
This process creates a temporary table.

If table_name is defined, the expression is ignored and the function
returns the table/view column names and data types.

Parameters
----------
expr: str, optional
    An expression in pure SQL. If empty, the parameter 'table_name' must be
    defined.
column: str, optional
    If not empty, it will return only the data type of the input column if it
    is in the relation.
table_name: str, optional
    Input table Name.
schema: str, optional
    Table schema.
usecols: list, optional
    List of columns to consider. This parameter can not be used if 'column'
    is defined.

Returns
-------
list of tuples
    The list of the different columns and their respective type.
    """
    assert expr or table_name, ParameterError(
        "Missing parameter: 'expr' and 'table_name' can not both be empty."
    )
    assert not (column) or not (usecols), ParameterError(
        "Parameters 'column' and 'usecols' can not both be defined."
    )
    if expr and table_name:
        warning_message = (
            "As parameter 'table_name' is defined, parameter 'expression' is ignored."
        )
        warnings.warn(warning_message, Warning)

    from verticapy.connect import current_cursor

    if isinstance(current_cursor(), vertica_python.vertica.cursor.Cursor) and not (
        table_name
    ):
        try:
            if column:
                column_name_ident = quote_ident(column)
                query = f"SELECT {column_name_ident} FROM ({expr}) x LIMIT 0;"
            elif usecols:
                query = f"""
                    SELECT 
                        {", ".join([quote_ident(column) for column in usecols])} 
                    FROM ({expr}) x 
                    LIMIT 0;"""
            else:
                query = expr
            executeSQL(query, print_time_sql=False)
            description, ctype = current_cursor().description, []
            for d in description:
                ctype += [
                    [
                        d[0],
                        get_final_vertica_type(
                            type_name=d.type_name,
                            display_size=d[2],
                            precision=d[4],
                            scale=d[5],
                        ),
                    ]
                ]
            if column:
                return ctype[0][1]
            return ctype
        except:
            pass
    if not (table_name):
        table_name, schema = gen_tmp_name(name="table"), "v_temp_schema"
        drop(format_schema_table(schema, table_name), method="table")
        try:
            if schema == "v_temp_schema":
                table = table_name
                local = "LOCAL"
            else:
                table = format_schema_table(schema, table_name)
                local = ""
            executeSQL(
                query=f"""
                    CREATE {local} TEMPORARY TABLE {table} 
                    ON COMMIT PRESERVE ROWS 
                    AS {expr}""",
                print_time_sql=False,
            )
        finally:
            drop(format_schema_table(schema, table_name), method="table")
        drop_final_table = True
    else:
        drop_final_table = False
    usecols_str, column_name = "", ""
    if usecols:
        usecols_str = [
            "'" + column.lower().replace("'", "''") + "'" for column in usecols
        ]
        usecols_str = f" AND LOWER(column_name) IN ({', '.join(usecols_str)})"
    if column:
        column_name = f"column_name = '{column}' AND "
    query = f"""
        SELECT 
            column_name,
            data_type,
            ordinal_position 
        FROM {{}}
        WHERE {column_name}table_name = '{table_name}' 
            AND table_schema = '{schema}'{usecols_str}"""
    cursor = executeSQL(
        query=f"""
            SELECT 
                /*+LABEL('utilities.get_data_types')*/ 
                column_name,
                data_type 
            FROM 
                (({query.format("columns")}) 
                 UNION 
                 ({query.format("view_columns")})) x 
                ORDER BY ordinal_position""",
        title="Getting the data types.",
    )
    ctype = cursor.fetchall()
    if column and ctype:
        ctype = ctype[0][1]
    if drop_final_table:
        drop(format_schema_table(schema, table_name), method="table")
    return ctype


@save_verticapy_logs
def help_start():
    """
VERTICAPY Interactive Help (FAQ).
    """
    path = os.path.dirname(vp.__file__)
    img1 = vp.gen_verticapy_logo_html(size="10%")
    img2 = vp.gen_verticapy_logo_str()
    message = img1 if (isnotebook()) else img2
    message += (
        "\n\n&#128226; Welcome to the <b>VerticaPy</b> help module."
        "\n\nThis module can help you connect to Vertica, "
        "create a Virtual DataFrame, load your data, and more.\n "
        "- <b>[Enter  0]</b> Overview of the library\n "
        "- <b>[Enter  1]</b> Load an example dataset\n "
        "- <b>[Enter  2]</b> View an example of data analysis with VerticaPy\n "
        "- <b>[Enter  3]</b> Contribute on GitHub\n "
        "- <b>[Enter  4]</b> View the SQL code generated by a vDataFrame and "
        "the time elapsed for the query\n "
        "- <b>[Enter  5]</b> Load your own dataset into Vertica \n "
        "- <b>[Enter  6]</b> Write SQL queries in Jupyter\n "
        "- <b>[Enter -1]</b> Exit"
    )
    if not (isnotebook()):
        message = message.replace("<b>", "").replace("</b>", "")
    display(Markdown(message)) if (isnotebook()) else print(message)
    try:
        response = int(input())
    except:
        print("Invalid choice.\nPlease enter a number between 0 and 11.")
        try:
            response = int(input())
        except:
            print("Invalid choice.\nRerun the help_start function when you need help.")
            return
    if response == 0:
        link = "https://www.vertica.com/python/quick-start.php"
    elif response == 1:
        link = "https://www.vertica.com/python/documentation_last/datasets/"
    elif response == 2:
        link = "https://www.vertica.com/python/examples/"
    elif response == 3:
        link = "https://github.com/vertica/VerticaPy/"
    elif response == 4:
        link = "https://www.vertica.com/python/documentation_last/utilities/set_option/"
    elif response == 5:
        link = "https://www.vertica.com/python/documentation_last/datasets/"
    elif response == 6:
        link = "https://www.vertica.com/python/documentation_last/extensions/sql/"
    elif response == -1:
        message = "Thank you for using the VerticaPy help module."
    elif response == 666:
        message = (
            "Thank you so much for using this library. My only purpose is to solve "
            "real Big Data problems in the context of Data Science. I worked years "
            "to be able to create this API and give you a real way to analyze your "
            "data.\n\nYour devoted Data Scientist: <i>Badr Ouali</i>"
        )
    else:
        message = "Invalid choice.\nPlease enter a number between -1 and 6."
    if 0 <= response <= 6:
        if not (isnotebook()):
            message = f"Please go to {link}"
        else:
            message = f"Please go to <a href='{link}'>{link}</a>"
    display(Markdown(message)) if (isnotebook()) else print(message)


def init_interactive_mode(all_interactive=False):
    """Activate the datatables representation for all the vDataFrames."""
    set_option("interactive", all_interactive)


@save_verticapy_logs
def insert_into(
    table_name: str,
    data: list,
    schema: str = "",
    column_names: list = [],
    copy: bool = True,
    genSQL: bool = False,
):
    """
Inserts the dataset into an existing Vertica table.

Parameters
----------
table_name: str
    Name of the table to insert into.
data: list
    The data to ingest.
schema: str, optional
    Schema name.
column_names: list, optional
    Name of the column(s) to insert into.
copy: bool, optional
    If set to True, the batch insert is converted to a COPY statement 
    with prepared statements. Otherwise, the INSERTs are performed
    sequentially.
genSQL: bool, optional
    If set to True, the SQL code that would be used to insert the data 
    is generated, but not executed.

Returns
-------
int
    The number of rows ingested.

See Also
--------
pandas_to_vertica : Ingests a pandas DataFrame into the Vertica database.
    """
    if not (schema):
        schema = vp.OPTIONS["temp_schema"]
    input_relation = format_schema_table(schema, table_name)
    if not (column_names):
        result = executeSQL(
            query=f"""
                SELECT /*+LABEL('utilities.insert_into')*/
                    column_name
                FROM columns 
                WHERE table_name = '{table_name}' 
                    AND table_schema = '{schema}' 
                ORDER BY ordinal_position""",
            title=f"Getting the table {input_relation} column names.",
            method="fetchall",
        )
        column_names = [elem[0] for elem in result]
        assert column_names, MissingRelation(
            f"The table {input_relation} does not exist."
        )
    cols = [quote_ident(col) for col in column_names]
    if copy and not (genSQL):
        executeSQL(
            query=f"""
                INSERT INTO {input_relation} 
                ({", ".join(cols)})
                VALUES ({", ".join(["%s" for i in range(len(cols))])})""",
            title=(
                f"Insert new lines in the {table_name} table. "
                "The batch insert is converted into a COPY "
                "statement by using prepared statements."
            ),
            data=list(map(tuple, data)),
        )
        executeSQL("COMMIT;", title="Commit.")
        return len(data)
    else:
        if genSQL:
            sql = []
        i, n, total_rows = 0, len(data), 0
        header = f"""
            INSERT INTO {input_relation}
            ({", ".join(cols)}) VALUES """
        for i in range(n):
            sql_tmp = "("
            for d in data[i]:
                if isinstance(d, str):
                    d_str = d.replace("'", "''")
                    sql_tmp += f"'{d_str}'"
                elif d is None or d != d:
                    sql_tmp += "NULL"
                else:
                    sql_tmp += f"'{d}'"
                sql_tmp += ","
            sql_tmp = sql_tmp[:-1] + ");"
            query = header + sql_tmp
            if genSQL:
                sql += [clean_query(query)]
            else:
                try:
                    executeSQL(
                        query=query,
                        title=f"Insert a new line in the relation: {input_relation}.",
                    )
                    executeSQL("COMMIT;", title="Commit.")
                    total_rows += 1
                except Exception as e:
                    warning_message = f"Line {i} was skipped.\n{e}"
                    warnings.warn(warning_message, Warning)
        if genSQL:
            return sql
        else:
            return total_rows


@save_verticapy_logs
def pandas_to_vertica(
    df: pd.DataFrame,
    name: str = "",
    schema: str = "",
    dtype: dict = {},
    parse_nrows: int = 10000,
    temp_path: str = "",
    insert: bool = False,
):
    """
Ingests a pandas DataFrame into the Vertica database by creating a 
CSV file and then using flex tables to load the data.

Parameters
----------
df: pandas.DataFrame
    The pandas.DataFrame to ingest.
name: str, optional
    Name of the new relation or the relation in which to insert the 
    data. If unspecified, a temporary local table is created. This 
    temporary table is dropped at the end of the local session.
schema: str, optional
    Schema of the new relation. If empty, a temporary schema is used. 
    To modify the temporary schema, use the 'set_option' function.
dtype: dict, optional
    Dictionary of input types. Providing a dictionary can increase 
    ingestion speed and precision. If specified, rather than parsing 
    the intermediate CSV and guessing the input types, VerticaPy uses 
    the specified input types instead.
parse_nrows: int, optional
    If this parameter is greater than 0, VerticaPy creates and 
    ingests a temporary file containing 'parse_nrows' number 
    of rows to determine the input data types before ingesting 
    the intermediate CSV file containing the rest of the data. 
    This method of data type identification is less accurate, 
    but is much faster for large datasets.
temp_path: str, optional
    The path to which to write the intermediate CSV file. This 
    is useful in cases where the user does not have write 
    permissions on the current directory.
insert: bool, optional
    If set to True, the data are ingested into the input relation. 
    The column names of your table and the pandas.DataFrame must 
    match.
    
Returns
-------
vDataFrame
    vDataFrame of the new relation.

See Also
--------
read_csv  : Ingests a  CSV file into the Vertica database.
read_json : Ingests a JSON file into the Vertica database.
    """
    if not (schema):
        schema = vp.OPTIONS["temp_schema"]
    assert name or not (insert), ParameterError(
        "Parameter 'name' can not be empty when parameter 'insert' is set to True."
    )
    if not (name):
        tmp_name = gen_tmp_name(name="df")[1:-1]
    else:
        tmp_name = ""
    sep = "/" if (len(temp_path) > 1 and temp_path[-1] != "/") else ""
    path = f"{temp_path}{sep}{name}.csv"
    try:
        # Adding the quotes to STR pandas columns in order to simplify the ingestion.
        # Not putting them can lead to wrong data ingestion.
        str_cols = []
        for c in df.columns:
            if df[c].dtype == object and isinstance(
                df[c].loc[df[c].first_valid_index()], str
            ):
                str_cols += [c]
        if str_cols:
            tmp_df = df.copy()
            for c in str_cols:
                tmp_df[c] = '"' + tmp_df[c].str.replace('"', '""') + '"'
            clear = True
        else:
            tmp_df = df
            clear = False
        tmp_df.to_csv(
            path, index=False, quoting=csv.QUOTE_NONE, quotechar="", escapechar="\027",
        )
        if str_cols:
            # to_csv is adding an undesired special character
            # we remove it
            with open(path, "r") as f:
                filedata = f.read()
            filedata = filedata.replace(",", ",")
            with open(path, "w") as f:
                f.write(filedata)

        if insert:
            input_relation = format_schema_table(schema, name)
            tmp_df_columns_str = ", ".join(
                ['"' + col.replace('"', '""') + '"' for col in tmp_df.columns]
            )
            executeSQL(
                query=f"""
                    COPY {input_relation}
                    ({tmp_df_columns_str}) 
                    FROM LOCAL '{path}' 
                    DELIMITER ',' 
                    NULL ''
                    ENCLOSED BY '\"' 
                    ESCAPE AS '\\' 
                    SKIP 1;""",
                title="Inserting the pandas.DataFrame.",
            )
            from verticapy import vDataFrame

            vdf = vDataFrame(name, schema=schema)
        elif tmp_name:
            vdf = read_csv(
                path,
                table_name=tmp_name,
                dtype=dtype,
                temporary_local_table=True,
                parse_nrows=parse_nrows,
                escape="\027",
            )
        else:
            vdf = read_csv(
                path,
                table_name=name,
                dtype=dtype,
                schema=schema,
                temporary_local_table=False,
                parse_nrows=parse_nrows,
                escape="\027",
            )
    finally:
        os.remove(path)
        if clear:
            del tmp_df
    return vdf


vHelp = help_start


@check_minimum_version
@save_verticapy_logs
def read_file(
    path: str,
    schema: str = "",
    table_name: str = "",
    dtype: dict = {},
    unknown: str = "varchar",
    varchar_varbinary_length: int = 80,
    insert: bool = False,
    temporary_table: bool = False,
    temporary_local_table: bool = True,
    gen_tmp_table_name: bool = True,
    ingest_local: bool = False,
    genSQL: bool = False,
    max_files: int = 100,
):
    """
Inspects and ingests a file in CSV, Parquet, ORC, JSON, or Avro format.
This function uses the Vertica complex data type.
For new table creation, the file must be located in the server.

Parameters
----------
path: str
    Path to a file or glob. Valid paths include any path that is 
    valid for COPY and that uses a file format supported by this 
    function. 
    When inferring the data type, only one file will be read, even 
    if a glob specifies multiple files. However, in the case of JSON, 
    more than one file may be read to infer the data type.
schema: str, optional
    Schema in which to create the table.
table_name: str, optional
    Name of the table to create. If empty, the file name is used.
dtype: dict, optional
    Dictionary of customised data type. The predicted data types will 
    be replaced by the input data types. The dictionary must include 
    the name of the column as key and the new data type as value.
unknown: str, optional
    Type used to replace unknown data types.
varchar_varbinary_length: int, optional
    Default length of varchar and varbinary columns.
insert: bool, optional
    If set to True, the data is ingested into the input relation.
    When you set this parameter to True, most of the parameters are 
    ignored.
temporary_table: bool, optional
    If set to True, a temporary table is created.
temporary_local_table: bool, optional
    If set to True, a temporary local table is created. The parameter 
    'schema' must be empty, otherwise this parameter is ignored.
gen_tmp_table_name: bool, optional
    Sets the name of the temporary table. This parameter is only used 
    when the parameter 'temporary_local_table' is set to True and the 
    parameters "table_name" and "schema" are unspecified.
ingest_local: bool, optional
    If set to True, the file is ingested from the local machine. 
    This currently only works for data insertion.
genSQL: bool, optional
    If set to True, the SQL code for creating the final table is 
    generated but not executed. This is a good way to change the final
    relation types or to customize the data ingestion.
max_files: int, optional
    (JSON only.) If path is a glob, specifies maximum number of files 
    in path to inspect. Use this parameter to increase the amount of 
    data the function considers. This can be beneficial if you suspect 
    variation among files. Files are chosen arbitrarily from the glob.
    The default value is 100.

Returns
-------
vDataFrame
    The vDataFrame of the relation.
    """
    from verticapy import vDataFrame

    assert not (ingest_local) or insert, ParameterError(
        "Ingest local to create new relations is not yet supported for 'read_file'"
    )
    file_format = path.split(".")[-1].lower()
    compression = extract_compression(path)
    if compression != "UNCOMPRESSED":
        raise ExtensionError(
            f"Compressed files are not supported for 'read_file' function."
        )
    if file_format not in ("json", "parquet", "avro", "orc", "csv"):
        raise ExtensionError("The file extension is incorrect !")
    if file_format == "csv":
        return read_csv(
            path=path,
            schema=schema,
            table_name=table_name,
            dtype=dtype,
            genSQL=genSQL,
            insert=insert,
            temporary_table=temporary_table,
            temporary_local_table=temporary_local_table,
            gen_tmp_table_name=gen_tmp_table_name,
            ingest_local=ingest_local,
        )
    if insert:
        if not (table_name):
            raise ParameterError(
                "Parameter 'table_name' must be defined when parameter 'insert' is set to True."
            )
        if not (schema) and temporary_local_table:
            schema = "v_temp_schema"
        elif not (schema):
            schema = "public"
        input_relation = quote_ident(schema) + "." + quote_ident(table_name)
        file_format = file_format.upper()
        if file_format.lower() in ("json", "avro"):
            parser = f" PARSER F{file_format}PARSER()"
        else:
            parser = f" {file_format}"
        path = path.replace("'", "''")
        local = "LOCAL " if ingest_local else ""
        query = f"COPY {input_relation} FROM {local}'{path}'{parser};"
        if genSQL:
            return [clean_query(query)]
        executeSQL(query, title="Inserting the data.")
        return vDataFrame(table_name, schema=schema)
    if schema:
        temporary_local_table = False
    elif temporary_local_table:
        schema = "v_temp_schema"
    else:
        schema = "public"
    basename = ".".join(path.split("/")[-1].split(".")[0:-1])
    if gen_tmp_table_name and temporary_local_table and not (table_name):
        table_name = gen_tmp_name(name=basename)
    if not (table_name):
        table_name = basename
    sql = (
        f"SELECT INFER_TABLE_DDL ('{path}' USING PARAMETERS "
        f"format='{file_format}', table_name='y_verticapy', "
        "table_schema='x_verticapy', table_type='native', "
        "with_copy_statement=true, one_line_result=true, "
        f"max_files={max_files}, max_candidates=1);"
    )
    result = executeSQL(
        sql, title="Generating the CREATE and COPY statement.", method="fetchfirstelem",
    )
    result = result.replace("UNKNOWN", unknown)
    result = "create" + "create".join(result.split("create")[1:])
    relation = format_schema_table(schema, table_name)
    if temporary_local_table:
        create_statement = f"CREATE LOCAL TEMPORARY TABLE {quote_ident(table_name)}"
    else:
        if not (schema):
            schema = "public"
        if temporary_table:
            create_statement = f"CREATE TEMPORARY TABLE {relation}"
        else:
            create_statement = f"CREATE TABLE {relation}"
    result = result.replace(
        'create table "x_verticapy"."y_verticapy"', create_statement
    )
    if ";\n copy" in result:
        result = result.split(";\n copy")
        if temporary_local_table:
            result[0] += " ON COMMIT PRESERVE ROWS;"
        else:
            result[0] += ";"
        result[1] = "copy" + result[1].replace('"x_verticapy"."y_verticapy"', relation,)
    else:
        if temporary_local_table:
            end = result.split(")")[-1]
            result = result.split(")")[0:-1] + ") ON COMMIT PRESERVE ROWS" + end
        result = [result]
    if varchar_varbinary_length != 80:
        result[0] = (
            result[0]
            .replace(" varchar", f" varchar({varchar_varbinary_length})")
            .replace(" varbinary", f" varbinary({varchar_varbinary_length})")
        )
    for col in dtype:
        extract_col_dt = extract_col_dt_from_query(result[0], col)
        if extract_col_dt is None:
            warning_message = f"The column '{col}' was not found.\nIt will be skipped."
            warnings.warn(warning_message, Warning)
        else:
            column, ctype = extract_col_dt
            result[0] = result[0].replace(
                column + " " + ctype, column + " " + dtype[col]
            )
    if genSQL:
        for idx in range(len(result)):
            result[idx] = clean_query(result[idx])
        return result
    if len(result) == 1:
        executeSQL(
            result, title="Creating the table and ingesting the data.",
        )
    else:
        executeSQL(
            result[0], title="Creating the table.",
        )
        try:
            executeSQL(
                result[1], title="Ingesting the data.",
            )
        finally:
            drop(f'"{schema}"."{table_name}"', method="table")
    return vDataFrame(input_relation=table_name, schema=schema)


@save_verticapy_logs
def read_shp(
    path: str, schema: str = "public", table_name: str = "",
):
    """
Ingests a SHP file. For the moment, only files located in the Vertica server 
can be ingested.

Parameters
----------
path: str
    Absolute path where the SHP file is located.
schema: str, optional
    Schema where the SHP file will be ingested.
table_name: str, optional
    Final relation name.

Returns
-------
vDataFrame
    The vDataFrame of the relation.
    """
    file = path.split("/")[-1]
    file_extension = file[-3 : len(file)]
    if file_extension != "shp":
        raise ExtensionError("The file extension is incorrect !")
    query = (
        f"SELECT /*+LABEL('utilities.read_shp')*/ STV_ShpCreateTable(USING PARAMETERS file='{path}')"
        " OVER() AS create_shp_table;"
    )
    result = executeSQL(query, title="Getting SHP definition.", method="fetchall")
    if not (table_name):
        table_name = file[:-4]
    result[0] = [f'CREATE TABLE "{schema}"."{table_name}"(']
    result = [elem[0] for elem in result]
    result = "".join(result)
    executeSQL(result, title="Creating the relation.")
    query = (
        f'COPY "{schema}"."{table_name}" WITH SOURCE STV_ShpSource(file=\'{path}\')'
        " PARSER STV_ShpParser();"
    )
    executeSQL(query, title="Ingesting the data.")
    print(f'The table "{schema}"."{table_name}" has been successfully created.')
    from verticapy import vDataFrame

    return vDataFrame(table_name, schema=schema)


@save_verticapy_logs
def readSQL(query: str, time_on: bool = False, limit: int = 100):
    """
    Returns the result of a SQL query as a tablesample object.

    Parameters
    ----------
    query: str
        SQL Query.
    time_on: bool, optional
        If set to True, displays the query elapsed time.
    limit: int, optional
        Maximum number of elements to display.

    Returns
    -------
    tablesample
        Result of the query.
    """
    while len(query) > 0 and query[-1] in (";", " "):
        query = query[:-1]
    if vp.OPTIONS["count_on"]:
        count = executeSQL(
            f"""SELECT 
                    /*+LABEL('utilities.readSQL')*/ COUNT(*) 
                FROM ({query}) VERTICAPY_SUBTABLE""",
            method="fetchfirstelem",
            print_time_sql=False,
        )
    else:
        count = -1
    sql_on_init = vp.OPTIONS["sql_on"]
    time_on_init = vp.OPTIONS["time_on"]
    try:
        vp.OPTIONS["time_on"] = time_on
        vp.OPTIONS["sql_on"] = False
        try:
            result = to_tablesample(f"{query} LIMIT {limit}")
        except:
            result = to_tablesample(query)
    finally:
        vp.OPTIONS["time_on"] = time_on_init
        vp.OPTIONS["sql_on"] = sql_on_init
    result.count = count
    if vp.OPTIONS["percent_bar"]:
        vdf = vDataFrameSQL(f"({query}) VERTICAPY_SUBTABLE")
        percent = vdf.agg(["percent"]).transpose().values
        for column in result.values:
            result.dtype[column] = vdf[column].ctype()
            result.percent[column] = percent[vdf.format_colnames(column)][0]
    return result


def save_to_query_profile(
    name: str,
    path: str = "",
    json_dict: dict = {},
    query_label: str = "verticapy_json",
    return_query: bool = False,
    add_identifier: bool = True,
):
    """
Saves information about the specified VerticaPy method to the QUERY_PROFILES 
table in the Vertica database. It is used to collect usage statistics on 
methods and their parameters. This function generates a JSON string.

Parameters
----------
name: str
    Name of the method.
path: str, optional
    Path to the function or method.
json_dict: dict, optional
    Dictionary of the different parameters to store.
query_label: str, optional
    Name to give to the identifier in the query profile table. If 
    unspecified, the name of the method is used.
return_query: bool, optional
    If set to True, the query is returned.
add_identifier: bool, optional
    If set to True, the VerticaPy identifier is added to the generated json.

Returns
-------
bool
    True if the operation succeeded, False otherwise.
    """
    if not (vp.OPTIONS["save_query_profile"]) or (
        isinstance(vp.OPTIONS["save_query_profile"], list)
        and name not in vp.OPTIONS["save_query_profile"]
    ):
        return False
    try:

        def dict_to_json_string(
            name: str = "",
            path: str = "",
            json_dict: dict = {},
            add_identifier: bool = False,
        ):
            from verticapy import vDataFrame
            from verticapy.learn.vmodel import vModel

            json = "{"
            if name:
                json += f'"verticapy_fname": "{name}", '
            if path:
                json += f'"verticapy_fpath": "{path}", '
            if add_identifier:
                json += f'"verticapy_id": "{vp.OPTIONS["identifier"]}", '
            for key in json_dict:
                json += f'"{key}": '
                if isinstance(json_dict[key], bool):
                    json += "true" if json_dict[key] else "false"
                elif isinstance(json_dict[key], (float, int)):
                    json += str(json_dict[key])
                elif json_dict[key] is None:
                    json += "null"
                elif isinstance(json_dict[key], vDataFrame):
                    json_dict_str = json_dict[key].__genSQL__().replace('"', '\\"')
                    json += f'"{json_dict_str}"'
                elif isinstance(json_dict[key], vModel):
                    json += f'"{json_dict[key].type}"'
                elif isinstance(json_dict[key], dict):
                    json += dict_to_json_string(json_dict=json_dict[key])
                elif isinstance(json_dict[key], list):
                    json_dict_str = ";".join([str(item) for item in json_dict[key]])
                    json += f'"{json_dict_str}"'
                else:
                    json_dict_str = str(json_dict[key]).replace('"', '\\"')
                    json += f'"{json_dict_str}"'
                json += ", "
            json = json[:-2] + "}"
            return json

        query_label_str = query_label.replace("'", "''")
        dict_to_json_string_str = dict_to_json_string(
            name, path, json_dict, add_identifier
        ).replace("'", "''")
        query = f"SELECT /*+LABEL('{query_label_str}')*/ '{dict_to_json_string_str}'"
        if return_query:
            return query
        executeSQL(
            query=query,
            title="Sending query to save the information in query profile table.",
            print_time_sql=False,
        )
        return True
    except:
        return False


class tablesample:
    """
The tablesample is the transition from 'Big Data' to 'Small Data'. 
This object allows you to conveniently display your results without any  
dependencies on any other module. It stores the aggregated result in memory
which can then be transformed into a pandas.DataFrame or vDataFrame.

Parameters
----------
values: dict, optional
	Dictionary of columns (keys) and their values. The dictionary must be
	similar to the following one:
	{"column1": [val1, ..., valm], ... "columnk": [val1, ..., valm]}
dtype: dict, optional
	Columns data types.
count: int, optional
	Number of elements if we had to load the entire dataset. It is used 
	only for rendering purposes.
offset: int, optional
	Number of elements that were skipped if we had to load the entire
	dataset. It is used only for rendering purposes.
percent: dict, optional
    Dictionary of missing values (Used to display the percent bars)
max_columns: int, optional
    Maximum number of columns to display.

Attributes
----------
The tablesample attributes are the same as the parameters.
	"""

    #
    # Special Methods
    #

    def __init__(
        self,
        values: dict = {},
        dtype: dict = {},
        count: int = 0,
        offset: int = 0,
        percent: dict = {},
        max_columns: int = -1,
    ):
        self.values = values
        self.dtype = dtype
        self.count = count
        self.offset = offset
        self.percent = percent
        self.max_columns = max_columns
        for column in values:
            if column not in dtype:
                self.dtype[column] = "undefined"

    def __iter__(self):
        return (elem for elem in self.values)

    def __getitem__(self, key):
        return find_val_in_dict(key, self.values)

    def _repr_html_(self, interactive=False):
        if len(self.values) == 0:
            return ""
        n = len(self.values)
        dtype = self.dtype
        max_columns = (
            self.max_columns if self.max_columns > 0 else vp.OPTIONS["max_columns"]
        )
        if n < max_columns:
            data_columns = [[column] + self.values[column] for column in self.values]
        else:
            k = int(max_columns / 2)
            columns = [elem for elem in self.values]
            values0 = [[columns[i]] + self.values[columns[i]] for i in range(k)]
            values1 = [["..." for i in range(len(self.values[columns[0]]) + 1)]]
            values2 = [
                [columns[i]] + self.values[columns[i]]
                for i in range(n - max_columns + k, n)
            ]
            data_columns = values0 + values1 + values2
            dtype["..."] = "undefined"
        percent = self.percent
        for elem in self.values:
            if elem not in percent and (elem != "index"):
                percent = {}
                break
        formatted_text = ""
        # get interactive table if condition true
        if vp.OPTIONS["interactive"] or interactive:
            formatted_text = datatables_repr(
                data_columns,
                repeat_first_column=("index" in self.values),
                offset=self.offset,
                dtype=dtype,
            )
        else:
            formatted_text = print_table(
                data_columns,
                is_finished=(self.count <= len(data_columns[0]) + self.offset),
                offset=self.offset,
                repeat_first_column=("index" in self.values),
                return_html=True,
                dtype=dtype,
                percent=percent,
            )
        if vp.OPTIONS["footer_on"]:
            formatted_text += '<div style="margin-top:6px; font-size:1.02em">'
            if (self.offset == 0) and (len(data_columns[0]) - 1 == self.count):
                rows = self.count
            else:
                start, end = self.offset + 1, len(data_columns[0]) - 1 + self.offset
                if start > end:
                    rows = f"0 of {self.count}" if (self.count > 0) else "0"
                else:
                    of = f" of {self.count}" if (self.count > 0) else ""
                    rows = f"{start}-{end}{of}"
            if len(self.values) == 1:
                column = list(self.values.keys())[0]
                if self.offset > self.count:
                    formatted_text += (
                        f"<b>Column:</b> {column} | "
                        f"<b>Type:</b> {self.dtype[column]}"
                    )
                else:
                    formatted_text += (
                        f"<b>Rows:</b> {rows} | <b>Column:</b> {column} "
                        f"| <b>Type:</b> {self.dtype[column]}"
                    )
            else:
                if self.offset > self.count:
                    formatted_text += f"<b>Columns:</b> {n}"
                else:
                    formatted_text += f"<b>Rows:</b> {rows} | <b>Columns:</b> {n}"
            formatted_text += "</div>"
        return formatted_text

    def __repr__(self):
        if len(self.values) == 0:
            return ""
        n = len(self.values)
        dtype = self.dtype
        max_columns = (
            self.max_columns if self.max_columns > 0 else vp.OPTIONS["max_columns"]
        )
        if n < max_columns:
            data_columns = [[column] + self.values[column] for column in self.values]
        else:
            k = int(max_columns / 2)
            columns = [elem for elem in self.values]
            values0 = [[columns[i]] + self.values[columns[i]] for i in range(k)]
            values1 = [["..." for i in range(len(self.values[columns[0]]) + 1)]]
            values2 = [
                [columns[i]] + self.values[columns[i]]
                for i in range(n - max_columns + k, n)
            ]
            data_columns = values0 + values1 + values2
            dtype["..."] = "undefined"
        formatted_text = print_table(
            data_columns,
            is_finished=(self.count <= len(data_columns[0]) + self.offset),
            offset=self.offset,
            repeat_first_column=("index" in self.values),
            return_html=False,
            dtype=dtype,
            percent=self.percent,
        )
        start, end = self.offset + 1, len(data_columns[0]) - 1 + self.offset
        if (self.offset == 0) and (len(data_columns[0]) - 1 == self.count):
            rows = self.count
        else:
            if start > end:
                rows = f"0 of {self.count}" if (self.count > 0) else "0"
            else:
                count_str = f" of {self.count}" if (self.count > 0) else ""
                rows = f"{start}-{end}{count_str}"
        if len(self.values) == 1:
            column = list(self.values.keys())[0]
            if self.offset > self.count:
                formatted_text += f"Column: {column} | Type: {self.dtype[column]}"
            else:
                formatted_text += (
                    f"Rows: {rows} | Column: {column} | Type: {self.dtype[column]}"
                )
        else:
            if self.offset > self.count:
                formatted_text += f"Columns: {n}"
            else:
                formatted_text += f"Rows: {rows} | Columns: {n}"
        return formatted_text

    #
    # Methods
    #

    def append(self, tbs):
        """
        Appends the input tablesample to a target tablesample.

        Parameters
        ----------
        tbs: tablesample
            Tablesample to append.

        Returns
        -------
        tablesample
            self
        """
        assert isinstance(tbs, tablesample), ParameterError(
            "tablesamples can only be appended to another tablesample."
        )
        n1, n2 = self.shape()[0], tbs.shape()[0]
        assert n1 == n2, ParameterError(
            "The input and target tablesamples must have the same number of columns."
            f" Expected {n1}, Found {n2}."
        )
        cols1, cols2 = [col for col in self.values], [col for col in tbs.values]
        for idx in range(n1):
            self.values[cols1[idx]] += tbs.values[cols2[idx]]
        return self

    def decimal_to_float(self):
        """
    Converts all the tablesample's decimals to floats.

    Returns
    -------
    tablesample
        self
        """
        for elem in self.values:
            if elem != "index":
                for i in range(len(self.values[elem])):
                    if isinstance(self.values[elem][i], decimal.Decimal):
                        self.values[elem][i] = float(self.values[elem][i])
        return self

    def merge(self, tbs):
        """
        Merges the input tablesample to a target tablesample.

        Parameters
        ----------
        tbs: tablesample
            Tablesample to merge.

        Returns
        -------
        tablesample
            self
        """
        assert isinstance(tbs, tablesample), ParameterError(
            "tablesamples can only be merged with other tablesamples."
        )
        n1, n2 = self.shape()[1], tbs.shape()[1]
        assert n1 == n2, ParameterError(
            "The input and target tablesamples must have the same number of rows."
            f" Expected {n1}, Found {n2}."
        )
        for col in tbs.values:
            if col != "index":
                if col not in self.values:
                    self.values[col] = []
                self.values[col] += tbs.values[col]
        return self

    def shape(self):
        """
    Computes the tablesample shape.

    Returns
    -------
    tuple
        (number of columns, number of rows)
        """
        cols = [col for col in self.values]
        n, m = len(cols), len(self.values[cols[0]])
        return (n, m)

    def sort(self, column: str, desc: bool = False):
        """
        Sorts the tablesample using the input column.

        Parameters
        ----------
        column: str, optional
            Column used to sort the data.
        desc: bool, optional
            If set to True, the result is sorted in descending order.

        Returns
        -------
        tablesample
            self
        """
        column = column.replace('"', "").lower()
        columns = [col for col in self.values]
        idx = None
        for i, col in enumerate(columns):
            col_tmp = col.replace('"', "").lower()
            if column == col_tmp:
                idx = i
                column = col
        if idx is None:
            raise MissingColumn(f"The Column '{column}' doesn't exist.")
        n, sort = len(self[column]), []
        for i in range(n):
            tmp_list = []
            for col in columns:
                tmp_list += [self[col][i]]
            sort += [tmp_list]
        sort.sort(key=lambda tup: tup[idx], reverse=desc)
        for i, col in enumerate(columns):
            self.values[col] = [sort[j][i] for j in range(n)]
        return self

    def transpose(self):
        """
	Transposes the tablesample.

 	Returns
 	-------
 	tablesample
 		transposed tablesample
		"""
        index = [column for column in self.values]
        first_item = list(self.values.keys())[0]
        columns = [[] for i in range(len(self.values[first_item]))]
        for column in self.values:
            for idx, item in enumerate(self.values[column]):
                try:
                    columns[idx] += [item]
                except:
                    pass
        columns = [index] + columns
        values = {}
        for item in columns:
            values[item[0]] = item[1 : len(item)]
        return tablesample(values, self.dtype, self.count, self.offset, self.percent)

    def to_list(self):
        """
    Converts the tablesample to a list.

    Returns
    -------
    list
        Python list.
        """
        result = []
        all_cols = [elem for elem in self.values]
        if all_cols == []:
            return []
        for i in range(len(self.values[all_cols[0]])):
            result_tmp = []
            for elem in self.values:
                if elem != "index":
                    result_tmp += [self.values[elem][i]]
            result += [result_tmp]
        return result

    def to_numpy(self):
        """
    Converts the tablesample to a numpy array.

    Returns
    -------
    numpy.array
        Numpy Array.
        """
        import numpy as np

        return np.array(self.to_list())

    def to_pandas(self):
        """
	Converts the tablesample to a pandas DataFrame.

 	Returns
 	-------
 	pandas.DataFrame
 		pandas DataFrame of the tablesample.

	See Also
	--------
	tablesample.to_sql : Generates the SQL query associated to the tablesample.
	tablesample.to_vdf : Converts the tablesample to vDataFrame.
		"""
        if "index" in self.values:
            df = pd.DataFrame(data=self.values, index=self.values["index"])
            return df.drop(columns=["index"])
        else:
            return pd.DataFrame(data=self.values)

    def to_sql(self):
        """
    Generates the SQL query associated to the tablesample.

    Returns
    -------
    str
        SQL query associated to the tablesample.

    See Also
    --------
    tablesample.to_pandas : Converts the tablesample to a pandas DataFrame.
    tablesample.to_sql    : Generates the SQL query associated to the tablesample.
        """

        def get_correct_format_and_cast(val):
            if isinstance(val, str):
                val = "'" + val.replace("'", "''") + "'"
            elif val == None:
                val = "NULL"
            elif isinstance(val, bytes):
                val = str(val)[2:-1]
                val = f"'{val}'::binary({len(val)})"
            elif isinstance(val, datetime.datetime):
                val = f"'{val}'::datetime"
            elif isinstance(val, datetime.date):
                val = f"'{val}'::date"
            elif isinstance(val, datetime.timedelta):
                val = f"'{val}'::interval"
            elif isinstance(val, datetime.time):
                val = f"'{val}'::time"
            elif isinstance(val, datetime.timezone):
                val = f"'{val}'::timestamptz"
            elif isinstance(val, (np.ndarray, list)):
                vertica_version(condition=[10, 0, 0])
                val = f"""
                ARRAY[
                    {", ".join([str(get_correct_format_and_cast(k)) for k in val])}
                     ]"""
            elif isinstance(val, dict):
                vertica_version(condition=[11, 0, 0])
                all_elems = [
                    f"{get_correct_format_and_cast(val[k])} AS {k}" for k in val
                ]
                val = ", ".join(all_elems)
                val = f"ROW({val})"
            try:
                if math.isnan(val):
                    val = "NULL"
            except:
                pass
            return val

        sql = []
        n = len(self.values[list(self.values.keys())[0]])
        for i in range(n):
            row = []
            for column in self.values:
                val = get_correct_format_and_cast(self.values[column][i])
                column_str = '"' + column.replace('"', "") + '"'
                row += [f"{val} AS {column_str}"]
            sql += [f"(SELECT {', '.join(row)})"]
        sql = " UNION ALL ".join(sql)
        return sql

    def to_vdf(self):
        """
	Converts the tablesample to a vDataFrame.

 	Returns
 	-------
 	vDataFrame
 		vDataFrame of the tablesample.

	See Also
	--------
	tablesample.to_pandas : Converts the tablesample to a pandas DataFrame.
	tablesample.to_sql    : Generates the SQL query associated to the tablesample.
		"""
        return vDataFrameSQL(f"({self.to_sql()}) sql_relation")


def to_tablesample(
    query: Union[str, str_sql],
    title: str = "",
    max_columns: int = -1,
    sql_push_ext: bool = False,
    symbol: str = "$",
):
    """
	Returns the result of a SQL query as a tablesample object.

	Parameters
	----------
	query: str, optional
		SQL Query.
	title: str, optional
		Query title when the query is displayed.
    max_columns: int, optional
        Maximum number of columns to display.
    sql_push_ext: bool, optional
        If set to True, the entire query is pushed to the external table. 
        This can increase performance but might increase the error rate. 
        For instance, some DBs might not support the same SQL as Vertica.
    symbol: str, optional
        One of the following:
        "$", "€", "£", "%", "@", "&", "§", "%", "?", "!"
        Symbol used to identify the external connection.
        See the connect.set_external_connection function for more information.

 	Returns
 	-------
 	tablesample
 		Result of the query.

	See Also
	--------
	tablesample : Object in memory created for rendering purposes.
	"""
    if vp.OPTIONS["sql_on"]:
        print_query(query, title)
    start_time = time.time()
    cursor = executeSQL(
        query, print_time_sql=False, sql_push_ext=sql_push_ext, symbol=symbol
    )
    description, dtype = cursor.description, {}
    for elem in description:
        dtype[elem[0]] = get_final_vertica_type(
            type_name=elem.type_name,
            display_size=elem[2],
            precision=elem[4],
            scale=elem[5],
        )
    elapsed_time = time.time() - start_time
    if vp.OPTIONS["time_on"]:
        print_time(elapsed_time)
    result = cursor.fetchall()
    columns = [column[0] for column in cursor.description]
    data_columns = [[item] for item in columns]
    data = [item for item in result]
    for row in data:
        for idx, val in enumerate(row):
            data_columns[idx] += [val]
    values = {}
    for column in data_columns:
        values[column[0]] = column[1 : len(column)]
    return tablesample(
        values=values, dtype=dtype, max_columns=max_columns,
    ).decimal_to_float()


def vDataFrameSQL(
    relation: str,
    name: str = "VDF",
    schema: str = "public",
    history: list = [],
    saving: list = [],
    vdf=None,
):
    """
Creates a vDataFrame based on a customized relation.

Parameters
----------
relation: str
	Relation. You can also specify a customized relation, 
    but you must enclose it with an alias. For example "(SELECT 1) x" is 
    correct whereas "(SELECT 1)" and "SELECT 1" are incorrect.
name: str, optional
	Name of the vDataFrame. It is used only when displaying the vDataFrame.
schema: str, optional
	Relation schema. It can be to use to be less ambiguous and allow to 
    create schema and relation name with dots '.' inside.
history: list, optional
	vDataFrame history (user modifications). To use to keep the previous 
    vDataFrame history.
saving: list, optional
	List to use to reconstruct the vDataFrame from previous transformations.

Returns
-------
vDataFrame
	The vDataFrame associated to the input relation.
	"""
    # Initialization
    from verticapy import vDataFrame
    from .flex import isvmap

    if isinstance(vdf, vDataFrame):
        external = vdf._VERTICAPY_VARIABLES_["external"]
        symbol = vdf._VERTICAPY_VARIABLES_["symbol"]
        sql_push_ext = vdf._VERTICAPY_VARIABLES_["sql_push_ext"]
        vdf.__init__("", empty=True)
        vdf._VERTICAPY_VARIABLES_["external"] = external
        vdf._VERTICAPY_VARIABLES_["symbol"] = symbol
        vdf._VERTICAPY_VARIABLES_["sql_push_ext"] = sql_push_ext
    else:
        vdf = vDataFrame("", empty=True)
    vdf._VERTICAPY_VARIABLES_["input_relation"] = name
    vdf._VERTICAPY_VARIABLES_["main_relation"] = relation
    vdf._VERTICAPY_VARIABLES_["schema"] = schema
    vdf._VERTICAPY_VARIABLES_["where"] = []
    vdf._VERTICAPY_VARIABLES_["order_by"] = {}
    vdf._VERTICAPY_VARIABLES_["exclude_columns"] = []
    vdf._VERTICAPY_VARIABLES_["history"] = history
    vdf._VERTICAPY_VARIABLES_["saving"] = saving
    dtypes = get_data_types(f"SELECT * FROM {relation} LIMIT 0")
    vdf._VERTICAPY_VARIABLES_["columns"] = ['"' + item[0] + '"' for item in dtypes]

    # Creating the vColumns
    for column, ctype in dtypes:
        if '"' in column:
            column_str = column.replace('"', "_")
            warning_message = (
                f'A double quote " was found in the column {column}, its '
                f"alias was changed using underscores '_' to {column_str}"
            )
            warnings.warn(warning_message, Warning)
        from verticapy.core.vcolumn import vColumn

        column_name = '"' + column.replace('"', "_") + '"'
        category = get_category_from_vertica_type(ctype)
        if (ctype.lower()[0:12] in ("long varbina", "long varchar")) and (
            isvmap(expr=relation, column=column,)
        ):
            category = "vmap"
            ctype = "VMAP(" + "(".join(ctype.split("(")[1:]) if "(" in ctype else "VMAP"
        new_vColumn = vColumn(
            column_name,
            parent=vdf,
            transformations=[(quote_ident(column), ctype, category,)],
        )
        setattr(vdf, column_name, new_vColumn)
        setattr(vdf, column_name[1:-1], new_vColumn)
        new_vColumn.init = False

    return vdf


vdf_from_relation = vDataFrameSQL


def vertica_version(condition: list = []):
    """
Returns the Vertica Version.

Parameters
----------
condition: list, optional
    List of the minimal version information. If the current version is not
    greater or equal to this one, it will raise an error.

Returns
-------
list
    List containing the version information.
    [MAJOR, MINOR, PATCH, POST]
    """
    # -#
    if condition:
        condition = condition + [0 for elem in range(4 - len(condition))]
    if not (vp.OPTIONS["vertica_version"]):
        current_version = executeSQL(
            "SELECT /*+LABEL('utilities.version')*/ version();",
            title="Getting the version.",
            method="fetchfirstelem",
        ).split("Vertica Analytic Database v")[1]
        current_version = current_version.split(".")
        result = []
        try:
            result += [int(current_version[0])]
            result += [int(current_version[1])]
            result += [int(current_version[2].split("-")[0])]
            result += [int(current_version[2].split("-")[1])]
        except:
            pass
        vp.OPTIONS["vertica_version"] = result
    else:
        result = vp.OPTIONS["vertica_version"]
    if condition:
        if condition[0] < result[0]:
            test = True
        elif condition[0] == result[0]:
            if condition[1] < result[1]:
                test = True
            elif condition[1] == result[1]:
                if condition[2] <= result[2]:
                    test = True
                else:
                    test = False
            else:
                test = False
        else:
            test = False
        if not (test):
            v0, v1, v2 = result[0], result[1], str(result[2]).split("-")[0]
            v = ".".join([str(c) for c in condition[:3]])
            raise VersionError(
                (
                    "This Function is not available for Vertica version "
                    f"{v0}.{v1}.{v2}.\nPlease upgrade your Vertica "
                    f"version to at least {v} to get this functionality."
                )
            )
    return result
