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
import random, time, shutil, re, decimal, warnings, pickle, datetime, math, os, copy, sys
from collections.abc import Iterable
from itertools import combinations_with_replacement
from typing import Union, Literal

pickle.DEFAULT_PROTOCOL = 4

# Other modules
import multiprocessing
from tqdm.auto import tqdm
import pandas as pd
import numpy as np
import scipy.stats as scipy_st
import scipy.special as scipy_special
from matplotlib.lines import Line2D

# Geopandas - Optional
try:
    from geopandas import GeoDataFrame
    from shapely import wkt

    GEOPANDAS_ON = True
except:
    GEOPANDAS_ON = False

# Jupyter - Optional
try:
    from IPython.display import HTML, display
except:
    pass

# VerticaPy Modules
import verticapy as vp
import verticapy.plotting._matplotlib as plt
import verticapy.utilities as util
import verticapy.learn.memmodel as mem
from verticapy.plotting._highcharts import hchart_from_vdf
from verticapy.utils._decorators import (
    save_verticapy_logs,
    check_minimum_version,
)
from verticapy.errors import (
    ConnectionError,
    EmptyParameter,
    FunctionError,
    MissingColumn,
    MissingRelation,
    ParameterError,
    ParsingError,
    QueryError,
)
from verticapy.utils._toolbox import *
from verticapy.plotting._colors import gen_colors, gen_cmap

###
#                                           _____
#   _______    ______ ____________    ____  \    \
#   \      |  |      |\           \   \   \ /____/|
#    |     /  /     /| \           \   |  |/_____|/
#    |\    \  \    |/   |    /\     |  |  |    ___
#    \ \    \ |    |    |   |  |    |  |   \__/   \
#     \|     \|    |    |    \/     | /      /\___/|
#      |\         /|   /           /|/      /| | | |
#      | \_______/ |  /___________/ ||_____| /\|_|/
#       \ |     | /  |           | / |     |/
#        \|_____|/   |___________|/  |_____|
#


class vDataFrame:
    """
An object that records all user modifications, allowing users to 
manipulate the relation without mutating the underlying data in Vertica. 
When changes are made, the vDataFrame queries the Vertica database, which 
aggregates and returns the final result. The vDataFrame creates, for each ]
column of the relation, a Virtual Column (vColumn) that stores the column 
alias an all user transformations. 

Parameters
----------
input_relation: str / tablesample / pandas.DataFrame 
                   / list / numpy.ndarray / dict, optional
    If the input_relation is of type str, it must represent the relation 
    (view, table, or temporary table) used to create the object. 
    To get a specific schema relation, your string must include both the 
    relation and schema: 'schema.relation' or '"schema"."relation"'. 
    Alternatively, you can use the 'schema' parameter, in which case 
    the input_relation must exclude the schema name.
    If it is a pandas.DataFrame, a temporary local table is created.
    Otherwise, the vDataFrame is created using the generated SQL code 
    of multiple UNIONs. 
columns: str / list, optional
    List of column names. Only used when input_relation is an array-like type.
usecols: str / list, optional
    List of columns to use to create the object. As Vertica is a columnar 
    DB including less columns makes the process faster. Do not hesitate 
    to not include useless columns.
schema: str, optional
    The schema of the relation. Specifying a schema allows you to specify a 
    table within a particular schema, or to specify a schema and relation name 
    that contain period '.' characters. If specified, the input_relation cannot 
    include a schema.
sql: str, optional
    A SQL query used to create the vDataFrame. If specified, the parameter 
    'input_relation' must be empty.
external: bool, optional
    A boolean to indicate whether it is an external table. If set to True, a
    Connection Identifier Database must be defined.
    See the connect.set_external_connection function for more information.
symbol: str, optional
    One of the following:
    "$", "€", "£", "%", "@", "&", "§", "?", "!"
    Symbol used to identify the external connection.
    See the connect.set_external_connection function for more information.
sql_push_ext: bool, optional
    If set to True, the external vDataFrame attempts to push the entire query 
    to the external table (only DQL statements - SELECT; for other statements,
    use SQL Magic directly). This can increase performance but might increase 
    the error rate. For instance, some DBs might not support the same SQL as 
    Vertica.
empty: bool, optional
    If set to True, the vDataFrame will be empty. You can use this to create 
    a custom vDataFrame and bypass the initialization check.

Attributes
----------
_VERTICAPY_VARIABLES_: dict
    Dictionary containing all vDataFrame attributes.
        allcols_ind, int      : Integer, used to optimize the SQL 
                                code generation.
        columns, list         : List of the vColumn names.
        count, int            : Number of elements of the vDataFrame 
                                (catalog).
        exclude_columns, list : vColumns to exclude from the final 
                                relation.
        external, bool        : True if it is an External vDataFrame.
        history, list         : vDataFrame history (user modifications).
        input_relation, str   : Name of the vDataFrame.
        isflex, bool          : True if it is a Flex vDataFrame.
        main_relation, str    : Relation to use to build the vDataFrame 
                                (first floor).
        order_by, dict        : Dictionary of all rules to sort the 
                                vDataFrame.
        saving, list          : List used to reconstruct the 
                                vDataFrame.
        schema, str           : Schema of the input relation.
        where, list           : List of all rules to filter the 
                                vDataFrame.
        max_colums, int       : Maximum number of columns to display.
        max_rows, int         : Maximum number of rows to display.
vColumns : vColumn
    Each vColumn of the vDataFrame is accessible by by specifying its name 
    between brackets. For example, to access the vColumn "myVC": 
    vDataFrame["myVC"].
    """

    #
    # Special Methods
    #

    @save_verticapy_logs
    def __init__(
        self,
        input_relation: Union[
            str, pd.DataFrame, np.ndarray, list, util.tablesample, dict
        ] = "",
        columns: Union[str, list] = [],
        usecols: Union[str, list] = [],
        schema: str = "",
        sql: str = "",
        external: bool = False,
        symbol: Literal[tuple(vp.SPECIAL_SYMBOLS)] = "$",
        sql_push_ext: bool = True,
        empty: bool = False,
    ):
        # Initialization
        if not (isinstance(input_relation, (pd.DataFrame, np.ndarray))):
            assert input_relation or sql or empty, ParameterError(
                "The parameters 'input_relation' and 'sql' cannot both be empty."
            )
            assert not (input_relation) or not (sql) or empty, ParameterError(
                "Either 'sql' or 'input_relation' must be empty."
            )
        else:
            assert not (sql) or empty, ParameterError(
                "Either 'sql' or 'input_relation' must be empty."
            )
        assert isinstance(input_relation, str) or not (schema), ParameterError(
            "schema must be empty when the 'input_relation' is not of type str."
        )
        assert not (sql) or not (schema), ParameterError(
            "schema must be empty when the parameter 'sql' is not empty."
        )
        if isinstance(usecols, str):
            usecols = [usecols]
        if isinstance(columns, str):
            columns = [columns]

        if external:
            if input_relation:
                assert isinstance(input_relation, str), ParameterError(
                    "Parameter 'input_relation' must be a string when using "
                    "external tables."
                )
                if schema:
                    relation = f"{schema}.{input_relation}"
                else:
                    relation = str(input_relation)
                cols = ", ".join(usecols) if usecols else "*"
                query = f"SELECT {cols} FROM {input_relation}"

            else:
                query = sql

            if symbol in vp.OPTIONS["external_connection"]:
                sql = symbol * 3 + query + symbol * 3

            else:
                raise ConnectionError(
                    "No corresponding Connection Identifier Database is "
                    f"defined (Using the symbol '{symbol}'). Use the "
                    "function connect.set_external_connection to set "
                    "one with the correct symbol."
                )

        self._VERTICAPY_VARIABLES_ = {
            "count": -1,
            "allcols_ind": -1,
            "max_rows": -1,
            "max_columns": -1,
            "sql_magic_result": False,
            "isflex": False,
            "external": external,
            "symbol": symbol,
            "sql_push_ext": external and sql_push_ext,
        }

        if isinstance(input_relation, (util.tablesample, list, np.ndarray, dict)):

            tb = input_relation

            if isinstance(input_relation, (list, np.ndarray)):

                if isinstance(input_relation, list):
                    input_relation = np.array(input_relation)

                assert len(input_relation.shape) == 2, ParameterError(
                    "vDataFrames can only be created with two-dimensional objects."
                )

                tb = {}
                nb_cols = len(input_relation[0])
                for idx in range(nb_cols):
                    col_name = columns[idx] if idx < len(columns) else f"col{idx}"
                    tb[col_name] = [l[idx] for l in input_relation]
                tb = util.tablesample(tb)

            elif isinstance(input_relation, dict):

                tb = util.tablesample(tb)

            if usecols:
                tb_final = {}
                for col in usecols:
                    tb_final[col] = tb[col]
                tb = util.tablesample(tb_final)

            relation = f"({tb.to_sql()}) sql_relation"
            util.vDataFrameSQL(relation, name="", schema="", vdf=self)

        elif isinstance(input_relation, pd.DataFrame):

            if usecols:
                df = util.pandas_to_vertica(input_relation[usecols])
            else:
                df = util.pandas_to_vertica(input_relation)
            schema = df._VERTICAPY_VARIABLES_["schema"]
            input_relation = df._VERTICAPY_VARIABLES_["input_relation"]
            self.__init__(input_relation=input_relation, schema=schema)

        elif sql:

            # Cleaning the Query
            sql_tmp = clean_query(sql)
            sql_tmp = f"({sql_tmp}) VERTICAPY_SUBTABLE"

            # Filtering some columns
            if usecols:
                usecols_tmp = ", ".join([quote_ident(col) for col in usecols])
                sql_tmp = f"(SELECT {usecols_tmp} FROM {sql_tmp}) VERTICAPY_SUBTABLE"

            # vDataFrame of the Query
            util.vDataFrameSQL(sql_tmp, name="", schema="", vdf=self)

        elif not (empty):

            if not (schema):
                schema, input_relation = schema_relation(input_relation)
            self._VERTICAPY_VARIABLES_["schema"] = schema.replace('"', "")
            self._VERTICAPY_VARIABLES_["input_relation"] = input_relation.replace(
                '"', ""
            )
            table_name = self._VERTICAPY_VARIABLES_["input_relation"].replace("'", "''")
            schema = self._VERTICAPY_VARIABLES_["schema"].replace("'", "''")
            isflex = util.isflextable(table_name=table_name, schema=schema)
            self._VERTICAPY_VARIABLES_["isflex"] = isflex
            if isflex:
                columns_dtype = util.compute_flextable_keys(
                    flex_name=f'"{schema}".{table_name}', usecols=usecols
                )
            else:
                columns_dtype = util.get_data_types(
                    table_name=table_name, schema=schema, usecols=usecols
                )
            columns_dtype = [(str(dt[0]), str(dt[1])) for dt in columns_dtype]
            columns = ['"' + dt[0].replace('"', "_") + '"' for dt in columns_dtype]
            if not (usecols):
                self._VERTICAPY_VARIABLES_["allcols_ind"] = len(columns)
            assert columns != [], MissingRelation(
                f"No table or views '{self._VERTICAPY_VARIABLES_['input_relation']}' found."
            )
            self._VERTICAPY_VARIABLES_["columns"] = [col for col in columns]
            for col_dtype in columns_dtype:
                column, dtype = col_dtype[0], col_dtype[1]
                if '"' in column:
                    column_str = column.replace('"', "_")
                    warning_message = (
                        f'A double quote " was found in the column {column}, '
                        f"its alias was changed using underscores '_' to {column_str}."
                    )
                    warnings.warn(warning_message, Warning)
                category = get_category_from_vertica_type(dtype)
                if (dtype.lower()[0:12] in ("long varbina", "long varchar")) and (
                    isflex
                    or util.isvmap(
                        expr=format_schema_table(schema, table_name), column=column,
                    )
                ):
                    category = "vmap"
                    dtype = (
                        "VMAP(" + "(".join(dtype.split("(")[1:])
                        if "(" in dtype
                        else "VMAP"
                    )
                column_name = '"' + column.replace('"', "_") + '"'
                new_vColumn = vp.vColumn(
                    column_name,
                    parent=self,
                    transformations=[(quote_ident(column), dtype, category,)],
                )
                setattr(self, column_name, new_vColumn)
                setattr(self, column_name[1:-1], new_vColumn)
                new_vColumn.init = False
            other_parameters = {
                "exclude_columns": [],
                "where": [],
                "order_by": {},
                "history": [],
                "saving": [],
                "main_relation": format_schema_table(
                    self._VERTICAPY_VARIABLES_["schema"],
                    self._VERTICAPY_VARIABLES_["input_relation"],
                ),
            }
            self._VERTICAPY_VARIABLES_ = {
                **self._VERTICAPY_VARIABLES_,
                **other_parameters,
            }

    def __abs__(self):
        return self.copy().abs()

    def __ceil__(self, n):
        vdf = self.copy()
        columns = vdf.numcol()
        for elem in columns:
            if vdf[elem].category() == "float":
                vdf[elem].apply_fun(func="ceil", x=n)
        return vdf

    def __floor__(self, n):
        vdf = self.copy()
        columns = vdf.numcol()
        for elem in columns:
            if vdf[elem].category() == "float":
                vdf[elem].apply_fun(func="floor", x=n)
        return vdf

    def __getitem__(self, index):

        if isinstance(index, slice):
            assert index.step in (1, None), ValueError(
                "vDataFrame doesn't allow slicing having steps different than 1."
            )
            index_stop = index.stop
            index_start = index.start
            if not (isinstance(index_start, int)):
                index_start = 0
            if index_start < 0:
                index_start += self.shape()[0]
            if isinstance(index_stop, int):
                if index_stop < 0:
                    index_stop += self.shape()[0]
                limit = index_stop - index_start
                if limit <= 0:
                    limit = 0
                limit = f" LIMIT {limit}"
            else:
                limit = ""
            query = f"""
                (SELECT * 
                FROM {self.__genSQL__()}
                {self.__get_last_order_by__()} 
                OFFSET {index_start}{limit}) VERTICAPY_SUBTABLE"""
            return util.vDataFrameSQL(query)

        elif isinstance(index, int):
            columns = self.get_columns()
            for idx, elem in enumerate(columns):
                if self[elem].category() == "float":
                    columns[idx] = f"{elem}::float"
            if index < 0:
                index += self.shape()[0]
            return executeSQL(
                query=f"""
                    SELECT /*+LABEL('vDataframe.__getitem__')*/ 
                        {', '.join(columns)} 
                    FROM {self.__genSQL__()}
                    {self.__get_last_order_by__()} 
                    OFFSET {index} LIMIT 1""",
                title="Getting the vDataFrame element.",
                method="fetchrow",
                sql_push_ext=self._VERTICAPY_VARIABLES_["sql_push_ext"],
                symbol=self._VERTICAPY_VARIABLES_["symbol"],
            )

        elif isinstance(index, (str, str_sql)):
            is_sql = False
            if isinstance(index, vp.vColumn):
                index = index.alias
            elif isinstance(index, str_sql):
                index = str(index)
                is_sql = True
            try:
                new_index = self.format_colnames(index)
                return getattr(self, new_index)
            except:
                if is_sql:
                    return self.search(conditions=index)
                else:
                    return getattr(self, index)

        elif isinstance(index, Iterable):
            try:
                return self.select(columns=[str(col) for col in index])
            except:
                return self.search(conditions=[str(col) for col in index])

        else:
            return getattr(self, index)

    def __iter__(self):
        columns = self.get_columns()
        return (col for col in columns)

    def __len__(self):
        return int(self.shape()[0])

    def __nonzero__(self):
        return self.shape()[0] > 0 and not (self.empty())

    def __repr__(self):
        if self._VERTICAPY_VARIABLES_["sql_magic_result"] and (
            self._VERTICAPY_VARIABLES_["main_relation"][-10:] == "VSQL_MAGIC"
        ):
            return util.readSQL(
                self._VERTICAPY_VARIABLES_["main_relation"][1:-12],
                vp.OPTIONS["time_on"],
                vp.OPTIONS["max_rows"],
            ).__repr__()
        max_rows = self._VERTICAPY_VARIABLES_["max_rows"]
        if max_rows <= 0:
            max_rows = vp.OPTIONS["max_rows"]
        return self.head(limit=max_rows).__repr__()

    def _repr_html_(self, interactive=False):
        if self._VERTICAPY_VARIABLES_["sql_magic_result"] and (
            self._VERTICAPY_VARIABLES_["main_relation"][-10:] == "VSQL_MAGIC"
        ):
            self._VERTICAPY_VARIABLES_["sql_magic_result"] = False
            return util.readSQL(
                self._VERTICAPY_VARIABLES_["main_relation"][1:-12],
                vp.OPTIONS["time_on"],
                vp.OPTIONS["max_rows"],
            )._repr_html_(interactive)
        max_rows = self._VERTICAPY_VARIABLES_["max_rows"]
        if max_rows <= 0:
            max_rows = vp.OPTIONS["max_rows"]
        return self.head(limit=max_rows)._repr_html_(interactive)

    def __round__(self, n):
        vdf = self.copy()
        columns = vdf.numcol()
        for elem in columns:
            if vdf[elem].category() == "float":
                vdf[elem].apply_fun(func="round", x=n)
        return vdf

    def __setattr__(self, attr, val):
        if isinstance(val, (str, str_sql, int, float)) and not isinstance(
            val, vp.vColumn
        ):
            val = str(val)
            if self.is_colname_in(attr):
                self[attr].apply(func=val)
            else:
                self.eval(name=attr, expr=val)
        elif isinstance(val, vp.vColumn) and not (val.init):
            final_trans, n = val.init_transf, len(val.transformations)
            for i in range(1, n):
                final_trans = val.transformations[i][0].replace("{}", final_trans)
            self.eval(name=attr, expr=final_trans)
        else:
            self.__dict__[attr] = val

    def __setitem__(self, index, val):
        setattr(self, index, val)

    #
    # Semi Special Methods
    #

    def __add_to_history__(self, message: str):
        """
    VERTICAPY stores the user modification and help the user to look at 
    what he/she did. This method is to use to add a customized message in the 
    vDataFrame history attribute.
        """
        self._VERTICAPY_VARIABLES_["history"] += [
            "{" + time.strftime("%c") + "}" + " " + message
        ]
        return self

    def __aggregate_matrix__(
        self,
        method: str = "pearson",
        columns: list = [],
        round_nb: int = 3,
        show: bool = True,
        ax=None,
        **style_kwds,
    ):
        """
    Global method to use to compute the Correlation/Cov/Regr Matrix.

    See Also
    --------
    vDataFrame.corr : Computes the Correlation Matrix of the vDataFrame.
    vDataFrame.cov  : Computes the Covariance  Matrix of the vDataFrame.
    vDataFrame.regr : Computes the Regression  Matrix of the vDataFrame.
        """
        method_name = "Correlation"
        method_type = f" using the method = '{method}'"
        if method == "cov":
            method_name = "Covariance"
            method_type = ""
        columns = self.format_colnames(columns)
        if method != "cramer":
            for column in columns:
                assert self[column].isnum(), TypeError(
                    f"vColumn {column} must be numerical to "
                    f"compute the {method_name} Matrix{method_type}."
                )
        if len(columns) == 1:
            if method in (
                "pearson",
                "spearman",
                "spearmand",
                "kendall",
                "biserial",
                "cramer",
            ):
                return 1.0
            elif method == "cov":
                return self[columns[0]].var()
        elif len(columns) == 2:
            pre_comp_val = self.__get_catalog_value__(method=method, columns=columns)
            if pre_comp_val != "VERTICAPY_NOT_PRECOMPUTED":
                return pre_comp_val
            cast_0 = "::int" if (self[columns[0]].isbool()) else ""
            cast_1 = "::int" if (self[columns[1]].isbool()) else ""
            if method in ("pearson", "spearman", "spearmand",):
                if columns[1] == columns[0]:
                    return 1
                if method == "pearson":
                    table = self.__genSQL__()
                else:
                    table = f"""
                        (SELECT 
                            RANK() OVER (ORDER BY {columns[0]}) AS {columns[0]}, 
                            RANK() OVER (ORDER BY {columns[1]}) AS {columns[1]} 
                        FROM {self.__genSQL__()}) rank_spearman_table
                    """
                query = f"""
                    SELECT 
                        /*+LABEL('vDataframe.__aggregate_matrix__')*/ 
                        CORR({columns[0]}{cast_0}, {columns[1]}{cast_1}) 
                    FROM {table}"""
                title = (
                    f"Computes the {method} correlation between "
                    f"{columns[0]} and {columns[1]}."
                )
            elif method == "biserial":
                if columns[1] == columns[0]:
                    return 1
                elif (self[columns[1]].category() != "int") and (
                    self[columns[0]].category() != "int"
                ):
                    return float("nan")
                elif self[columns[1]].category() == "int":
                    if not (self[columns[1]].isbool()):
                        agg = (
                            self[columns[1]]
                            .aggregate(["approx_unique", "min", "max"])
                            .values[columns[1]]
                        )
                        if (agg[0] != 2) or (agg[1] != 0) or (agg[2] != 1):
                            return float("nan")
                    column_b, column_n = columns[1], columns[0]
                    cast_b, cast_n = cast_1, cast_0
                elif self[columns[0]].category() == "int":
                    if not (self[columns[0]].isbool()):
                        agg = (
                            self[columns[0]]
                            .aggregate(["approx_unique", "min", "max"])
                            .values[columns[0]]
                        )
                        if (agg[0] != 2) or (agg[1] != 0) or (agg[2] != 1):
                            return float("nan")
                    column_b, column_n = columns[0], columns[1]
                    cast_b, cast_n = cast_0, cast_1
                else:
                    return float("nan")
                query = f"""
                    SELECT 
                        /*+LABEL('vDataframe.__aggregate_matrix__')*/
                        (AVG(DECODE({column_b}{cast_b}, 1, 
                                    {column_n}{cast_n}, NULL)) 
                       - AVG(DECODE({column_b}{cast_b}, 0, 
                                    {column_n}{cast_n}, NULL))) 
                       / STDDEV({column_n}{cast_n}) 
                       * SQRT(SUM({column_b}{cast_b}) 
                       * SUM(1 - {column_b}{cast_b}) 
                       / COUNT(*) / COUNT(*)) 
                    FROM {self.__genSQL__()} 
                    WHERE {column_b} IS NOT NULL 
                      AND {column_n} IS NOT NULL;"""
                title = (
                    "Computes the biserial correlation "
                    f"between {column_b} and {column_n}."
                )
            elif method == "cramer":
                if columns[1] == columns[0]:
                    return 1
                table_0_1 = f"""
                    SELECT 
                        {columns[0]}, 
                        {columns[1]}, 
                        COUNT(*) AS nij 
                    FROM {self.__genSQL__()} 
                    WHERE {columns[0]} IS NOT NULL 
                      AND {columns[1]} IS NOT NULL 
                    GROUP BY 1, 2"""
                table_0 = f"""
                    SELECT 
                        {columns[0]}, 
                        COUNT(*) AS ni 
                    FROM {self.__genSQL__()} 
                    WHERE {columns[0]} IS NOT NULL 
                      AND {columns[1]} IS NOT NULL 
                    GROUP BY 1"""
                table_1 = f"""
                    SELECT 
                        {columns[1]}, 
                        COUNT(*) AS nj 
                    FROM {self.__genSQL__()} 
                    WHERE {columns[0]} IS NOT NULL 
                      AND {columns[1]} IS NOT NULL 
                    GROUP BY 1"""
                n, k, r = executeSQL(
                    query=f"""
                        SELECT /*+LABEL('vDataframe.__aggregate_matrix__')*/
                            COUNT(*) AS n, 
                            APPROXIMATE_COUNT_DISTINCT({columns[0]}) AS k, 
                            APPROXIMATE_COUNT_DISTINCT({columns[1]}) AS r 
                         FROM {self.__genSQL__()} 
                         WHERE {columns[0]} IS NOT NULL 
                           AND {columns[1]} IS NOT NULL""",
                    title="Computing the columns cardinalities.",
                    method="fetchrow",
                    sql_push_ext=self._VERTICAPY_VARIABLES_["sql_push_ext"],
                    symbol=self._VERTICAPY_VARIABLES_["symbol"],
                )
                chi2 = f"""
                    SELECT /*+LABEL('vDataframe.__aggregate_matrix__')*/
                        SUM((nij - ni * nj / {n}) * (nij - ni * nj / {n}) 
                            / ((ni * nj) / {n})) AS chi2 
                    FROM 
                        (SELECT 
                            * 
                         FROM ({table_0_1}) table_0_1 
                         LEFT JOIN ({table_0}) table_0 
                         ON table_0_1.{columns[0]} = table_0.{columns[0]}) x 
                         LEFT JOIN ({table_1}) table_1 
                         ON x.{columns[1]} = table_1.{columns[1]}"""
                result = executeSQL(
                    chi2,
                    title=(
                        f"Computing the CramerV correlation between {columns[0]} "
                        f"and {columns[1]} (Chi2 Statistic)."
                    ),
                    method="fetchfirstelem",
                    sql_push_ext=self._VERTICAPY_VARIABLES_["sql_push_ext"],
                    symbol=self._VERTICAPY_VARIABLES_["symbol"],
                )
                if min(k - 1, r - 1) == 0:
                    result = float("nan")
                else:
                    result = float(math.sqrt(result / n / min(k - 1, r - 1)))
                    if result > 1 or result < 0:
                        result = float("nan")
                return result
            elif method == "kendall":
                if columns[1] == columns[0]:
                    return 1
                n_ = "SQRT(COUNT(*))"
                n_c = f"""
                    (SUM(((x.{columns[0]}{cast_0} < y.{columns[0]}{cast_0} 
                       AND x.{columns[1]}{cast_1} < y.{columns[1]}{cast_1}) 
                       OR (x.{columns[0]}{cast_0} > y.{columns[0]}{cast_0} 
                       AND x.{columns[1]}{cast_1} > y.{columns[1]}{cast_1}))::int))/2"""
                n_d = f"""
                    (SUM(((x.{columns[0]}{cast_0} > y.{columns[0]}{cast_0} 
                       AND x.{columns[1]}{cast_1} < y.{columns[1]}{cast_1}) 
                       OR (x.{columns[0]}{cast_0} < y.{columns[0]}{cast_0}
                       AND x.{columns[1]}{cast_1} > y.{columns[1]}{cast_1}))::int))/2"""
                n_1 = f"(SUM((x.{columns[0]}{cast_0} = y.{columns[0]}{cast_0})::int)-{n_})/2"
                n_2 = f"(SUM((x.{columns[1]}{cast_1} = y.{columns[1]}{cast_1})::int)-{n_})/2"
                n_0 = f"{n_} * ({n_} - 1)/2"
                tau_b = f"({n_c} - {n_d}) / sqrt(({n_0} - {n_1}) * ({n_0} - {n_2}))"
                query = f"""
                    SELECT /*+LABEL('vDataframe.__aggregate_matrix__')*/
                        {tau_b} 
                    FROM 
                        (SELECT 
                            {columns[0]}, 
                            {columns[1]} 
                         FROM {self.__genSQL__()}) x 
                        CROSS JOIN 
                        (SELECT 
                            {columns[0]}, 
                            {columns[1]} 
                         FROM {self.__genSQL__()}) y"""
                title = f"Computing the kendall correlation between {columns[0]} and {columns[1]}."
            elif method == "cov":
                query = f"""
                    SELECT /*+LABEL('vDataframe.__aggregate_matrix__')*/ 
                        COVAR_POP({columns[0]}{cast_0}, {columns[1]}{cast_1}) 
                    FROM {self.__genSQL__()}"""
                title = (
                    f"Computing the covariance between {columns[0]} and {columns[1]}."
                )
            try:
                result = executeSQL(
                    query=query,
                    title=title,
                    method="fetchfirstelem",
                    sql_push_ext=self._VERTICAPY_VARIABLES_["sql_push_ext"],
                    symbol=self._VERTICAPY_VARIABLES_["symbol"],
                )
            except:
                result = float("nan")
            self.__update_catalog__(
                values={columns[1]: result}, matrix=method, column=columns[0]
            )
            self.__update_catalog__(
                values={columns[0]: result}, matrix=method, column=columns[1]
            )
            if isinstance(result, decimal.Decimal):
                result = float(result)
            return result
        elif len(columns) > 2:
            try:
                nb_precomputed, n = 0, len(columns)
                for column1 in columns:
                    for column2 in columns:
                        pre_comp_val = self.__get_catalog_value__(
                            method=method, columns=[column1, column2]
                        )
                        if pre_comp_val != "VERTICAPY_NOT_PRECOMPUTED":
                            nb_precomputed += 1
                assert (nb_precomputed <= n * n / 3) and (
                    method in ("pearson", "spearman", "spearmand",)
                )
                fun = "DENSE_RANK" if method == "spearmand" else "RANK"
                if method == "pearson":
                    table = self.__genSQL__()
                else:
                    columns_str = ", ".join(
                        [
                            f"{fun}() OVER (ORDER BY {column}) AS {column}"
                            for column in columns
                        ]
                    )
                    table = f"(SELECT {columns_str} FROM {self.__genSQL__()}) spearman_table"
                util.vertica_version(condition=[9, 2, 1])
                result = executeSQL(
                    query=f"""SELECT /*+LABEL('vDataframe.__aggregate_matrix__')*/ 
                                CORR_MATRIX({', '.join(columns)}) 
                                OVER () 
                             FROM {table}""",
                    title=f"Computing the {method} Corr Matrix.",
                    method="fetchall",
                )
                corr_dict = {}
                for idx, column in enumerate(columns):
                    corr_dict[column] = idx
                n = len(columns)
                matrix = [[1 for i in range(0, n + 1)] for i in range(0, n + 1)]
                for elem in result:
                    i, j = (
                        corr_dict[quote_ident(elem[0])],
                        corr_dict[quote_ident(elem[1])],
                    )
                    matrix[i + 1][j + 1] = elem[2]
                matrix[0] = [""] + columns
                for idx, column in enumerate(columns):
                    matrix[idx + 1][0] = column
                title = f"Correlation Matrix ({method})"
            except:
                if method in (
                    "pearson",
                    "spearman",
                    "spearmand",
                    "kendall",
                    "biserial",
                    "cramer",
                ):
                    title_query = "Computing all Correlations in a single query"
                    title = f"Correlation Matrix ({method})"
                    if method == "biserial":
                        i0, step = 0, 1
                    else:
                        i0, step = 1, 0
                elif method == "cov":
                    title_query = "Computing all covariances in a single query"
                    title = "Covariance Matrix"
                    i0, step = 0, 1
                n = len(columns)
                loop = tqdm(range(i0, n)) if vp.OPTIONS["tqdm"] else range(i0, n)
                try:
                    all_list = []
                    nb_precomputed = 0
                    nb_loop = 0
                    for i in loop:
                        for j in range(0, i + step):
                            nb_loop += 1
                            cast_i = "::int" if (self[columns[i]].isbool()) else ""
                            cast_j = "::int" if (self[columns[j]].isbool()) else ""
                            pre_comp_val = self.__get_catalog_value__(
                                method=method, columns=[columns[i], columns[j]]
                            )
                            if pre_comp_val == None or pre_comp_val != pre_comp_val:
                                pre_comp_val = "NULL"
                            if pre_comp_val != "VERTICAPY_NOT_PRECOMPUTED":
                                all_list += [str(pre_comp_val)]
                                nb_precomputed += 1
                            elif method in ("pearson", "spearman", "spearmand"):
                                all_list += [
                                    f"""ROUND(CORR({columns[i]}{cast_i}, 
                                                  {columns[j]}{cast_j}), {round_nb})"""
                                ]
                            elif method == "kendall":
                                n_ = "SQRT(COUNT(*))"
                                n_c = f"""
                                    (SUM(((x.{columns[i]}{cast_i} 
                                         < y.{columns[i]}{cast_i} 
                                       AND x.{columns[j]}{cast_j} 
                                         < y.{columns[j]}{cast_j})
                                       OR (x.{columns[i]}{cast_i} 
                                         > y.{columns[i]}{cast_i} 
                                       AND x.{columns[j]}{cast_j} 
                                         > y.{columns[j]}{cast_j}))::int))/2"""
                                n_d = f"""
                                    (SUM(((x.{columns[i]}{cast_i} 
                                         > y.{columns[i]}{cast_i} 
                                       AND x.{columns[j]}{cast_j} 
                                         < y.{columns[j]}{cast_j}) 
                                       OR (x.{columns[i]}{cast_i} 
                                         < y.{columns[i]}{cast_i} 
                                       AND x.{columns[j]}{cast_j} 
                                         > y.{columns[j]}{cast_j}))::int))/2"""
                                n_1 = f"""
                                    (SUM((x.{columns[i]}{cast_i} = 
                                          y.{columns[i]}{cast_i})::int)-{n_})/2"""
                                n_2 = f"""(SUM((x.{columns[j]}{cast_j} = 
                                          y.{columns[j]}{cast_j})::int)-{n_})/2"""
                                n_0 = f"{n_} * ({n_} - 1)/2"
                                tau_b = f"({n_c} - {n_d}) / sqrt(({n_0} - {n_1}) * ({n_0} - {n_2}))"
                                all_list += [tau_b]
                            elif method == "cov":
                                all_list += [
                                    f"COVAR_POP({columns[i]}{cast_i}, {columns[j]}{cast_j})"
                                ]
                            else:
                                raise
                    if method in ("spearman", "spearmand"):
                        fun = "DENSE_RANK" if method == "spearmand" else "RANK"
                        rank = [
                            f"{fun}() OVER (ORDER BY {column}) AS {column}"
                            for column in columns
                        ]
                        table = f"(SELECT {', '.join(rank)} FROM {self.__genSQL__()}) rank_spearman_table"
                    elif method == "kendall":
                        table = f"""
                            (SELECT {", ".join(columns)} FROM {self.__genSQL__()}) x 
                 CROSS JOIN (SELECT {", ".join(columns)} FROM {self.__genSQL__()}) y"""
                    else:
                        table = self.__genSQL__()
                    if nb_precomputed == nb_loop:
                        result = executeSQL(
                            query=f"""
                                SELECT 
                                    /*+LABEL('vDataframe.__aggregate_matrix__')*/ 
                                    {', '.join(all_list)}""",
                            print_time_sql=False,
                            method="fetchrow",
                        )
                    else:
                        result = executeSQL(
                            query=f"""
                                SELECT 
                                    /*+LABEL('vDataframe.__aggregate_matrix__')*/ 
                                    {', '.join(all_list)} 
                                FROM {table}""",
                            title=title_query,
                            method="fetchrow",
                            sql_push_ext=self._VERTICAPY_VARIABLES_["sql_push_ext"],
                            symbol=self._VERTICAPY_VARIABLES_["symbol"],
                        )
                except:
                    n = len(columns)
                    result = []
                    for i in loop:
                        for j in range(0, i + step):
                            result += [
                                self.__aggregate_matrix__(
                                    method, [columns[i], columns[j]]
                                )
                            ]
                matrix = [[1 for i in range(0, n + 1)] for i in range(0, n + 1)]
                matrix[0] = [""] + columns
                for i in range(0, n + 1):
                    matrix[i][0] = columns[i - 1]
                k = 0
                for i in range(i0, n):
                    for j in range(0, i + step):
                        current = result[k]
                        k += 1
                        if current == None:
                            current = float("nan")
                        matrix[i + 1][j + 1] = current
                        matrix[j + 1][i + 1] = current
            if show:
                vmin = 0 if (method == "cramer") else -1
                if method == "cov":
                    vmin = None
                vmax = (
                    1
                    if (
                        method
                        in (
                            "pearson",
                            "spearman",
                            "spearmand",
                            "kendall",
                            "biserial",
                            "cramer",
                        )
                    )
                    else None
                )
                if "cmap" not in style_kwds:
                    cm1, cm2 = gen_cmap()
                    cmap = cm1 if (method == "cramer") else cm2
                    style_kwds["cmap"] = cmap
                plt.cmatrix(
                    matrix,
                    columns,
                    columns,
                    n,
                    n,
                    vmax=vmax,
                    vmin=vmin,
                    title=title,
                    mround=round_nb,
                    ax=ax,
                    **style_kwds,
                )
            values = {"index": matrix[0][1 : len(matrix[0])]}
            del matrix[0]
            for column in matrix:
                values[column[0]] = column[1 : len(column)]
            for column1 in values:
                if column1 != "index":
                    val = {}
                    for idx, column2 in enumerate(values["index"]):
                        val[column2] = values[column1][idx]
                    self.__update_catalog__(values=val, matrix=method, column=column1)
            return util.tablesample(values=values).decimal_to_float()
        else:
            if method == "cramer":
                cols = self.catcol()
                assert len(cols) != 0, EmptyParameter(
                    "No categorical column found in the vDataFrame."
                )
            else:
                cols = self.numcol()
                assert len(cols) != 0, EmptyParameter(
                    "No numerical column found in the vDataFrame."
                )
            return self.__aggregate_matrix__(
                method=method, columns=cols, round_nb=round_nb, show=show, **style_kwds,
            )

    def __aggregate_vector__(
        self,
        focus: str,
        method: str = "pearson",
        columns: list = [],
        round_nb: int = 3,
        show: bool = True,
        ax=None,
        **style_kwds,
    ):
        """
    Global method to use to compute the Correlation/Cov/Beta Vector.

    See Also
    --------
    vDataFrame.corr : Computes the Correlation Matrix of the vDataFrame.
    vDataFrame.cov  : Computes the covariance matrix of the vDataFrame.
    vDataFrame.regr : Computes the regression matrix of the vDataFrame.
        """
        if not (columns):
            if method == "cramer":
                cols = self.catcol()
                assert cols, EmptyParameter(
                    "No categorical column found in the vDataFrame."
                )
            else:
                cols = self.numcol()
                assert cols, EmptyParameter(
                    "No numerical column found in the vDataFrame."
                )
        else:
            cols = self.format_colnames(columns)
        if method != "cramer":
            method_name = "Correlation"
            method_type = f" using the method = '{method}'"
            if method == "cov":
                method_name = "Covariance"
                method_type = ""
            for column in cols:
                assert self[column].isnum(), TypeError(
                    f"vColumn '{column}' must be numerical to "
                    f"compute the {method_name} Vector{method_type}."
                )
        if method in ("spearman", "spearmand", "pearson", "kendall", "cov") and (
            len(cols) >= 1
        ):
            try:
                fail = 0
                cast_i = "::int" if (self[focus].isbool()) else ""
                all_list, all_cols = [], [focus]
                nb_precomputed = 0
                for column in cols:
                    if (
                        column.replace('"', "").lower()
                        != focus.replace('"', "").lower()
                    ):
                        all_cols += [column]
                    cast_j = "::int" if (self[column].isbool()) else ""
                    pre_comp_val = self.__get_catalog_value__(
                        method=method, columns=[focus, column]
                    )
                    if pre_comp_val == None or pre_comp_val != pre_comp_val:
                        pre_comp_val = "NULL"
                    if pre_comp_val != "VERTICAPY_NOT_PRECOMPUTED":
                        all_list += [str(pre_comp_val)]
                        nb_precomputed += 1
                    elif method in ("pearson", "spearman", "spearmand"):
                        all_list += [
                            f"ROUND(CORR({focus}{cast_i}, {column}{cast_j}), {round_nb})"
                        ]
                    elif method == "kendall":
                        n = "SQRT(COUNT(*))"
                        n_c = f"""
                            (SUM(((x.{focus}{cast_i} 
                                 < y.{focus}{cast_i} 
                               AND x.{column}{cast_j}
                                 < y.{column}{cast_j})
                               OR (x.{focus}{cast_i} 
                                 > y.{focus}{cast_i} 
                               AND x.{column}{cast_j} 
                                 > y.{column}{cast_j}))::int))/2"""
                        n_d = f"""
                            (SUM(((x.{focus}{cast_i} 
                                 > y.{focus}{cast_i} 
                               AND x.{column}{cast_j} 
                                 < y.{column}{cast_j})
                               OR (x.{focus}{cast_i}
                                 < y.{focus}{cast_i}
                               AND x.{column}{cast_j} 
                                 > y.{column}{cast_j}))::int))/2"""
                        n_1 = (
                            f"(SUM((x.{focus}{cast_i} = y.{focus}{cast_i})::int)-{n})/2"
                        )
                        n_2 = f"(SUM((x.{column}{cast_j} = y.{column}{cast_j})::int)-{n})/2"
                        n_0 = f"{n} * ({n} - 1)/2"
                        tau_b = (
                            f"({n_c} - {n_d}) / sqrt(({n_0} - {n_1}) * ({n_0} - {n_2}))"
                        )
                        all_list += [tau_b]
                    elif method == "cov":
                        all_list += [f"COVAR_POP({focus}{cast_i}, {column}{cast_j})"]
                if method in ("spearman", "spearmand"):
                    fun = "DENSE_RANK" if method == "spearmand" else "RANK"
                    rank = [
                        f"{fun}() OVER (ORDER BY {column}) AS {column}"
                        for column in all_cols
                    ]
                    table = f"(SELECT {', '.join(rank)} FROM {self.__genSQL__()}) rank_spearman_table"
                elif method == "kendall":
                    table = f"""
                        (SELECT {", ".join(all_cols)} FROM {self.__genSQL__()}) x 
             CROSS JOIN (SELECT {", ".join(all_cols)} FROM {self.__genSQL__()}) y"""
                else:
                    table = self.__genSQL__()
                if nb_precomputed == len(cols):
                    result = executeSQL(
                        query=f"""
                            SELECT 
                                /*+LABEL('vDataframe.__aggregate_vector__')*/ 
                                {', '.join(all_list)}""",
                        method="fetchrow",
                        print_time_sql=False,
                    )
                else:
                    result = executeSQL(
                        query=f"""
                            SELECT 
                                /*+LABEL('vDataframe.__aggregate_vector__')*/ 
                                {', '.join(all_list)} 
                            FROM {table} 
                            LIMIT 1""",
                        title=f"Computing the Correlation Vector ({method})",
                        method="fetchrow",
                        sql_push_ext=self._VERTICAPY_VARIABLES_["sql_push_ext"],
                        symbol=self._VERTICAPY_VARIABLES_["symbol"],
                    )
                vector = [elem for elem in result]
            except:
                fail = 1
        if not (
            method in ("spearman", "spearmand", "pearson", "kendall", "cov")
            and (len(cols) >= 1)
        ) or (fail):
            vector = []
            for column in cols:
                if column.replace('"', "").lower() == focus.replace('"', "").lower():
                    vector += [1]
                else:
                    vector += [
                        self.__aggregate_matrix__(
                            method=method, columns=[column, focus]
                        )
                    ]
        vector = [0 if (elem == None) else elem for elem in vector]
        data = [(cols[i], vector[i]) for i in range(len(vector))]
        data.sort(key=lambda tup: abs(tup[1]), reverse=True)
        cols, vector = [elem[0] for elem in data], [elem[1] for elem in data]
        if show:
            vmin = 0 if (method == "cramer") else -1
            if method == "cov":
                vmin = None
            vmax = (
                1
                if (
                    method
                    in (
                        "pearson",
                        "spearman",
                        "spearmand",
                        "kendall",
                        "biserial",
                        "cramer",
                    )
                )
                else None
            )
            if "cmap" not in style_kwds:
                cm1, cm2 = gen_cmap()
                cmap = cm1 if (method == "cramer") else cm2
                style_kwds["cmap"] = cmap
            title = f"Correlation Vector of {focus} ({method})"
            plt.cmatrix(
                [cols, [focus] + vector],
                cols,
                [focus],
                len(cols),
                1,
                vmax=vmax,
                vmin=vmin,
                title=title,
                mround=round_nb,
                is_vector=True,
                ax=ax,
                **style_kwds,
            )
        for idx, column in enumerate(cols):
            self.__update_catalog__(
                values={focus: vector[idx]}, matrix=method, column=column
            )
            self.__update_catalog__(
                values={column: vector[idx]}, matrix=method, column=focus
            )
        return util.tablesample(
            values={"index": cols, focus: vector}
        ).decimal_to_float()

    def __genSQL__(
        self, split: bool = False, transformations: dict = {}, force_columns: list = [],
    ):
        """
    Method to use to generate the SQL final relation. It will look at all 
    transformations to build a nested query where each transformation will 
    be associated to a specific floor.

    Parameters
    ----------
    split: bool, optional
        Adds a split column __verticapy_split__ in the relation 
        which can be to use to downsample the data.
    transformations: dict, optional
        Dictionary of columns and their respective transformation. It 
        will be to use to test if an expression is correct and can be 
        added it in the final relation.
    force_columns: list, optional
        Columns to use to generate the final relation.

    Returns
    -------
    str
        The SQL final relation.
        """
        # The First step is to find the Max Floor
        all_imputations_grammar = []
        force_columns_copy = [col for col in force_columns]
        if not (force_columns):
            force_columns = [col for col in self._VERTICAPY_VARIABLES_["columns"]]
        for column in force_columns:
            all_imputations_grammar += [
                [transformation[0] for transformation in self[column].transformations]
            ]
        for column in transformations:
            all_imputations_grammar += [transformations[column]]
        max_transformation_floor = len(max(all_imputations_grammar, key=len))
        # We complete all virtual columns transformations which do not have enough floors
        # with the identity transformation x :-> x in order to generate the correct SQL query
        for imputations in all_imputations_grammar:
            diff = max_transformation_floor - len(imputations)
            if diff > 0:
                imputations += ["{}"] * diff
        # We find the position of all filters in order to write them at the correct floor
        where_positions = [item[1] for item in self._VERTICAPY_VARIABLES_["where"]]
        max_where_pos = max(where_positions + [0])
        all_where = [[] for item in range(max_where_pos + 1)]
        for i in range(0, len(self._VERTICAPY_VARIABLES_["where"])):
            all_where[where_positions[i]] += [self._VERTICAPY_VARIABLES_["where"][i][0]]
        all_where = [
            " AND ".join([f"({elem})" for elem in condition]) for condition in all_where
        ]
        for i in range(len(all_where)):
            if all_where[i] != "":
                all_where[i] = f" WHERE {all_where[i]}"
        # We compute the first floor
        columns = force_columns + [column for column in transformations]
        first_values = [item[0] for item in all_imputations_grammar]
        transformations_first_floor = False
        for i in range(0, len(first_values)):
            if (first_values[i] != "___VERTICAPY_UNDEFINED___") and (
                first_values[i] != columns[i]
            ):
                first_values[i] = f"{first_values[i]} AS {columns[i]}"
                transformations_first_floor = True
        if (transformations_first_floor) or (
            self._VERTICAPY_VARIABLES_["allcols_ind"] != len(first_values)
        ):
            table = f"""
                SELECT 
                    {', '.join(first_values)} 
                FROM {self._VERTICAPY_VARIABLES_['main_relation']}"""
        else:
            table = f"""SELECT * FROM {self._VERTICAPY_VARIABLES_["main_relation"]}"""
        # We compute the other floors
        for i in range(1, max_transformation_floor):
            values = [item[i] for item in all_imputations_grammar]
            for j in range(0, len(values)):
                if values[j] == "{}":
                    values[j] = columns[j]
                elif values[j] != "___VERTICAPY_UNDEFINED___":
                    values_str = values[j].replace("{}", columns[j])
                    values[j] = f"{values_str} AS {columns[j]}"
            table = f"SELECT {', '.join(values)} FROM ({table}) VERTICAPY_SUBTABLE"
            if len(all_where) > i - 1:
                table += all_where[i - 1]
            if (i - 1) in self._VERTICAPY_VARIABLES_["order_by"]:
                table += self._VERTICAPY_VARIABLES_["order_by"][i - 1]
        where_final = (
            all_where[max_transformation_floor - 1]
            if (len(all_where) > max_transformation_floor - 1)
            else ""
        )
        # Only the last order_by matters as the order_by will never change
        # the final relation
        try:
            order_final = self._VERTICAPY_VARIABLES_["order_by"][
                max_transformation_floor - 1
            ]
        except:
            order_final = ""
        for vml_undefined in [
            ", ___VERTICAPY_UNDEFINED___",
            "___VERTICAPY_UNDEFINED___, ",
            "___VERTICAPY_UNDEFINED___",
        ]:
            table = table.replace(vml_undefined, "")
        random_func = get_random_function()
        split = f", {random_func} AS __verticapy_split__" if (split) else ""
        if (where_final == "") and (order_final == ""):
            if split:
                table = f"SELECT *{split} FROM ({table}) VERTICAPY_SUBTABLE"
            table = f"({table}) VERTICAPY_SUBTABLE"
        else:
            table = f"({table}) VERTICAPY_SUBTABLE{where_final}{order_final}"
            table = f"(SELECT *{split} FROM {table}) VERTICAPY_SUBTABLE"
        if (self._VERTICAPY_VARIABLES_["exclude_columns"]) and not (split):
            if not (force_columns_copy):
                force_columns_copy = self.get_columns()
            force_columns_copy = ", ".join(force_columns_copy)
            table = f"""
                (SELECT 
                    {force_columns_copy}{split} 
                FROM {table}) VERTICAPY_SUBTABLE"""
        main_relation = self._VERTICAPY_VARIABLES_["main_relation"]
        all_main_relation = f"(SELECT * FROM {main_relation}) VERTICAPY_SUBTABLE"
        table = table.replace(all_main_relation, main_relation)
        return table

    def __get_catalog_value__(
        self, column: str = "", key: str = "", method: str = "", columns: list = []
    ):
        """
    VERTICAPY stores the already computed aggregations to avoid useless 
    computations. This method returns the stored aggregation if it was already 
    computed.
        """
        if not (vp.OPTIONS["cache"]):
            return "VERTICAPY_NOT_PRECOMPUTED"
        if column == "VERTICAPY_COUNT":
            if self._VERTICAPY_VARIABLES_["count"] < 0:
                return "VERTICAPY_NOT_PRECOMPUTED"
            total = self._VERTICAPY_VARIABLES_["count"]
            if not (isinstance(total, (int, float))):
                return "VERTICAPY_NOT_PRECOMPUTED"
            return total
        elif method:
            method = get_verticapy_function(method.lower())
            if columns[1] in self[columns[0]].catalog[method]:
                return self[columns[0]].catalog[method][columns[1]]
            else:
                return "VERTICAPY_NOT_PRECOMPUTED"
        key = get_verticapy_function(key.lower())
        column = self.format_colnames(column)
        try:
            if (key == "approx_unique") and ("unique" in self[column].catalog):
                key = "unique"
            result = (
                "VERTICAPY_NOT_PRECOMPUTED"
                if key not in self[column].catalog
                else self[column].catalog[key]
            )
        except:
            result = "VERTICAPY_NOT_PRECOMPUTED"
        if result != result:
            result = None
        if ("top" not in key) and (result == None):
            return "VERTICAPY_NOT_PRECOMPUTED"
        return result

    def __get_last_order_by__(self):
        """
    Returns the last column used to sort the data.
        """
        max_pos, order_by = 0, ""
        columns_tmp = [elem for elem in self.get_columns()]
        for column in columns_tmp:
            max_pos = max(max_pos, len(self[column].transformations) - 1)
        if max_pos in self._VERTICAPY_VARIABLES_["order_by"]:
            order_by = self._VERTICAPY_VARIABLES_["order_by"][max_pos]
        return order_by

    def __get_sort_syntax__(self, columns: list):
        """
    Returns the SQL syntax to use to sort the input columns.
        """
        if not (columns):
            return ""
        if isinstance(columns, dict):
            order_by = []
            for col in columns:
                column_name = self.format_colnames(col)
                if columns[col].lower() not in ("asc", "desc"):
                    warning_message = (
                        f"Method of {column_name} must be in (asc, desc), "
                        f"found '{columns[col].lower()}'\nThis column was ignored."
                    )
                    warnings.warn(warning_message, Warning)
                else:
                    order_by += [f"{column_name} {columns[col].upper()}"]
        else:
            order_by = [quote_ident(col) for col in columns]
        return f" ORDER BY {', '.join(order_by)}"

    def __isexternal__(self):
        """
    Returns true if it is an external vDataFrame.
        """
        return self._VERTICAPY_VARIABLES_["external"]

    def __update_catalog__(
        self,
        values: dict = {},
        erase: bool = False,
        columns: list = [],
        matrix: str = "",
        column: str = "",
    ):
        """
    VERTICAPY stores the already computed aggregations to avoid useless 
    computations. This method stores the input aggregation in the vColumn catalog.
        """
        columns = self.format_colnames(columns)
        agg_dict = {
            "cov": {},
            "pearson": {},
            "spearman": {},
            "spearmand": {},
            "kendall": {},
            "cramer": {},
            "biserial": {},
            "regr_avgx": {},
            "regr_avgy": {},
            "regr_count": {},
            "regr_intercept": {},
            "regr_r2": {},
            "regr_slope": {},
            "regr_sxx": {},
            "regr_sxy": {},
            "regr_syy": {},
        }
        if erase:
            if not (columns):
                columns = self.get_columns()
            for column in columns:
                self[column].catalog = copy.deepcopy(agg_dict)
            self._VERTICAPY_VARIABLES_["count"] = -1
        elif matrix:
            matrix = get_verticapy_function(matrix.lower())
            if matrix in agg_dict:
                for elem in values:
                    val = values[elem]
                    try:
                        val = float(val)
                    except:
                        pass
                    self[column].catalog[matrix][elem] = val
        else:
            columns = [elem for elem in values]
            columns.remove("index")
            for column in columns:
                for i in range(len(values["index"])):
                    key, val = values["index"][i].lower(), values[column][i]
                    if key not in ["listagg"]:
                        key = get_verticapy_function(key)
                        try:
                            val = float(val)
                            if val - int(val) == 0:
                                val = int(val)
                        except:
                            pass
                        if val != val:
                            val = None
                        self[column].catalog[key] = val

    def __vDataFrameSQL__(self, table: str, func: str, history: str):
        """
    This method is to use to build a vDataFrame based on a relation
        """
        schema = self._VERTICAPY_VARIABLES_["schema"]
        history = self._VERTICAPY_VARIABLES_["history"] + [history]
        saving = self._VERTICAPY_VARIABLES_["saving"]
        return util.vDataFrameSQL(table, func, schema, history, saving)

    #
    # Methods used to check & format the inputs
    #

    def format_colnames(
        self,
        *argv,
        columns: Union[str, list, dict] = [],
        expected_nb_of_cols: Union[int, list] = [],
        raise_error: bool = True,
    ):
        """
    Method used to format the input columns by using the vDataFrame columns' names.

    Parameters
    ----------
    *argv: str / list / dict, optional
        List of columns' names to format. It allows to use as input multiple
        objects and to get all of them formatted.
        Example: self.format_colnames(x0, x1, x2) will return x0_f, x1_f, 
        x2_f where xi_f represents xi correctly formatted.
    columns: str / list / dict, optional
        List of columns' names to format.
    expected_nb_of_cols: int / list
        [Only used for the function first argument]
        List of the expected number of columns.
        Example: If expected_nb_of_cols is set to [2, 3], the parameters
        'columns' or the first argument of argv should have exactly 2 or
        3 elements. Otherwise, the function will raise an error.
    raise_error: bool, optional
        If set to True and if there is an error, it will be raised.

    Returns
    -------
    str / list
        Formatted columns' names.
        """
        if argv:
            result = []
            for arg in argv:
                result += [self.format_colnames(columns=arg, raise_error=raise_error)]
            if len(argv) == 1:
                result = result[0]
        else:
            if not (columns) or isinstance(columns, (int, float)):
                return copy.deepcopy(columns)
            if raise_error:
                if isinstance(columns, str):
                    cols_to_check = [columns]
                else:
                    cols_to_check = copy.deepcopy(columns)
                all_columns = self.get_columns()
                for column in cols_to_check:
                    result = []
                    if column not in all_columns:
                        min_distance, min_distance_op = 1000, ""
                        is_error = True
                        for col in all_columns:
                            if quote_ident(column).lower() == quote_ident(col).lower():
                                is_error = False
                                break
                            else:
                                ldistance = levenshtein(column, col)
                                if ldistance < min_distance:
                                    min_distance, min_distance_op = ldistance, col
                        if is_error:
                            error_message = (
                                f"The Virtual Column '{column}' doesn't exist."
                            )
                            if min_distance < 10:
                                error_message += f"\nDid you mean '{min_distance_op}' ?"
                            raise MissingColumn(error_message)

            if isinstance(columns, str):
                result = columns
                vdf_columns = self.get_columns()
                for col in vdf_columns:
                    if quote_ident(columns).lower() == quote_ident(col).lower():
                        result = col
                        break
            elif isinstance(columns, dict):
                result = {}
                for col in columns:
                    key = self.format_colnames(col, raise_error=raise_error)
                    result[key] = columns[col]
            else:
                result = []
                for col in columns:
                    result += [self.format_colnames(col, raise_error=raise_error)]
        if raise_error:
            if isinstance(expected_nb_of_cols, int):
                expected_nb_of_cols = [expected_nb_of_cols]
            if len(expected_nb_of_cols) > 0:
                if len(argv) > 0:
                    columns = argv[0]
                n = len(columns)
                if n not in expected_nb_of_cols:
                    x = "|".join([str(nb) for nb in expected_nb_of_cols])
                    raise ParameterError(
                        f"The number of Virtual Columns expected is [{x}], found {n}."
                    )
        return result

    def is_colname_in(self, column: str):
        """
    Method used to check if the input column name is used by the vDataFrame.
    If not, the function raises an error.

    Parameters
    ----------
    column: str
        Input column.

    Returns
    -------
    bool
        True if the column is used by the vDataFrame
        False otherwise.
        """
        columns = self.get_columns()
        column = quote_ident(column).lower()
        for col in columns:
            if column == quote_ident(col).lower():
                return True
        return False

    def get_nearest_column(self, column: str):
        """
    Method used to find the nearest column's name to the input one.

    Parameters
    ----------
    column: str
        Input column.

    Returns
    -------
    tuple
        (nearest column, levenstein distance)
        """
        columns = self.get_columns()
        col = column.replace('"', "").lower()
        result = (columns[0], levenshtein(col, columns[0].replace('"', "").lower()))
        if len(columns) == 1:
            return result
        for col in columns:
            if col != result[0]:
                current_col = col.replace('"', "").lower()
                d = levenshtein(current_col, col)
                if result[1] > d:
                    result = (col, d)
        return result

    #
    # Interactive display
    #

    def idisplay(self):
        """This method displays the interactive table. It is used when 
        you don't want to activate interactive table for all vDataFrames."""
        return display(HTML(self.copy()._repr_html_(interactive=True)))

    #
    # Methods
    #

    @save_verticapy_logs
    def aad(
        self, columns: list = [], **agg_kwds,
    ):
        """
    Aggregates the vDataFrame using 'aad' (Average Absolute Deviation).

    Parameters
    ----------
    columns: list, optional
        List of the vColumns names. If empty, all numerical vColumns will be 
        used.
    **agg_kwds
        Any optional parameter to pass to the Aggregate function.

    Returns
    -------
    tablesample
        An object containing the result. For more information, see
        utilities.tablesample.

    See Also
    --------
    vDataFrame.aggregate : Computes the vDataFrame input aggregations.
        """
        return self.aggregate(func=["aad"], columns=columns, **agg_kwds,)

    @save_verticapy_logs
    def abs(self, columns: Union[str, list] = []):
        """
    Applies the absolute value function to all input vColumns. 

    Parameters
    ----------
    columns: str / list, optional
        List of the vColumns names. If empty, all numerical vColumns will 
        be used.

    Returns
    -------
    vDataFrame
        self

    See Also
    --------
    vDataFrame.apply    : Applies functions to the input vColumns.
    vDataFrame.applymap : Applies a function to all vColumns.
        """
        if isinstance(columns, str):
            columns = [columns]
        columns = self.numcol() if not (columns) else self.format_colnames(columns)
        func = {}
        for column in columns:
            if not (self[column].isbool()):
                func[column] = "ABS({})"
        return self.apply(func)

    @save_verticapy_logs
    def acf(
        self,
        column: str,
        ts: str,
        by: Union[str, list] = [],
        p: Union[int, list] = 12,
        unit: str = "rows",
        method: Literal[
            "pearson", "kendall", "spearman", "spearmand", "biserial", "cramer"
        ] = "pearson",
        acf_type: Literal["line", "heatmap", "bar"] = "bar",
        confidence: bool = True,
        alpha: float = 0.95,
        round_nb: int = 3,
        show: bool = True,
        ax=None,
        **style_kwds,
    ):
        """
    Computes the correlations of the input vColumn and its lags. 

    Parameters
    ----------
    column: str
        Input vColumn to use to compute the Auto Correlation Plot.
    ts: str
        TS (Time Series) vColumn to use to order the data. It can be of type date
        or a numerical vColumn.
    by: str / list, optional
        vColumns used in the partition.
    p: int/list, optional
        Int equals to the maximum number of lag to consider during the computation
        or List of the different lags to include during the computation.
        p must be positive or a list of positive integers.
    unit: str, optional
        Unit to use to compute the lags.
            rows: Natural lags
            else : Any time unit, for example you can write 'hour' to compute the hours
                lags or 'day' to compute the days lags.
    method: str, optional
        Method to use to compute the correlation.
            pearson   : Pearson's correlation coefficient (linear).
            spearman  : Spearman's correlation coefficient (monotonic - rank based).
            spearmanD : Spearman's correlation coefficient using the DENSE RANK
                        function instead of the RANK function.
            kendall   : Kendall's correlation coefficient (similar trends). The method
                        will compute the Tau-B coefficient.
                       \u26A0 Warning : This method uses a CROSS JOIN during computation 
                                        and is therefore computationally expensive at 
                                        O(n * n), where n is the total count of the 
                                        vDataFrame.
            cramer    : Cramer's V (correlation between categories).
            biserial  : Biserial Point (correlation between binaries and a numericals).
    acf_type: str, optional
        ACF Type.
            bar     : Classical Autocorrelation Plot using bars.
            heatmap : Draws the ACF heatmap.
            line    : Draws the ACF using a Line Plot.
    confidence: bool, optional
        If set to True, the confidence band width is drawn.
    alpha: float, optional
        Significance Level. Probability to accept H0. Only used to compute the confidence
        band width.
    round_nb: int, optional
        Round the coefficient using the input number of digits. It is used only if 
        acf_type is 'heatmap'.
    show: bool, optional
        If set to True, the Auto Correlation Plot will be drawn using Matplotlib.
    ax: Matplotlib axes object, optional
        The axes to plot on.
    **style_kwds
        Any optional parameter to pass to the Matplotlib functions.

    Returns
    -------
    tablesample
        An object containing the result. For more information, see
        utilities.tablesample.

    See Also
    --------
    vDataFrame.interpolate : Interpolates and computes a regular time 
                             interval vDataFrame.
    vDataFrame.corr        : Computes the Correlation Matrix of a vDataFrame.
    vDataFrame.cov         : Computes the covariance matrix of the vDataFrame.
    vDataFrame.pacf        : Computes the partial autocorrelations of the 
                             input vColumn.
        """
        method = str(method).lower()
        if isinstance(by, str):
            by = [by]
        by, column, ts = self.format_colnames(by, column, ts)
        if unit == "rows":
            table = self.__genSQL__()
        else:
            table = self.interpolate(
                ts=ts, rule=f"1 {unit}", method={column: "linear"}, by=by
            ).__genSQL__()
        if isinstance(p, (int, float)):
            p = range(1, p + 1)
        by = f"PARTITION BY {', '.join(by)} " if (by) else ""
        columns = [
            f"LAG({column}, {i}) OVER ({by}ORDER BY {ts}) AS lag_{i}_{gen_name([column])}"
            for i in p
        ]
        relation = f"(SELECT {', '.join([column] + columns)} FROM {table}) acf"
        if len(p) == 1:
            return self.__vDataFrameSQL__(relation, "acf", "").corr([], method=method)
        elif acf_type == "heatmap":
            return self.__vDataFrameSQL__(relation, "acf", "").corr(
                [],
                method=method,
                round_nb=round_nb,
                focus=column,
                show=show,
                **style_kwds,
            )
        else:
            result = self.__vDataFrameSQL__(relation, "acf", "").corr(
                [], method=method, focus=column, show=False
            )
            columns = [elem for elem in result.values["index"]]
            acf = [elem for elem in result.values[column]]
            acf_band = []
            if confidence:
                for k in range(1, len(acf) + 1):
                    acf_band += [
                        math.sqrt(2)
                        * scipy_special.erfinv(alpha)
                        / math.sqrt(self[column].count() - k + 1)
                        * math.sqrt((1 + 2 * sum([acf[i] ** 2 for i in range(1, k)])))
                    ]
            if columns[0] == column:
                columns[0] = 0
            for i in range(1, len(columns)):
                columns[i] = int(columns[i].split("_")[1])
            data = [(columns[i], acf[i]) for i in range(len(columns))]
            data.sort(key=lambda tup: tup[0])
            del result.values[column]
            result.values["index"] = [elem[0] for elem in data]
            result.values["value"] = [elem[1] for elem in data]
            if acf_band:
                result.values["confidence"] = acf_band
            if show:
                plt.acf_plot(
                    result.values["index"],
                    result.values["value"],
                    title="Autocorrelation",
                    confidence=acf_band,
                    type_bar=True if acf_type == "bar" else False,
                    ax=ax,
                    **style_kwds,
                )
            return result

    @save_verticapy_logs
    def add_duplicates(self, weight: Union[int, str], use_gcd: bool = True):
        """
    Duplicates the vDataFrame using the input weight.

    Parameters
    ----------
    weight: str / integer
        vColumn or integer representing the weight.
    use_gcd: bool
        If set to True, uses the GCD (Greatest Common Divisor) to reduce all 
        common weights to avoid unnecessary duplicates.

    Returns
    -------
    vDataFrame
        the output vDataFrame
        """
        if isinstance(weight, str):
            weight = self.format_colnames(weight)
            assert self[weight].category() == "int", TypeError(
                "The weight vColumn category must be "
                f"'integer', found {self[weight].category()}."
            )
            L = sorted(self[weight].distinct())
            gcd, max_value, n = L[0], L[-1], len(L)
            assert gcd >= 0, ValueError(
                "The weight vColumn must only include positive integers."
            )
            if use_gcd:
                if gcd != 1:
                    for i in range(1, n):
                        if gcd != 1:
                            gcd = math.gcd(gcd, L[i])
                        else:
                            break
            else:
                gcd = 1
            columns = self.get_columns(exclude_columns=[weight])
            vdf = self.search(self[weight] != 0, usecols=columns)
            for i in range(2, int(max_value / gcd) + 1):
                vdf = vdf.append(
                    self.search((self[weight] / gcd) >= i, usecols=columns)
                )
        else:
            assert weight >= 2 and isinstance(weight, int), ValueError(
                "The weight must be an integer greater or equal to 2."
            )
            vdf = self.copy()
            for i in range(2, weight + 1):
                vdf = vdf.append(self)
        return vdf

    @save_verticapy_logs
    def aggregate(
        self,
        func: Union[str, list],
        columns: Union[str, list] = [],
        ncols_block: int = 20,
        processes: int = 1,
    ):
        """
    Aggregates the vDataFrame using the input functions.

    Parameters
    ----------
    func: str / list
        List of the different aggregations.
            aad            : average absolute deviation
            approx_median  : approximate median
            approx_q%      : approximate q quantile 
                             (ex: approx_50% for the approximate median)
            approx_unique  : approximative cardinality
            count          : number of non-missing elements
            cvar           : conditional value at risk
            dtype          : virtual column type
            iqr            : interquartile range
            kurtosis       : kurtosis
            jb             : Jarque-Bera index 
            mad            : median absolute deviation
            max            : maximum
            mean           : average
            median         : median
            min            : minimum
            mode           : most occurent element
            percent        : percent of non-missing elements 
            q%             : q quantile (ex: 50% for the median)
                             Use the 'approx_q%' (approximate quantile) 
                             aggregation to get better performances.
            prod           : product
            range          : difference between the max and the min
            sem            : standard error of the mean
            skewness       : skewness
            sum            : sum
            std            : standard deviation
            topk           : kth most occurent element (ex: top1 for the mode)
            topk_percent   : kth most occurent element density
            unique         : cardinality (count distinct)
            var            : variance
                Other aggregations will work if supported by your version of 
                the database.
    columns: str / list, optional
        List of the vColumn's names. If empty, depending on the aggregations,
        all or only numerical vColumns will be used.
    ncols_block: int, optional
        Number of columns used per query. Setting this parameter divides
        what would otherwise be one large query into many smaller queries called
        "blocks." The size of each block is determined by the ncols_block parameter.
    processes: int, optional
        Number of child processes to create. Setting this with the ncols_block parameter
        lets you parallelize a single query into many smaller queries, where each child 
        process creates its own connection to the database and sends one query. This can 
        improve query performance, but consumes more resources. If processes is set to 1, 
        the queries are sent iteratively from a single process.

    Returns
    -------
    tablesample
        An object containing the result. For more information, see
        utilities.tablesample.

    See Also
    --------
    vDataFrame.analytic : Adds a new vColumn to the vDataFrame by using an advanced 
        analytical function on a specific vColumn.
        """
        if isinstance(columns, str):
            columns = [columns]
        if isinstance(func, str):
            func = [func]
        if not (columns):
            columns = self.get_columns()
            cat_agg = [
                "count",
                "unique",
                "approx_unique",
                "approximate_count_distinct",
                "dtype",
                "percent",
            ]
            for fun in func:
                if ("top" not in fun) and (fun not in cat_agg):
                    columns = self.numcol()
                    break
        else:
            columns = self.format_colnames(columns)

        # Some aggregations are not compatibles, we need to pre-compute them.

        agg_unique = []
        agg_approx = []
        agg_exact_percent = []
        agg_percent = []
        other_agg = []

        for fun in func:

            if fun[-1] == "%":
                if (len(fun.lower()) >= 8) and fun[0:7] == "approx_":
                    agg_approx += [fun.lower()]
                else:
                    agg_exact_percent += [fun.lower()]

            elif fun.lower() in ("approx_unique", "approximate_count_distinct"):
                agg_approx += [fun.lower()]

            elif fun.lower() == "unique":
                agg_unique += [fun.lower()]

            else:
                other_agg += [fun.lower()]

        exact_percent, uniques = {}, {}

        if agg_exact_percent and (other_agg or agg_percent or agg_approx or agg_unique):
            exact_percent = self.aggregate(
                func=agg_exact_percent,
                columns=columns,
                ncols_block=ncols_block,
                processes=processes,
            ).transpose()

        if agg_unique and agg_approx:
            uniques = self.aggregate(
                func=["unique"],
                columns=columns,
                ncols_block=ncols_block,
                processes=processes,
            ).transpose()

        # Some aggregations are using some others. We need to precompute them.

        for fun in func:
            if fun.lower() in [
                "kurtosis",
                "kurt",
                "skewness",
                "skew",
                "jb",
            ]:
                count_avg_stddev = (
                    self.aggregate(func=["count", "avg", "stddev"], columns=columns)
                    .transpose()
                    .values
                )
                break

        # Computing iteratively aggregations using block of columns.

        if ncols_block < len(columns) and processes <= 1:

            if vp.OPTIONS["tqdm"]:
                loop = tqdm(range(0, len(columns), ncols_block))
            else:
                loop = range(0, len(columns), ncols_block)
            for i in loop:
                res_tmp = self.aggregate(
                    func=func,
                    columns=columns[i : i + ncols_block],
                    ncols_block=ncols_block,
                )
                if i == 0:
                    result = res_tmp
                else:
                    result.append(res_tmp)
            return result

        # Computing the aggregations using multiple queries at the same time.

        elif ncols_block < len(columns):

            parameters = []
            for i in range(0, len(columns), ncols_block):
                parameters += [(self, func, columns, ncols_block, i)]
            a_pool = multiprocessing.Pool(processes)
            L = a_pool.starmap(func=aggregate_parallel_block, iterable=parameters)
            result = L[0]
            for i in range(1, len(L)):
                result.append(L[i])
            return result

        agg = [[] for i in range(len(columns))]
        nb_precomputed = 0

        # Computing all the other aggregations.

        for idx, column in enumerate(columns):
            cast = "::int" if (self[column].isbool()) else ""
            for fun in func:
                pre_comp = self.__get_catalog_value__(column, fun)

                if pre_comp != "VERTICAPY_NOT_PRECOMPUTED":
                    nb_precomputed += 1
                    if pre_comp == None or pre_comp != pre_comp:
                        expr = "NULL"
                    elif isinstance(pre_comp, (int, float)):
                        expr = pre_comp
                    else:
                        pre_comp_str = str(pre_comp).replace("'", "''")
                        expr = f"'{pre_comp_str}'"

                elif ("_percent" in fun.lower()) and (fun.lower()[0:3] == "top"):
                    n = fun.lower().replace("top", "").replace("_percent", "")
                    if n == "":
                        n = 1
                    try:
                        n = int(n)
                        assert n >= 1
                    except:
                        raise FunctionError(
                            f"The aggregation '{fun}' doesn't exist. To"
                            " compute the frequency of the n-th most "
                            "occurent element, use 'topk_percent' with "
                            "k > 0. For example: top2_percent computes "
                            "the frequency of the second most occurent "
                            "element."
                        )
                    try:
                        expr = str(
                            self[column]
                            .topk(k=n, dropna=False)
                            .values["percent"][n - 1]
                        )
                    except:
                        expr = "0.0"

                elif (len(fun.lower()) > 2) and (fun.lower()[0:3] == "top"):
                    n = fun.lower()[3:] if (len(fun.lower()) > 3) else 1
                    try:
                        n = int(n)
                        assert n >= 1
                    except:
                        raise FunctionError(
                            f"The aggregation '{fun}' doesn't exist. To"
                            " compute the n-th most occurent element, use "
                            "'topk' with n > 0. For example: "
                            "top2 computes the second most occurent element."
                        )
                    expr = format_magic(self[column].mode(n=n))

                elif fun.lower() == "mode":
                    expr = format_magic(self[column].mode(n=1))

                elif fun.lower() in ("kurtosis", "kurt"):
                    count, avg, std = count_avg_stddev[column]
                    if (
                        count == 0
                        or (std != std)
                        or (avg != avg)
                        or (std == None)
                        or (avg == None)
                    ):
                        expr = "NULL"
                    elif (count == 1) or (std == 0):
                        expr = "-3"
                    else:
                        expr = f"AVG(POWER(({column}{cast} - {avg}) / {std}, 4))"
                        if count > 3:
                            expr += f"""
                                * {count * count * (count + 1) / (count - 1) / (count - 2) / (count - 3)} 
                                - 3 * {(count - 1) * (count - 1) / (count - 2) / (count - 3)}"""
                        else:
                            expr += "* - 3"
                            expr += (
                                f"* {count * count / (count - 1) / (count - 2)}"
                                if (count == 3)
                                else ""
                            )

                elif fun.lower() in ("skewness", "skew"):
                    count, avg, std = count_avg_stddev[column]
                    if (
                        count == 0
                        or (std != std)
                        or (avg != avg)
                        or (std == None)
                        or (avg == None)
                    ):
                        expr = "NULL"
                    elif (count == 1) or (std == 0):
                        expr = "0"
                    else:
                        expr = f"AVG(POWER(({column}{cast} - {avg}) / {std}, 3))"
                        if count >= 3:
                            expr += f"* {count * count / (count - 1) / (count - 2)}"

                elif fun.lower() == "jb":
                    count, avg, std = count_avg_stddev[column]
                    if (count < 4) or (std == 0):
                        expr = "NULL"
                    else:
                        expr = f"""
                            {count} / 6 * (POWER(AVG(POWER(({column}{cast} - {avg}) 
                            / {std}, 3)) * {count * count / (count - 1) / (count - 2)}, 
                            2) + POWER(AVG(POWER(({column}{cast} - {avg}) / {std}, 4)) 
                            - 3 * {count * count / (count - 1) / (count - 2)}, 2) / 4)"""

                elif fun.lower() == "dtype":
                    expr = f"'{self[column].ctype()}'"

                elif fun.lower() == "range":
                    expr = f"MAX({column}{cast}) - MIN({column}{cast})"

                elif fun.lower() == "unique":
                    if column in uniques:
                        expr = format_magic(uniques[column][0])
                    else:
                        expr = f"COUNT(DISTINCT {column})"

                elif fun.lower() in ("approx_unique", "approximate_count_distinct"):
                    expr = f"APPROXIMATE_COUNT_DISTINCT({column})"

                elif fun.lower() == "count":
                    expr = f"COUNT({column})"

                elif fun.lower() in ("approx_median", "approximate_median"):
                    expr = f"APPROXIMATE_MEDIAN({column}{cast})"

                elif fun.lower() == "median":
                    expr = f"MEDIAN({column}{cast}) OVER ()"

                elif fun.lower() in ("std", "stddev", "stdev"):
                    expr = f"STDDEV({column}{cast})"

                elif fun.lower() in ("var", "variance"):
                    expr = f"VARIANCE({column}{cast})"

                elif fun.lower() in ("mean", "avg"):
                    expr = f"AVG({column}{cast})"

                elif fun.lower() == "iqr":
                    expr = f"""
                        APPROXIMATE_PERCENTILE({column}{cast} 
                                               USING PARAMETERS
                                               percentile = 0.75) 
                      - APPROXIMATE_PERCENTILE({column}{cast}
                                               USING PARAMETERS 
                                               percentile = 0.25)"""

                elif "%" == fun[-1]:
                    try:
                        if (len(fun.lower()) >= 8) and fun[0:7] == "approx_":
                            percentile = float(fun[7:-1]) / 100
                            expr = f"""
                                APPROXIMATE_PERCENTILE({column}{cast} 
                                                       USING PARAMETERS 
                                                       percentile = {percentile})"""
                        else:
                            if column in exact_percent:
                                expr = format_magic(exact_percent[column][0])
                            else:
                                percentile = float(fun[0:-1]) / 100
                                expr = f"""
                                    PERCENTILE_CONT({percentile}) 
                                                    WITHIN GROUP 
                                                    (ORDER BY {column}{cast}) 
                                                    OVER ()"""
                    except:
                        raise FunctionError(
                            f"The aggregation '{fun}' doesn't exist. If you "
                            "want to compute the percentile x of the element "
                            "please write 'x%' with x > 0. Example: 50% for "
                            "the median or approx_50% for the approximate median."
                        )

                elif fun.lower() == "cvar":
                    q95 = self[column].quantile(0.95)
                    expr = f"""AVG(
                                CASE 
                                    WHEN {column}{cast} >= {q95} 
                                        THEN {column}{cast} 
                                    ELSE NULL 
                                END)"""

                elif fun.lower() == "sem":
                    expr = f"STDDEV({column}{cast}) / SQRT(COUNT({column}))"

                elif fun.lower() == "aad":
                    mean = self[column].avg()
                    expr = f"SUM(ABS({column}{cast} - {mean})) / COUNT({column})"

                elif fun.lower() == "mad":
                    median = self[column].median()
                    expr = f"APPROXIMATE_MEDIAN(ABS({column}{cast} - {median}))"

                elif fun.lower() in ("prod", "product"):
                    expr = f"""
                        DECODE(ABS(MOD(SUM(
                            CASE 
                                WHEN {column}{cast} < 0 THEN 1 
                                ELSE 0 
                            END), 
                        2)), 0, 1, -1) * 
                        POWER(10, SUM(LOG(ABS({column}{cast}))))"""

                elif fun.lower() in ("percent", "count_percent"):
                    expr = (
                        f"ROUND(COUNT({column}) / { self.shape()[0]} * 100, 3)::float"
                    )

                elif "{}" not in fun:
                    expr = f"{fun.upper()}({column}{cast})"

                else:
                    expr = fun.replace("{}", column)

                agg[idx] += [expr]

        for idx, elem in enumerate(func):
            if "AS " in str(elem).upper():
                try:
                    func[idx] = (
                        str(elem)
                        .lower()
                        .split("as ")[1]
                        .replace("'", "")
                        .replace('"', "")
                    )
                except:
                    pass
        values = {"index": func}

        try:

            if nb_precomputed == len(func) * len(columns):
                res = executeSQL(
                    query=f"""
                        SELECT 
                            /*+LABEL('vDataframe.aggregate')*/ 
                            {", ".join([str(item) for sublist in agg for item in sublist])}""",
                    print_time_sql=False,
                    method="fetchrow",
                )
            else:
                res = executeSQL(
                    query=f"""
                        SELECT 
                            /*+LABEL('vDataframe.aggregate')*/ 
                            {", ".join([str(item) for sublist in agg for item in sublist])} 
                        FROM {self.__genSQL__()} 
                        LIMIT 1""",
                    title="Computing the different aggregations.",
                    method="fetchrow",
                    sql_push_ext=self._VERTICAPY_VARIABLES_["sql_push_ext"],
                    symbol=self._VERTICAPY_VARIABLES_["symbol"],
                )
            result = [item for item in res]
            try:
                result = [float(item) for item in result]
            except:
                pass
            values = {"index": func}
            i = 0
            for column in columns:
                values[column] = result[i : i + len(func)]
                i += len(func)

        except:

            try:
                query = [
                    "SELECT {0} FROM vdf_table LIMIT 1".format(
                        ", ".join(
                            [
                                format_magic(item, cast_float_int_to_str=True)
                                for item in elem
                            ]
                        )
                    )
                    for elem in agg
                ]
                query = (
                    " UNION ALL ".join([f"({q})" for q in query])
                    if (len(query) != 1)
                    else query[0]
                )
                query = f"""
                    WITH vdf_table AS 
                        (SELECT 
                            /*+LABEL('vDataframe.aggregate')*/ * 
                         FROM {self.__genSQL__()}) {query}"""
                if nb_precomputed == len(func) * len(columns):
                    result = executeSQL(query, print_time_sql=False, method="fetchall")
                else:
                    result = executeSQL(
                        query,
                        title="Computing the different aggregations using UNION ALL.",
                        method="fetchall",
                        sql_push_ext=self._VERTICAPY_VARIABLES_["sql_push_ext"],
                        symbol=self._VERTICAPY_VARIABLES_["symbol"],
                    )

                for idx, elem in enumerate(result):
                    values[columns[idx]] = [item for item in elem]

            except:

                try:

                    for i, elem in enumerate(agg):
                        pre_comp_val = []
                        for fun in func:
                            pre_comp = self.__get_catalog_value__(columns[i], fun)
                            if pre_comp == "VERTICAPY_NOT_PRECOMPUTED":
                                columns_str = ", ".join(
                                    [
                                        format_magic(item, cast_float_int_to_str=True)
                                        for item in elem
                                    ]
                                )
                                executeSQL(
                                    query=f"""
                                        SELECT 
                                            /*+LABEL('vDataframe.aggregate')*/ 
                                            {columns_str} 
                                        FROM {self.__genSQL__()}""",
                                    title=(
                                        "Computing the different aggregations one "
                                        "vColumn at a time."
                                    ),
                                    sql_push_ext=self._VERTICAPY_VARIABLES_[
                                        "sql_push_ext"
                                    ],
                                    symbol=self._VERTICAPY_VARIABLES_["symbol"],
                                )
                                pre_comp_val = []
                                break
                            pre_comp_val += [pre_comp]
                        if pre_comp_val:
                            values[columns[i]] = pre_comp_val
                        else:
                            values[columns[i]] = [
                                elem for elem in vp.current_cursor().fetchone()
                            ]
                except:

                    for i, elem in enumerate(agg):
                        values[columns[i]] = []
                        for j, agg_fun in enumerate(elem):
                            pre_comp = self.__get_catalog_value__(columns[i], func[j])
                            if pre_comp == "VERTICAPY_NOT_PRECOMPUTED":
                                result = executeSQL(
                                    query=f"""
                                        SELECT 
                                            /*+LABEL('vDataframe.aggregate')*/ 
                                            {agg_fun} 
                                        FROM {self.__genSQL__()}""",
                                    title=(
                                        "Computing the different aggregations one "
                                        "vColumn & one agg at a time."
                                    ),
                                    method="fetchfirstelem",
                                    sql_push_ext=self._VERTICAPY_VARIABLES_[
                                        "sql_push_ext"
                                    ],
                                    symbol=self._VERTICAPY_VARIABLES_["symbol"],
                                )
                            else:
                                result = pre_comp
                            values[columns[i]] += [result]

        for elem in values:
            for idx in range(len(values[elem])):
                if isinstance(values[elem][idx], str) and "top" not in elem:
                    try:
                        values[elem][idx] = float(values[elem][idx])
                    except:
                        pass

        self.__update_catalog__(values)
        return util.tablesample(values=values).decimal_to_float().transpose()

    agg = aggregate

    @save_verticapy_logs
    def all(
        self, columns: list, **agg_kwds,
    ):
        """
    Aggregates the vDataFrame using 'bool_and'.

    Parameters
    ----------
    columns: list
        List of the vColumns names.
    **agg_kwds
        Any optional parameter to pass to the Aggregate function.


    Returns
    -------
    tablesample
        An object containing the result. For more information, see
        utilities.tablesample.

    See Also
    --------
    vDataFrame.aggregate : Computes the vDataFrame input aggregations.
        """
        return self.aggregate(func=["bool_and"], columns=columns, **agg_kwds,)

    @save_verticapy_logs
    def analytic(
        self,
        func: str,
        columns: Union[str, list] = [],
        by: Union[str, list] = [],
        order_by: Union[dict, list] = [],
        name: str = "",
        offset: int = 1,
        x_smoothing: float = 0.5,
        add_count: bool = True,
    ):
        """
    Adds a new vColumn to the vDataFrame by using an advanced analytical 
    function on one or two specific vColumns.

    \u26A0 Warning : Some analytical functions can make the vDataFrame 
                     structure more resource intensive. It is best to check 
                     the structure of the vDataFrame using the 'current_relation' 
                     method and to save it using the 'to_db' method with 
                     the parameters 'inplace = True' and 
                     'relation_type = table'

    Parameters
    ----------
    func: str
        Function to apply.
            aad          : average absolute deviation
            beta         : Beta Coefficient between 2 vColumns
            count        : number of non-missing elements
            corr         : Pearson's correlation between 2 vColumns
            cov          : covariance between 2 vColumns
            dense_rank   : dense rank
            ema          : exponential moving average
            first_value  : first non null lead
            iqr          : interquartile range
            kurtosis     : kurtosis
            jb           : Jarque-Bera index 
            lead         : next element
            lag          : previous element
            last_value   : first non null lag
            mad          : median absolute deviation
            max          : maximum
            mean         : average
            median       : median
            min          : minimum
            mode         : most occurent element
            q%           : q quantile (ex: 50% for the median)
            pct_change   : ratio between the current value and the previous one
            percent_rank : percent rank
            prod         : product
            range        : difference between the max and the min
            rank         : rank
            row_number   : row number
            sem          : standard error of the mean
            skewness     : skewness
            sum          : sum
            std          : standard deviation
            unique       : cardinality (count distinct)
            var          : variance
                Other analytical functions could work if it is part of 
                the DB version you are using.
    columns: str / list, optional
        Input vColumns. It can be a list of one or two elements.
    by: str / list, optional
        vColumns used in the partition.
    order_by: dict / list, optional
        List of the vColumns to use to sort the data using asc order or
        dictionary of all sorting methods. For example, to sort by "column1"
        ASC and "column2" DESC, write {"column1": "asc", "column2": "desc"}
    name: str, optional
        Name of the new vColumn. If empty a default name based on the other
        parameters will be generated.
    offset: int, optional
        Lead/Lag offset if parameter 'func' is the function 'lead'/'lag'.
    x_smoothing: float, optional
        The smoothing parameter of the 'ema' if the function is 'ema'. It must be in [0;1]
    add_count: bool, optional
        If the function is the 'mode' and this parameter is True then another column will 
        be added to the vDataFrame with the mode number of occurences.

    Returns
    -------
    vDataFrame
        self

    See Also
    --------
    vDataFrame.eval    : Evaluates a customized expression.
    vDataFrame.rolling : Computes a customized moving window.
        """
        if isinstance(by, str):
            by = [by]
        if isinstance(order_by, str):
            order_by = [order_by]
        if isinstance(columns, str):
            if columns:
                columns = [columns]
            else:
                columns = []
        columns, by = self.format_colnames(columns, by)
        by_name = ["by"] + by if (by) else []
        by_order = ["order_by"] + [elem for elem in order_by] if (order_by) else []
        if not (name):
            name = gen_name([func] + columns + by_name + by_order)
        func = func.lower()
        by = ", ".join(by)
        by = f"PARTITION BY {by}" if (by) else ""
        order_by = self.__get_sort_syntax__(order_by)
        func = get_verticapy_function(func.lower(), method="vertica")
        if func in (
            "max",
            "min",
            "avg",
            "sum",
            "count",
            "stddev",
            "median",
            "variance",
            "unique",
            "top",
            "kurtosis",
            "skewness",
            "mad",
            "aad",
            "range",
            "prod",
            "jb",
            "iqr",
            "sem",
        ) or ("%" in func):
            if order_by and not (vp.OPTIONS["print_info"]):
                print(
                    f"\u26A0 '{func}' analytic method doesn't need an "
                    "order by clause, it was ignored"
                )
            elif not (columns):
                raise MissingColumn(
                    "The parameter 'column' must be a vDataFrame Column "
                    f"when using analytic method '{func}'"
                )
            if func in ("skewness", "kurtosis", "aad", "mad", "jb"):
                random_nb = random.randint(0, 10000000)
                column_str = columns[0].replace('"', "")
                mean_name = f"{column_str}_mean_{random_nb}"
                median_name = f"{column_str}_median_{random_nb}"
                std_name = f"{column_str}_std_{random_nb}"
                count_name = f"{column_str}_count_{random_nb}"
                all_cols = [elem for elem in self._VERTICAPY_VARIABLES_["columns"]]
                if func == "mad":
                    self.eval(median_name, f"MEDIAN({columns[0]}) OVER ({by})")
                else:
                    self.eval(mean_name, f"AVG({columns[0]}) OVER ({by})")
                if func not in ("aad", "mad"):
                    self.eval(std_name, f"STDDEV({columns[0]}) OVER ({by})")
                    self.eval(count_name, f"COUNT({columns[0]}) OVER ({by})")
                if func == "kurtosis":
                    self.eval(
                        name,
                        f"""AVG(POWER(({columns[0]} - {mean_name}) 
                          / NULLIFZERO({std_name}), 4)) OVER ({by}) 
                          * POWER({count_name}, 2) 
                          * ({count_name} + 1) 
                          / NULLIFZERO(({count_name} - 1) 
                          * ({count_name} - 2) 
                          * ({count_name} - 3)) 
                          - 3 * POWER({count_name} - 1, 2) 
                          / NULLIFZERO(({count_name} - 2) 
                          * ({count_name} - 3))""",
                    )
                elif func == "skewness":
                    self.eval(
                        name,
                        f"""AVG(POWER(({columns[0]} - {mean_name}) 
                         / NULLIFZERO({std_name}), 3)) OVER ({by}) 
                         * POWER({count_name}, 2) 
                         / NULLIFZERO(({count_name} - 1) 
                         * ({count_name} - 2))""",
                    )
                elif func == "jb":
                    self.eval(
                        name,
                        f"""{count_name} / 6 * (POWER(AVG(POWER(({columns[0]} 
                          - {mean_name}) / NULLIFZERO({std_name}), 3)) OVER ({by}) 
                          * POWER({count_name}, 2) / NULLIFZERO(({count_name} - 1) 
                          * ({count_name} - 2)), 2) + POWER(AVG(POWER(({columns[0]} 
                          - {mean_name}) / NULLIFZERO({std_name}), 4)) OVER ({by}) 
                          * POWER({count_name}, 2) * ({count_name} + 1) 
                          / NULLIFZERO(({count_name} - 1) * ({count_name} - 2) 
                          * ({count_name} - 3)) - 3 * POWER({count_name} - 1, 2) 
                          / NULLIFZERO(({count_name} - 2) * ({count_name} - 3)), 2) / 4)""",
                    )
                elif func == "aad":
                    self.eval(
                        name, f"AVG(ABS({columns[0]} - {mean_name})) OVER ({by})",
                    )
                elif func == "mad":
                    self.eval(
                        name, f"AVG(ABS({columns[0]} - {median_name})) OVER ({by})",
                    )
            elif func == "top":
                if not (by):
                    by_str = f"PARTITION BY {columns[0]}"
                else:
                    by_str = f"{by}, {columns[0]}"
                self.eval(name, f"ROW_NUMBER() OVER ({by_str})")
                if add_count:
                    name_str = name.replace('"', "")
                    self.eval(
                        f"{name_str}_count",
                        f"NTH_VALUE({name}, 1) OVER ({by} ORDER BY {name} DESC)",
                    )
                self[name].apply(
                    f"NTH_VALUE({columns[0]}, 1) OVER ({by} ORDER BY {{}} DESC)"
                )
            elif func == "unique":
                self.eval(
                    name,
                    f"""DENSE_RANK() OVER ({by} ORDER BY {columns[0]} ASC) 
                      + DENSE_RANK() OVER ({by} ORDER BY {columns[0]} DESC) - 1""",
                )
            elif "%" == func[-1]:
                try:
                    x = float(func[0:-1]) / 100
                except:
                    raise FunctionError(
                        f"The aggregate function '{fun}' doesn't exist. "
                        "If you want to compute the percentile x of the "
                        "element please write 'x%' with x > 0. Example: "
                        "50% for the median."
                    )
                self.eval(
                    name,
                    f"PERCENTILE_CONT({x}) WITHIN GROUP(ORDER BY {columns[0]}) OVER ({by})",
                )
            elif func == "range":
                self.eval(
                    name,
                    f"MAX({columns[0]}) OVER ({by}) - MIN({columns[0]}) OVER ({by})",
                )
            elif func == "iqr":
                self.eval(
                    name,
                    f"""PERCENTILE_CONT(0.75) WITHIN GROUP(ORDER BY {columns[0]}) OVER ({by}) 
                      - PERCENTILE_CONT(0.25) WITHIN GROUP(ORDER BY {columns[0]}) OVER ({by})""",
                )
            elif func == "sem":
                self.eval(
                    name,
                    f"STDDEV({columns[0]}) OVER ({by}) / SQRT(COUNT({columns[0]}) OVER ({by}))",
                )
            elif func == "prod":
                self.eval(
                    name,
                    f"""DECODE(ABS(MOD(SUM(CASE 
                                            WHEN {columns[0]} < 0 
                                            THEN 1 ELSE 0 END) 
                                       OVER ({by}), 2)), 0, 1, -1) 
                     * POWER(10, SUM(LOG(ABS({columns[0]}))) 
                                 OVER ({by}))""",
                )
            else:
                self.eval(name, f"{func.upper()}({columns[0]}) OVER ({by})")
        elif func in (
            "lead",
            "lag",
            "row_number",
            "percent_rank",
            "dense_rank",
            "rank",
            "first_value",
            "last_value",
            "exponential_moving_average",
            "pct_change",
        ):
            if not (columns) and func in (
                "lead",
                "lag",
                "first_value",
                "last_value",
                "pct_change",
            ):
                raise ParameterError(
                    "The parameter 'columns' must be a vDataFrame column when "
                    f"using analytic method '{func}'"
                )
            elif (columns) and func not in (
                "lead",
                "lag",
                "first_value",
                "last_value",
                "pct_change",
                "exponential_moving_average",
            ):
                raise ParameterError(
                    "The parameter 'columns' must be empty when using analytic"
                    f" method '{func}'"
                )
            if (by) and (order_by):
                order_by = f" {order_by}"
            if func in ("lead", "lag"):
                info_param = f", {offset}"
            elif func in ("last_value", "first_value"):
                info_param = " IGNORE NULLS"
            elif func == "exponential_moving_average":
                info_param = f", {x_smoothing}"
            else:
                info_param = ""
            if func == "pct_change":
                self.eval(
                    name, f"{columns[0]} / (LAG({columns[0]}) OVER ({by}{order_by}))",
                )
            else:
                columns0 = columns[0] if (columns) else ""
                self.eval(
                    name,
                    f"{func.upper()}({columns0}{info_param}) OVER ({by}{order_by})",
                )
        elif func in ("corr", "cov", "beta"):
            if order_by:
                print(
                    f"\u26A0 '{func}' analytic method doesn't need an "
                    "order by clause, it was ignored"
                )
            assert len(columns) == 2, MissingColumn(
                "The parameter 'columns' includes 2 vColumns when using "
                f"analytic method '{func}'"
            )
            if columns[0] == columns[1]:
                if func == "cov":
                    expr = f"VARIANCE({columns[0]}) OVER ({by})"
                else:
                    expr = 1
            else:
                if func == "corr":
                    den = f" / (STDDEV({columns[0]}) OVER ({by}) * STDDEV({columns[1]}) OVER ({by}))"
                elif func == "beta":
                    den = f" / (VARIANCE({columns[1]}) OVER ({by}))"
                else:
                    den = ""
                expr = f"""
                    (AVG({columns[0]} * {columns[1]}) OVER ({by}) 
                   - AVG({columns[0]}) OVER ({by}) 
                   * AVG({columns[1]}) OVER ({by})){den}"""
            self.eval(name, expr)
        else:
            try:
                self.eval(
                    name,
                    f"{func.upper()}({columns[0]}{info_param}) OVER ({by}{order_by})",
                )
            except:
                raise FunctionError(
                    f"The aggregate function '{func}' doesn't exist or is not "
                    "managed by the 'analytic' method. If you want more "
                    "flexibility use the 'eval' method."
                )
        if func in ("kurtosis", "skewness", "jb"):
            self._VERTICAPY_VARIABLES_["exclude_columns"] += [
                quote_ident(mean_name),
                quote_ident(std_name),
                quote_ident(count_name),
            ]
        elif func == "aad":
            self._VERTICAPY_VARIABLES_["exclude_columns"] += [quote_ident(mean_name)]
        elif func == "mad":
            self._VERTICAPY_VARIABLES_["exclude_columns"] += [quote_ident(median_name)]
        return self

    @save_verticapy_logs
    def animated(
        self,
        ts: str,
        columns: Union[list] = [],
        by: str = "",
        start_date: Union[str, int, float, datetime.datetime, datetime.date] = "",
        end_date: Union[str, int, float, datetime.datetime, datetime.date] = "",
        kind: Literal["auto", "bar", "bubble", "ts", "pie"] = "auto",
        limit_over: int = 6,
        limit: int = 1000000,
        limit_labels: int = 6,
        ts_steps: dict = {"window": 100, "step": 5},
        bubble_img: dict = {"bbox": [], "img": ""},
        fixed_xy_lim: bool = False,
        date_in_title: bool = False,
        date_f=None,
        date_style_dict: dict = {},
        interval: int = 300,
        repeat: bool = True,
        return_html: bool = True,
        ax=None,
        **style_kwds,
    ):
        """
    Draws the animated chart.

    Parameters
    ----------
    ts: str
        TS (Time Series) vColumn to use to order the data. The vColumn type must be
        date like (date, datetime, timestamp...) or numerical.
    columns: str / list, optional
        List of the vColumns names.
    by: str, optional
        Categorical vColumn used in the partition.
    start_date: str / date, optional
        Input Start Date. For example, time = '03-11-1993' will filter the data when 
        'ts' is lesser than November 1993 the 3rd.
    end_date: str / date, optional
        Input End Date. For example, time = '03-11-1993' will filter the data when 
        'ts' is greater than November 1993 the 3rd.
    kind: str, optional
        Animation Type.
            auto   : Pick up automatically the type.
            bar    : Animated Bar Race.
            bubble : Animated Bubble Plot.
            pie    : Animated Pie Chart.
            ts     : Animated Time Series.
    limit_over: int, optional
        Limited number of elements to consider for each category.
    limit: int, optional
        Maximum number of data points to use.
    limit_labels: int, optional
        [Only used when kind = 'bubble']
        Maximum number of text labels to draw.
    ts_steps: dict, optional
        [Only used when kind = 'ts']
        dictionary including 2 keys.
            step   : number of elements used to update the time series.
            window : size of the window used to draw the time series.
    bubble_img: dict, optional
        [Only used when kind = 'bubble']
        dictionary including 2 keys.
            img  : Path to the image to display as background.
            bbox : List of 4 elements to delimit the boundaries of the final Plot.
                   It must be similar the following list: [xmin, xmax, ymin, ymax]
    fixed_xy_lim: bool, optional
        If set to True, the xlim and ylim will be fixed.
    date_in_title: bool, optional
        If set to True, the ts vColumn will be displayed in the title section.
    date_f: function, optional
        Function used to display the ts vColumn.
    date_style_dict: dict, optional
        Style Dictionary used to display the ts vColumn when date_in_title = False.
    interval: int, optional
        Number of ms between each update.
    repeat: bool, optional
        If set to True, the animation will be repeated.
    return_html: bool, optional
        If set to True and if using a Jupyter notebook, the HTML of the animation will be 
        generated.
    ax: Matplotlib axes object, optional
        The axes to plot on.
    **style_kwds
        Any optional parameter to pass to the Matplotlib functions.

    Returns
    -------
    animation
        Matplotlib animation object
        """
        if isinstance(columns, str):
            columns = [columns]
        if kind == "auto":
            if len(columns) > 3 or len(columns) <= 1:
                kind = "ts"
            elif len(columns) == 2:
                kind = "bar"
            else:
                kind = "bubble"
        assert kind == "ts" or columns, ParameterError(
            f"Parameter 'columns' can not be empty when using kind = '{kind}'."
        )
        assert (
            2 <= len(columns) <= 4
            and self[columns[0]].isnum()
            and self[columns[1]].isnum()
        ) or kind != "bubble", ParameterError(
            f"Parameter 'columns' must include at least 2 numerical vColumns and maximum 4 vColumns when using kind = '{kind}'."
        )
        columns, ts, by = self.format_colnames(columns, ts, by)
        if kind == "bubble":
            if len(columns) == 3 and not (self[columns[2]].isnum()):
                label_name = columns[2]
                columns = columns[0:2]
            elif len(columns) >= 4:
                if not (self[columns[3]].isnum()):
                    label_name = columns[3]
                    columns = columns[0:3]
                else:
                    label_name = columns[2]
                    columns = columns[0:2] + [columns[3]]
            else:
                label_name = ""
            if "img" not in bubble_img:
                bubble_img["img"] = ""
            if "bbox" not in bubble_img:
                bubble_img["bbox"] = []
            return plt.animated_bubble_plot(
                self,
                order_by=ts,
                columns=columns,
                label_name=label_name,
                by=by,
                order_by_start=start_date,
                order_by_end=end_date,
                limit_over=limit_over,
                limit=limit,
                lim_labels=limit_labels,
                fixed_xy_lim=fixed_xy_lim,
                date_in_title=date_in_title,
                date_f=date_f,
                date_style_dict=date_style_dict,
                interval=interval,
                repeat=repeat,
                return_html=return_html,
                img=bubble_img["img"],
                bbox=bubble_img["bbox"],
                ax=ax,
                **style_kwds,
            )
        elif kind in ("bar", "pie"):
            return plt.animated_bar(
                self,
                order_by=ts,
                columns=columns,
                by=by,
                order_by_start=start_date,
                order_by_end=end_date,
                limit_over=limit_over,
                limit=limit,
                fixed_xy_lim=fixed_xy_lim,
                date_in_title=date_in_title,
                date_f=date_f,
                date_style_dict=date_style_dict,
                interval=interval,
                repeat=repeat,
                return_html=return_html,
                pie=(kind == "pie"),
                ax=ax,
                **style_kwds,
            )
        else:
            if by:
                assert len(columns) == 1, ParameterError(
                    "Parameter 'columns' can not be empty when using kind = 'ts' and when parameter 'by' is not empty."
                )
                vdf = self.pivot(index=ts, columns=by, values=columns[0])
            else:
                vdf = self
            columns = vdf.numcol()[0:limit_over]
            if "step" not in ts_steps:
                ts_steps["step"] = 5
            if "window" not in ts_steps:
                ts_steps["window"] = 100
            return plt.animated_ts_plot(
                vdf,
                order_by=ts,
                columns=columns,
                order_by_start=start_date,
                order_by_end=end_date,
                limit=limit,
                fixed_xy_lim=fixed_xy_lim,
                window_size=ts_steps["window"],
                step=ts_steps["step"],
                interval=interval,
                repeat=repeat,
                return_html=return_html,
                ax=ax,
                **style_kwds,
            )

    @save_verticapy_logs
    def any(
        self, columns: list, **agg_kwds,
    ):
        """
    Aggregates the vDataFrame using 'bool_or'.

    Parameters
    ----------
    columns: list
        List of the vColumns names.
    **agg_kwds
        Any optional parameter to pass to the Aggregate function.

    Returns
    -------
    tablesample
        An object containing the result. For more information, see
        utilities.tablesample.

    See Also
    --------
    vDataFrame.aggregate : Computes the vDataFrame input aggregations.
        """
        return self.aggregate(func=["bool_or"], columns=columns, **agg_kwds,)

    @save_verticapy_logs
    def append(
        self,
        input_relation: Union[str, str_sql],
        expr1: Union[str, list] = [],
        expr2: Union[str, list] = [],
        union_all: bool = True,
    ):
        """
    Merges the vDataFrame with another one or an input relation and returns 
    a new vDataFrame.

    Parameters
    ----------
    input_relation: str / vDataFrame
        Relation to use to do the merging.
    expr1: str / list, optional
        List of pure-SQL expressions from the current vDataFrame to use during merging.
        For example, 'CASE WHEN "column" > 3 THEN 2 ELSE NULL END' and 'POWER("column", 2)' 
        will work. If empty, all vDataFrame vColumns will be used. Aliases are 
        recommended to avoid auto-naming.
    expr2: str / list, optional
        List of pure-SQL expressions from the input relation to use during the merging.
        For example, 'CASE WHEN "column" > 3 THEN 2 ELSE NULL END' and 'POWER("column", 2)' 
        will work. If empty, all input relation columns will be used. Aliases are 
        recommended to avoid auto-naming.
    union_all: bool, optional
        If set to True, the vDataFrame will be merged with the input relation using an
        'UNION ALL' instead of an 'UNION'.

    Returns
    -------
    vDataFrame
       vDataFrame of the Union

    See Also
    --------
    vDataFrame.groupby : Aggregates the vDataFrame.
    vDataFrame.join    : Joins the vDataFrame with another relation.
    vDataFrame.sort    : Sorts the vDataFrame.
        """
        if isinstance(expr1, str):
            expr1 = [expr1]
        if isinstance(expr2, str):
            expr2 = [expr2]
        first_relation = self.__genSQL__()
        if isinstance(input_relation, str):
            second_relation = input_relation
        elif isinstance(input_relation, vDataFrame):
            second_relation = input_relation.__genSQL__()
        columns = ", ".join(self.get_columns()) if not (expr1) else ", ".join(expr1)
        columns2 = columns if not (expr2) else ", ".join(expr2)
        union = "UNION" if not (union_all) else "UNION ALL"
        table = f"""
            (SELECT 
                {columns} 
             FROM {first_relation}) 
             {union} 
            (SELECT 
                {columns2} 
             FROM {second_relation})"""
        return self.__vDataFrameSQL__(
            f"({table}) append_table",
            self._VERTICAPY_VARIABLES_["input_relation"],
            "[Append]: Union of two relations",
        )

    @save_verticapy_logs
    def apply(self, func: dict):
        """
    Applies each function of the dictionary to the input vColumns.

    Parameters
     ----------
     func: dict
        Dictionary of functions.
        The dictionary must be like the following: 
        {column1: func1, ..., columnk: funck}. Each function variable must
        be composed of two flower brackets {}. For example to apply the 
        function: x -> x^2 + 2 use "POWER({}, 2) + 2".

     Returns
     -------
     vDataFrame
        self

    See Also
    --------
    vDataFrame.applymap : Applies a function to all vColumns.
    vDataFrame.eval     : Evaluates a customized expression.
        """
        func = self.format_colnames(func)
        for column in func:
            self[column].apply(func[column])
        return self

    @save_verticapy_logs
    def applymap(self, func: str, numeric_only: bool = True):
        """
    Applies a function to all vColumns. 

    Parameters
    ----------
    func: str
        The function.
        The function variable must be composed of two flower brackets {}. 
        For example to apply the function: x -> x^2 + 2 use "POWER({}, 2) + 2".
    numeric_only: bool, optional
        If set to True, only the numerical columns will be used.

    Returns
    -------
    vDataFrame
        self

    See Also
    --------
    vDataFrame.apply : Applies functions to the input vColumns.
        """
        function = {}
        columns = self.numcol() if numeric_only else self.get_columns()
        for column in columns:
            function[column] = (
                func if not (self[column].isbool()) else func.replace("{}", "{}::int")
            )
        return self.apply(function)

    @save_verticapy_logs
    def interpolate(
        self,
        ts: str,
        rule: Union[str, datetime.timedelta],
        method: dict = {},
        by: Union[str, list] = [],
    ):
        """
    Computes a regular time interval vDataFrame by interpolating the missing 
    values using different techniques.

    Parameters
    ----------
    ts: str
        TS (Time Series) vColumn to use to order the data. The vColumn type 
        must be date like (date, datetime, timestamp...)
    rule: str / time
        Interval used to create the time slices. The final interpolation is 
        divided by these intervals. For example, specifying '5 minutes' 
        creates records separated by time intervals of '5 minutes' 
    method: dict, optional
        Dictionary, with the following format, of interpolation methods:
        {"column1": "interpolation1" ..., "columnk": "interpolationk"}
        Interpolation methods must be one of the following:
            bfill  : Interpolates with the final value of the time slice.
            ffill  : Interpolates with the first value of the time slice.
            linear : Linear interpolation.
    by: str / list, optional
        vColumns used in the partition.

    Returns
    -------
    vDataFrame
        object result of the interpolation.

    See Also
    --------
    vDataFrame[].fillna  : Fills the vColumn missing values.
    vDataFrame[].slice   : Slices the vColumn.
        """
        if isinstance(by, str):
            by = [by]
        method, ts, by = self.format_colnames(method, ts, by)
        all_elements = []
        for column in method:
            assert method[column] in (
                "bfill",
                "backfill",
                "pad",
                "ffill",
                "linear",
            ), ParameterError(
                "Each element of the 'method' dictionary must be "
                "in bfill|backfill|pad|ffill|linear"
            )
            if method[column] in ("bfill", "backfill"):
                func, interp = "TS_LAST_VALUE", "const"
            elif method[column] in ("pad", "ffill"):
                func, interp = "TS_FIRST_VALUE", "const"
            else:
                func, interp = "TS_FIRST_VALUE", "linear"
            all_elements += [f"{func}({column}, '{interp}') AS {column}"]
        table = f"SELECT {{}} FROM {self.__genSQL__()}"
        tmp_query = [f"slice_time AS {quote_ident(ts)}"]
        tmp_query += [quote_ident(column) for column in by]
        tmp_query += all_elements
        table = table.format(", ".join(tmp_query))
        partition = ""
        if by:
            partition = ", ".join([quote_ident(column) for column in by])
            partition = f"PARTITION BY {partition} "
        table += f""" 
            TIMESERIES slice_time AS '{rule}' 
            OVER ({partition}ORDER BY {quote_ident(ts)}::timestamp)"""
        return self.__vDataFrameSQL__(
            f"({table}) interpolate",
            "interpolate",
            "[interpolate]: The data was resampled",
        )

    asfreq = interpolate

    @save_verticapy_logs
    def astype(self, dtype: dict):
        """
    Converts the vColumns to the input types.

    Parameters
    ----------
    dtype: dict
        Dictionary of the different types. Each key of the dictionary must 
        represent a vColumn. The dictionary must be similar to the 
        following: {"column1": "type1", ... "columnk": "typek"}

    Returns
    -------
    vDataFrame
        self
        """
        for column in dtype:
            self[self.format_colnames(column)].astype(dtype=dtype[column])
        return self

    @save_verticapy_logs
    def at_time(self, ts: str, time: Union[str, datetime.timedelta]):
        """
    Filters the vDataFrame by only keeping the records at the input time.

    Parameters
    ----------
    ts: str
        TS (Time Series) vColumn to use to filter the data. The vColumn type must be
        date like (date, datetime, timestamp...)
    time: str / time
        Input Time. For example, time = '12:00' will filter the data when time('ts') 
        is equal to 12:00.

    Returns
    -------
    vDataFrame
        self

    See Also
    --------
    vDataFrame.between_time : Filters the data between two time ranges.
    vDataFrame.first        : Filters the data by only keeping the first records.
    vDataFrame.filter       : Filters the data using the input expression.
    vDataFrame.last         : Filters the data by only keeping the last records.
        """
        self.filter(f"{self.format_colnames(ts)}::time = '{time}'")
        return self

    @save_verticapy_logs
    def avg(
        self, columns: list = [], **agg_kwds,
    ):
        """
    Aggregates the vDataFrame using 'avg' (Average).

    Parameters
    ----------
    columns: list, optional
        List of the vColumns names. If empty, all numerical vColumns will be 
        used.
    **agg_kwds
        Any optional parameter to pass to the Aggregate function.

    Returns
    -------
    tablesample
        An object containing the result. For more information, see
        utilities.tablesample.

    See Also
    --------
    vDataFrame.aggregate : Computes the vDataFrame input aggregations.
        """
        return self.aggregate(func=["avg"], columns=columns, **agg_kwds,)

    mean = avg

    @save_verticapy_logs
    def bar(
        self,
        columns: Union[str, list],
        method: str = "density",
        of: str = "",
        max_cardinality: tuple = (6, 6),
        h: tuple = (None, None),
        hist_type: Literal[
            "auto",
            "fully_stacked",
            "stacked",
            "fully",
            "fully stacked",
            "pyramid",
            "density",
        ] = "auto",
        ax=None,
        **style_kwds,
    ):
        """
    Draws the bar chart of the input vColumns based on an aggregation.

    Parameters
    ----------
    columns: str / list
        List of the vColumns names. The list must have one or two elements.
    method: str, optional
        The method to use to aggregate the data.
            count   : Number of elements.
            density : Percentage of the distribution.
            mean    : Average of the vColumn 'of'.
            min     : Minimum of the vColumn 'of'.
            max     : Maximum of the vColumn 'of'.
            sum     : Sum of the vColumn 'of'.
            q%      : q Quantile of the vColumn 'of' (ex: 50% to get the median).
        It can also be a cutomized aggregation (ex: AVG(column1) + 5).
    of: str, optional
         The vColumn to use to compute the aggregation.
    h: tuple, optional
        Interval width of the vColumns 1 and 2 bars. It is only valid if the 
        vColumns are numerical. Optimized h will be computed if the parameter 
        is empty or invalid.
    max_cardinality: tuple, optional
        Maximum number of distinct elements for vColumns 1 and 2 to be used as 
        categorical (No h will be picked or computed)
    hist_type: str, optional
        The Histogram Type.
            auto          : Regular Bar Chart based on 1 or 2 vColumns.
            pyramid       : Pyramid Density Bar Chart. Only works if one of
                            the two vColumns is binary and the 'method' is 
                            set to 'density'.
            stacked       : Stacked Bar Chart based on 2 vColumns.
            fully_stacked : Fully Stacked Bar Chart based on 2 vColumns.
    ax: Matplotlib axes object, optional
        The axes to plot on.
    **style_kwds
        Any optional parameter to pass to the Matplotlib functions.

    Returns
    -------
    ax
        Matplotlib axes object

     See Also
     --------
     vDataFrame.boxplot     : Draws the Box Plot of the input vColumns.
     vDataFrame.hist        : Draws the histogram of the input vColumns based 
                              on an aggregation.
     vDataFrame.pivot_table : Draws the pivot table of vColumns based on an 
                              aggregation.
        """
        if isinstance(columns, str):
            columns = [columns]
        columns, of = self.format_colnames(columns, of, expected_nb_of_cols=[1, 2])
        if len(columns) == 1:
            return self[columns[0]].bar(method, of, 6, 0, 0, ax=ax, **style_kwds)
        else:
            stacked, fully_stacked, density = False, False, False
            if hist_type in ("fully", "fully stacked", "fully_stacked"):
                fully_stacked = True
            elif hist_type == "stacked":
                stacked = True
            elif hist_type in ("pyramid", "density"):
                density = True
            return plt.bar2D(
                self,
                columns,
                method,
                of,
                max_cardinality,
                h,
                stacked,
                fully_stacked,
                density,
                ax=ax,
                **style_kwds,
            )

    @save_verticapy_logs
    def balance(
        self,
        column: str,
        method: Literal["hybrid", "over", "under"] = "hybrid",
        x: float = 0.5,
        order_by: Union[str, list] = [],
    ):
        """
    Balances the dataset using the input method.

    \u26A0 Warning : If the data is not sorted, the generated SQL code may
                     differ between attempts.

    Parameters
    ----------
    column: str
        Column used to compute the different categories.
    method: str, optional
        The method with which to sample the data
            hybrid : hybrid sampling
            over   : oversampling
            under  : undersampling
    x: float, optional
        The desired ratio between the majority class and minority classes.
        Only used when method is 'over' or 'under'.
    order_by: str / list, optional
        vColumns used to sort the data.

    Returns
    -------
    vDataFrame
        balanced vDataFrame
        """
        column, order_by = self.format_colnames(column, order_by)
        if isinstance(order_by, str):
            order_by = [order_by]
        assert 0 < x < 1, ParameterError("Parameter 'x' must be between 0 and 1")
        topk = self[column].topk()
        last_count, last_elem, n = (
            topk["count"][-1],
            topk["index"][-1],
            len(topk["index"]),
        )
        if method == "over":
            last_count = last_count * x
        elif method == "under":
            last_count = last_count / x
        vdf = self.search(f"{column} = '{last_elem}'")
        for i in range(n - 1):
            vdf = vdf.append(
                self.search(f"{column} = '{topk['index'][i]}'").sample(
                    n=int(last_count)
                )
            )
        vdf.sort(order_by)
        return vdf

    @save_verticapy_logs
    def between_time(
        self,
        ts: str,
        start_time: Union[str, datetime.timedelta],
        end_time: Union[str, datetime.timedelta],
    ):
        """
    Filters the vDataFrame by only keeping the records between two input times.

    Parameters
    ----------
    ts: str
        TS (Time Series) vColumn to use to filter the data. The vColumn type must be
        date like (date, datetime, timestamp...)
    start_time: str / time
        Input Start Time. For example, time = '12:00' will filter the data when 
        time('ts') is lesser than 12:00.
    end_time: str / time
        Input End Time. For example, time = '14:00' will filter the data when 
        time('ts') is greater than 14:00.

    Returns
    -------
    vDataFrame
        self

    See Also
    --------
    vDataFrame.at_time : Filters the data at the input time.
    vDataFrame.first   : Filters the data by only keeping the first records.
    vDataFrame.filter  : Filters the data using the input expression.
    vDataFrame.last    : Filters the data by only keeping the last records.
        """
        self.filter(
            f"{self.format_colnames(ts)}::time BETWEEN '{start_time}' AND '{end_time}'",
        )
        return self

    @save_verticapy_logs
    def bool_to_int(self):
        """
    Converts all booleans vColumns to integers.

    Returns
    -------
    vDataFrame
        self
    
    See Also
    --------
    vDataFrame.astype : Converts the vColumns to the input types.
        """
        columns = self.get_columns()
        for column in columns:
            if self[column].isbool():
                self[column].astype("int")
        return self

    @save_verticapy_logs
    def boxplot(self, columns: Union[str, list] = [], ax=None, **style_kwds):
        """
    Draws the Box Plot of the input vColumns. 

    Parameters
    ----------
    columns: str / list, optional
        List of the vColumns names. If empty, all numerical vColumns will 
        be used.
    ax: Matplotlib axes object, optional
        The axes to plot on.
    **style_kwds
        Any optional parameter to pass to the Matplotlib functions.

    Returns
    -------
    ax
        Matplotlib axes object

    See Also
    --------
    vDataFrame.bar         : Draws the bar chart of the input vColumns based 
                             on an aggregation.
    vDataFrame.boxplot     : Draws the vColumn box plot.
    vDataFrame.hist        : Draws the histogram of the input vColumns based 
                             on an aggregation.
    vDataFrame.pivot_table : Draws the pivot table of vColumns based on an 
                             aggregation.
        """
        if isinstance(columns, str):
            columns = [columns]
        columns = self.format_colnames(columns) if (columns) else self.numcol()
        return plt.boxplot2D(self, columns, ax=ax, **style_kwds)

    @save_verticapy_logs
    def bubble(
        self,
        columns: Union[str, list],
        size_bubble_col: str = "",
        catcol: str = "",
        cmap_col: str = "",
        max_nb_points: int = 20000,
        bbox: list = [],
        img: str = "",
        ax=None,
        **style_kwds,
    ):
        """
    Draws the bubble plot of the input vColumns.

    Parameters
    ----------
    columns: str / list
        List of the vColumns names. The list must have two elements.
    size_bubble_col: str
        Numerical vColumn to use to represent the Bubble size.
    catcol: str, optional
        Categorical column used as color.
    cmap_col: str, optional
        Numerical column used with a color map as color.
    max_nb_points: int, optional
        Maximum number of points to display.
    bbox: list, optional
        List of 4 elements to delimit the boundaries of the final Plot. 
        It must be similar the following list: [xmin, xmax, ymin, ymax]
    img: str, optional
        Path to the image to display as background.
    ax: Matplotlib axes object, optional
        The axes to plot on.
    **style_kwds
        Any optional parameter to pass to the Matplotlib functions.

    Returns
    -------
    ax
       Matplotlib axes object

    See Also
    --------
    vDataFrame.scatter : Draws the scatter plot of the input vColumns.
        """
        if isinstance(columns, str):
            columns = [columns]
        columns, catcol, size_bubble_col, cmap_col = self.format_colnames(
            columns, catcol, size_bubble_col, cmap_col, expected_nb_of_cols=2
        )
        return plt.bubble(
            self,
            columns + [size_bubble_col] if size_bubble_col else columns,
            catcol,
            cmap_col,
            max_nb_points,
            bbox,
            img,
            ax=ax,
            **style_kwds,
        )

    def catcol(self, max_cardinality: int = 12):
        """
    Returns the vDataFrame categorical vColumns.
    
    Parameters
    ----------
    max_cardinality: int, optional
        Maximum number of unique values to consider integer vColumns as categorical.

    Returns
    -------
    List
        List of the categorical vColumns names.
    
    See Also
    --------
    vDataFrame.get_columns : Returns a list of names of the vColumns in the vDataFrame.
    vDataFrame.numcol      : Returns a list of names of the numerical vColumns in the 
                             vDataFrame.
        """
        # -#
        columns = []
        for column in self.get_columns():
            if (self[column].category() == "int") and not (self[column].isbool()):
                is_cat = executeSQL(
                    query=f"""
                        SELECT 
                            /*+LABEL('vDataframe.catcol')*/ 
                            (APPROXIMATE_COUNT_DISTINCT({column}) < {max_cardinality}) 
                        FROM {self.__genSQL__()}""",
                    title="Looking at columns with low cardinality.",
                    method="fetchfirstelem",
                    sql_push_ext=self._VERTICAPY_VARIABLES_["sql_push_ext"],
                    symbol=self._VERTICAPY_VARIABLES_["symbol"],
                )
            elif self[column].category() == "float":
                is_cat = False
            else:
                is_cat = True
            if is_cat:
                columns += [column]
        return columns

    @save_verticapy_logs
    def cdt(
        self,
        columns: Union[str, list] = [],
        max_cardinality: int = 20,
        nbins: int = 10,
        tcdt: bool = True,
        drop_transf_cols: bool = True,
    ):
        """
    Returns the complete disjunctive table of the vDataFrame.
    Numerical features are transformed to categorical using
    the 'discretize' method. Applying PCA on TCDT leads to MCA 
    (Multiple correspondence analysis).

    \u26A0 Warning : This method can become computationally expensive when
                     used with categorical variables with many categories.

    Parameters
    ----------
    columns: str / list, optional
        List of the vColumns names.
    max_cardinality: int, optional
        For any categorical variable, keeps the most frequent categories and 
        merges the less frequent categories into a new unique category.
    nbins: int, optional
        Number of bins used for the discretization (must be > 1).
    tcdt: bool, optional
        If set to True, returns the transformed complete disjunctive table 
        (TCDT). 
    drop_transf_cols: bool, optional
        If set to True, drops the columns used during the transformation.

    Returns
    -------
    vDataFrame
        the CDT relation.
        """
        if isinstance(columns, str):
            columns = [columns]
        if columns:
            columns = self.format_colnames(columns)
        else:
            columns = self.get_columns()
        vdf = self.copy()
        columns_to_drop = []
        for elem in columns:
            if vdf[elem].isbool():
                vdf[elem].astype("int")
            elif vdf[elem].isnum():
                vdf[elem].discretize(nbins=nbins)
                columns_to_drop += [elem]
            elif vdf[elem].isdate():
                vdf[elem].drop()
            else:
                vdf[elem].discretize(method="topk", k=max_cardinality)
                columns_to_drop += [elem]
        new_columns = vdf.get_columns()
        vdf.one_hot_encode(
            columns=columns,
            max_cardinality=max(max_cardinality, nbins) + 2,
            drop_first=False,
        )
        new_columns = vdf.get_columns(exclude_columns=new_columns)
        if drop_transf_cols:
            vdf.drop(columns=columns_to_drop)
        if tcdt:
            for elem in new_columns:
                sum_cat = vdf[elem].sum()
                vdf[elem].apply(f"{{}} / {sum_cat} - 1")
        return vdf

    @save_verticapy_logs
    def chaid(
        self,
        response: str,
        columns: Union[str, list],
        nbins: int = 4,
        method: Literal["smart", "same_width"] = "same_width",
        RFmodel_params: dict = {},
        **kwds,
    ):
        """
    Returns a CHAID (Chi-square Automatic Interaction Detector) tree.
    CHAID is a decision tree technique based on adjusted significance testing 
    (Bonferroni test).

    Parameters
    ----------
    response: str
        Categorical response vColumn.
    columns: str / list
        List of the vColumn names. The maximum number of categories for each
        categorical column is 16; categorical columns with a higher cardinality
        are discarded.
    nbins: int, optional
        Integer in the range [2,16], the number of bins used 
        to discretize the numerical features.
    method: str, optional
        The method with which to discretize the numerical vColumns, 
        one of the following:
            same_width : Computes bins of regular width.
            smart      : Uses a random forest model on a response column to find the best
                interval for discretization.
    RFmodel_params: dict, optional
        Dictionary of the parameters of the random forest model used to compute the best splits 
        when 'method' is 'smart'. If the response column is numerical (but not of type int or bool), 
        this function trains and uses a random forest regressor. Otherwise, this function 
        trains a random forest classifier.
        For example, to train a random forest with 20 trees and a maximum depth of 10, use:
            {"n_estimators": 20, "max_depth": 10}

    Returns
    -------
    memModel
        An independent model containing the result. For more information, see
        learn.memmodel.
        """
        if "process" not in kwds or kwds["process"]:
            if isinstance(columns, str):
                columns = [columns]
            assert 2 <= nbins <= 16, ParameterError(
                "Parameter 'nbins' must be between 2 and 16, inclusive."
            )
            columns = self.chaid_columns(columns)
            if not (columns):
                raise ValueError("No column to process.")
        idx = 0 if ("node_id" not in kwds) else kwds["node_id"]
        p = self.pivot_table_chi2(response, columns, nbins, method, RFmodel_params)
        categories, split_predictor, is_numerical, chi2 = (
            p["categories"][0],
            p["index"][0],
            p["is_numerical"][0],
            p["chi2"][0],
        )
        split_predictor_idx = get_match_index(
            split_predictor,
            columns
            if "process" not in kwds or kwds["process"]
            else kwds["columns_init"],
        )
        tree = {
            "split_predictor": split_predictor,
            "split_predictor_idx": split_predictor_idx,
            "split_is_numerical": is_numerical,
            "chi2": chi2,
            "is_leaf": False,
            "node_id": idx,
        }
        if is_numerical:
            if categories:
                if ";" in categories[0]:
                    categories = sorted(
                        [float(c.split(";")[1][0:-1]) for c in categories]
                    )
                    ctype = "float"
                else:
                    categories = sorted([int(c) for c in categories])
                    ctype = "int"
            else:
                categories, ctype = [], "int"
        if "process" not in kwds or kwds["process"]:
            classes = self[response].distinct()
        else:
            classes = kwds["classes"]
        if len(columns) == 1:
            if categories:
                if is_numerical:
                    column = "(CASE "
                    for c in categories:
                        column += f"WHEN {split_predictor} <= {c} THEN {c} "
                    column += f"ELSE NULL END)::{ctype} AS {split_predictor}"
                else:
                    column = split_predictor
                result = executeSQL(
                    query=f"""
                        SELECT 
                            /*+LABEL('vDataframe.chaid')*/ 
                            {split_predictor}, 
                            {response}, 
                            (cnt / SUM(cnt) 
                                OVER (PARTITION BY {split_predictor}))::float 
                                AS proba 
                        FROM 
                            (SELECT 
                                {column}, 
                                {response}, 
                                COUNT(*) AS cnt 
                             FROM {self.__genSQL__()} 
                             WHERE {split_predictor} IS NOT NULL 
                               AND {response} IS NOT NULL 
                             GROUP BY 1, 2) x 
                        ORDER BY 1;""",
                    title="Computing the CHAID tree probability.",
                    method="fetchall",
                    sql_push_ext=self._VERTICAPY_VARIABLES_["sql_push_ext"],
                    symbol=self._VERTICAPY_VARIABLES_["symbol"],
                )
            else:
                result = []
            children = {}
            for c in categories:
                children[c] = {}
                for cl in classes:
                    children[c][cl] = 0.0
            for elem in result:
                children[elem[0]][elem[1]] = elem[2]
            for elem in children:
                idx += 1
                children[elem] = {
                    "prediction": [children[elem][c] for c in children[elem]],
                    "is_leaf": True,
                    "node_id": idx,
                }
            tree["children"] = children
            if "process" not in kwds or kwds["process"]:
                return mem.memModel(
                    "CHAID", attributes={"tree": tree, "classes": classes}
                )
            return tree, idx
        else:
            tree["children"] = {}
            columns_tmp = columns.copy()
            columns_tmp.remove(split_predictor)
            for c in categories:
                if is_numerical:
                    vdf = self.search(
                        f"""{split_predictor} <= {c}
                        AND {split_predictor} IS NOT NULL
                        AND {response} IS NOT NULL""",
                        usecols=columns_tmp + [response],
                    )
                else:
                    vdf = self.search(
                        f"""{split_predictor} = '{c}'
                        AND {split_predictor} IS NOT NULL
                        AND {response} IS NOT NULL""",
                        usecols=columns_tmp + [response],
                    )
                tree["children"][c], idx = vdf.chaid(
                    response,
                    columns_tmp,
                    nbins,
                    method,
                    RFmodel_params,
                    process=False,
                    columns_init=columns,
                    classes=classes,
                    node_id=idx + 1,
                )
            if "process" not in kwds or kwds["process"]:
                return mem.memModel(
                    "CHAID", attributes={"tree": tree, "classes": classes}
                )
            return tree, idx

    @save_verticapy_logs
    def chaid_columns(self, columns: list = [], max_cardinality: int = 16):
        """
    Function used to simplify the code. It returns the columns picked by
    the CHAID algorithm.

    Parameters
    ----------
    columns: list
        List of the vColumn names.
    max_cardinality: int, optional
        The maximum number of categories for each categorical column. Categorical 
        columns with a higher cardinality are discarded.

    Returns
    -------
    list
        columns picked by the CHAID algorithm
        """
        columns_tmp = columns.copy()
        if not (columns_tmp):
            columns_tmp = self.get_columns()
            remove_cols = []
            for col in columns_tmp:
                if self[col].category() not in ("float", "int", "text") or (
                    self[col].category() == "text"
                    and self[col].nunique() > max_cardinality
                ):
                    remove_cols += [col]
        else:
            remove_cols = []
            columns_tmp = self.format_colnames(columns_tmp)
            for col in columns_tmp:
                if self[col].category() not in ("float", "int", "text") or (
                    self[col].category() == "text"
                    and self[col].nunique() > max_cardinality
                ):
                    remove_cols += [col]
                    if self[col].category() not in ("float", "int", "text"):
                        warning_message = (
                            f"vColumn '{col}' is of category '{self[col].category()}'. "
                            "This method only accepts categorical & numerical inputs. "
                            "This vColumn was ignored."
                        )
                    else:
                        warning_message = (
                            f"vColumn '{col}' has a too high cardinality "
                            f"(> {max_cardinality}). This vColumn was ignored."
                        )
                    warnings.warn(warning_message, Warning)
        for col in remove_cols:
            columns_tmp.remove(col)
        return columns_tmp

    def copy(self):
        """
    Returns a deep copy of the vDataFrame.

    Returns
    -------
    vDataFrame
        The copy of the vDataFrame.
        """
        return copy.deepcopy(self)

    @save_verticapy_logs
    def case_when(self, name: str, *argv):
        """
    Creates a new feature by evaluating some conditions.
    
    Parameters
    ----------
    name: str
        Name of the new feature.
    argv: object
        Infinite Number of Expressions.
        The expression generated will look like:
        even: CASE ... WHEN argv[2 * i] THEN argv[2 * i + 1] ... END
        odd : CASE ... WHEN argv[2 * i] THEN argv[2 * i + 1] ... ELSE argv[n] END

    Returns
    -------
    vDataFrame
        self
    
    See Also
    --------
    vDataFrame[].decode : Encodes the vColumn using a User Defined Encoding.
    vDataFrame.eval : Evaluates a customized expression.
        """
        return self.eval(name=name, expr=vp.stats.case_when(*argv))

    @save_verticapy_logs
    def contour(self, columns: list, func, nbins: int = 100, ax=None, **style_kwds):
        """
    Draws the contour plot of the input function two input vColumns.

    Parameters
    ----------
    columns: list
        List of the vColumns names. The list must have two elements.
    func: function / str
        Function used to compute the contour score. It can also be a SQL
        expression.
    nbins: int, optional
        Number of bins used to discretize the two input numerical vColumns.
    ax: Matplotlib axes object, optional
        The axes to plot on.
    **style_kwds
        Any optional parameter to pass to the Matplotlib functions.

    Returns
    -------
    ax
        Matplotlib axes object

     See Also
     --------
     vDataFrame.boxplot     : Draws the Box Plot of the input vColumns.
     vDataFrame.hist        : Draws the histogram of the input vColumns based on an aggregation.
     vDataFrame.pivot_table : Draws the pivot table of vColumns based on an aggregation.
        """
        columns = self.format_colnames(columns, expected_nb_of_cols=2)
        return plt.contour_plot(self, columns, func, nbins, ax=ax, **style_kwds,)

    @save_verticapy_logs
    def corr(
        self,
        columns: Union[str, list] = [],
        method: Literal[
            "pearson", "kendall", "spearman", "spearmand", "biserial", "cramer"
        ] = "pearson",
        round_nb: int = 3,
        focus: str = "",
        show: bool = True,
        ax=None,
        **style_kwds,
    ):
        """
    Computes the Correlation Matrix of the vDataFrame. 

    Parameters
    ----------
    columns: str / list, optional
        List of the vColumns names. If empty, all numerical vColumns will be 
        used.
    method: str, optional
        Method to use to compute the correlation.
            pearson   : Pearson's correlation coefficient (linear).
            spearman  : Spearman's correlation coefficient (monotonic - rank based).
            spearmanD : Spearman's correlation coefficient using the DENSE RANK
                        function instead of the RANK function.
            kendall   : Kendall's correlation coefficient (similar trends). The method
                        will compute the Tau-B coefficient.
                        \u26A0 Warning : This method uses a CROSS JOIN during computation 
                                         and is therefore computationally expensive at 
                                         O(n * n), where n is the total count of the 
                                         vDataFrame.
            cramer    : Cramer's V (correlation between categories).
            biserial  : Biserial Point (correlation between binaries and a numericals).
    round_nb: int, optional
        Rounds the coefficient using the input number of digits.
    focus: str, optional
        Focus the computation on only one vColumn.
    show: bool, optional
        If set to True, the Correlation Matrix will be drawn using Matplotlib.
    ax: Matplotlib axes object, optional
        The axes to plot on.
    **style_kwds
        Any optional parameter to pass to the Matplotlib functions.

    Returns
    -------
    tablesample
        An object containing the result. For more information, see
        utilities.tablesample.

    See Also
    --------
    vDataFrame.acf  : Computes the correlations between a vColumn and its lags.
    vDataFrame.cov  : Computes the covariance matrix of the vDataFrame.
    vDataFrame.pacf : Computes the partial autocorrelations of the input vColumn.
    vDataFrame.regr : Computes the regression matrix of the vDataFrame. 
        """
        method = str(method).lower()
        if isinstance(columns, str):
            columns = [columns]
        columns, focus = self.format_colnames(columns, focus)
        fun = self.__aggregate_matrix__
        argv = []
        kwds = {
            "method": method,
            "columns": columns,
            "round_nb": round_nb,
            "show": show,
            "ax": ax,
            **style_kwds,
        }
        if focus:
            argv += [focus]
            fun = self.__aggregate_vector__
        return fun(*argv, **kwds)

    @save_verticapy_logs
    def corr_pvalue(
        self,
        column1: str,
        column2: str,
        method: Literal[
            "pearson",
            "kendall",
            "kendalla",
            "kendallb",
            "kendallc",
            "spearman",
            "spearmand",
            "biserial",
            "cramer",
        ] = "pearson",
    ):
        """
    Computes the Correlation Coefficient of the two input vColumns and its pvalue. 

    Parameters
    ----------
    column1: str
        Input vColumn.
    column2: str
        Input vColumn.
    method: str, optional
        Method to use to compute the correlation.
            pearson   : Pearson's correlation coefficient (linear).
            spearman  : Spearman's correlation coefficient (monotonic - rank based).
            spearmanD : Spearman's correlation coefficient using the DENSE RANK
                        function instead of the RANK function.
            kendall   : Kendall's correlation coefficient (similar trends). 
                        Use kendallA to compute Tau-A, kendallB or kendall to compute 
                        Tau-B and kendallC to compute Tau-C.
                        \u26A0 Warning : This method uses a CROSS JOIN during computation 
                                         and is therefore computationally expensive at 
                                         O(n * n), where n is the total count of the 
                                         vDataFrame.
            cramer    : Cramer's V (correlation between categories).
            biserial  : Biserial Point (correlation between binaries and a numericals).

    Returns
    -------
    tuple
        (Correlation Coefficient, pvalue)

    See Also
    --------
    vDataFrame.corr : Computes the Correlation Matrix of the vDataFrame.
        """
        method = str(method).lower()
        column1, column2 = self.format_colnames(column1, column2)
        if method[0:7] == "kendall":
            if method == "kendall":
                kendall_type = "b"
            else:
                kendall_type = method[-1]
            method = "kendall"
        else:
            kendall_type = None
        if (method == "kendall" and kendall_type == "b") or (method != "kendall"):
            val = self.corr(columns=[column1, column2], method=method)
        sql = f"""
            SELECT 
                /*+LABEL('vDataframe.corr_pvalue')*/ COUNT(*) 
            FROM {self.__genSQL__()} 
            WHERE {column1} IS NOT NULL AND {column2} IS NOT NULL;"""
        n = executeSQL(
            sql,
            title="Computing the number of elements.",
            method="fetchfirstelem",
            sql_push_ext=self._VERTICAPY_VARIABLES_["sql_push_ext"],
            symbol=self._VERTICAPY_VARIABLES_["symbol"],
        )
        if method in ("pearson", "biserial"):
            x = val * math.sqrt((n - 2) / (1 - val * val))
            pvalue = 2 * scipy_st.t.sf(abs(x), n - 2)
        elif method in ("spearman", "spearmand"):
            z = math.sqrt((n - 3) / 1.06) * 0.5 * np.log((1 + val) / (1 - val))
            pvalue = 2 * scipy_st.norm.sf(abs(z))
        elif method == "kendall":
            cast_i = "::int" if (self[column1].isbool()) else ""
            cast_j = "::int" if (self[column2].isbool()) else ""
            n_c = f"""
                (SUM(((x.{column1}{cast_i} 
                     < y.{column1}{cast_i} 
                   AND x.{column2}{cast_j} 
                     < y.{column2}{cast_j})
                   OR (x.{column1}{cast_i} 
                     > y.{column1}{cast_i}
                   AND x.{column2}{cast_j} 
                     > y.{column2}{cast_j}))::int))/2"""
            n_d = f"""
                (SUM(((x.{column1}{cast_i} 
                     > y.{column1}{cast_i}
                   AND x.{column2}{cast_j} 
                     < y.{column2}{cast_j})
                   OR (x.{column1}{cast_i} 
                     < y.{column1}{cast_i} 
                   AND x.{column2}{cast_j} 
                     > y.{column2}{cast_j}))::int))/2"""
            table = f"""
                (SELECT 
                    {", ".join([column1, column2])} 
                 FROM {self.__genSQL__()}) x 
                CROSS JOIN 
                (SELECT 
                    {", ".join([column1, column2])} 
                 FROM {self.__genSQL__()}) y"""
            nc, nd = executeSQL(
                query=f"""
                    SELECT 
                        /*+LABEL('vDataframe.corr_pvalue')*/ 
                        {n_c}::float, 
                        {n_d}::float 
                    FROM {table};""",
                title="Computing nc and nd.",
                method="fetchrow",
                sql_push_ext=self._VERTICAPY_VARIABLES_["sql_push_ext"],
                symbol=self._VERTICAPY_VARIABLES_["symbol"],
            )
            if kendall_type == "a":
                val = (nc - nd) / (n * (n - 1) / 2)
                Z = 3 * (nc - nd) / math.sqrt(n * (n - 1) * (2 * n + 5) / 2)
            elif kendall_type in ("b", "c"):
                vt, v1_0, v2_0 = executeSQL(
                    query=f"""
                        SELECT 
                            /*+LABEL('vDataframe.corr_pvalue')*/
                            SUM(ni * (ni - 1) * (2 * ni + 5)), 
                            SUM(ni * (ni - 1)), 
                            SUM(ni * (ni - 1) * (ni - 2)) 
                        FROM 
                            (SELECT 
                                {column1}, 
                                COUNT(*) AS ni 
                             FROM {self.__genSQL__()} 
                             GROUP BY 1) VERTICAPY_SUBTABLE""",
                    title="Computing vti.",
                    method="fetchrow",
                    sql_push_ext=self._VERTICAPY_VARIABLES_["sql_push_ext"],
                    symbol=self._VERTICAPY_VARIABLES_["symbol"],
                )
                vu, v1_1, v2_1 = executeSQL(
                    query=f"""
                        SELECT 
                            /*+LABEL('vDataframe.corr_pvalue')*/
                            SUM(ni * (ni - 1) * (2 * ni + 5)), 
                            SUM(ni * (ni - 1)), 
                            SUM(ni * (ni - 1) * (ni - 2)) 
                       FROM 
                            (SELECT 
                                {column2}, 
                                COUNT(*) AS ni 
                             FROM {self.__genSQL__()} 
                             GROUP BY 1) VERTICAPY_SUBTABLE""",
                    title="Computing vui.",
                    method="fetchrow",
                    sql_push_ext=self._VERTICAPY_VARIABLES_["sql_push_ext"],
                    symbol=self._VERTICAPY_VARIABLES_["symbol"],
                )
                v0 = n * (n - 1) * (2 * n + 5)
                v1 = v1_0 * v1_1 / (2 * n * (n - 1))
                v2 = v2_0 * v2_1 / (9 * n * (n - 1) * (n - 2))
                Z = (nc - nd) / math.sqrt((v0 - vt - vu) / 18 + v1 + v2)
                if kendall_type == "c":
                    k, r = executeSQL(
                        query=f"""
                            SELECT /*+LABEL('vDataframe.corr_pvalue')*/
                                APPROXIMATE_COUNT_DISTINCT({column1}) AS k, 
                                APPROXIMATE_COUNT_DISTINCT({column2}) AS r 
                            FROM {self.__genSQL__()} 
                            WHERE {column1} IS NOT NULL 
                              AND {column2} IS NOT NULL""",
                        title="Computing the columns categories in the pivot table.",
                        method="fetchrow",
                        sql_push_ext=self._VERTICAPY_VARIABLES_["sql_push_ext"],
                        symbol=self._VERTICAPY_VARIABLES_["symbol"],
                    )
                    m = min(k, r)
                    val = 2 * (nc - nd) / (n * n * (m - 1) / m)
            pvalue = 2 * scipy_st.norm.sf(abs(Z))
        elif method == "cramer":
            k, r = executeSQL(
                query=f"""
                    SELECT /*+LABEL('vDataframe.corr_pvalue')*/
                        APPROXIMATE_COUNT_DISTINCT({column1}) AS k, 
                        APPROXIMATE_COUNT_DISTINCT({column2}) AS r 
                    FROM {self.__genSQL__()} 
                    WHERE {column1} IS NOT NULL 
                      AND {column2} IS NOT NULL""",
                title="Computing the columns categories in the pivot table.",
                method="fetchrow",
                sql_push_ext=self._VERTICAPY_VARIABLES_["sql_push_ext"],
                symbol=self._VERTICAPY_VARIABLES_["symbol"],
            )
            x = val * val * n * min(k, r)
            pvalue = scipy_st.chi2.sf(x, (k - 1) * (r - 1))
        return (val, pvalue)

    @save_verticapy_logs
    def count(
        self, columns: list = [], **agg_kwds,
    ):
        """
    Aggregates the vDataFrame using a list of 'count' (Number of non-missing 
    values).

    Parameters
    ----------
    columns: list, optional
        List of the vColumns names. If empty, all vColumns will be used.
    **agg_kwds
        Any optional parameter to pass to the Aggregate function.

    Returns
    -------
    tablesample
        An object containing the result. For more information, see
        utilities.tablesample.

    See Also
    --------
    vDataFrame.aggregate : Computes the vDataFrame input aggregations.
        """
        return self.aggregate(func=["count"], columns=columns, **agg_kwds,)

    @save_verticapy_logs
    def count_percent(
        self,
        columns: Union[str, list] = [],
        sort_result: bool = True,
        desc: bool = True,
        **agg_kwds,
    ):
        """
    Aggregates the vDataFrame using a list of 'count' (the number of non-missing 
    values) and percent (the percent of non-missing values).

    Parameters
    ----------
    columns: str / list, optional
        List of vColumn names. If empty, all vColumns will be used.
    sort_result: bool, optional
        If set to True, the result will be sorted.
    desc: bool, optional
        If set to True and 'sort_result' is set to True, the result will be 
        sorted in descending order.
    **agg_kwds
        Any optional parameter to pass to the Aggregate function.

    Returns
    -------
    tablesample
        An object containing the result. For more information, see
        utilities.tablesample.

    See Also
    --------
    vDataFrame.aggregate : Computes the vDataFrame input aggregations.
        """
        result = self.aggregate(func=["count", "percent"], columns=columns, **agg_kwds,)
        if sort_result:
            result.sort("count", desc)
        return result

    @save_verticapy_logs
    def cov(
        self,
        columns: Union[str, list] = [],
        focus: str = "",
        show: bool = True,
        ax=None,
        **style_kwds,
    ):
        """
    Computes the covariance matrix of the vDataFrame. 

    Parameters
    ----------
    columns: str / list, optional
        List of the vColumns names. If empty, all numerical vColumns will be 
        used.
    focus: str, optional
        Focus the computation on only one vColumn.
    show: bool, optional
        If set to True, the Covariance Matrix will be drawn using Matplotlib.
    ax: Matplotlib axes object, optional
        The axes to plot on.
    **style_kwds
        Any optional parameter to pass to the Matplotlib functions.

    Returns
    -------
    tablesample
        An object containing the result. For more information, see
        utilities.tablesample.

    See Also
    --------
    vDataFrame.acf  : Computes the correlations between a vColumn and its lags.
    vDataFrame.corr : Computes the Correlation Matrix of the vDataFrame.
    vDataFrame.pacf : Computes the partial autocorrelations of the input vColumn.
    vDataFrame.regr : Computes the regression matrix of the vDataFrame.
        """
        if isinstance(columns, str):
            columns = [columns]

        columns, focus = self.format_colnames(columns, focus)
        fun = self.__aggregate_matrix__
        argv = []
        kwds = {
            "method": "cov",
            "columns": columns,
            "show": show,
            "ax": ax,
            **style_kwds,
        }
        if focus:
            argv += [focus]
            fun = self.__aggregate_vector__

        return fun(*argv, **kwds)

    @save_verticapy_logs
    def cummax(
        self,
        column: str,
        by: list = [],
        order_by: Union[dict, list] = [],
        name: str = "",
    ):
        """
    Adds a new vColumn to the vDataFrame by computing the cumulative maximum of
    the input vColumn.

    Parameters
    ----------
    column: str
        Input vColumn.
    by: list, optional
        vColumns used in the partition.
    order_by: dict / list, optional
        List of the vColumns to use to sort the data using asc order or
        dictionary of all sorting methods. For example, to sort by "column1"
        ASC and "column2" DESC, write {"column1": "asc", "column2": "desc"}
    name: str, optional
        Name of the new vColumn. If empty, a default name will be generated.

    Returns
    -------
    vDataFrame
        self

    See Also
    --------
    vDataFrame.rolling : Computes a customized moving window.
        """
        return self.rolling(
            func="max",
            columns=column,
            window=("UNBOUNDED", 0),
            by=by,
            order_by=order_by,
            name=name,
        )

    @save_verticapy_logs
    def cummin(
        self,
        column: str,
        by: list = [],
        order_by: Union[dict, list] = [],
        name: str = "",
    ):
        """
    Adds a new vColumn to the vDataFrame by computing the cumulative minimum of
    the input vColumn.

    Parameters
    ----------
    column: str
        Input vColumn.
    by: list, optional
        vColumns used in the partition.
    order_by: dict / list, optional
        List of the vColumns to use to sort the data using asc order or
        dictionary of all sorting methods. For example, to sort by "column1"
        ASC and "column2" DESC, write {"column1": "asc", "column2": "desc"}
    name: str, optional
        Name of the new vColumn. If empty, a default name will be generated.

    Returns
    -------
    vDataFrame
        self

    See Also
    --------
    vDataFrame.rolling : Computes a customized moving window.
        """
        return self.rolling(
            func="min",
            columns=column,
            window=("UNBOUNDED", 0),
            by=by,
            order_by=order_by,
            name=name,
        )

    @save_verticapy_logs
    def cumprod(
        self,
        column: str,
        by: list = [],
        order_by: Union[dict, list] = [],
        name: str = "",
    ):
        """
    Adds a new vColumn to the vDataFrame by computing the cumulative product of 
    the input vColumn.

    Parameters
    ----------
    column: str
        Input vColumn.
    by: list, optional
        vColumns used in the partition.
    order_by: dict / list, optional
        List of the vColumns to use to sort the data using asc order or
        dictionary of all sorting methods. For example, to sort by "column1"
        ASC and "column2" DESC, write {"column1": "asc", "column2": "desc"}
    name: str, optional
        Name of the new vColumn. If empty, a default name will be generated.

    Returns
    -------
    vDataFrame
        self

    See Also
    --------
    vDataFrame.rolling : Computes a customized moving window.
        """
        return self.rolling(
            func="prod",
            columns=column,
            window=("UNBOUNDED", 0),
            by=by,
            order_by=order_by,
            name=name,
        )

    @save_verticapy_logs
    def cumsum(
        self,
        column: str,
        by: list = [],
        order_by: Union[dict, list] = [],
        name: str = "",
    ):
        """
    Adds a new vColumn to the vDataFrame by computing the cumulative sum of the 
    input vColumn.

    Parameters
    ----------
    column: str
        Input vColumn.
    by: list, optional
        vColumns used in the partition.
    order_by: dict / list, optional
        List of the vColumns to use to sort the data using asc order or
        dictionary of all sorting methods. For example, to sort by "column1"
        ASC and "column2" DESC, write {"column1": "asc", "column2": "desc"}
    name: str, optional
        Name of the new vColumn. If empty, a default name will be generated.

    Returns
    -------
    vDataFrame
        self

    See Also
    --------
    vDataFrame.rolling : Computes a customized moving window.
        """
        return self.rolling(
            func="sum",
            columns=column,
            window=("UNBOUNDED", 0),
            by=by,
            order_by=order_by,
            name=name,
        )

    def current_relation(self, reindent: bool = True):
        """
    Returns the current vDataFrame relation.

    Parameters
    ----------
    reindent: bool, optional
        Reindent the text to be more readable. 

    Returns
    -------
    str
        The formatted current vDataFrame relation.
        """
        if reindent:
            return indentSQL(self.__genSQL__())
        else:
            return self.__genSQL__()

    def datecol(self):
        """
    Returns a list of the vColumns of type date in the vDataFrame.

    Returns
    -------
    List
        List of all vColumns of type date.

    See Also
    --------
    vDataFrame.catcol : Returns a list of the categorical vColumns in the vDataFrame.
    vDataFrame.numcol : Returns a list of names of the numerical vColumns in the 
                        vDataFrame.
        """
        columns = []
        cols = self.get_columns()
        for column in cols:
            if self[column].isdate():
                columns += [column]
        return columns

    def del_catalog(self):
        """
    Deletes the current vDataFrame catalog.

    Returns
    -------
    vDataFrame
        self
        """
        self.__update_catalog__(erase=True)
        return self

    @save_verticapy_logs
    def density(
        self,
        columns: Union[str, list] = [],
        bandwidth: float = 1.0,
        kernel: Literal["gaussian", "logistic", "sigmoid", "silverman"] = "gaussian",
        nbins: int = 50,
        xlim: tuple = None,
        ax=None,
        **style_kwds,
    ):
        """
    Draws the vColumns Density Plot.

    Parameters
    ----------
    columns: str / list, optional
        List of the vColumns names. If empty, all numerical vColumns will 
        be selected.
    bandwidth: float, optional
        The bandwidth of the kernel.
    kernel: str, optional
        The method used for the plot.
            gaussian  : Gaussian Kernel.
            logistic  : Logistic Kernel.
            sigmoid   : Sigmoid Kernel.
            silverman : Silverman Kernel.
    nbins: int, optional
        Maximum number of points to use to evaluate the approximate density function.
        Increasing this parameter will increase the precision but will also increase 
        the time of the learning and the scoring phases.
    xlim: tuple, optional
        Set the x limits of the current axes.
    ax: Matplotlib axes object, optional
        The axes to plot on.
    **style_kwds
        Any optional parameter to pass to the Matplotlib functions.

    Returns
    -------
    ax
        Matplotlib axes object

    See Also
    --------
    vDataFrame[].hist : Draws the histogram of the vColumn based on an aggregation.
        """
        if isinstance(columns, str):
            columns = [columns]
        columns = self.format_colnames(columns)
        if not (columns):
            columns = self.numcol()
        else:
            for column in columns:
                assert self[column].isnum(), TypeError(
                    f"vColumn {column} is not numerical to draw KDE"
                )
        assert columns, EmptyParameter("No Numerical Columns found to draw KDE.")
        colors = gen_colors()
        min_max = self.agg(func=["min", "max"], columns=columns)
        if not xlim:
            xmin = min(min_max["min"])
            xmax = max(min_max["max"])
        else:
            xmin, xmax = xlim
        custom_lines = []
        for idx, column in enumerate(columns):
            param = {"color": colors[idx % len(colors)]}
            ax = self[column].density(
                bandwidth=bandwidth,
                kernel=kernel,
                nbins=nbins,
                xlim=(xmin, xmax),
                ax=ax,
                **updated_dict(param, style_kwds, idx),
            )
            custom_lines += [
                Line2D([0], [0], color=colors[idx % len(colors)], lw=4),
            ]
        ax.legend(custom_lines, columns, loc="center left", bbox_to_anchor=[1, 0.5])
        ax.set_ylim(bottom=0)
        return ax

    @save_verticapy_logs
    def describe(
        self,
        method: Literal[
            "numerical", "categorical", "statistics", "length", "range", "all", "auto",
        ] = "auto",
        columns: Union[str, list] = [],
        unique: bool = False,
        ncols_block: int = 20,
        processes: int = 1,
    ):
        """
    Aggregates the vDataFrame using multiple statistical aggregations: min, 
    max, median, unique... depending on the types of the vColumns.

    Parameters
    ----------
    method: str, optional
        The describe method.
            all         : Aggregates all selected vDataFrame vColumns different 
                methods depending on the vColumn type (numerical dtype: numerical; 
                timestamp dtype: range; categorical dtype: length)
            auto        : Sets the method to 'numerical' if at least one vColumn 
                of the vDataFrame is numerical, 'categorical' otherwise.
            categorical : Uses only categorical aggregations.
            length      : Aggregates the vDataFrame using numerical aggregation 
                on the length of all selected vColumns.
            numerical   : Uses only numerical descriptive statistics which are 
                 computed in a faster way than the 'aggregate' method.
            range       : Aggregates the vDataFrame using multiple statistical
                aggregations - min, max, range...
            statistics  : Aggregates the vDataFrame using multiple statistical 
                aggregations - kurtosis, skewness, min, max...
    columns: str / list, optional
        List of the vColumns names. If empty, the vColumns will be selected
        depending on the parameter 'method'.
    unique: bool, optional
        If set to True, the cardinality of each element will be computed.
    ncols_block: int, optional
        Number of columns used per query. Setting this parameter divides
        what would otherwise be one large query into many smaller queries called
        "blocks." The size of each block is determined by the ncols_block parmeter.
    processes: int, optional
        Number of child processes to create. Setting this with the ncols_block parameter
        lets you parallelize a single query into many smaller queries, where each child 
        process creates its own connection to the database and sends one query. This can 
        improve query performance, but consumes more resources. If processes is set to 1, 
        the queries are sent iteratively from a single process.

    Returns
    -------
    tablesample
        An object containing the result. For more information, see
        utilities.tablesample.

    See Also
    --------
    vDataFrame.aggregate : Computes the vDataFrame input aggregations.
        """
        if isinstance(columns, str):
            columns = [columns]
        if method == "auto":
            method = "numerical" if (self.numcol()) else "categorical"
        columns = self.format_colnames(columns)
        for i in range(len(columns)):
            columns[i] = quote_ident(columns[i])
        dtype, percent = {}, {}

        if method == "numerical":

            if not (columns):
                columns = self.numcol()
            else:
                for column in columns:
                    assert self[column].isnum(), TypeError(
                        f"vColumn {column} must be numerical to run describe"
                        " using parameter method = 'numerical'"
                    )
            assert columns, EmptyParameter(
                "No Numerical Columns found to run describe using parameter"
                " method = 'numerical'."
            )
            if ncols_block < len(columns) and processes <= 1:
                if vp.OPTIONS["tqdm"]:
                    loop = tqdm(range(0, len(columns), ncols_block))
                else:
                    loop = range(0, len(columns), ncols_block)
                for i in loop:
                    res_tmp = self.describe(
                        method=method,
                        columns=columns[i : i + ncols_block],
                        unique=unique,
                        ncols_block=ncols_block,
                    )
                    if i == 0:
                        result = res_tmp
                    else:
                        result.append(res_tmp)
                return result
            elif ncols_block < len(columns):
                parameters = []
                for i in range(0, len(columns), ncols_block):
                    parameters += [(self, method, columns, unique, ncols_block, i)]
                a_pool = multiprocessing.Pool(processes)
                L = a_pool.starmap(func=describe_parallel_block, iterable=parameters)
                result = L[0]
                for i in range(1, len(L)):
                    result.append(L[i])
                return result
            try:
                util.vertica_version(condition=[9, 0, 0])
                idx = [
                    "index",
                    "count",
                    "mean",
                    "std",
                    "min",
                    "approx_25%",
                    "approx_50%",
                    "approx_75%",
                    "max",
                ]
                values = {}
                for key in idx:
                    values[key] = []
                col_to_compute = []
                for column in columns:
                    if self[column].isnum():
                        for fun in idx[1:]:
                            pre_comp = self.__get_catalog_value__(column, fun)
                            if pre_comp == "VERTICAPY_NOT_PRECOMPUTED":
                                col_to_compute += [column]
                                break
                    elif vp.OPTIONS["print_info"]:
                        warning_message = (
                            f"The vColumn {column} is not numerical, it was ignored."
                            "\nTo get statistical information about all different "
                            "variables, please use the parameter method = 'categorical'."
                        )
                        warnings.warn(warning_message, Warning)
                for column in columns:
                    if column not in col_to_compute:
                        values["index"] += [column.replace('"', "")]
                        for fun in idx[1:]:
                            values[fun] += [self.__get_catalog_value__(column, fun)]
                if col_to_compute:
                    cols_to_compute_str = [
                        col if not (self[col].isbool()) else f"{col}::int"
                        for col in col_to_compute
                    ]
                    cols_to_compute_str = ", ".join(cols_to_compute_str)
                    query_result = executeSQL(
                        query=f"""
                            SELECT 
                                /*+LABEL('vDataframe.describe')*/ 
                                SUMMARIZE_NUMCOL({cols_to_compute_str}) OVER () 
                            FROM {self.__genSQL__()}""",
                        title=(
                            "Computing the descriptive statistics of all numerical "
                            "columns using SUMMARIZE_NUMCOL."
                        ),
                        method="fetchall",
                    )

                    # Formatting - to have the same columns' order than the input one.
                    for i, key in enumerate(idx):
                        values[key] += [elem[i] for elem in query_result]
                    tb = util.tablesample(values).transpose()
                    vals = {"index": tb["index"]}
                    for col in columns:
                        vals[col] = tb[col]
                    values = util.tablesample(vals).transpose().values

            except:

                values = self.aggregate(
                    [
                        "count",
                        "mean",
                        "std",
                        "min",
                        "approx_25%",
                        "approx_50%",
                        "approx_75%",
                        "max",
                    ],
                    columns=columns,
                    ncols_block=ncols_block,
                    processes=processes,
                ).values

        elif method == "categorical":

            func = ["dtype", "count", "top", "top_percent"]
            values = self.aggregate(
                func, columns=columns, ncols_block=ncols_block, processes=processes,
            ).values

        elif method == "statistics":

            func = [
                "dtype",
                "percent",
                "count",
                "avg",
                "stddev",
                "min",
                "approx_1%",
                "approx_10%",
                "approx_25%",
                "approx_50%",
                "approx_75%",
                "approx_90%",
                "approx_99%",
                "max",
                "skewness",
                "kurtosis",
            ]
            values = self.aggregate(
                func=func,
                columns=columns,
                ncols_block=ncols_block,
                processes=processes,
            ).values

        elif method == "length":

            if not (columns):
                columns = self.get_columns()
            func = [
                "dtype",
                "percent",
                "count",
                "SUM(CASE WHEN LENGTH({}::varchar) = 0 THEN 1 ELSE 0 END) AS empty",
                "AVG(LENGTH({}::varchar)) AS avg_length",
                "STDDEV(LENGTH({}::varchar)) AS stddev_length",
                "MIN(LENGTH({}::varchar))::int AS min_length",
                """APPROXIMATE_PERCENTILE(LENGTH({}::varchar) 
                        USING PARAMETERS percentile = 0.25)::int AS '25%_length'""",
                """APPROXIMATE_PERCENTILE(LENGTH({}::varchar)
                        USING PARAMETERS percentile = 0.5)::int AS '50%_length'""",
                """APPROXIMATE_PERCENTILE(LENGTH({}::varchar) 
                        USING PARAMETERS percentile = 0.75)::int AS '75%_length'""",
                "MAX(LENGTH({}::varchar))::int AS max_length",
            ]
            values = self.aggregate(
                func=func,
                columns=columns,
                ncols_block=ncols_block,
                processes=processes,
            ).values

        elif method == "range":

            if not (columns):
                columns = []
                all_cols = self.get_columns()
                for idx, column in enumerate(all_cols):
                    if self[column].isnum() or self[column].isdate():
                        columns += [column]
            func = ["dtype", "percent", "count", "min", "max", "range"]
            values = self.aggregate(
                func=func,
                columns=columns,
                ncols_block=ncols_block,
                processes=processes,
            ).values

        elif method == "all":

            datecols, numcol, catcol = [], [], []
            if not (columns):
                columns = self.get_columns()
            for elem in columns:
                if self[elem].isnum():
                    numcol += [elem]
                elif self[elem].isdate():
                    datecols += [elem]
                else:
                    catcol += [elem]
            values = self.aggregate(
                func=[
                    "dtype",
                    "percent",
                    "count",
                    "top",
                    "top_percent",
                    "avg",
                    "stddev",
                    "min",
                    "approx_25%",
                    "approx_50%",
                    "approx_75%",
                    "max",
                    "range",
                ],
                columns=numcol,
                ncols_block=ncols_block,
                processes=processes,
            ).values
            values["empty"] = [None] * len(numcol)
            if datecols:
                tmp = self.aggregate(
                    func=[
                        "dtype",
                        "percent",
                        "count",
                        "top",
                        "top_percent",
                        "min",
                        "max",
                        "range",
                    ],
                    columns=datecols,
                    ncols_block=ncols_block,
                    processes=processes,
                ).values
                for elem in [
                    "index",
                    "dtype",
                    "percent",
                    "count",
                    "top",
                    "top_percent",
                    "min",
                    "max",
                    "range",
                ]:
                    values[elem] += tmp[elem]
                for elem in [
                    "avg",
                    "stddev",
                    "approx_25%",
                    "approx_50%",
                    "approx_75%",
                    "empty",
                ]:
                    values[elem] += [None] * len(datecols)
            if catcol:
                tmp = self.aggregate(
                    func=[
                        "dtype",
                        "percent",
                        "count",
                        "top",
                        "top_percent",
                        "AVG(LENGTH({}::varchar)) AS avg",
                        "STDDEV(LENGTH({}::varchar)) AS stddev",
                        "MIN(LENGTH({}::varchar))::int AS min",
                        """APPROXIMATE_PERCENTILE(LENGTH({}::varchar) 
                                USING PARAMETERS percentile = 0.25)::int AS 'approx_25%'""",
                        """APPROXIMATE_PERCENTILE(LENGTH({}::varchar) 
                                USING PARAMETERS percentile = 0.5)::int AS 'approx_50%'""",
                        """APPROXIMATE_PERCENTILE(LENGTH({}::varchar) 
                                USING PARAMETERS percentile = 0.75)::int AS 'approx_75%'""",
                        "MAX(LENGTH({}::varchar))::int AS max",
                        "MAX(LENGTH({}::varchar))::int - MIN(LENGTH({}::varchar))::int AS range",
                        "SUM(CASE WHEN LENGTH({}::varchar) = 0 THEN 1 ELSE 0 END) AS empty",
                    ],
                    columns=catcol,
                    ncols_block=ncols_block,
                    processes=processes,
                ).values
                for elem in [
                    "index",
                    "dtype",
                    "percent",
                    "count",
                    "top",
                    "top_percent",
                    "avg",
                    "stddev",
                    "min",
                    "approx_25%",
                    "approx_50%",
                    "approx_75%",
                    "max",
                    "range",
                    "empty",
                ]:
                    values[elem] += tmp[elem]
            for i in range(len(values["index"])):
                dtype[values["index"][i]] = values["dtype"][i]
                percent[values["index"][i]] = values["percent"][i]

        if unique:
            values["unique"] = self.aggregate(
                ["unique"],
                columns=columns,
                ncols_block=ncols_block,
                processes=processes,
            ).values["unique"]

        self.__update_catalog__(util.tablesample(values).transpose().values)
        values["index"] = [quote_ident(elem) for elem in values["index"]]
        result = util.tablesample(
            values, percent=percent, dtype=dtype
        ).decimal_to_float()
        if method == "all":
            result = result.transpose()

        return result

    @save_verticapy_logs
    def drop(self, columns: Union[str, list] = []):
        """
    Drops the input vColumns from the vDataFrame. Dropping vColumns means 
    not selecting them in the final SQL code generation.
    Be Careful when using this method. It can make the vDataFrame structure 
    heavier if some other vColumns are computed using the dropped vColumns.

    Parameters
    ----------
    columns: str / list, optional
        List of the vColumns names.

    Returns
    -------
    vDataFrame
        self
        """
        if isinstance(columns, str):
            columns = [columns]
        columns = self.format_colnames(columns)
        for column in columns:
            self[column].drop()
        return self

    @save_verticapy_logs
    def drop_duplicates(self, columns: Union[str, list] = []):
        """
    Filters the duplicated using a partition by the input vColumns.

    \u26A0 Warning : Dropping duplicates will make the vDataFrame structure 
                     heavier. It is recommended to always check the current structure 
                     using the 'current_relation' method and to save it using the 
                     'to_db' method with the parameters 'inplace = True' and 
                     'relation_type = table'

    Parameters
    ----------
    columns: str / list, optional
        List of the vColumns names. If empty, all vColumns will be selected.

    Returns
    -------
    vDataFrame
        self
        """
        if isinstance(columns, str):
            columns = [columns]
        count = self.duplicated(columns=columns, count=True)
        if count:
            columns = (
                self.get_columns() if not (columns) else self.format_colnames(columns)
            )
            name = (
                "__verticapy_duplicated_index__"
                + str(random.randint(0, 10000000))
                + "_"
            )
            self.eval(
                name=name,
                expr=f"""ROW_NUMBER() OVER (PARTITION BY {", ".join(columns)})""",
            )
            self.filter(f'"{name}" = 1')
            self._VERTICAPY_VARIABLES_["exclude_columns"] += [f'"{name}"']
        elif vp.OPTIONS["print_info"]:
            print("No duplicates detected.")
        return self

    @save_verticapy_logs
    def dropna(self, columns: Union[str, list] = []):
        """
    Filters the vDataFrame where the input vColumns are missing.

    Parameters
    ----------
    columns: str / list, optional
        List of the vColumns names. If empty, all vColumns will be selected.

    Returns
    -------
    vDataFrame
        self

    See Also
    --------
    vDataFrame.filter: Filters the data using the input expression.
        """
        if isinstance(columns, str):
            columns = [columns]
        columns = self.get_columns() if not (columns) else self.format_colnames(columns)
        total = self.shape()[0]
        print_info = vp.OPTIONS["print_info"]
        for column in columns:
            vp.OPTIONS["print_info"] = False
            self[column].dropna()
            vp.OPTIONS["print_info"] = print_info
        if vp.OPTIONS["print_info"]:
            total -= self.shape()[0]
            if total == 0:
                print("Nothing was filtered.")
            else:
                conj = "s were " if total > 1 else " was "
                print(f"{total} element{conj}filtered.")
        return self

    @save_verticapy_logs
    def dtypes(self):
        """
    Returns the different vColumns types.

    Returns
    -------
    tablesample
        An object containing the result. For more information, see
        utilities.tablesample.
        """
        values = {"index": [], "dtype": []}
        for column in self.get_columns():
            values["index"] += [column]
            values["dtype"] += [self[column].ctype()]
        return util.tablesample(values)

    @save_verticapy_logs
    def duplicated(
        self, columns: Union[str, list] = [], count: bool = False, limit: int = 30
    ):
        """
    Returns the duplicated values.

    Parameters
    ----------
    columns: str / list, optional
        List of the vColumns names. If empty, all vColumns will be selected.
    count: bool, optional
        If set to True, the method will also return the count of each duplicates.
    limit: int, optional
        The limited number of elements to be displayed.

    Returns
    -------
    tablesample
        An object containing the result. For more information, see
        utilities.tablesample.

    See Also
    --------
    vDataFrame.drop_duplicates : Filters the duplicated values.
        """
        if not (columns):
            columns = self.get_columns()
        elif isinstance(columns, str):
            columns = [columns]
        columns = self.format_colnames(columns)
        columns = ", ".join(columns)
        main_table = f"""
            (SELECT 
                *, 
                ROW_NUMBER() OVER (PARTITION BY {columns}) AS duplicated_index 
             FROM {self.__genSQL__()}) duplicated_index_table 
             WHERE duplicated_index > 1"""
        if count:
            total = executeSQL(
                query=f"""
                    SELECT 
                        /*+LABEL('vDataframe.duplicated')*/ COUNT(*) 
                    FROM {main_table}""",
                title="Computing the number of duplicates.",
                method="fetchfirstelem",
                sql_push_ext=self._VERTICAPY_VARIABLES_["sql_push_ext"],
                symbol=self._VERTICAPY_VARIABLES_["symbol"],
            )
            return total
        result = util.to_tablesample(
            query=f"""
                SELECT 
                    {columns},
                    MAX(duplicated_index) AS occurrence 
                FROM {main_table} 
                GROUP BY {columns} 
                ORDER BY occurrence DESC LIMIT {limit}""",
            sql_push_ext=self._VERTICAPY_VARIABLES_["sql_push_ext"],
            symbol=self._VERTICAPY_VARIABLES_["symbol"],
        )
        result.count = executeSQL(
            query=f"""
                SELECT 
                    /*+LABEL('vDataframe.duplicated')*/ COUNT(*) 
                FROM 
                    (SELECT 
                        {columns}, 
                        MAX(duplicated_index) AS occurrence 
                     FROM {main_table} 
                     GROUP BY {columns}) t""",
            title="Computing the number of distinct duplicates.",
            method="fetchfirstelem",
            sql_push_ext=self._VERTICAPY_VARIABLES_["sql_push_ext"],
            symbol=self._VERTICAPY_VARIABLES_["symbol"],
        )
        return result

    def empty(self):
        """
    Returns True if the vDataFrame is empty.

    Returns
    -------
    bool
        True if the vDataFrame has no vColumns.
        """
        return not (self.get_columns())

    @save_verticapy_logs
    def eval(self, name: str, expr: Union[str, str_sql]):
        """
    Evaluates a customized expression.

    Parameters
    ----------
    name: str
        Name of the new vColumn.
    expr: str
        Expression in pure SQL to use to compute the new feature.
        For example, 'CASE WHEN "column" > 3 THEN 2 ELSE NULL END' and
        'POWER("column", 2)' will work.

    Returns
    -------
    vDataFrame
        self

    See Also
    --------
    vDataFrame.analytic : Adds a new vColumn to the vDataFrame by using an advanced 
        analytical function on a specific vColumn.
        """
        if isinstance(expr, str_sql):
            expr = str(expr)
        name = quote_ident(name.replace('"', "_"))
        if self.is_colname_in(name):
            raise NameError(
                f"A vColumn has already the alias {name}.\n"
                "By changing the parameter 'name', you'll "
                "be able to solve this issue."
            )
        try:
            query = f"SELECT {expr} AS {name} FROM {self.__genSQL__()} LIMIT 0"
            ctype = util.get_data_types(query, name[1:-1].replace("'", "''"),)
        except:
            raise QueryError(
                f"The expression '{expr}' seems to be incorrect.\nBy "
                "turning on the SQL with the 'set_option' function, "
                "you'll print the SQL code generation and probably "
                "see why the evaluation didn't work."
            )
        if not (ctype):
            ctype = "undefined"
        elif (ctype.lower()[0:12] in ("long varbina", "long varchar")) and (
            self._VERTICAPY_VARIABLES_["isflex"]
            or util.isvmap(expr=f"({query}) VERTICAPY_SUBTABLE", column=name,)
        ):
            category = "vmap"
            ctype = "VMAP(" + "(".join(ctype.split("(")[1:]) if "(" in ctype else "VMAP"
        else:
            category = get_category_from_vertica_type(ctype=ctype)
        all_cols, max_floor = self.get_columns(), 0
        for column in all_cols:
            column_str = column.replace('"', "")
            if (quote_ident(column) in expr) or (
                re.search(re.compile(f"\\b{column_str}\\b"), expr)
            ):
                max_floor = max(len(self[column].transformations), max_floor)
        transformations = [
            (
                "___VERTICAPY_UNDEFINED___",
                "___VERTICAPY_UNDEFINED___",
                "___VERTICAPY_UNDEFINED___",
            )
            for i in range(max_floor)
        ] + [(expr, ctype, category)]
        new_vColumn = vp.vColumn(name, parent=self, transformations=transformations)
        setattr(self, name, new_vColumn)
        setattr(self, name.replace('"', ""), new_vColumn)
        new_vColumn.init = False
        new_vColumn.init_transf = name
        self._VERTICAPY_VARIABLES_["columns"] += [name]
        self.__add_to_history__(
            f"[Eval]: A new vColumn {name} was added to the vDataFrame."
        )
        return self

    @save_verticapy_logs
    def expected_store_usage(self, unit: str = "b"):
        """
    Returns the vDataFrame expected store usage. 

    Parameters
    ----------
    unit: str, optional
        unit used for the computation
        b : byte
        kb: kilo byte
        gb: giga byte
        tb: tera byte

    Returns
    -------
    tablesample
        An object containing the result. For more information, see
        utilities.tablesample.

    See Also
    --------
    vDataFrame.memory_usage : Returns the vDataFrame memory usage.
        """
        if unit.lower() == "kb":
            div_unit = 1024
        elif unit.lower() == "mb":
            div_unit = 1024 * 1024
        elif unit.lower() == "gb":
            div_unit = 1024 * 1024 * 1024
        elif unit.lower() == "tb":
            div_unit = 1024 * 1024 * 1024 * 1024
        else:
            unit, div_unit = "b", 1
        total, total_expected = 0, 0
        columns = self.get_columns()
        values = self.aggregate(func=["count"], columns=columns).transpose().values
        values["index"] = [
            f"expected_size ({unit})",
            f"max_size ({unit})",
            "type",
        ]
        for column in columns:
            ctype = self[column].ctype()
            if (
                (ctype[0:4] == "date")
                or (ctype[0:4] == "time")
                or (ctype[0:8] == "interval")
                or (ctype == "smalldatetime")
            ):
                maxsize, expsize = 8, 8
            elif "int" in ctype:
                maxsize, expsize = 8, self[column].store_usage()
            elif ctype[0:4] == "bool":
                maxsize, expsize = 1, 1
            elif (
                (ctype[0:5] == "float")
                or (ctype[0:6] == "double")
                or (ctype[0:4] == "real")
            ):
                maxsize, expsize = 8, 8
            elif (
                (ctype[0:7] in ("numeric", "decimal"))
                or (ctype[0:6] == "number")
                or (ctype[0:5] == "money")
            ):
                try:
                    size = sum(
                        [
                            int(item)
                            for item in ctype.split("(")[1].split(")")[0].split(",")
                        ]
                    )
                except:
                    size = 38
                maxsize, expsize = size, size
            elif ctype[0:7] == "varchar":
                try:
                    size = int(ctype.split("(")[1].split(")")[0])
                except:
                    size = 80
                maxsize, expsize = size, self[column].store_usage()
            elif (ctype[0:4] == "char") or (ctype[0:3] == "geo") or ("binary" in ctype):
                try:
                    size = int(ctype.split("(")[1].split(")")[0])
                    maxsize, expsize = size, size
                except:
                    if ctype[0:3] == "geo":
                        maxsize, expsize = 10000000, 10000
                    elif "long" in ctype:
                        maxsize, expsize = 32000000, 10000
                    else:
                        maxsize, expsize = 65000, 1000
            elif ctype[0:4] == "uuid":
                maxsize, expsize = 16, 16
            else:
                maxsize, expsize = 80, self[column].store_usage()
            maxsize /= div_unit
            expsize /= div_unit
            values[column] = [expsize, values[column][0] * maxsize, ctype]
            total_expected += values[column][0]
            total += values[column][1]
        values["separator"] = [
            len(columns) * self.shape()[0] / div_unit,
            len(columns) * self.shape()[0] / div_unit,
            "",
        ]
        total += values["separator"][0]
        total_expected += values["separator"][0]
        values["header"] = [
            (sum([len(item) for item in columns]) + len(columns)) / div_unit,
            (sum([len(item) for item in columns]) + len(columns)) / div_unit,
            "",
        ]
        total += values["header"][0]
        total_expected += values["header"][0]
        values["rawsize"] = [total_expected, total, ""]
        return util.tablesample(values=values).transpose()

    @save_verticapy_logs
    def explain(self, digraph: bool = False):
        """
    Provides information on how Vertica is computing the current vDataFrame
    relation.

    Parameters
    ----------
    digraph: bool, optional
        If set to True, returns only the digraph of the explain plan.

    Returns
    -------
    str
        explain plan
        """
        result = executeSQL(
            query=f"""
                EXPLAIN 
                SELECT 
                    /*+LABEL('vDataframe.explain')*/ * 
                FROM {self.__genSQL__()}""",
            title="Explaining the Current Relation",
            method="fetchall",
            sql_push_ext=self._VERTICAPY_VARIABLES_["sql_push_ext"],
            symbol=self._VERTICAPY_VARIABLES_["symbol"],
        )
        result = [elem[0] for elem in result]
        result = "\n".join(result)
        if not (digraph):
            result = result.replace("------------------------------\n", "")
            result = result.replace("\\n", "\n\t")
            result = result.replace(", ", ",").replace(",", ", ").replace("\n}", "}")
        else:
            result = "digraph G {" + result.split("digraph G {")[1]
        return result

    @save_verticapy_logs
    def fillna(self, val: dict = {}, method: dict = {}, numeric_only: bool = False):
        """
    Fills the vColumns missing elements using specific rules.

    Parameters
    ----------
    val: dict, optional
        Dictionary of values. The dictionary must be similar to the following:
        {"column1": val1 ..., "columnk": valk}. Each key of the dictionary must
        be a vColumn. The missing values of the input vColumns will be replaced
        by the input value.
    method: dict, optional
        Method to use to impute the missing values.
            auto    : Mean for the numerical and Mode for the categorical vColumns.
            mean    : Average.
            median  : Median.
            mode    : Mode (most occurent element).
            0ifnull : 0 when the vColumn is null, 1 otherwise.
                More Methods are available on the vDataFrame[].fillna method.
    numeric_only: bool, optional
        If parameters 'val' and 'method' are empty and 'numeric_only' is set
        to True then all numerical vColumns will be imputed by their average.
        If set to False, all categorical vColumns will be also imputed by their
        mode.

    Returns
    -------
    vDataFrame
        self

    See Also
    --------
    vDataFrame[].fillna : Fills the vColumn missing values. This method is more 
        complete than the vDataFrame.fillna method by allowing more parameters.
        """
        print_info = vp.OPTIONS["print_info"]
        vp.OPTIONS["print_info"] = False
        try:
            if not (val) and not (method):
                cols = self.get_columns()
                for column in cols:
                    if numeric_only:
                        if self[column].isnum():
                            self[column].fillna(method="auto")
                    else:
                        self[column].fillna(method="auto")
            else:
                for column in val:
                    self[self.format_colnames(column)].fillna(val=val[column])
                for column in method:
                    self[self.format_colnames(column)].fillna(method=method[column],)
            return self
        finally:
            vp.OPTIONS["print_info"] = print_info

    @save_verticapy_logs
    def filter(self, conditions: Union[list, str] = [], *argv, **kwds):
        """
    Filters the vDataFrame using the input expressions.

    Parameters
    ---------- 
    conditions: str / list, optional
        List of expressions. For example to keep only the records where the 
        vColumn 'column' is greater than 5 and lesser than 10 you can write 
        ['"column" > 5', '"column" < 10'].

    Returns
    -------
    vDataFrame
        self

    See Also
    --------
    vDataFrame.at_time      : Filters the data at the input time.
    vDataFrame.between_time : Filters the data between two time ranges.
    vDataFrame.first        : Filters the data by only keeping the first records.
    vDataFrame.last         : Filters the data by only keeping the last records.
    vDataFrame.search       : Searches the elements which matches with the input 
        conditions.
        """
        count = self.shape()[0]
        conj = "s were " if count > 1 else " was "
        if not (isinstance(conditions, str)) or (argv):
            if isinstance(conditions, str) or not (isinstance(conditions, Iterable)):
                conditions = [conditions]
            else:
                conditions = list(conditions)
            conditions += list(argv)
            for condition in conditions:
                self.filter(str(condition), print_info=False)
            count -= self.shape()[0]
            if count > 0:
                if vp.OPTIONS["print_info"]:
                    print(f"{count} element{conj}filtered")
                self.__add_to_history__(
                    f"[Filter]: {count} element{conj}filtered "
                    f"using the filter '{conditions}'"
                )
            elif vp.OPTIONS["print_info"]:
                print("Nothing was filtered.")
        else:
            max_pos = 0
            columns_tmp = [elem for elem in self._VERTICAPY_VARIABLES_["columns"]]
            for column in columns_tmp:
                max_pos = max(max_pos, len(self[column].transformations) - 1)
            new_count = self.shape()[0]
            self._VERTICAPY_VARIABLES_["where"] += [(conditions, max_pos)]
            try:
                new_count = executeSQL(
                    query=f"""
                        SELECT 
                            /*+LABEL('vDataframe.filter')*/ 
                            COUNT(*) 
                        FROM {self.__genSQL__()}""",
                    title="Computing the new number of elements.",
                    method="fetchfirstelem",
                    sql_push_ext=self._VERTICAPY_VARIABLES_["sql_push_ext"],
                    symbol=self._VERTICAPY_VARIABLES_["symbol"],
                )
                count -= new_count
            except:
                del self._VERTICAPY_VARIABLES_["where"][-1]
                if vp.OPTIONS["print_info"]:
                    warning_message = (
                        f"The expression '{conditions}' is incorrect.\n"
                        "Nothing was filtered."
                    )
                    warnings.warn(warning_message, Warning)
                return self
            if count > 0:
                self.__update_catalog__(erase=True)
                self._VERTICAPY_VARIABLES_["count"] = new_count
                conj = "s were " if count > 1 else " was "
                if vp.OPTIONS["print_info"] and "print_info" not in kwds:
                    print(f"{count} element{conj}filtered.")
                conditions_clean = clean_query(conditions)
                self.__add_to_history__(
                    f"[Filter]: {count} element{conj}filtered using "
                    f"the filter '{conditions_clean}'"
                )
            else:
                del self._VERTICAPY_VARIABLES_["where"][-1]
                if vp.OPTIONS["print_info"] and "print_info" not in kwds:
                    print("Nothing was filtered.")
        return self

    @save_verticapy_logs
    def first(self, ts: str, offset: str):
        """
    Filters the vDataFrame by only keeping the first records.

    Parameters
    ----------
    ts: str
        TS (Time Series) vColumn to use to filter the data. The vColumn type must be
        date like (date, datetime, timestamp...)
    offset: str
        Interval offset. For example, to filter and keep only the first 6 months of
        records, offset should be set to '6 months'.

    Returns
    -------
    vDataFrame
        self

    See Also
    --------
    vDataFrame.at_time      : Filters the data at the input time.
    vDataFrame.between_time : Filters the data between two time ranges.
    vDataFrame.filter       : Filters the data using the input expression.
    vDataFrame.last         : Filters the data by only keeping the last records.
        """
        ts = self.format_colnames(ts)
        first_date = executeSQL(
            query=f"""
                SELECT 
                    /*+LABEL('vDataframe.first')*/ 
                    (MIN({ts}) + '{offset}'::interval)::varchar 
                FROM {self.__genSQL__()}""",
            title="Getting the vDataFrame first values.",
            method="fetchfirstelem",
            sql_push_ext=self._VERTICAPY_VARIABLES_["sql_push_ext"],
            symbol=self._VERTICAPY_VARIABLES_["symbol"],
        )
        self.filter(f"{ts} <= '{first_date}'")
        return self

    @save_verticapy_logs
    def flat_vmap(
        self,
        vmap_col: Union[str, list] = [],
        limit: int = 100,
        exclude_columns: list = [],
    ):
        """
    Flatten the selected VMap. A new vDataFrame is returned.
    
    \u26A0 Warning : This function might have a long runtime and can make your
                     vDataFrame less performant. It makes many calls to the
                     MAPLOOKUP function, which can be slow if your VMap is
                     large.

    Parameters
    ----------
    vmap_col: str / list, optional
        List of VMap columns to flatten.
    limit: int, optional
        Maximum number of keys to consider for each VMap. Only the most occurent 
        keys are used.
    exclude_columns: list, optional
        List of VMap columns to exclude.

    Returns
    -------
    vDataFrame
        object with the flattened VMaps.
        """
        if not (vmap_col):
            vmap_col = []
            all_cols = self.get_columns()
            for col in all_cols:
                if self[col].isvmap():
                    vmap_col += [col]
        if isinstance(vmap_col, str):
            vmap_col = [vmap_col]
        exclude_columns_final, vmap_col_final = (
            [quote_ident(col).lower() for col in exclude_columns],
            [],
        )
        for col in vmap_col:
            if quote_ident(col).lower() not in exclude_columns_final:
                vmap_col_final += [col]
        if not (vmap_col):
            raise EmptyParameter("No VMAP was detected.")
        maplookup = []
        for vmap in vmap_col_final:
            keys = util.compute_vmap_keys(expr=self, vmap_col=vmap, limit=limit)
            keys = [k[0] for k in keys]
            for k in keys:
                column = quote_ident(vmap)
                alias = quote_ident(vmap.replace('"', "") + "." + k.replace('"', ""))
                maplookup += [f"MAPLOOKUP({column}, '{k}') AS {alias}"]
        return self.select(self.get_columns() + maplookup)

    def get_columns(self, exclude_columns: Union[str, list] = []):
        """
    Returns the vDataFrame vColumns.

    Parameters
    ----------
    exclude_columns: str / list, optional
        List of the vColumns names to exclude from the final list. 

    Returns
    -------
    List
        List of all vDataFrame columns.

    See Also
    --------
    vDataFrame.catcol  : Returns all categorical vDataFrame vColumns.
    vDataFrame.datecol : Returns all vDataFrame vColumns of type date.
    vDataFrame.numcol  : Returns all numerical vDataFrame vColumns.
        """
        # -#
        if isinstance(exclude_columns, str):
            exclude_columns = [columns]
        columns = [elem for elem in self._VERTICAPY_VARIABLES_["columns"]]
        result = []
        exclude_columns = [elem for elem in exclude_columns]
        exclude_columns += [
            elem for elem in self._VERTICAPY_VARIABLES_["exclude_columns"]
        ]
        exclude_columns = [elem.replace('"', "").lower() for elem in exclude_columns]
        for column in columns:
            if column.replace('"', "").lower() not in exclude_columns:
                result += [column]
        return result

    @save_verticapy_logs
    def one_hot_encode(
        self,
        columns: Union[str, list] = [],
        max_cardinality: int = 12,
        prefix_sep: str = "_",
        drop_first: bool = True,
        use_numbers_as_suffix: bool = False,
    ):
        """
    Encodes the vColumns using the One Hot Encoding algorithm.

    Parameters
    ----------
    columns: str / list, optional
        List of the vColumns to use to train the One Hot Encoding model. If empty, 
        only the vColumns having a cardinality lesser than 'max_cardinality' will 
        be used.
    max_cardinality: int, optional
        Cardinality threshold to use to determine if the vColumn will be taken into
        account during the encoding. This parameter is used only if the parameter 
        'columns' is empty.
    prefix_sep: str, optional
        Prefix delimitor of the dummies names.
    drop_first: bool, optional
        Drops the first dummy to avoid the creation of correlated features.
    use_numbers_as_suffix: bool, optional
        Uses numbers as suffix instead of the vColumns categories.

    Returns
    -------
    vDataFrame
        self

    See Also
    --------
    vDataFrame[].decode       : Encodes the vColumn using a user defined Encoding.
    vDataFrame[].discretize   : Discretizes the vColumn.
    vDataFrame[].get_dummies  : Computes the vColumns result of One Hot Encoding.
    vDataFrame[].label_encode : Encodes the vColumn using the Label Encoding.
    vDataFrame[].mean_encode  : Encodes the vColumn using the Mean Encoding of a response.
        """
        if isinstance(columns, str):
            columns = [columns]
        columns = self.format_colnames(columns)
        if not (columns):
            columns = self.get_columns()
        cols_hand = True if (columns) else False
        for column in columns:
            if self[column].nunique(True) < max_cardinality:
                self[column].get_dummies(
                    "", prefix_sep, drop_first, use_numbers_as_suffix
                )
            elif cols_hand and vp.OPTIONS["print_info"]:
                warning_message = (
                    f"The vColumn '{column}' was ignored because of "
                    "its high cardinality.\nIncrease the parameter "
                    "'max_cardinality' to solve this issue or use "
                    "directly the vColumn get_dummies method."
                )
                warnings.warn(warning_message, Warning)
        return self

    get_dummies = one_hot_encode

    @save_verticapy_logs
    def groupby(
        self,
        columns: Union[str, list],
        expr: Union[str, list] = [],
        rollup: Union[bool, list] = False,
        having: str = "",
    ):
        """
    Aggregates the vDataFrame by grouping the elements.

    Parameters
    ----------
    columns: str / list
        List of the vColumns used to group the elements or a customized expression. 
        If rollup is set to True, this can be a list of tuples.
    expr: str / list, optional
        List of the different aggregations in pure SQL. Aliases can be used.
        For example, 'SUM(column)' or 'AVG(column) AS my_new_alias' are correct 
        whereas 'AVG' is incorrect. Aliases are recommended to keep the track of 
        the features and to prevent ambiguous names. For example, the MODE 
        function does not exist, but can be replicated by using the 'analytic' 
        method and then grouping the result.
    rollup: bool / list of bools, optional
        If set to True, the rollup operator is used.
        If set to a list of bools, the rollup operator is used on the matching
        indexes and the length of 'rollup' must match the length of 'columns.'
        For example, for columns = ['col1', ('col2', 'col3'), 'col4'] and
        rollup = [False, True, True], the rollup operator is used on the set
        ('col2', 'col3') and on 'col4'.
    having: str, optional
        Expression used to filter the result.

    Returns
    -------
    vDataFrame
        object result of the grouping.

    See Also
    --------
    vDataFrame.append   : Merges the vDataFrame with another relation.
    vDataFrame.analytic : Adds a new vColumn to the vDataFrame by using an advanced 
        analytical function on a specific vColumn.
    vDataFrame.join     : Joins the vDataFrame with another relation.
    vDataFrame.sort     : Sorts the vDataFrame.
        """
        if isinstance(columns, str):
            columns = [columns]
        if isinstance(expr, str):
            expr = [expr]
        assert not (isinstance(rollup, list)) or len(rollup) == len(
            columns
        ), ParameterError(
            "If parameter 'rollup' is of type list, it should have "
            "the same length as the 'columns' parameter."
        )
        columns_to_select = []
        if rollup == True:
            rollup_expr = "ROLLUP(" if rollup == True else ""
        else:
            rollup_expr = ""
        for idx, elem in enumerate(columns):
            if isinstance(elem, tuple) and rollup:
                if rollup == True:
                    rollup_expr += "("
                elif rollup[idx] == True:
                    rollup_expr += "ROLLUP("
                elif not (isinstance(rollup[idx], bool)):
                    raise ParameterError(
                        "When parameter 'rollup' is not a boolean, it "
                        "has to be a list of booleans."
                    )
                for item in elem:
                    colname = self.format_colnames(item)
                    if colname:
                        rollup_expr += colname
                        columns_to_select += [colname]
                    else:
                        rollup_expr += str(item)
                        columns_to_select += [item]
                    rollup_expr += ", "
                rollup_expr = rollup_expr[:-2] + "), "
            elif isinstance(elem, str):
                colname = self.format_colnames(elem)
                if colname:
                    if not (isinstance(rollup, bool)) and (rollup[idx] == True):
                        rollup_expr += "ROLLUP(" + colname + ")"
                    else:
                        rollup_expr += colname
                    columns_to_select += [colname]
                else:
                    if not (isinstance(rollup, bool)) and (rollup[idx] == True):
                        rollup_expr += "ROLLUP(" + str(elem) + ")"
                    else:
                        rollup_expr += str(elem)
                    columns_to_select += [elem]
                rollup_expr += ", "
            else:
                raise ParameterError(
                    "Parameter 'columns' must be a string; list of strings "
                    "or tuples (only when rollup is set to True)."
                )
        rollup_expr = rollup_expr[:-2]
        if rollup == True:
            rollup_expr += ")"
        if having:
            having = f" HAVING {having}"
        columns_str = ", ".join(
            [str(elem) for elem in columns_to_select] + [str(elem) for elem in expr]
        )
        if not (rollup):
            rollup_expr_str = ", ".join(
                [
                    str(i + 1)
                    for i in range(len([str(elem) for elem in columns_to_select]))
                ],
            )
        else:
            rollup_expr_str = rollup_expr
        relation = f"""
            (SELECT 
                {columns_str} 
            FROM {self.__genSQL__()} 
            GROUP BY {rollup_expr_str}{having}) VERTICAPY_SUBTABLE"""
        if not (rollup):
            rollup_expr_str = ", ".join([str(c) for c in columns_to_select])
        else:
            rollup_expr_str = rollup_expr
        return self.__vDataFrameSQL__(
            relation,
            "groupby",
            f"[Groupby]: The columns were grouped by {rollup_expr_str}",
        )

    @save_verticapy_logs
    def hchart(
        self,
        x: Union[str, list] = None,
        y: Union[str, list] = None,
        z: Union[str, list] = None,
        c: Union[str, list] = None,
        aggregate: bool = True,
        kind: Literal[
            "area",
            "area_range",
            "area_ts",
            "bar",
            "boxplot",
            "bubble",
            "candlestick",
            "donut",
            "donut3d",
            "heatmap",
            "hist",
            "line",
            "negative_bar",
            "pie",
            "pie_half",
            "pie3d",
            "scatter",
            "spider",
            "spline",
            "stacked_bar",
            "stacked_hist",
            "pearson",
            "kendall",
            "cramer",
            "biserial",
            "spearman",
            "spearmand",
        ] = "boxplot",
        width: int = 600,
        height: int = 400,
        options: dict = {},
        h: float = -1,
        max_cardinality: int = 10,
        limit: int = 10000,
        drilldown: bool = False,
        stock: bool = False,
        alpha: float = 0.25,
    ):
        """
    [Beta Version]
    Draws responsive charts using the High Chart API: 
    https://api.highcharts.com/highcharts/

    The returned object can be customized using the API parameters and the 
    'set_dict_options' method.

    \u26A0 Warning : This function uses the unsupported HighChart Python API. 
                     For more information, see python-hicharts repository:
                     https://github.com/kyper-data/python-highcharts

    Parameters
    ----------
    x / y / z / c: str / list
        The vColumns and aggregations used to draw the chart. These will depend 
        on the chart type. You can also specify an expression, but it must be a SQL 
        statement. For example: AVG(column1) + SUM(column2) AS new_name.

            area / area_ts / line / spline
                x: numerical or type date like vColumn.
                y: a single expression or list of expressions used to draw the plot
                z: [OPTIONAL] vColumn representing the different categories 
                    (only if y is a single vColumn)
            area_range
                x: numerical or date type vColumn.
                y: list of three expressions [expression, lower bound, upper bound]
            bar (single) / donut / donut3d / hist (single) / pie / pie_half / pie3d
                x: vColumn used to compute the categories.
                y: [OPTIONAL] numerical expression representing the categories values. 
                    If empty, COUNT(*) is used as the default aggregation.
            bar (double / drilldown) / hist (double / drilldown) / pie (drilldown) 
            / stacked_bar / stacked_hist
                x: vColumn used to compute the first category.
                y: vColumn used to compute the second category.
                z: [OPTIONAL] numerical expression representing the different categories 
                    values. 
                    If empty, COUNT(*) is used as the default aggregation.
            biserial / boxplot / pearson / kendall / pearson / spearman / spearmanD
                x: list of the vColumns used to draw the Chart.
            bubble / scatter
                x: numerical vColumn.
                y: numerical vColumn.
                z: numerical vColumn (bubble size in case of bubble plot, third 
                     dimension in case of scatter plot)
                c: [OPTIONAL] vColumn used to compute the different categories.
            candlestick
                x: date type vColumn.
                y: Can be a numerical vColumn or list of 5 expressions 
                    [last quantile, maximum, minimum, first quantile, volume]
            negative_bar
                x: binary vColumn used to compute the first category.
                y: vColumn used to compute the second category.
                z: [OPTIONAL] numerical expression representing the categories values. 
                    If empty, COUNT(*) is used as the default aggregation.
            spider
                x: vColumn used to compute the different categories.
                y: [OPTIONAL] Can be a list of the expressions used to draw the Plot 
                    or a single expression. 
                    If empty, COUNT(*) is used as the default aggregation.
    aggregate: bool, optional
        If set to True, the input vColumns will be aggregated.
    kind: str, optional
        Chart Type.
            area         : Area Chart
            area_range   : Area Range Chart
            area_ts      : Area Chart with Time Series Design
            bar          : Bar Chart
            biserial     : Biserial Point Matrix (Correlation between binary
                             variables and numerical)
            boxplot      : Box Plot
            bubble       : Bubble Plot
            candlestick  : Candlestick and Volumes (Time Series Special Plot)
            cramer       : Cramer's V Matrix (Correlation between categories)
            donut        : Donut Chart
            donut3d      : 3D Donut Chart
            heatmap      : Heatmap
            hist         : Histogram
            kendall      : Kendall Correlation Matrix. The method will compute the Tau-B 
                           coefficients.
                           \u26A0 Warning : This method uses a CROSS JOIN during computation 
                                            and is therefore computationally expensive at 
                                            O(n * n), where n is the total count of the 
                                            vDataFrame.
            line         : Line Plot
            negative_bar : Multi Bar Chart for binary classes
            pearson      : Pearson Correlation Matrix
            pie          : Pie Chart
            pie_half     : Half Pie Chart
            pie3d        : 3D Pie Chart
            scatter      : Scatter Plot
            spider       : Spider Chart
            spline       : Spline Plot
            stacked_bar  : Stacked Bar Chart
            stacked_hist : Stacked Histogram
            spearman     : Spearman's Correlation Matrix
            spearmanD    : Spearman's Correlation Matrix using the DENSE RANK
                           function instead of the RANK function.
    width: int, optional
        Chart Width.
    height: int, optional
        Chart Height.
    options: dict, optional
        High Chart Dictionary to use to customize the Chart. Look at the API 
        documentation to know the different options.
    h: float, optional
        Interval width of the bar. If empty, an optimized value will be used.
    max_cardinality: int, optional
        Maximum number of the vColumn distinct elements.
    limit: int, optional
        Maximum number of elements to draw.
    drilldown: bool, optional
        Drilldown Chart: Only possible for Bars, Histograms, donuts and pies.
                          Instead of drawing 2D charts, this option allows you
                          to add a drilldown effect to 1D Charts.
    stock: bool, optional
        Stock Chart: Only possible for Time Series. The design of the Time
                     Series is dragable and have multiple options.
    alpha: float, optional
        Value used to determine the position of the upper and lower quantile 
        (Used when kind is set to 'candlestick')

    Returns
    -------
    Highchart
        Chart Object
        """
        kind = str(kind).lower()
        params = [
            self,
            x,
            y,
            z,
            c,
            aggregate,
            kind,
            width,
            height,
            options,
            h,
            max_cardinality,
            limit,
            drilldown,
            stock,
            alpha,
        ]
        try:
            return hchart_from_vdf(*params)
        except:
            params[5] = not (params[5])
            return hchart_from_vdf(*params)

    def head(self, limit: int = 5):
        """
    Returns the vDataFrame head.

    Parameters
    ----------
    limit: int, optional
        Number of elements to display.

    Returns
    -------
    tablesample
        An object containing the result. For more information, see
        utilities.tablesample.

    See Also
    --------
    vDataFrame.tail : Returns the vDataFrame tail.
        """
        return self.iloc(limit=limit, offset=0)

    @save_verticapy_logs
    def heatmap(
        self,
        columns: Union[str, list],
        method: str = "count",
        of: str = "",
        h: tuple = (None, None),
        ax=None,
        **style_kwds,
    ):
        """
    Draws the Heatmap of the two input vColumns.

    Parameters
    ----------
    columns: str / list
        List of the vColumns names. The list must have two elements.
    method: str, optional
        The method to use to aggregate the data.
            count   : Number of elements.
            density : Percentage of the distribution.
            mean    : Average of the vColumn 'of'.
            min     : Minimum of the vColumn 'of'.
            max     : Maximum of the vColumn 'of'.
            sum     : Sum of the vColumn 'of'.
            q%      : q Quantile of the vColumn 'of (ex: 50% to get the median).
        It can also be a cutomized aggregation (ex: AVG(column1) + 5).
    of: str, optional
        The vColumn to use to compute the aggregation.
    h: tuple, optional
        Interval width of the vColumns 1 and 2 bars. Optimized h will be computed 
        if the parameter is empty or invalid.
    ax: Matplotlib axes object, optional
        The axes to plot on.
    **style_kwds
        Any optional parameter to pass to the Matplotlib functions.

    Returns
    -------
    ax
        Matplotlib axes object

    See Also
    --------
    vDataFrame.pivot_table  : Draws the pivot table of vColumns based on an aggregation.
        """
        if isinstance(columns, str):
            columns = [columns]
        columns, of = self.format_colnames(columns, of, expected_nb_of_cols=2)
        for column in columns:
            assert self[column].isnum(), TypeError(
                f"vColumn {column} must be numerical to draw the Heatmap."
            )
        min_max = self.agg(func=["min", "max"], columns=columns).transpose()
        ax = plt.pivot_table(
            vdf=self,
            columns=columns,
            method=method,
            of=of,
            h=h,
            max_cardinality=(0, 0),
            show=True,
            with_numbers=False,
            fill_none=0.0,
            ax=ax,
            return_ax=True,
            extent=min_max[columns[0]] + min_max[columns[1]],
            **style_kwds,
        )
        return ax

    @save_verticapy_logs
    def hexbin(
        self,
        columns: Union[str, list],
        method: Literal["density", "count", "avg", "min", "max", "sum"] = "count",
        of: str = "",
        bbox: list = [],
        img: str = "",
        ax=None,
        **style_kwds,
    ):
        """
    Draws the Hexbin of the input vColumns based on an aggregation.

    Parameters
    ----------
    columns: str / list
        List of the vColumns names. The list must have two elements.
    method: str, optional
        The method to use to aggregate the data.
            count   : Number of elements.
            density : Percentage of the distribution.
            mean    : Average of the vColumn 'of'.
            min     : Minimum of the vColumn 'of'.
            max     : Maximum of the vColumn 'of'.
            sum     : Sum of the vColumn 'of'.
    of: str, optional
        The vColumn to use to compute the aggregation.
    bbox: list, optional
        List of 4 elements to delimit the boundaries of the final Plot. 
        It must be similar the following list: [xmin, xmax, ymin, ymax]
    img: str, optional
         Path to the image to display as background.
    ax: Matplotlib axes object, optional
        The axes to plot on.
    **style_kwds
        Any optional parameter to pass to the Matplotlib functions.

    Returns
    -------
    ax
        Matplotlib axes object

    See Also
    --------
    vDataFrame.pivot_table : Draws the pivot table of vColumns based on an aggregation.
        """
        if isinstance(columns, str):
            columns = [columns]
        columns, of = self.format_colnames(columns, of, expected_nb_of_cols=2)
        return plt.hexbin(self, columns, method, of, bbox, img, ax=ax, **style_kwds)

    @save_verticapy_logs
    def hist(
        self,
        columns: Union[str, list],
        method: str = "density",
        of: str = "",
        max_cardinality: tuple = (6, 6),
        h: Union[int, float, tuple] = (None, None),
        hist_type: Literal["auto", "multi", "stacked"] = "auto",
        ax=None,
        **style_kwds,
    ):
        """
    Draws the histogram of the input vColumns based on an aggregation.

    Parameters
    ----------
    columns: str / list
        List of the vColumns names. The list must have less than 5 elements.
    method: str, optional
        The method to use to aggregate the data.
            count   : Number of elements.
            density : Percentage of the distribution.
            mean    : Average of the vColumn 'of'.
            min     : Minimum of the vColumn 'of'.
            max     : Maximum of the vColumn 'of'.
            sum     : Sum of the vColumn 'of'.
            q%      : q Quantile of the vColumn 'of' (ex: 50% to get the median).
        It can also be a cutomized aggregation (ex: AVG(column1) + 5).
    of: str, optional
        The vColumn to use to compute the aggregation.
    h: int/float/tuple, optional
        Interval width of the vColumns 1 and 2 bars. It is only valid if the 
        vColumns are numerical. Optimized h will be computed if the parameter 
        is empty or invalid.
    max_cardinality: tuple, optional
        Maximum number of distinct elements for vColumns 1 and 2 to be used as 
        categorical (No h will be picked or computed)
    hist_type: str, optional
        The Histogram Type.
            auto    : Regular Histogram based on 1 or 2 vColumns.
            multi   : Multiple Regular Histograms based on 1 to 5 vColumns.
            stacked : Stacked Histogram based on 2 vColumns.
    ax: Matplotlib axes object, optional
        The axes to plot on.
    **style_kwds
        Any optional parameter to pass to the Matplotlib functions.

    Returns
    -------
    ax
        Matplotlib axes object

    See Also
    --------
    vDataFrame.bar         : Draws the bar chart of the input vColumns based on an aggregation.
    vDataFrame.boxplot     : Draws the Box Plot of the input vColumns.
    vDataFrame.pivot_table : Draws the pivot table of vColumns based on an aggregation.
        """
        if isinstance(columns, str):
            columns = [columns]
        columns, of = self.format_colnames(
            columns, of, expected_nb_of_cols=[1, 2, 3, 4, 5]
        )
        stacked = True if (hist_type.lower() == "stacked") else False
        multi = True if (hist_type.lower() == "multi") else False
        if len(columns) == 1:
            return self[columns[0]].hist(method, of, 6, 0, 0, **style_kwds)
        else:
            if multi:
                if isinstance(h, (int, float)):
                    h_0 = h
                else:
                    h_0 = h[0] if (h[0]) else 0
                return plt.multiple_hist(
                    self, columns, method, of, h_0, ax=ax, **style_kwds,
                )
            else:
                return plt.hist2D(
                    self,
                    columns,
                    method,
                    of,
                    max_cardinality,
                    h,
                    stacked,
                    ax=ax,
                    **style_kwds,
                )

    def iloc(self, limit: int = 5, offset: int = 0, columns: Union[str, list] = []):
        """
    Returns a part of the vDataFrame (delimited by an offset and a limit).

    Parameters
    ----------
    limit: int, optional
        Number of elements to display.
    offset: int, optional
        Number of elements to skip.
    columns: str / list, optional
        A list containing the names of the vColumns to include in the result. 
        If empty, all vColumns will be selected.


    Returns
    -------
    tablesample
        An object containing the result. For more information, see
        utilities.tablesample.

    See Also
    --------
    vDataFrame.head : Returns the vDataFrame head.
    vDataFrame.tail : Returns the vDataFrame tail.
        """
        # -#
        if isinstance(columns, str):
            columns = [columns]
        if offset < 0:
            offset = max(0, self.shape()[0] - limit)
        columns = self.format_colnames(columns)
        if not (columns):
            columns = self.get_columns()
        all_columns = []
        for column in columns:
            cast = bin_spatial_to_str(self[column].category(), column)
            all_columns += [f"{cast} AS {column}"]
        title = (
            "Reads the final relation using a limit "
            f"of {limit} and an offset of {offset}."
        )
        result = util.to_tablesample(
            query=f"""
                SELECT 
                    {', '.join(all_columns)} 
                FROM {self.__genSQL__()}
                {self.__get_last_order_by__()} 
                LIMIT {limit} OFFSET {offset}""",
            title=title,
            max_columns=self._VERTICAPY_VARIABLES_["max_columns"],
            sql_push_ext=self._VERTICAPY_VARIABLES_["sql_push_ext"],
            symbol=self._VERTICAPY_VARIABLES_["symbol"],
        )
        pre_comp = self.__get_catalog_value__("VERTICAPY_COUNT")
        if pre_comp != "VERTICAPY_NOT_PRECOMPUTED":
            result.count = pre_comp
        elif vp.OPTIONS["count_on"]:
            result.count = self.shape()[0]
        result.offset = offset
        result.name = self._VERTICAPY_VARIABLES_["input_relation"]
        columns = self.get_columns()
        all_percent = True
        for column in columns:
            if not ("percent" in self[column].catalog):
                all_percent = False
        all_percent = (all_percent or (vp.OPTIONS["percent_bar"] == True)) and (
            vp.OPTIONS["percent_bar"] != False
        )
        if all_percent:
            percent = self.aggregate(["percent"], columns).transpose().values
        for column in result.values:
            result.dtype[column] = self[column].ctype()
            if all_percent:
                result.percent[column] = percent[self.format_colnames(column)][0]
        return result

    def info(self):
        """
    Displays information about the different vDataFrame transformations.

    Returns
    -------
    str
        information on the vDataFrame modifications
        """
        if len(self._VERTICAPY_VARIABLES_["history"]) == 0:
            result = "The vDataFrame was never modified."
        elif len(self._VERTICAPY_VARIABLES_["history"]) == 1:
            result = "The vDataFrame was modified with only one action: "
            result += "\n * " + self._VERTICAPY_VARIABLES_["history"][0]
        else:
            result = "The vDataFrame was modified many times: "
            for modif in self._VERTICAPY_VARIABLES_["history"]:
                result += "\n * " + modif
        return result

    @save_verticapy_logs
    def isin(self, val: dict):
        """
    Looks if some specific records are in the vDataFrame and it returns the new 
    vDataFrame of the search.

    Parameters
    ----------
    val: dict
        Dictionary of the different records. Each key of the dictionary must 
        represent a vColumn. For example, to check if Badr Ouali and 
        Fouad Teban are in the vDataFrame. You can write the following dict:
        {"name": ["Teban", "Ouali"], "surname": ["Fouad", "Badr"]}

    Returns
    -------
    vDataFrame
        The vDataFrame of the search.
        """
        val = self.format_colnames(val)
        n = len(val[list(val.keys())[0]])
        result = []
        for i in range(n):
            tmp_query = []
            for column in val:
                if val[column][i] == None:
                    tmp_query += [f"{quote_ident(column)} IS NULL"]
                else:
                    val_str = str(val[column][i]).replace("'", "''")
                    tmp_query += [f"{quote_ident(column)} = '{val_str}'"]
            result += [" AND ".join(tmp_query)]
        return self.search(" OR ".join(result))

    @save_verticapy_logs
    def join(
        self,
        input_relation,
        on: Union[tuple, dict, list] = {},
        on_interpolate: dict = {},
        how: Literal[
            "left", "right", "cross", "full", "natural", "self", "inner", ""
        ] = "natural",
        expr1: Union[str, list] = ["*"],
        expr2: Union[str, list] = ["*"],
    ):
        """
    Joins the vDataFrame with another one or an input relation.

    \u26A0 Warning : Joins can make the vDataFrame structure heavier. It is 
                     recommended to always check the current structure 
                     using the 'current_relation' method and to save it using the 
                     'to_db' method with the parameters 'inplace = True' and 
                     'relation_type = table'

    Parameters
    ----------
    input_relation: str/vDataFrame
        Relation to use to do the merging.
    on: tuple / dict / list, optional
        If it is a list then:
        List of 3-tuples. Each tuple must include (key1, key2, operator)—where
        key1 is the key of the vDataFrame, key2 is the key of the input relation,
        and operator can be one of the following:
                     '=' : exact match
                     '<' : key1  < key2
                     '>' : key1  > key2
                    '<=' : key1 <= key2
                    '>=' : key1 >= key2
                 'llike' : key1 LIKE '%' || key2 || '%'
                 'rlike' : key2 LIKE '%' || key1 || '%'
           'linterpolate': key1 INTERPOLATE key2
           'rinterpolate': key2 INTERPOLATE key1
        Some operators need 5-tuples: (key1, key2, operator, operator2, x)—where
        operator2 is a simple operator (=, >, <, <=, >=), x is a float or an integer, 
        and operator is one of the following:
                 'jaro' : JARO(key1, key2) operator2 x
                'jarow' : JARO_WINCKLER(key1, key2) operator2 x
                  'lev' : LEVENSHTEIN(key1, key2) operator2 x
        
        If it is a dictionary then:
        This parameter must include all the different keys. It must be similar 
        to the following:
        {"relationA_key1": "relationB_key1" ..., "relationA_keyk": "relationB_keyk"}
        where relationA is the current vDataFrame and relationB is the input relation
        or the input vDataFrame.
    on_interpolate: dict, optional
        Dictionary of all different keys. Used to join two event series together 
        using some ordered attribute, event series joins let you compare values from 
        two series directly, rather than having to normalize the series to the same 
        measurement interval. The dict must be similar to the following:
        {"relationA_key1": "relationB_key1" ..., "relationA_keyk": "relationB_keyk"}
        where relationA is the current vDataFrame and relationB is the input relation
        or the input vDataFrame.
    how: str, optional
        Join Type.
            left    : Left Join.
            right   : Right Join.
            cross   : Cross Join.
            full    : Full Outer Join.
            natural : Natural Join.
            inner   : Inner Join.
    expr1: str / list, optional
        List of the different columns in pure SQL to select from the current 
        vDataFrame, optionally as aliases. Aliases are recommended to avoid 
        ambiguous names. For example: 'column' or 'column AS my_new_alias'. 
    expr2: str / list, optional
        List of the different columns in pure SQL to select from the input 
        relation optionally as aliases. Aliases are recommended to avoid 
        ambiguous names. For example: 'column' or 'column AS my_new_alias'.

    Returns
    -------
    vDataFrame
        object result of the join.

    See Also
    --------
    vDataFrame.append  : Merges the vDataFrame with another relation.
    vDataFrame.groupby : Aggregates the vDataFrame.
    vDataFrame.sort    : Sorts the vDataFrame.
        """
        if isinstance(expr1, str):
            expr1 = [expr1]
        if isinstance(expr2, str):
            expr2 = [expr2]
        if isinstance(on, tuple):
            on = [on]
        # Giving the right alias to the right relation
        def create_final_relation(relation: str, alias: str):
            if (
                ("SELECT" in relation.upper())
                and ("FROM" in relation.upper())
                and ("(" in relation)
                and (")" in relation)
            ):
                return f"(SELECT * FROM {relation}) AS {alias}"
            else:
                return f"{relation} AS {alias}"

        # List with the operators
        if str(how).lower() == "natural" and (on or on_interpolate):
            raise ParameterError(
                "Natural Joins cannot be computed if any of "
                "the parameters 'on' or 'on_interpolate' are "
                "defined."
            )
        on_list = []
        if isinstance(on, dict):
            on_list += [(key, on[key], "=") for key in on]
        else:
            on_list += [elem for elem in on]
        on_list += [(key, on[key], "linterpolate") for key in on_interpolate]
        # Checks
        self.format_colnames([elem[0] for elem in on_list])
        if isinstance(input_relation, vDataFrame):
            input_relation.format_colnames([elem[1] for elem in on_list])
            relation = input_relation.__genSQL__()
        else:
            relation = input_relation
        # Relations
        first_relation = create_final_relation(self.__genSQL__(), alias="x")
        second_relation = create_final_relation(relation, alias="y")
        # ON
        on_join = []
        all_operators = [
            "=",
            ">",
            ">=",
            "<",
            "<=",
            "llike",
            "rlike",
            "linterpolate",
            "rinterpolate",
            "jaro",
            "jarow",
            "lev",
        ]
        simple_operators = all_operators[0:5]
        for elem in on_list:
            key1, key2, op = quote_ident(elem[0]), quote_ident(elem[1]), elem[2]
            if op not in all_operators:
                raise ValueError(
                    f"Incorrect operator: '{op}'.\nCorrect values: {', '.join(simple_operators)}."
                )
            if op in ("=", ">", ">=", "<", "<="):
                on_join += [f"x.{key1} {op} y.{key2}"]
            elif op == "llike":
                on_join += [f"x.{key1} LIKE '%' || y.{key2} || '%'"]
            elif op == "rlike":
                on_join += [f"y.{key2} LIKE '%' || x.{key1} || '%'"]
            elif op == "linterpolate":
                on_join += [f"x.{key1} INTERPOLATE PREVIOUS VALUE y.{key2}"]
            elif op == "rinterpolate":
                on_join += [f"y.{key2} INTERPOLATE PREVIOUS VALUE x.{key1}"]
            elif op in ("jaro", "jarow", "lev"):
                if op in ("jaro", "jarow"):
                    util.vertica_version(condition=[12, 0, 2])
                else:
                    util.vertica_version(condition=[10, 1, 0])
                op2, x = elem[3], elem[4]
                if op2 not in simple_operators:
                    raise ValueError(
                        f"Incorrect operator: '{op2}'.\nCorrect values: {', '.join(simple_operators)}."
                    )
                map_to_fun = {
                    "jaro": "JARO_DISTANCE",
                    "jarow": "JARO_WINKLER_DISTANCE",
                    "lev": "EDIT_DISTANCE",
                }
                fun = map_to_fun[op]
                on_join += [f"{fun}(x.{key1}, y.{key2}) {op2} {x}"]
        # Final
        on_join = " ON " + " AND ".join(on_join) if on_join else ""
        expr = [f"x.{key}" for key in expr1] + [f"y.{key}" for key in expr2]
        expr = "*" if not (expr) else ", ".join(expr)
        if how:
            how = " " + how.upper() + " "
        table = (
            f"SELECT {expr} FROM {first_relation}{how}JOIN {second_relation} {on_join}"
        )
        return self.__vDataFrameSQL__(
            f"({table}) VERTICAPY_SUBTABLE",
            "join",
            "[Join]: Two relations were joined together",
        )

    @save_verticapy_logs
    def kurtosis(
        self, columns: list = [], **agg_kwds,
    ):
        """
    Aggregates the vDataFrame using 'kurtosis'.

    Parameters
    ----------
    columns: list, optional
        List of the vColumns names. If empty, all numerical vColumns will be 
        used.
    **agg_kwds
        Any optional parameter to pass to the Aggregate function.

    Returns
    -------
    tablesample
        An object containing the result. For more information, see
        utilities.tablesample.

    See Also
    --------
    vDataFrame.aggregate : Computes the vDataFrame input aggregations.
        """
        return self.aggregate(func=["kurtosis"], columns=columns, **agg_kwds,)

    kurt = kurtosis

    @save_verticapy_logs
    def last(self, ts: str, offset: str):
        """
    Filters the vDataFrame by only keeping the last records.

    Parameters
    ----------
    ts: str
        TS (Time Series) vColumn to use to filter the data. The vColumn type must be
        date like (date, datetime, timestamp...)
    offset: str
        Interval offset. For example, to filter and keep only the last 6 months of
        records, offset should be set to '6 months'.

    Returns
    -------
    vDataFrame
        self

    See Also
    --------
    vDataFrame.at_time      : Filters the data at the input time.
    vDataFrame.between_time : Filters the data between two time ranges.
    vDataFrame.first        : Filters the data by only keeping the first records.
    vDataFrame.filter       : Filters the data using the input expression.
        """
        ts = self.format_colnames(ts)
        last_date = executeSQL(
            query=f"""
                SELECT 
                    /*+LABEL('vDataframe.last')*/ 
                    (MAX({ts}) - '{offset}'::interval)::varchar 
                FROM {self.__genSQL__()}""",
            title="Getting the vDataFrame last values.",
            method="fetchfirstelem",
            sql_push_ext=self._VERTICAPY_VARIABLES_["sql_push_ext"],
            symbol=self._VERTICAPY_VARIABLES_["symbol"],
        )
        self.filter(f"{ts} >= '{last_date}'")
        return self

    @save_verticapy_logs
    def load(self, offset: int = -1):
        """
    Loads a previous structure of the vDataFrame. 

    Parameters
    ----------
    offset: int, optional
        offset of the saving. Example: -1 to load the last saving.

    Returns
    -------
    vDataFrame
        vDataFrame of the loading.

    See Also
    --------
    vDataFrame.save : Saves the current vDataFrame structure.
        """
        save = self._VERTICAPY_VARIABLES_["saving"][offset]
        vdf = pickle.loads(save)
        return vdf

    @save_verticapy_logs
    def mad(
        self, columns: list = [], **agg_kwds,
    ):
        """
    Aggregates the vDataFrame using 'mad' (Median Absolute Deviation).

    Parameters
    ----------
    columns: list, optional
        List of the vColumns names. If empty, all numerical vColumns will be 
        used.
    **agg_kwds
        Any optional parameter to pass to the Aggregate function.

    Returns
    -------
    tablesample
        An object containing the result. For more information, see
        utilities.tablesample.

    See Also
    --------
    vDataFrame.aggregate : Computes the vDataFrame input aggregations.
        """
        return self.aggregate(func=["mad"], columns=columns, **agg_kwds,)

    @save_verticapy_logs
    def max(
        self, columns: list = [], **agg_kwds,
    ):
        """
    Aggregates the vDataFrame using 'max' (Maximum).

    Parameters
    ----------
    columns: list, optional
        List of the vColumns names. If empty, all numerical vColumns will be 
        used.
    **agg_kwds
        Any optional parameter to pass to the Aggregate function.

    Returns
    -------
    tablesample
        An object containing the result. For more information, see
        utilities.tablesample.

    See Also
    --------
    vDataFrame.aggregate : Computes the vDataFrame input aggregations.
        """
        return self.aggregate(func=["max"], columns=columns, **agg_kwds,)

    @save_verticapy_logs
    def median(
        self, columns: list = [], approx: bool = True, **agg_kwds,
    ):
        """
    Aggregates the vDataFrame using 'median'.

    Parameters
    ----------
    columns: list, optional
        List of the vColumns names. If empty, all numerical vColumns will be 
        used.
    approx: bool, optional
        If set to True, the approximate median is returned. By setting this 
        parameter to False, the function's performance can drastically decrease.
    **agg_kwds
        Any optional parameter to pass to the Aggregate function.

    Returns
    -------
    tablesample
        An object containing the result. For more information, see
        utilities.tablesample.

    See Also
    --------
    vDataFrame.aggregate : Computes the vDataFrame input aggregations.
        """
        return self.quantile(0.5, columns=columns, approx=approx, **agg_kwds,)

    @save_verticapy_logs
    def memory_usage(self):
        """
    Returns the vDataFrame memory usage. 

    Returns
    -------
    tablesample
        An object containing the result. For more information, see
        utilities.tablesample.

    See Also
    --------
    vDataFrame.expected_store_usage : Returns the expected store usage.
        """
        total = sum(
            [sys.getsizeof(elem) for elem in self._VERTICAPY_VARIABLES_]
        ) + sys.getsizeof(self)
        values = {"index": ["object"], "value": [total]}
        columns = [elem for elem in self._VERTICAPY_VARIABLES_["columns"]]
        for column in columns:
            values["index"] += [column]
            values["value"] += [self[column].memory_usage()]
            total += self[column].memory_usage()
        values["index"] += ["total"]
        values["value"] += [total]
        return util.tablesample(values=values)

    @save_verticapy_logs
    def merge_similar_names(self, skip_word: Union[str, list]):
        """
    Merges columns with similar names. The function generates a COALESCE 
    statement that merges the columns into a single column that excludes 
    the input words. Note that the order of the variables in the COALESCE 
    statement is based on the order of the 'get_columns' method.
    
    Parameters
    ---------- 
    skip_word: str / list, optional
        List of words to exclude from the provided column names. 
        For example, if two columns are named 'age.information.phone' 
        and 'age.phone' AND skip_word is set to ['.information'], then 
        the two columns will be merged together with the following 
        COALESCE statement:
        COALESCE("age.phone", "age.information.phone") AS "age.phone"

    Returns
    -------
    vDataFrame
        An object containing the merged element.
        """
        if isinstance(skip_word, str):
            skip_word = [skip_word]
        columns = self.get_columns()
        group_dict = group_similar_names(columns, skip_word=skip_word)
        sql = f"""
            (SELECT 
                {gen_coalesce(group_dict)} 
            FROM {self.__genSQL__()}) VERTICAPY_SUBTABLE"""
        return self.__vDataFrameSQL__(
            sql,
            "merge_similar_names",
            "[merge_similar_names]: The columns were merged.",
        )

    @save_verticapy_logs
    def min(
        self, columns: list = [], **agg_kwds,
    ):
        """
    Aggregates the vDataFrame using 'min' (Minimum).

    Parameters
    ----------
    columns: list, optional
        List of the vColumns names. If empty, all numerical vColumns will be 
        used.
    **agg_kwds
        Any optional parameter to pass to the Aggregate function.

    Returns
    -------
    tablesample
        An object containing the result. For more information, see
        utilities.tablesample.

    See Also
    --------
    vDataFrame.aggregate : Computes the vDataFrame input aggregations.
        """
        return self.aggregate(func=["min"], columns=columns, **agg_kwds,)

    @save_verticapy_logs
    def narrow(
        self,
        index: Union[str, list],
        columns: Union[str, list] = [],
        col_name: str = "column",
        val_name: str = "value",
    ):
        """
    Returns the Narrow Table of the vDataFrame using the input vColumns.

    Parameters
    ----------
    index: str / list
        Index(es) used to identify the Row.
    columns: str / list, optional
        List of the vColumns names. If empty, all vColumns except the index(es)
        will be used.
    col_name: str, optional
        Alias of the vColumn representing the different input vColumns names as 
        categories.
    val_name: str, optional
        Alias of the vColumn representing the different input vColumns values.

    Returns
    -------
    vDataFrame
        the narrow table object.

    See Also
    --------
    vDataFrame.pivot : Returns the pivot table of the vDataFrame.
        """
        index, columns = self.format_colnames(index, columns)
        if isinstance(columns, str):
            columns = [columns]
        if isinstance(index, str):
            index = [index]
        if not (columns):
            columns = self.numcol()
        for idx in index:
            if idx in columns:
                columns.remove(idx)
        query = []
        all_are_num, all_are_date = True, True
        for column in columns:
            if not (self[column].isnum()):
                all_are_num = False
            if not (self[column].isdate()):
                all_are_date = False
        for column in columns:
            conv = ""
            if not (all_are_num) and not (all_are_num):
                conv = "::varchar"
            elif self[column].category() == "int":
                conv = "::int"
            column_str = column.replace("'", "''")[1:-1]
            query += [
                f"""
                (SELECT 
                    {', '.join(index)}, 
                    '{column_str}' AS {col_name}, 
                    {column}{conv} AS {val_name} 
                FROM {self.__genSQL__()})"""
            ]
        query = " UNION ALL ".join(query)
        query = f"({query}) VERTICAPY_SUBTABLE"
        return self.__vDataFrameSQL__(
            query, "narrow", f"[Narrow]: Narrow table using index = {index}",
        )

    melt = narrow

    @save_verticapy_logs
    def normalize(
        self,
        columns: Union[str, list] = [],
        method: Literal["zscore", "robust_zscore", "minmax"] = "zscore",
    ):
        """
    Normalizes the input vColumns using the input method.

    Parameters
    ----------
    columns: str / list, optional
        List of the vColumns names. If empty, all numerical vColumns will be 
        used.
    method: str, optional
        Method to use to normalize.
            zscore        : Normalization using the Z-Score (avg and std).
                (x - avg) / std
            robust_zscore : Normalization using the Robust Z-Score (median and mad).
                (x - median) / (1.4826 * mad)
            minmax        : Normalization using the MinMax (min and max).
                (x - min) / (max - min)

    Returns
    -------
    vDataFrame
        self

    See Also
    --------
    vDataFrame.outliers    : Computes the vDataFrame Global Outliers.
    vDataFrame[].normalize : Normalizes the vColumn. This method is more complete 
        than the vDataFrame.normalize method by allowing more parameters.
        """
        if isinstance(columns, str):
            columns = [columns]
        no_cols = True if not (columns) else False
        columns = self.numcol() if not (columns) else self.format_colnames(columns)
        for column in columns:
            if self[column].isnum() and not (self[column].isbool()):
                self[column].normalize(method=method)
            elif (no_cols) and (self[column].isbool()):
                pass
            elif vp.OPTIONS["print_info"]:
                warning_message = (
                    f"The vColumn {column} was skipped.\n"
                    "Normalize only accept numerical data types."
                )
                warnings.warn(warning_message, Warning)
        return self

    def numcol(self, exclude_columns: list = []):
        """
    Returns a list of names of the numerical vColumns in the vDataFrame.

    Parameters
    ----------
    exclude_columns: list, optional
        List of the vColumns names to exclude from the final list. 

    Returns
    -------
    List
        List of numerical vColumns names. 
    
    See Also
    --------
    vDataFrame.catcol      : Returns the categorical type vColumns in the vDataFrame.
    vDataFrame.get_columns : Returns the vColumns of the vDataFrame.
        """
        columns, cols = [], self.get_columns(exclude_columns=exclude_columns)
        for column in cols:
            if self[column].isnum():
                columns += [column]
        return columns

    @save_verticapy_logs
    def nunique(
        self, columns: list = [], approx: bool = True, **agg_kwds,
    ):
        """
    Aggregates the vDataFrame using 'unique' (cardinality).

    Parameters
    ----------
    columns: list, optional
        List of the vColumns names. If empty, all vColumns will be used.
    approx: bool, optional
        If set to True, the approximate cardinality is returned. By setting 
        this parameter to False, the function's performance can drastically 
        decrease.
    **agg_kwds
        Any optional parameter to pass to the Aggregate function.

    Returns
    -------
    tablesample
        An object containing the result. For more information, see
        utilities.tablesample.

    See Also
    --------
    vDataFrame.aggregate : Computes the vDataFrame input aggregations.
        """
        func = ["approx_unique"] if approx else ["unique"]
        return self.aggregate(func=func, columns=columns, **agg_kwds,)

    @save_verticapy_logs
    def outliers(
        self,
        columns: Union[str, list] = [],
        name: str = "distribution_outliers",
        threshold: float = 3.0,
        robust: bool = False,
    ):
        """
    Adds a new vColumn labeled with 0 and 1. 1 means that the record is a global 
    outlier.

    Parameters
    ----------
    columns: str / list, optional
        List of the vColumns names. If empty, all numerical vColumns will be 
        used.
    name: str, optional
        Name of the new vColumn.
    threshold: float, optional
        Threshold equals to the critical score.
    robust: bool
        If set to True, the score used will be the Robust Z-Score instead of 
        the Z-Score.

    Returns
    -------
    vDataFrame
        self

    See Also
    --------
    vDataFrame.normalize : Normalizes the input vColumns.
        """
        if isinstance(columns, str):
            columns = [columns]
        columns = self.format_colnames(columns) if (columns) else self.numcol()
        if not (robust):
            result = self.aggregate(func=["std", "avg"], columns=columns).values
        else:
            result = self.aggregate(
                func=["mad", "approx_median"], columns=columns
            ).values
        conditions = []
        for idx, col in enumerate(result["index"]):
            if not (robust):
                conditions += [
                    f"""
                    ABS({col} - {result['avg'][idx]}) 
                    / NULLIFZERO({result['std'][idx]}) 
                    > {threshold}"""
                ]
            else:
                conditions += [
                    f"""
                    ABS({col} - {result['approx_median'][idx]}) 
                    / NULLIFZERO({result['mad'][idx]} * 1.4826) 
                    > {threshold}"""
                ]
        self.eval(name, f"(CASE WHEN {' OR '.join(conditions)} THEN 1 ELSE 0 END)")
        return self

    @save_verticapy_logs
    def outliers_plot(
        self,
        columns: Union[str, list],
        threshold: float = 3.0,
        color: str = "orange",
        outliers_color: str = "black",
        inliers_color: str = "white",
        inliers_border_color: str = "red",
        max_nb_points: int = 500,
        ax=None,
        **style_kwds,
    ):
        """
    Draws the global outliers plot of one or two columns based on their ZSCORE.

    Parameters
    ----------
    columns: str / list
        List of one or two vColumn names.
    threshold: float, optional
        ZSCORE threshold used to detect outliers.
    color: str, optional
        Inliers Area color.
    outliers_color: str, optional
        Outliers color.
    inliers_color: str, optional
        Inliers color.
    inliers_border_color: str, optional
        Inliers border color.
    max_nb_points: int, optional
        Maximum number of points to display.
    ax: Matplotlib axes object, optional
        The axes to plot on.
    **style_kwds
        Any optional parameter to pass to the Matplotlib functions.

    Returns
    -------
    ax: Matplotlib axes object, optional
        The axes to plot on.
        """
        if isinstance(columns, str):
            columns = [columns]
        columns = self.format_colnames(columns, expected_nb_of_cols=[1, 2])
        return plt.outliers_contour_plot(
            self,
            columns,
            color=color,
            threshold=threshold,
            outliers_color=outliers_color,
            inliers_color=inliers_color,
            inliers_border_color=inliers_border_color,
            max_nb_points=max_nb_points,
            ax=ax,
            **style_kwds,
        )

    @save_verticapy_logs
    def pacf(
        self,
        column: str,
        ts: str,
        by: Union[str, list] = [],
        p: Union[int, list] = 5,
        unit: str = "rows",
        confidence: bool = True,
        alpha: float = 0.95,
        show: bool = True,
        ax=None,
        **style_kwds,
    ):
        """
    Computes the partial autocorrelations of the input vColumn.

    Parameters
    ----------
    column: str
        Input vColumn to use to compute the partial autocorrelation plot.
    ts: str
        TS (Time Series) vColumn to use to order the data. It can be of type date
        or a numerical vColumn.
    by: str / list, optional
        vColumns used in the partition.
    p: int/list, optional
        Int equals to the maximum number of lag to consider during the computation
        or List of the different lags to include during the computation.
        p must be positive or a list of positive integers.
    unit: str, optional
        Unit to use to compute the lags.
            rows: Natural lags
            else : Any time unit, for example you can write 'hour' to compute the hours
                lags or 'day' to compute the days lags.
    confidence: bool, optional
        If set to True, the confidence band width is drawn.
    alpha: float, optional
        Significance Level. Probability to accept H0. Only used to compute the confidence
        band width.
    show: bool, optional
        If set to True, the Partial Auto Correlation Plot will be drawn using Matplotlib.
    ax: Matplotlib axes object, optional
        The axes to plot on.
    **style_kwds
        Any optional parameter to pass to the Matplotlib functions.

    Returns
    -------
    tablesample
        An object containing the result. For more information, see
        utilities.tablesample.

    See Also
    --------
    vDataFrame.acf    : Computes the correlations between a vColumn and its lags.
    vDataFrame.interpolate : Interpolates and computes a regular time interval vDataFrame.
    vDataFrame.corr   : Computes the correlation matrix of a vDataFrame.
    vDataFrame.cov    : Computes the covariance matrix of the vDataFrame.
        """
        if isinstance(by, str):
            by = [by]
        if isinstance(p, Iterable) and (len(p) == 1):
            p = p[0]
            if p == 0:
                return 1.0
            elif p == 1:
                return self.acf(ts=ts, column=column, by=by, p=[1], unit=unit)
            by, column, ts = self.format_colnames(by, column, ts)
            if unit == "rows":
                table = self.__genSQL__()
            else:
                table = self.interpolate(
                    ts=ts, rule=f"1 {unit}", method={column: "linear"}, by=by
                ).__genSQL__()
            by = f"PARTITION BY {', '.join(by)} " if (by) else ""
            columns = [
                f"LAG({column}, {i}) OVER ({by}ORDER BY {ts}) AS lag_{i}_{gen_name([column])}"
                for i in range(1, p + 1)
            ]
            relation = f"(SELECT {', '.join([column] + columns)} FROM {table}) pacf"
            tmp_view_name = gen_tmp_name(
                schema=vp.OPTIONS["temp_schema"], name="linear_reg_view"
            )
            tmp_lr0_name = gen_tmp_name(
                schema=vp.OPTIONS["temp_schema"], name="linear_reg0"
            )
            tmp_lr1_name = gen_tmp_name(
                schema=vp.OPTIONS["temp_schema"], name="linear_reg1"
            )
            try:
                util.drop(tmp_view_name, method="view")
                query = f"""
                    CREATE VIEW {tmp_view_name} 
                        AS SELECT /*+LABEL('vDataframe.pacf')*/ * FROM {relation}"""
                executeSQL(query, print_time_sql=False)
                vdf = vDataFrame(tmp_view_name)
                util.drop(tmp_lr0_name, method="model")
                model = vp.learn.linear_model.LinearRegression(
                    name=tmp_lr0_name, solver="Newton"
                )
                model.fit(
                    input_relation=tmp_view_name,
                    X=[f"lag_{i}_{gen_name([column])}" for i in range(1, p)],
                    y=column,
                )
                model.predict(vdf, name="prediction_0")
                util.drop(tmp_lr1_name, method="model")
                model = vp.learn.linear_model.LinearRegression(
                    name=tmp_lr1_name, solver="Newton"
                )
                model.fit(
                    input_relation=tmp_view_name,
                    X=[f"lag_{i}_{gen_name([column])}" for i in range(1, p)],
                    y=f"lag_{p}_{gen_name([column])}",
                )
                model.predict(vdf, name="prediction_p")
                vdf.eval(expr=f"{column} - prediction_0", name="eps_0")
                vdf.eval(
                    expr=f"lag_{p}_{gen_name([column])} - prediction_p", name="eps_p",
                )
                result = vdf.corr(["eps_0", "eps_p"])
            finally:
                util.drop(tmp_view_name, method="view")
                util.drop(tmp_lr0_name, method="model")
                util.drop(tmp_lr1_name, method="model")
            return result
        else:
            if isinstance(p, (float, int)):
                p = range(0, p + 1)
            loop = tqdm(p) if vp.OPTIONS["tqdm"] else p
            pacf = []
            for i in loop:
                pacf += [self.pacf(ts=ts, column=column, by=by, p=[i], unit=unit)]
            columns = [elem for elem in p]
            pacf_band = []
            if confidence:
                for k in range(1, len(pacf) + 1):
                    pacf_band += [
                        math.sqrt(2)
                        * scipy_special.erfinv(alpha)
                        / math.sqrt(self[column].count() - k + 1)
                        * math.sqrt((1 + 2 * sum([pacf[i] ** 2 for i in range(1, k)])))
                    ]
            result = util.tablesample({"index": columns, "value": pacf})
            if pacf_band:
                result.values["confidence"] = pacf_band
            if show:
                plt.acf_plot(
                    result.values["index"],
                    result.values["value"],
                    title="Partial Autocorrelation",
                    confidence=pacf_band,
                    type_bar=True,
                    ax=ax,
                    **style_kwds,
                )
            return result

    @save_verticapy_logs
    def pie(
        self,
        columns: Union[str, list],
        max_cardinality: Union[int, tuple, list] = None,
        h: Union[float, tuple] = None,
        ax=None,
        **style_kwds,
    ):
        """
    Draws the nested density pie chart of the input vColumns.

    Parameters
    ----------
    columns: list
        List of the vColumns names.
    max_cardinality: int / tuple / list, optional
        Maximum number of the vColumn distinct elements to be used as categorical 
        (No h will be picked or computed).
        If of type tuple, it must represent each column 'max_cardinality'.
    h: float/tuple, optional
        Interval width of the bar. If empty, an optimized h will be computed.
        If of type tuple, it must represent each column 'h'.
    ax: Matplotlib axes object, optional
        The axes to plot on.
    **style_kwds
        Any optional parameter to pass to the Matplotlib functions.

    Returns
    -------
    ax
        Matplotlib axes object

    See Also
    --------
    vDataFrame[].pie : Draws the Pie Chart of the vColumn based on an aggregation.
        """
        if isinstance(columns, str):
            columns = [columns]
        columns = self.format_colnames(columns)
        return plt.nested_pie(self, columns, max_cardinality, h, ax=None, **style_kwds)

    @save_verticapy_logs
    def pivot(
        self,
        index: str,
        columns: str,
        values: str,
        aggr: str = "sum",
        prefix: str = "",
    ):
        """
    Returns the Pivot of the vDataFrame using the input aggregation.

    Parameters
    ----------
    index: str
        vColumn to use to group the elements.
    columns: str
        The vColumn used to compute the different categories, which then act 
        as the columns in the pivot table.
    values: str
        The vColumn whose values populate the new vDataFrame.
    aggr: str, optional
        Aggregation to use on 'values'. To use complex aggregations, 
        you must use braces: {}. For example, to aggregate using the 
        aggregation: x -> MAX(x) - MIN(x), write "MAX({}) - MIN({})".
    prefix: str, optional
        The prefix for the pivot table's column names.

    Returns
    -------
    vDataFrame
        the pivot table object.

    See Also
    --------
    vDataFrame.narrow      : Returns the Narrow table of the vDataFrame.
    vDataFrame.pivot_table : Draws the pivot table of one or two columns based on an 
        aggregation.
        """
        index, columns, values = self.format_colnames(index, columns, values)
        aggr = aggr.upper()
        if "{}" not in aggr:
            aggr += "({})"
        new_cols = self[columns].distinct()
        new_cols_trans = []
        for elem in new_cols:
            if elem == None:
                new_cols_trans += [
                    aggr.replace(
                        "{}",
                        f"(CASE WHEN {columns} IS NULL THEN {values} ELSE NULL END)",
                    )
                    + f"AS '{prefix}NULL'"
                ]
            else:
                new_cols_trans += [
                    aggr.replace(
                        "{}",
                        f"(CASE WHEN {columns} = '{elem}' THEN {values} ELSE NULL END)",
                    )
                    + f"AS '{prefix}{elem}'"
                ]
        return self.__vDataFrameSQL__(
            f"""
            (SELECT 
                {index},
                {", ".join(new_cols_trans)}
             FROM {self.__genSQL__()}
             GROUP BY 1) VERTICAPY_SUBTABLE""",
            "pivot",
            (
                f"[Pivot]: Pivot table using index = {index} & "
                f"columns = {columns} & values = {values}"
            ),
        )

    @save_verticapy_logs
    def pivot_table_chi2(
        self,
        response: str,
        columns: Union[str, list] = [],
        nbins: int = 16,
        method: Literal["smart", "same_width"] = "same_width",
        RFmodel_params: dict = {},
    ):
        """
    Returns the chi-square term using the pivot table of the response vColumn 
    against the input vColumns.

    Parameters
    ----------
    response: str
        Categorical response vColumn.
    columns: str / list, optional
        List of the vColumn names. The maximum number of categories for each
        categorical columns is 16. Categorical columns with a higher cardinality
        are discarded.
    nbins: int, optional
        Integer in the range [2,16], the number of bins used to discretize 
        the numerical features.
    method: str, optional
        The method to use to discretize the numerical vColumns.
            same_width : Computes bins of regular width.
            smart      : Uses a random forest model on a response column to find the best
                interval for discretization.
    RFmodel_params: dict, optional
        Dictionary of the parameters of the random forest model used to compute the best splits 
        when 'method' is 'smart'. If the response column is numerical (but not of type int or bool), 
        this function trains and uses a random forest regressor.  Otherwise, this function 
        trains a random forest classifier.
        For example, to train a random forest with 20 trees and a maximum depth of 10, use:
            {"n_estimators": 20, "max_depth": 10}

    Returns
    -------
    tablesample
        An object containing the result. For more information, see
        utilities.tablesample.
        """
        if isinstance(columns, str):
            columns = [columns]
        columns, response = self.format_colnames(columns, response)
        assert 2 <= nbins <= 16, ParameterError(
            "Parameter 'nbins' must be between 2 and 16, inclusive."
        )
        columns = self.chaid_columns(columns)
        for col in columns:
            if quote_ident(response) == quote_ident(col):
                columns.remove(col)
                break
        if not (columns):
            raise ValueError("No column to process.")
        if self.shape()[0] == 0:
            return {
                "index": columns,
                "chi2": [0.0 for col in columns],
                "categories": [[] for col in columns],
                "is_numerical": [self[col].isnum() for col in columns],
            }
        vdf = self.copy()
        for col in columns:
            if vdf[col].isnum():
                vdf[col].discretize(
                    method=method,
                    nbins=nbins,
                    response=response,
                    RFmodel_params=RFmodel_params,
                )
        response = vdf.format_colnames(response)
        if response in columns:
            columns.remove(response)
        chi2_list = []
        for col in columns:
            tmp_res = vdf.pivot_table(
                columns=[col, response], max_cardinality=(10000, 100), show=False
            ).to_numpy()[:, 1:]
            tmp_res = np.where(tmp_res == "", "0", tmp_res)
            tmp_res = tmp_res.astype(float)
            i = 0
            all_chi2 = []
            for row in tmp_res:
                j = 0
                for col_in_row in row:
                    all_chi2 += [
                        col_in_row ** 2 / (sum(tmp_res[i]) * sum(tmp_res[:, j]))
                    ]
                    j += 1
                i += 1
            val = sum(sum(tmp_res)) * (sum(all_chi2) - 1)
            k, r = tmp_res.shape
            dof = (k - 1) * (r - 1)
            pval = scipy_st.chi2.sf(val, dof)
            chi2_list += [(col, val, pval, dof, vdf[col].distinct(), self[col].isnum())]
        chi2_list = sorted(chi2_list, key=lambda tup: tup[1], reverse=True)
        result = {
            "index": [chi2[0] for chi2 in chi2_list],
            "chi2": [chi2[1] for chi2 in chi2_list],
            "p_value": [chi2[2] for chi2 in chi2_list],
            "dof": [chi2[3] for chi2 in chi2_list],
            "categories": [chi2[4] for chi2 in chi2_list],
            "is_numerical": [chi2[5] for chi2 in chi2_list],
        }
        return util.tablesample(result)

    @save_verticapy_logs
    def pivot_table(
        self,
        columns: Union[str, list],
        method: str = "count",
        of: str = "",
        max_cardinality: tuple = (20, 20),
        h: tuple = (None, None),
        show: bool = True,
        with_numbers: bool = True,
        fill_none: float = 0.0,
        ax=None,
        **style_kwds,
    ):
        """
    Draws the pivot table of one or two columns based on an aggregation.

    Parameters
    ----------
    columns: str / list
        List of the vColumns names. The list must have one or two elements.
    method: str, optional
        The method to use to aggregate the data.
            count   : Number of elements.
            density : Percentage of the distribution.
            mean    : Average of the vColumn 'of'.
            min     : Minimum of the vColumn 'of'.
            max     : Maximum of the vColumn 'of'.
            sum     : Sum of the vColumn 'of'.
            q%      : q Quantile of the vColumn 'of (ex: 50% to get the median).
        It can also be a cutomized aggregation (ex: AVG(column1) + 5).
    of: str, optional
        The vColumn to use to compute the aggregation.
    max_cardinality: tuple, optional
        Maximum number of distinct elements for vColumns 1 and 2 to be used as 
        categorical (No h will be picked or computed)
    h: tuple, optional
        Interval width of the vColumns 1 and 2 bars. It is only valid if the 
        vColumns are numerical. Optimized h will be computed if the parameter 
        is empty or invalid.
    show: bool, optional
        If set to True, the result will be drawn using Matplotlib.
    with_numbers: bool, optional
        If set to True, no number will be displayed in the final drawing.
    fill_none: float, optional
        The empty values of the pivot table will be filled by this number.
    ax: Matplotlib axes object, optional
        The axes to plot on.
    **style_kwds
        Any optional parameter to pass to the Matplotlib functions.

    Returns
    -------
    tablesample
        An object containing the result. For more information, see
        utilities.tablesample.

    See Also
    --------
    vDataFrame.hexbin : Draws the Hexbin Plot of 2 vColumns based on an aggregation.
    vDataFrame.pivot  : Returns the Pivot of the vDataFrame using the input aggregation.
        """
        if isinstance(columns, str):
            columns = [columns]
        columns, of = self.format_colnames(columns, of, expected_nb_of_cols=[1, 2])
        return plt.pivot_table(
            self,
            columns,
            method,
            of,
            h,
            max_cardinality,
            show,
            with_numbers,
            fill_none,
            ax=ax,
            **style_kwds,
        )

    @save_verticapy_logs
    def plot(
        self,
        ts: str,
        columns: list = [],
        start_date: Union[str, int, float, datetime.datetime, datetime.date] = "",
        end_date: Union[str, int, float, datetime.datetime, datetime.date] = "",
        step: bool = False,
        ax=None,
        **style_kwds,
    ):
        """
    Draws the time series.

    Parameters
    ----------
    ts: str
        TS (Time Series) vColumn to use to order the data. The vColumn type must be
        date like (date, datetime, timestamp...) or numerical.
    columns: list, optional
        List of the vColumns names. If empty, all numerical vColumns will be 
        used.
    start_date: str / int / float / date, optional
        Input Start Date. For example, time = '03-11-1993' will filter the data when 
        'ts' is lesser than November 1993 the 3rd.
    end_date: str / int / float / date, optional
        Input End Date. For example, time = '03-11-1993' will filter the data when 
        'ts' is greater than November 1993 the 3rd.
    step: bool, optional
        If set to True, draw a Step Plot.
    ax: Matplotlib axes object, optional
        The axes to plot on.
    **style_kwds
        Any optional parameter to pass to the Matplotlib functions.

    Returns
    -------
    ax
        Matplotlib axes object

    See Also
    --------
    vDataFrame[].plot : Draws the Time Series of one vColumn.
        """
        if isinstance(columns, str):
            columns = [columns]
        columns, ts = self.format_colnames(columns, ts)
        kind = "step" if step else "line"
        return plt.multi_ts_plot(
            self, ts, columns, start_date, end_date, kind, ax=ax, **style_kwds,
        )

    @save_verticapy_logs
    def polynomial_comb(self, columns: Union[str, list] = [], r: int = 2):
        """
    Returns a vDataFrame containing different product combination of the 
    input vColumns. This function is ideal for bivariate analysis.

    Parameters
    ----------
    columns: str / list, optional
        List of the vColumns names. If empty, all numerical vColumns will be 
        used.
    r: int, optional
        Degree of the polynomial.

    Returns
    -------
    vDataFrame
        the Polynomial object.
        """
        if isinstance(columns, str):
            columns = [columns]
        if not (columns):
            numcol = self.numcol()
        else:
            numcol = self.format_colnames(columns)
        vdf = self.copy()
        all_comb = combinations_with_replacement(numcol, r=r)
        for elem in all_comb:
            name = "_".join(elem)
            vdf.eval(name.replace('"', ""), expr=" * ".join(elem))
        return vdf

    @save_verticapy_logs
    def product(
        self, columns: list = [], **agg_kwds,
    ):
        """
    Aggregates the vDataFrame using 'product'.

    Parameters
    ----------
    columns: list, optional
        List of the vColumn names. If empty, all numerical vColumns will be used.
    **agg_kwds
        Any optional parameter to pass to the Aggregate function.

    Returns
    -------
    tablesample
        An object containing the result. For more information, see
        utilities.tablesample.

    See Also
    --------
    vDataFrame.aggregate : Computes the vDataFrame input aggregations.
        """
        return self.aggregate(func=["prod"], columns=columns, **agg_kwds,)

    prod = product

    @save_verticapy_logs
    def quantile(
        self,
        q: Union[int, float, list],
        columns: list = [],
        approx: bool = True,
        **agg_kwds,
    ):
        """
    Aggregates the vDataFrame using a list of 'quantiles'.

    Parameters
    ----------
    q: int / float / list
        List of the different quantiles. They must be numbers between 0 and 1.
        For example [0.25, 0.75] will return Q1 and Q3.
    columns: list, optional
        List of the vColumns names. If empty, all numerical vColumns will be 
        used.
    approx: bool, optional
        If set to True, the approximate quantile is returned. By setting this 
        parameter to False, the function's performance can drastically decrease.
    **agg_kwds
        Any optional parameter to pass to the Aggregate function.

    Returns
    -------
    tablesample
        An object containing the result. For more information, see
        utilities.tablesample.

    See Also
    --------
    vDataFrame.aggregate : Computes the vDataFrame input aggregations.
        """
        if isinstance(q, (int, float)):
            q = [q]
        prefix = "approx_" if approx else ""
        return self.aggregate(
            func=[
                get_verticapy_function(prefix + f"{float(item) * 100}%") for item in q
            ],
            columns=columns,
            **agg_kwds,
        )

    @save_verticapy_logs
    def recommend(
        self,
        unique_id: str,
        item_id: str,
        method: Literal["count", "avg", "median"] = "count",
        rating: Union[str, tuple] = "",
        ts: str = "",
        start_date: Union[str, int, float, datetime.datetime, datetime.date] = "",
        end_date: Union[str, int, float, datetime.datetime, datetime.date] = "",
    ):
        """
    Recommend items based on the Collaborative Filtering (CF) technique.
    The implementation is the same as APRIORI algorithm, but is limited to pairs 
    of items.

    Parameters
    ----------
    unique_id: str
        Input vColumn corresponding to a unique ID. It is a primary key.
    item_id: str
        Input vColumn corresponding to an item ID. It is a secondary key used to 
        compute the different pairs.
    method: str, optional
        Method used to recommend.
            count  : Each item will be recommended based on frequencies of the
                     different pairs of items.
            avg    : Each item will be recommended based on the average rating
                     of the different item pairs with a differing second element.
            median : Each item will be recommended based on the median rating
                     of the different item pairs with a differing second element.
    rating: str / tuple, optional
        Input vColumn including the items rating.
        If the 'rating' type is 'tuple', it must composed of 3 elements: 
        (r_vdf, r_item_id, r_name) where:
            r_vdf is an input vDataFrame.
            r_item_id is an input vColumn which must includes the same id as 'item_id'.
            r_name is an input vColumn including the items rating. 
    ts: str, optional
        TS (Time Series) vColumn to use to order the data. The vColumn type must be
        date like (date, datetime, timestamp...) or numerical.
    start_date: str / int / float / date, optional
        Input Start Date. For example, time = '03-11-1993' will filter the data when 
        'ts' is lesser than November 1993 the 3rd.
    end_date: str / int / float / date, optional
        Input End Date. For example, time = '03-11-1993' will filter the data when 
        'ts' is greater than November 1993 the 3rd.

    Returns
    -------
    vDataFrame
        The vDataFrame of the recommendation.
        """
        unique_id, item_id, ts = self.format_colnames(unique_id, item_id, ts)
        vdf = self.copy()
        assert (
            method == "count" or rating
        ), f"Method '{method}' can not be used if parameter 'rating' is empty."
        if rating:
            assert isinstance(rating, str) or len(rating) == 3, ParameterError(
                "Parameter 'rating' must be of type str or composed of "
                "exactly 3 elements: (r_vdf, r_item_id, r_name)."
            )
            assert (
                method != "count"
            ), "Method 'count' can not be used if parameter 'rating' is defined."
            rating = self.format_colnames(rating)
        if ts:
            if start_date and end_date:
                vdf = self.search(f"{ts} BETWEEN '{start_date}' AND '{end_date}'")
            elif start_date:
                vdf = self.search(f"{ts} >= '{start_date}'")
            elif end_date:
                vdf = self.search(f"{ts} <= '{end_date}'")
        vdf = (
            vdf.join(
                vdf,
                how="left",
                on={unique_id: unique_id},
                expr1=[f"{item_id} AS item1"],
                expr2=[f"{item_id} AS item2"],
            )
            .groupby(["item1", "item2"], ["COUNT(*) AS cnt"])
            .search("item1 != item2 AND cnt > 1")
        )
        order_columns = "cnt DESC"
        if method in ("avg", "median"):
            fun = "AVG" if method == "avg" else "APPROXIMATE_MEDIAN"
            if isinstance(rating, str):
                r_vdf = self.groupby([item_id], [f"{fun}({rating}) AS score"])
                r_item_id = item_id
                r_name = "score"
            else:
                r_vdf, r_item_id, r_name = rating
                r_vdf = r_vdf.groupby([r_item_id], [f"{fun}({r_name}) AS {r_name}"])
            vdf = vdf.join(
                r_vdf,
                how="left",
                on={"item1": r_item_id},
                expr2=[f"{r_name} AS score1"],
            ).join(
                r_vdf,
                how="left",
                on={"item2": r_item_id},
                expr2=[f"{r_name} AS score2"],
            )
            order_columns = "score2 DESC, score1 DESC, cnt DESC"
        vdf["rank"] = f"ROW_NUMBER() OVER (PARTITION BY item1 ORDER BY {order_columns})"
        return vdf

    @save_verticapy_logs
    def regexp(
        self,
        column: str,
        pattern: str,
        method: Literal[
            "count",
            "ilike",
            "instr",
            "like",
            "not_ilike",
            "not_like",
            "replace",
            "substr",
        ] = "substr",
        position: int = 1,
        occurrence: int = 1,
        replacement: str = "",
        return_position: int = 0,
        name: str = "",
    ):
        """
    Computes a new vColumn based on regular expressions. 

    Parameters
    ----------
    column: str
        Input vColumn to use to compute the regular expression.
    pattern: str
        The regular expression.
    method: str, optional
        Method to use to compute the regular expressions.
            count     : Returns the number times a regular expression matches 
                each element of the input vColumn. 
            ilike     : Returns True if the vColumn element contains a match 
                for the regular expression.
            instr     : Returns the starting or ending position in a vColumn 
                element where a regular expression matches. 
            like      : Returns True if the vColumn element matches the regular 
                expression.
            not_ilike : Returns True if the vColumn element does not match the 
                case-insensitive regular expression.
            not_like  : Returns True if the vColumn element does not contain a 
                match for the regular expression.
            replace   : Replaces all occurrences of a substring that match a 
                regular expression with another substring.
            substr    : Returns the substring that matches a regular expression 
                within a vColumn.
    position: int, optional
        The number of characters from the start of the string where the function 
        should start searching for matches.
    occurrence: int, optional
        Controls which occurrence of a pattern match in the string to return.
    replacement: str, optional
        The string to replace matched substrings.
    return_position: int, optional
        Sets the position within the string to return.
    name: str, optional
        New feature name. If empty, a name will be generated.

    Returns
    -------
    vDataFrame
        self

    See Also
    --------
    vDataFrame.eval : Evaluates a customized expression.
        """
        column = self.format_colnames(column)
        pattern_str = pattern.replace("'", "''")
        expr = f"REGEXP_{method.upper()}({column}, '{pattern_str}'"
        if method == "replace":
            replacement_str = replacement.replace("'", "''")
            expr += f", '{replacement_str}'"
        if method in ("count", "instr", "replace", "substr"):
            expr += f", {position}"
        if method in ("instr", "replace", "substr"):
            expr += f", {occurrence}"
        if method == "instr":
            expr += f", {return_position}"
        expr += ")"
        gen_name([method, column])
        return self.eval(name=name, expr=expr)

    @save_verticapy_logs
    def regr(
        self,
        columns: Union[str, list] = [],
        method: Literal[
            "avgx",
            "avgy",
            "count",
            "intercept",
            "r2",
            "slope",
            "sxx",
            "sxy",
            "syy",
            "beta",
            "alpha",
        ] = "r2",
        show: bool = True,
        ax=None,
        **style_kwds,
    ):
        """
    Computes the regression matrix of the vDataFrame.

    Parameters
    ----------
    columns: list, optional
        List of the vColumns names. If empty, all numerical vColumns will be 
        used.
    method: str, optional
        Method to use to compute the regression matrix.
            avgx  : Average of the independent expression in an expression pair.
            avgy  : Average of the dependent expression in an expression pair.
            count : Count of all rows in an expression pair.
            alpha : Intercept of the regression line determined by a set of 
                expression pairs.
            r2    : Square of the correlation coefficient of a set of expression 
                pairs.
            beta  : Slope of the regression line, determined by a set of expression 
                pairs.
            sxx   : Sum of squares of the independent expression in an expression 
                pair.
            sxy   : Sum of products of the independent expression multiplied by the 
                dependent expression in an expression pair.
            syy   : Returns the sum of squares of the dependent expression in an 
                expression pair.
    show: bool, optional
        If set to True, the Regression Matrix will be drawn using Matplotlib.
    ax: Matplotlib axes object, optional
        The axes to plot on.
    **style_kwds
        Any optional parameter to pass to the Matplotlib functions.

    Returns
    -------
    tablesample
        An object containing the result. For more information, see
        utilities.tablesample.

    See Also
    --------
    vDataFrame.acf   : Computes the correlations between a vColumn and its lags.
    vDataFrame.cov   : Computes the covariance matrix of the vDataFrame.
    vDataFrame.corr  : Computes the Correlation Matrix of the vDataFrame.
    vDataFrame.pacf  : Computes the partial autocorrelations of the input vColumn.
        """
        if isinstance(columns, str):
            columns = [columns]
        if method == "beta":
            method = "slope"
        elif method == "alpha":
            method = "intercept"
        method = f"regr_{method}"
        if not (columns):
            columns = self.numcol()
            assert columns, EmptyParameter(
                "No numerical column found in the vDataFrame."
            )
        columns = self.format_colnames(columns)
        for column in columns:
            assert self[column].isnum(), TypeError(
                f"vColumn {column} must be numerical to compute the Regression Matrix."
            )
        n = len(columns)
        all_list, nb_precomputed = [], 0
        for i in range(0, n):
            for j in range(0, n):
                cast_i = "::int" if (self[columns[i]].isbool()) else ""
                cast_j = "::int" if (self[columns[j]].isbool()) else ""
                pre_comp_val = self.__get_catalog_value__(
                    method=method, columns=[columns[i], columns[j]]
                )
                if pre_comp_val == None or pre_comp_val != pre_comp_val:
                    pre_comp_val = "NULL"
                if pre_comp_val != "VERTICAPY_NOT_PRECOMPUTED":
                    all_list += [str(pre_comp_val)]
                    nb_precomputed += 1
                else:
                    all_list += [
                        f"{method.upper()}({columns[i]}{cast_i}, {columns[j]}{cast_j})"
                    ]
        try:
            if nb_precomputed == n * n:
                result = executeSQL(
                    query=f"""
                        SELECT 
                            /*+LABEL('vDataframe.regr')*/ 
                            {", ".join(all_list)}""",
                    print_time_sql=False,
                    method="fetchrow",
                )
            else:
                result = executeSQL(
                    query=f"""
                        SELECT 
                            /*+LABEL('vDataframe.regr')*/
                            {", ".join(all_list)} 
                        FROM {self.__genSQL__()}""",
                    title=f"Computing the {method.upper()} Matrix.",
                    method="fetchrow",
                    sql_push_ext=self._VERTICAPY_VARIABLES_["sql_push_ext"],
                    symbol=self._VERTICAPY_VARIABLES_["symbol"],
                )
            if n == 1:
                return result[0]
        except:
            n = len(columns)
            result = []
            for i in range(0, n):
                for j in range(0, n):
                    result += [
                        executeSQL(
                            query=f"""
                                SELECT 
                                    /*+LABEL('vDataframe.regr')*/ 
                                    {method.upper()}({columns[i]}{cast_i}, 
                                                     {columns[j]}{cast_j}) 
                                FROM {self.__genSQL__()}""",
                            title=f"Computing the {method.upper()} aggregation, one at a time.",
                            method="fetchfirstelem",
                            sql_push_ext=self._VERTICAPY_VARIABLES_["sql_push_ext"],
                            symbol=self._VERTICAPY_VARIABLES_["symbol"],
                        )
                    ]
        matrix = [[1 for i in range(0, n + 1)] for i in range(0, n + 1)]
        matrix[0] = [""] + columns
        for i in range(0, n + 1):
            matrix[i][0] = columns[i - 1]
        k = 0
        for i in range(0, n):
            for j in range(0, n):
                current = result[k]
                k += 1
                if current == None:
                    current = float("nan")
                matrix[i + 1][j + 1] = current
        if show:
            if method == "slope":
                method_title = "Beta"
            elif method == "intercept":
                method_title = "Alpha"
            else:
                method_title = method
            plt.cmatrix(
                matrix,
                columns,
                columns,
                n,
                n,
                vmax=None,
                vmin=None,
                title=f"{method_title} Matrix",
                ax=ax,
                **style_kwds,
            )
        values = {"index": matrix[0][1 : len(matrix[0])]}
        del matrix[0]
        for column in matrix:
            values[column[0]] = column[1 : len(column)]
        for column1 in values:
            if column1 != "index":
                val = {}
                for idx, column2 in enumerate(values["index"]):
                    val[column2] = values[column1][idx]
                self.__update_catalog__(values=val, matrix=method, column=column1)
        return util.tablesample(values=values).decimal_to_float()

    @save_verticapy_logs
    def rolling(
        self,
        func: str,
        window: Union[list, tuple],
        columns: Union[str, list],
        by: Union[str, list] = [],
        order_by: Union[dict, list] = [],
        name: str = "",
    ):
        """
    Adds a new vColumn to the vDataFrame by using an advanced analytical window 
    function on one or two specific vColumns.

    \u26A0 Warning : Some window functions can make the vDataFrame structure 
                     heavier. It is recommended to always check the current structure 
                     using the 'current_relation' method and to save it using the 
                     'to_db' method with the parameters 'inplace = True' and 
                     'relation_type = table'

    Parameters
    ----------
    func: str
        Function to use.
            aad         : average absolute deviation
            beta        : Beta Coefficient between 2 vColumns
            count       : number of non-missing elements
            corr        : Pearson correlation between 2 vColumns
            cov         : covariance between 2 vColumns
            kurtosis    : kurtosis
            jb          : Jarque-Bera index
            max         : maximum
            mean        : average
            min         : minimum
            prod        : product
            range       : difference between the max and the min
            sem         : standard error of the mean
            skewness    : skewness
            sum         : sum
            std         : standard deviation
            var         : variance
                Other window functions could work if it is part of 
                the DB version you are using.
    window: list / tuple
        Window Frame Range.
        If two integers, it will compute a Row Window, otherwise it will compute
        a Time Window. For example, if set to (-5, 1), the moving windows will
        take 5 rows preceding and one following. If set to ('- 5 minutes', '0 minutes'),
        the moving window will take all elements of the last 5 minutes.
    columns: str / list
        Input vColumns. It can be a list of one or two elements.
    by: str / list, optional
        vColumns used in the partition.
    order_by: dict / list, optional
        List of the vColumns to use to sort the data using asc order or
        dictionary of all sorting methods. For example, to sort by "column1"
        ASC and "column2" DESC, write {"column1": "asc", "column2": "desc"}
    name: str, optional
        Name of the new vColumn. If empty, a default name will be generated.

    Returns
    -------
    vDataFrame
        self

    See Also
    --------
    vDataFrame.eval     : Evaluates a customized expression.
    vDataFrame.analytic : Adds a new vColumn to the vDataFrame by using an advanced 
        analytical function on a specific vColumn.
        """
        if isinstance(columns, str):
            columns = [columns]
        if isinstance(by, str):
            by = [by]
        if isinstance(order_by, str):
            order_by = [order_by]
        assert len(window) == 2, ParameterError(
            "The window must be composed of exactly 2 elements."
        )
        window = list(window)
        rule = [0, 0]
        unbounded, method = False, "rows"
        for idx, w in enumerate(window):
            if isinstance(w, (int, float)) and abs(w) == float("inf"):
                w = "unbounded"
            if isinstance(w, (str)):
                if w.lower() == "unbounded":
                    rule[idx] = "PRECEDING" if idx == 0 else "FOLLOWING"
                    window[idx] = "UNBOUNDED"
                else:
                    nb_min = 0
                    for i, char in enumerate(window[idx]):
                        if char == "-":
                            nb_min += 1
                        elif char != " ":
                            break
                    rule[idx] = "PRECEDING" if nb_min % 2 == 1 else "FOLLOWING"
                    window[idx] = "'" + window[idx][i:] + "'"
                    method = "range"
            elif isinstance(w, (datetime.timedelta)):
                rule[idx] = (
                    "PRECEDING" if window[idx] < datetime.timedelta(0) else "FOLLOWING"
                )
                window[idx] = "'" + str(abs(window[idx])) + "'"
                method = "range"
            else:
                rule[idx] = "PRECEDING" if int(window[idx]) < 0 else "FOLLOWING"
                window[idx] = abs(int(window[idx]))
        if isinstance(columns, str):
            columns = [columns]
        if not (name):
            name = gen_name([func] + columns + [window[0], rule[0], window[1], rule[1]])
            name = f"moving_{name}"
        columns, by = self.format_colnames(columns, by)
        by = "" if not (by) else "PARTITION BY " + ", ".join(by)
        if not (order_by):
            order_by = f" ORDER BY {columns[0]}"
        else:
            order_by = self.__get_sort_syntax__(order_by)
        func = get_verticapy_function(func.lower(), method="vertica")
        windows_frame = f""" 
            OVER ({by}{order_by} 
            {method.upper()} 
            BETWEEN {window[0]} {rule[0]} 
            AND {window[1]} {rule[1]})"""
        all_cols = [
            elem.replace('"', "").lower()
            for elem in self._VERTICAPY_VARIABLES_["columns"]
        ]
        if func in ("kurtosis", "skewness", "aad", "prod", "jb"):
            if func in ("skewness", "kurtosis", "aad", "jb"):
                columns_0_str = columns[0].replace('"', "").lower()
                random_int = random.randint(0, 10000000)
                mean_name = f"{columns_0_str}_mean_{random_int}"
                std_name = f"{columns_0_str}_std_{random_int}"
                count_name = f"{columns_0_str}_count_{random_int}"
                self.eval(mean_name, f"AVG({columns[0]}){windows_frame}")
                if func != "aad":
                    self.eval(std_name, f"STDDEV({columns[0]}){windows_frame}")
                    self.eval(count_name, f"COUNT({columns[0]}){windows_frame}")
                if func == "kurtosis":
                    expr = f"""
                        AVG(POWER(({columns[0]} - {mean_name}) 
                      / NULLIFZERO({std_name}), 4))# 
                      * POWER({count_name}, 2) 
                      * ({count_name} + 1) 
                      / NULLIFZERO(
                         ({count_name} - 1) 
                        * ({count_name} - 2) 
                        * ({count_name} - 3)) 
                      - 3 * POWER({count_name} - 1, 2) 
                      / NULLIFZERO(
                         ({count_name} - 2) 
                        * ({count_name} - 3))"""
                elif func == "skewness":
                    expr = f"""
                        AVG(POWER(({columns[0]} - {mean_name}) 
                      / NULLIFZERO({std_name}), 3))# 
                      * POWER({count_name}, 2) 
                      / NULLIFZERO(({count_name} - 1) 
                        * ({count_name} - 2))"""
                elif func == "jb":
                    expr = f"""
                        {count_name} / 6 * (POWER(AVG(POWER((
                            {columns[0]} - {mean_name}) 
                          / NULLIFZERO({std_name}), 3))# 
                          * POWER({count_name}, 2) 
                          / NULLIFZERO(({count_name} - 1) 
                          * ({count_name} - 2)), 2) 
                          + POWER(AVG(POWER(({columns[0]} 
                          - {mean_name}) / NULLIFZERO({std_name}), 4))# 
                          * POWER({count_name}, 2) * ({count_name} + 1) 
                          / NULLIFZERO(({count_name} - 1) 
                          * ({count_name} - 2) * ({count_name} - 3)) 
                          - 3 * POWER({count_name} - 1, 2) 
                          / NULLIFZERO(({count_name} - 2) 
                          * ({count_name} - 3)), 2) / 4)"""
                elif func == "aad":
                    expr = f"AVG(ABS({columns[0]} - {mean_name}))#"
            else:
                expr = f"""
                    DECODE(ABS(MOD(SUM(CASE WHEN {columns[0]} < 0 
                           THEN 1 ELSE 0 END)#, 2)), 0, 1, -1) 
                  * POWER(10, SUM(LOG(ABS({columns[0]})))#)"""
        elif func in ("corr", "cov", "beta"):
            if columns[1] == columns[0]:
                if func == "cov":
                    expr = f"VARIANCE({columns[0]})#"
                else:
                    expr = "1"
            else:
                if func == "corr":
                    den = f" / (STDDEV({columns[0]})# * STDDEV({columns[1]})#)"
                elif func == "beta":
                    den = f" / (VARIANCE({columns[1]})#)"
                else:
                    den = ""
                expr = f"""
                    (AVG({columns[0]} * {columns[1]})# 
                  - AVG({columns[0]})# * AVG({columns[1]})#) 
                    {den}"""
        elif func == "range":
            expr = f"MAX({columns[0]})# - MIN({columns[0]})#"
        elif func == "sem":
            expr = f"STDDEV({columns[0]})# / SQRT(COUNT({columns[0]})#)"
        else:
            expr = f"{func.upper()}({columns[0]})#"
        expr = expr.replace("#", windows_frame)
        self.eval(name=name, expr=expr)
        if func in ("kurtosis", "skewness", "jb"):
            self._VERTICAPY_VARIABLES_["exclude_columns"] += [
                quote_ident(mean_name),
                quote_ident(std_name),
                quote_ident(count_name),
            ]
        elif func == "aad":
            self._VERTICAPY_VARIABLES_["exclude_columns"] += [quote_ident(mean_name)]
        return self

    @save_verticapy_logs
    def sample(
        self,
        n: Union[int, float] = None,
        x: float = None,
        method: Literal["random", "systematic", "stratified"] = "random",
        by: Union[str, list] = [],
    ):
        """
    Downsamples the input vDataFrame.

    \u26A0 Warning : The result may be inconsistent between attempts at SQL
                     code generation if the data is not ordered.

    Parameters
     ----------
     n: int / float, optional
        Approximate number of element to consider in the sample.
     x: float, optional
        The sample size. For example it has to be equal to 0.33 to downsample to 
        approximatively 33% of the relation.
    method: str, optional
        The Sample method.
            random     : random sampling.
            systematic : systematic sampling.
            stratified : stratified sampling.
    by: str / list, optional
        vColumns used in the partition.

    Returns
    -------
    vDataFrame
        sample vDataFrame
        """
        if x == 1:
            return self.copy()
        assert n != None or x != None, ParameterError(
            "One of the parameter 'n' or 'x' must not be empty."
        )
        assert n == None or x == None, ParameterError(
            "One of the parameter 'n' or 'x' must be empty."
        )
        if n != None:
            x = float(n / self.shape()[0])
            if x >= 1:
                return self.copy()
        if isinstance(method, str):
            method = method.lower()
        if method in ("systematic", "random"):
            order_by = ""
            assert not (by), ParameterError(
                f"Parameter 'by' must be empty when using '{method}' sampling."
            )
        if isinstance(by, str):
            by = [by]
        by = self.format_colnames(by)
        random_int = random.randint(0, 10000000)
        name = f"__verticapy_random_{random_int}__"
        name2 = f"__verticapy_random_{random_int + 1}__"
        vdf = self.copy()
        assert 0 < x < 1, ParameterError("Parameter 'x' must be between 0 and 1")
        if method == "random":
            random_state = vp.OPTIONS["random_state"]
            random_seed = random.randint(-10e6, 10e6)
            if isinstance(random_state, int):
                random_seed = random_state
            random_func = f"SEEDED_RANDOM({random_seed})"
            vdf.eval(name, random_func)
            q = vdf[name].quantile(x)
            print_info_init = vp.OPTIONS["print_info"]
            vp.OPTIONS["print_info"] = False
            vdf.filter(f"{name} <= {q}")
            vp.OPTIONS["print_info"] = print_info_init
            vdf._VERTICAPY_VARIABLES_["exclude_columns"] += [name]
        elif method in ("stratified", "systematic"):
            assert method != "stratified" or (by), ParameterError(
                "Parameter 'by' must include at least one "
                "column when using 'stratified' sampling."
            )
            if method == "stratified":
                order_by = "ORDER BY " + ", ".join(by)
            vdf.eval(name, f"ROW_NUMBER() OVER({order_by})")
            vdf.eval(
                name2,
                f"""MIN({name}) OVER (PARTITION BY CAST({name} * {x} AS Integer) 
                    ORDER BY {name} ROWS BETWEEN UNBOUNDED PRECEDING AND 0 FOLLOWING)""",
            )
            print_info_init = vp.OPTIONS["print_info"]
            vp.OPTIONS["print_info"] = False
            vdf.filter(f"{name} = {name2}")
            vp.OPTIONS["print_info"] = print_info_init
            vdf._VERTICAPY_VARIABLES_["exclude_columns"] += [name, name2]
        return vdf

    @save_verticapy_logs
    def save(self):
        """
    Saves the current structure of the vDataFrame. 
    This function is useful for loading previous transformations.

    Returns
    -------
    vDataFrame
        self

    See Also
    --------
    vDataFrame.load : Loads a saving.
        """
        vdf = self.copy()
        self._VERTICAPY_VARIABLES_["saving"] += [pickle.dumps(vdf)]
        return self

    @save_verticapy_logs
    def scatter(
        self,
        columns: Union[str, list],
        catcol: str = "",
        max_cardinality: int = 6,
        cat_priority: list = [],
        with_others: bool = True,
        max_nb_points: int = 20000,
        dimensions: tuple = None,
        bbox: list = [],
        img: str = "",
        ax=None,
        **style_kwds,
    ):
        """
    Draws the scatter plot of the input vColumns.

    Parameters
    ----------
    columns: str, list
        List of the vColumns names. 
    catcol: str, optional
        Categorical vColumn to use to label the data.
    max_cardinality: int, optional
        Maximum number of distinct elements for 'catcol' to be used as 
        categorical. The less frequent elements will be gathered together to 
        create a new category: 'Others'.
    cat_priority: list, optional
        List of the different categories to consider when labeling the data using
        the vColumn 'catcol'. The other categories will be filtered.
    with_others: bool, optional
        If set to false and the cardinality of the vColumn 'catcol' is too big then
        the less frequent element will not be merged to another category and they 
        will not be drawn.
    max_nb_points: int, optional
        Maximum number of points to display.
    dimensions: tuple, optional
        Tuple of two elements representing the IDs of the PCA's components.
        If empty and the number of input columns is greater than 3, the
        first and second PCA will be drawn.
    bbox: list, optional
        List of 4 elements to delimit the boundaries of the final Plot. 
        It must be similar the following list: [xmin, xmax, ymin, ymax]
    img: str, optional
        Path to the image to display as background.
    ax: Matplotlib axes object, optional
        The axes to plot on.
    **style_kwds
        Any optional parameter to pass to the Matplotlib functions.

    Returns
    -------
    ax
        Matplotlib axes object

    See Also
    --------
    vDataFrame.bubble      : Draws the bubble plot of the input vColumns.
    vDataFrame.pivot_table : Draws the pivot table of vColumns based on an aggregation.
        """
        if len(columns) > 3 and dimensions == None:
            dimensions = (1, 2)
        if isinstance(dimensions, Iterable):
            model_name = gen_tmp_name(schema=vp.OPTIONS["temp_schema"], name="pca_plot")
            model = vp.learn.decomposition.PCA(model_name)
            model.drop()
            try:
                model.fit(self, columns)
                ax = model.transform(self).scatter(
                    columns=["col1", "col2"],
                    catcol=catcol,
                    max_cardinality=100,
                    max_nb_points=max_nb_points,
                    ax=ax,
                    **style_kwds,
                )
                explained_variance = model.explained_variance_["explained_variance"]
                for idx, fun in enumerate([ax.set_xlabel, ax.set_ylabel]):
                    if not (explained_variance[dimensions[idx] - 1]):
                        dimension2 = ""
                    else:
                        x2 = round(explained_variance[dimensions[idx] - 1] * 100, 1)
                        dimension2 = f"({x2}%)"
                    fun(f"Dim{dimensions[idx]} {dimension2}")
            finally:
                model.drop()
            return ax
        args = [
            self,
            columns,
            catcol,
            max_cardinality,
            cat_priority,
            with_others,
            max_nb_points,
            bbox,
            img,
        ]
        return plt.scatter(*args, ax=ax, **style_kwds,)

    @save_verticapy_logs
    def scatter_matrix(self, columns: Union[str, list] = [], **style_kwds):
        """
    Draws the scatter matrix of the vDataFrame.

    Parameters
    ----------
    columns: str / list, optional
        List of the vColumns names. If empty, all numerical vColumns will be 
        used.
    **style_kwds
        Any optional parameter to pass to the Matplotlib functions.

    Returns
    -------
    ax
        Matplotlib axes object

    See Also
    --------
    vDataFrame.scatter : Draws the scatter plot of the input vColumns.
        """
        if isinstance(columns, str):
            columns = [columns]
        columns = self.format_colnames(columns)
        return plt.scatter_matrix(self, columns, **style_kwds)

    @save_verticapy_logs
    def search(
        self,
        conditions: Union[str, list] = "",
        usecols: Union[str, list] = [],
        expr: Union[str, list] = [],
        order_by: Union[str, dict, list] = [],
    ):
        """
    Searches the elements which matches with the input conditions.
    
    Parameters
    ----------
    conditions: str / list, optional
        Filters of the search. It can be a list of conditions or an expression.
    usecols: str / list, optional
        vColumns to select from the final vDataFrame relation. If empty, all
        vColumns will be selected.
    expr: str / list, optional
        List of customized expressions in pure SQL.
        For example: 'column1 * column2 AS my_name'.
    order_by: str / dict / list, optional
        List of the vColumns to use to sort the data using asc order or
        dictionary of all sorting methods. For example, to sort by "column1"
        ASC and "column2" DESC, write {"column1": "asc", "column2": "desc"}

    Returns
    -------
    vDataFrame
        vDataFrame of the search

    See Also
    --------
    vDataFrame.filter : Filters the vDataFrame using the input expressions.
    vDataFrame.select : Returns a copy of the vDataFrame with only the selected vColumns.
        """
        if isinstance(order_by, str):
            order_by = [order_by]
        if isinstance(usecols, str):
            usecols = [usecols]
        if isinstance(expr, str):
            expr = [expr]
        if isinstance(conditions, Iterable) and not (isinstance(conditions, str)):
            conditions = " AND ".join([f"({elem})" for elem in conditions])
        if conditions:
            conditions = f" WHERE {conditions}"
        all_cols = ", ".join(["*"] + expr)
        table = f"""
            (SELECT 
                {all_cols} 
            FROM {self.__genSQL__()}{conditions}) VERTICAPY_SUBTABLE"""
        result = self.__vDataFrameSQL__(table, "search", "")
        if usecols:
            result = result.select(usecols)
        return result.sort(order_by)

    @save_verticapy_logs
    def select(self, columns: Union[str, list]):
        """
    Returns a copy of the vDataFrame with only the selected vColumns.

    Parameters
    ----------
    columns: str / list
        List of the vColumns to select. It can also be customized expressions.

    Returns
    -------
    vDataFrame
        object with only the selected columns.

    See Also
    --------
    vDataFrame.search : Searches the elements which matches with the input conditions.
        """
        if isinstance(columns, str):
            columns = [columns]
        for i in range(len(columns)):
            column = self.format_colnames(columns[i], raise_error=False)
            if column:
                dtype = ""
                if self._VERTICAPY_VARIABLES_["isflex"]:
                    dtype = self[column].ctype().lower()
                    if (
                        "array" in dtype
                        or "map" in dtype
                        or "row" in dtype
                        or "set" in dtype
                    ):
                        dtype = ""
                    else:
                        dtype = f"::{dtype}"
                columns[i] = column + dtype
            else:
                columns[i] = str(columns[i])
        table = f"""
            (SELECT 
                {', '.join(columns)} 
            FROM {self.__genSQL__()}) VERTICAPY_SUBTABLE"""
        return self.__vDataFrameSQL__(
            table, self._VERTICAPY_VARIABLES_["input_relation"], ""
        )

    @save_verticapy_logs
    def sem(
        self, columns: list = [], **agg_kwds,
    ):
        """
    Aggregates the vDataFrame using 'sem' (Standard Error of the Mean).

    Parameters
    ----------
    columns: list, optional
        List of the vColumns names. If empty, all numerical vColumns will be 
        used.
    **agg_kwds
        Any optional parameter to pass to the Aggregate function.

    Returns
    -------
    tablesample
        An object containing the result. For more information, see
        utilities.tablesample.

    See Also
    --------
    vDataFrame.aggregate : Computes the vDataFrame input aggregations.
        """
        return self.aggregate(func=["sem"], columns=columns, **agg_kwds,)

    @save_verticapy_logs
    def sessionize(
        self,
        ts: str,
        by: Union[str, list] = [],
        session_threshold: str = "30 minutes",
        name: str = "session_id",
    ):
        """
    Adds a new vColumn to the vDataFrame which will correspond to sessions 
    (user activity during a specific time). A session ends when ts - lag(ts) 
    is greater than a specific threshold.

    Parameters
    ----------
    ts: str
        vColumn used as timeline. It will be to use to order the data. It can be
        a numerical or type date like (date, datetime, timestamp...) vColumn.
    by: str / list, optional
        vColumns used in the partition.
    session_threshold: str, optional
        This parameter is the threshold which will determine the end of the 
        session. For example, if it is set to '10 minutes' the session ends
        after 10 minutes of inactivity.
    name: str, optional
        The session name.

    Returns
    -------
    vDataFrame
        self

    See Also
    --------
    vDataFrame.analytic : Adds a new vColumn to the vDataFrame by using an advanced 
        analytical function on a specific vColumn.
        """
        if isinstance(by, str):
            by = [by]
        by, ts = self.format_colnames(by, ts)
        partition = ""
        if by:
            partition = f"PARTITION BY {', '.join(by)}"
        expr = f"""CONDITIONAL_TRUE_EVENT(
                    {ts}::timestamp - LAG({ts}::timestamp) 
                  > '{session_threshold}') 
                  OVER ({partition} ORDER BY {ts})"""
        return self.eval(name=name, expr=expr)

    @save_verticapy_logs
    def score(
        self,
        y_true: str,
        y_score: str,
        method: ...,  # TO COMPLETE Literal[vp.learn.metrics.FUNCTIONS_DICTIONNARY]
        nbins: int = 30,
    ):
        """
    Computes the score using the input columns and the input method.

    Parameters
    ----------
    y_true: str
        Response column.
    y_score: str
        Prediction.
    method: str
        The method to use to compute the score.
            --- For Classification ---
            accuracy    : Accuracy
            auc         : Area Under the Curve (ROC)
            best_cutoff : Cutoff which optimised the ROC Curve prediction.
            bm          : Informedness = tpr + tnr - 1
            csi         : Critical Success Index = tp / (tp + fn + fp)
            f1          : F1 Score 
            logloss     : Log Loss
            mcc         : Matthews Correlation Coefficient 
            mk          : Markedness = ppv + npv - 1
            npv         : Negative Predictive Value = tn / (tn + fn)
            prc_auc     : Area Under the Curve (PRC)
            precision   : Precision = tp / (tp + fp)
            recall      : Recall = tp / (tp + fn)
            specificity : Specificity = tn / (tn + fp)
            --- For Regression ---
            max    : Max Error
            mae    : Mean Absolute Error
            median : Median Absolute Error
            mse    : Mean Squared Error
            msle   : Mean Squared Log Error
            r2     : R squared coefficient
            var    : Explained Variance  
            --- Plots ---
            roc  : ROC Curve
            prc  : PRC Curve
            lift : Lift Chart
    nbins: int, optional
        Number of bins used to compute some of the metrics (AUC, PRC AUC...)

    Returns
    -------
    float / tablesample
        score / tablesample of the curve

    See Also
    --------
    vDataFrame.aggregate : Computes the vDataFrame input aggregations.
        """
        y_true, y_score = self.format_colnames(y_true, y_score)
        fun = vp.learn.metrics.FUNCTIONS_DICTIONNARY[method]
        argv = [y_true, y_score, self.__genSQL__()]
        kwds = {}
        if method in ("accuracy", "acc"):
            kwds["pos_label"] = None
        elif method in ("best_cutoff", "best_threshold"):
            kwds["nbins"] = nbins
            kwds["best_threshold"] = True
        elif method in ("roc_curve", "roc", "prc_curve", "prc", "lift_chart", "lift"):
            kwds["nbins"] = nbins
        return vp.learn.metrics.FUNCTIONS_DICTIONNARY[method](*argv, **kwds)

    def shape(self):
        """
    Returns the number of rows and columns of the vDataFrame.

    Returns
    -------
    tuple
        (number of lines, number of columns)
        """
        m = len(self.get_columns())
        pre_comp = self.__get_catalog_value__("VERTICAPY_COUNT")
        if pre_comp != "VERTICAPY_NOT_PRECOMPUTED":
            return (pre_comp, m)
        self._VERTICAPY_VARIABLES_["count"] = executeSQL(
            query=f"""
                SELECT 
                    /*+LABEL('vDataframe.shape')*/ COUNT(*) 
                FROM {self.__genSQL__()} LIMIT 1
            """,
            title="Computing the total number of elements (COUNT(*))",
            method="fetchfirstelem",
            sql_push_ext=self._VERTICAPY_VARIABLES_["sql_push_ext"],
            symbol=self._VERTICAPY_VARIABLES_["symbol"],
        )
        return (self._VERTICAPY_VARIABLES_["count"], m)

    @save_verticapy_logs
    def skewness(
        self, columns: list = [], **agg_kwds,
    ):
        """
    Aggregates the vDataFrame using 'skewness'.

    Parameters
    ----------
    columns: list, optional
        List of the vColumns names. If empty, all numerical vColumns will be 
        used.
    **agg_kwds
        Any optional parameter to pass to the Aggregate function.

    Returns
    -------
    tablesample
        An object containing the result. For more information, see
        utilities.tablesample.

    See Also
    --------
    vDataFrame.aggregate : Computes the vDataFrame input aggregations.
        """
        return self.aggregate(func=["skewness"], columns=columns, **agg_kwds,)

    skew = skewness

    @save_verticapy_logs
    def sort(self, columns: Union[str, dict, list]):
        """
    Sorts the vDataFrame using the input vColumns.

    Parameters
    ----------
    columns: str / dict / list
        List of the vColumns to use to sort the data using asc order or
        dictionary of all sorting methods. For example, to sort by "column1"
        ASC and "column2" DESC, write {"column1": "asc", "column2": "desc"}

    Returns
    -------
    vDataFrame
        self

    See Also
    --------
    vDataFrame.append  : Merges the vDataFrame with another relation.
    vDataFrame.groupby : Aggregates the vDataFrame.
    vDataFrame.join    : Joins the vDataFrame with another relation.
        """
        if isinstance(columns, str):
            columns = [columns]
        columns = self.format_colnames(columns)
        max_pos = 0
        columns_tmp = [elem for elem in self._VERTICAPY_VARIABLES_["columns"]]
        for column in columns_tmp:
            max_pos = max(max_pos, len(self[column].transformations) - 1)
        self._VERTICAPY_VARIABLES_["order_by"][max_pos] = self.__get_sort_syntax__(
            columns
        )
        return self

    @save_verticapy_logs
    def stacked_area(
        self,
        ts: str,
        columns: list = [],
        start_date: Union[int, float, str, datetime.datetime, datetime.date] = "",
        end_date: Union[int, float, str, datetime.datetime, datetime.date] = "",
        fully: bool = False,
        ax=None,
        **style_kwds,
    ):
        """
    Draws the stacked area chart of the time series.

    Parameters
    ----------
    ts: str
        TS (Time Series) vColumn to use to order the data. The vColumn type must be
        date like (date, datetime, timestamp...) or numerical.
    columns: list, optional
        List of the vColumns names. If empty, all numerical vColumns will be 
        used. They must all include only positive values.
    start_date: int / float / str / date, optional
        Input Start Date. For example, time = '03-11-1993' will filter the data when 
        'ts' is lesser than November 1993 the 3rd.
    end_date: int / float / str / date, optional
        Input End Date. For example, time = '03-11-1993' will filter the data when 
        'ts' is greater than November 1993 the 3rd.
    fully: bool, optional
        If set to True, a Fully Stacked Area Chart will be drawn.
    ax: Matplotlib axes object, optional
        The axes to plot on.
    **style_kwds
        Any optional parameter to pass to the Matplotlib functions.

    Returns
    -------
    ax
        Matplotlib axes object
        """
        if isinstance(columns, str):
            columns = [columns]
        if fully:
            kind = "area_percent"
        else:
            kind = "area_stacked"
        assert min(self.min(columns)["min"]) >= 0, ValueError(
            "Columns having negative values can not be "
            "processed by the 'stacked_area' method."
        )
        columns, ts = self.format_colnames(columns, ts)
        return plt.multi_ts_plot(
            self, ts, columns, start_date, end_date, kind=kind, ax=ax, **style_kwds,
        )

    @save_verticapy_logs
    def std(
        self, columns: list = [], **agg_kwds,
    ):
        """
    Aggregates the vDataFrame using 'std' (Standard Deviation).

    Parameters
    ----------
    columns: list, optional
        List of the vColumns names. If empty, all numerical vColumns will be 
        used.
    **agg_kwds
        Any optional parameter to pass to the Aggregate function.

    Returns
    -------
    tablesample
        An object containing the result. For more information, see
        utilities.tablesample.

    See Also
    --------
    vDataFrame.aggregate : Computes the vDataFrame input aggregations.
        """
        return self.aggregate(func=["stddev"], columns=columns, **agg_kwds,)

    stddev = std

    @save_verticapy_logs
    def sum(
        self, columns: list = [], **agg_kwds,
    ):
        """
    Aggregates the vDataFrame using 'sum'.

    Parameters
    ----------
    columns: list, optional
        List of the vColumns names. If empty, all numerical vColumns will be 
        used.
    **agg_kwds
        Any optional parameter to pass to the Aggregate function.

    Returns
    -------
    tablesample
        An object containing the result. For more information, see
        utilities.tablesample.

    See Also
    --------
    vDataFrame.aggregate : Computes the vDataFrame input aggregations.
        """
        return self.aggregate(func=["sum"], columns=columns, **agg_kwds,)

    @save_verticapy_logs
    def swap(self, column1: Union[int, str], column2: Union[int, str]):
        """
    Swap the two input vColumns.

    Parameters
    ----------
    column1: str / int
        The first vColumn or its index to swap.
    column2: str / int
        The second vColumn or its index to swap.

    Returns
    -------
    vDataFrame
        self
        """
        if isinstance(column1, int):
            assert column1 < self.shape()[1], ParameterError(
                "The parameter 'column1' is incorrect, it is greater or equal "
                f"to the vDataFrame number of columns: {column1}>={self.shape()[1]}"
                "\nWhen this parameter type is 'integer', it must represent the index "
                "of the column to swap."
            )
            column1 = self.get_columns()[column1]
        if isinstance(column2, int):
            assert column2 < self.shape()[1], ParameterError(
                "The parameter 'column2' is incorrect, it is greater or equal "
                f"to the vDataFrame number of columns: {column2}>={self.shape()[1]}"
                "\nWhen this parameter type is 'integer', it must represent the "
                "index of the column to swap."
            )
            column2 = self.get_columns()[column2]
        column1, column2 = self.format_colnames(column1, column2)
        columns = self._VERTICAPY_VARIABLES_["columns"]
        all_cols = {}
        for idx, elem in enumerate(columns):
            all_cols[elem] = idx
        columns[all_cols[column1]], columns[all_cols[column2]] = (
            columns[all_cols[column2]],
            columns[all_cols[column1]],
        )
        return self

    def tail(self, limit: int = 5):
        """
    Returns the tail of the vDataFrame.

    Parameters
    ----------
    limit: int, optional
        Number of elements to display.

    Returns
    -------
    tablesample
        An object containing the result. For more information, see
        utilities.tablesample.

    See Also
    --------
    vDataFrame.head : Returns the vDataFrame head.
        """
        return self.iloc(limit=limit, offset=-1)

    @save_verticapy_logs
    def to_csv(
        self,
        path: str = "",
        sep: str = ",",
        na_rep: str = "",
        quotechar: str = '"',
        usecols: Union[str, list] = [],
        header: bool = True,
        new_header: list = [],
        order_by: Union[str, list, dict] = [],
        n_files: int = 1,
    ):
        """
    Creates a CSV file or folder of CSV files of the current vDataFrame 
    relation.

    Parameters
    ----------
    path: str, optional
        File/Folder system path. Be careful: if a CSV file with the same name 
        exists, it will over-write it.
    sep: str, optional
        Column separator.
    na_rep: str, optional
        Missing values representation.
    quotechar: str, optional
        Char which will enclose the str values.
    usecols: str / list, optional
        vColumns to select from the final vDataFrame relation. If empty, all
        vColumns will be selected.
    header: bool, optional
        If set to False, no header will be written in the CSV file.
    new_header: list, optional
        List of columns to use to replace vColumns name in the CSV.
    order_by: str / dict / list, optional
        List of the vColumns to use to sort the data using asc order or
        dictionary of all sorting methods. For example, to sort by "column1"
        ASC and "column2" DESC, write {"column1": "asc", "column2": "desc"}
    n_files: int, optional
        Integer greater than or equal to 1, the number of CSV files to generate.
        If n_files is greater than 1, you must also set order_by to sort the data,
        ideally with a column with unique values (e.g. ID).
        Greater values of n_files decrease memory usage, but increase execution 
        time.

    Returns
    -------
    str or list
        JSON str or list (n_files>1) if 'path' is not defined; otherwise, nothing

    See Also
    --------
    vDataFrame.to_db   : Saves the vDataFrame current relation to the Vertica database.
    vDataFrame.to_json : Creates a JSON file of the current vDataFrame relation.
        """
        if isinstance(order_by, str):
            order_by = [order_by]
        if isinstance(usecols, str):
            usecols = [usecols]
        assert n_files >= 1, ParameterError(
            "Parameter 'n_files' must be greater or equal to 1."
        )
        assert (n_files == 1) or order_by, ParameterError(
            "If you want to store the vDataFrame in many CSV files, "
            "you have to sort your data by using at least one column. "
            "If the column hasn't unique values, the final result can "
            "not be guaranteed."
        )
        columns = (
            self.get_columns()
            if not (usecols)
            else [quote_ident(column) for column in usecols]
        )
        for col in columns:
            if self[col].category() in ("vmap", "complex"):
                raise TypeError(
                    f"Impossible to export virtual column {col} as"
                    " it includes complex data types or vmaps. "
                    "Use 'astype' method to cast them before using "
                    "this function."
                )
        assert not (new_header) or len(new_header) == len(columns), ParsingError(
            "The header has an incorrect number of columns"
        )
        total = self.shape()[0]
        current_nb_rows_written, file_id = 0, 0
        limit = int(total / n_files) + 1
        order_by = self.__get_sort_syntax__(order_by)
        if not (order_by):
            order_by = self.__get_last_order_by__()
        if n_files > 1 and path:
            os.makedirs(path)
        csv_files = []
        while current_nb_rows_written < total:
            if new_header:
                csv_file = sep.join(
                    [
                        quotechar + column.replace('"', "") + quotechar
                        for column in new_header
                    ]
                )
            elif header:
                csv_file = sep.join(
                    [
                        quotechar + column.replace('"', "") + quotechar
                        for column in columns
                    ]
                )
            result = executeSQL(
                query=f"""
                    SELECT 
                        /*+LABEL('vDataframe.to_csv')*/ 
                        {', '.join(columns)} 
                    FROM {self.__genSQL__()}
                    {order_by} 
                    LIMIT {limit} 
                    OFFSET {current_nb_rows_written}""",
                title="Reading the data.",
                method="fetchall",
                sql_push_ext=self._VERTICAPY_VARIABLES_["sql_push_ext"],
                symbol=self._VERTICAPY_VARIABLES_["symbol"],
            )
            for row in result:
                tmp_row = []
                for item in row:
                    if isinstance(item, str):
                        tmp_row += [quotechar + item + quotechar]
                    elif item == None:
                        tmp_row += [na_rep]
                    else:
                        tmp_row += [str(item)]
                csv_file += "\n" + sep.join(tmp_row)
            current_nb_rows_written += limit
            file_id += 1
            if n_files == 1 and path:
                file = open(path, "w+")
                file.write(csv_file)
                file.close()
            elif path:
                file = open(f"{path}/{file_id}.csv", "w+")
                file.write(csv_file)
                file.close()
            else:
                csv_files += [csv_file]
        if not (path):
            if n_files == 1:
                return csv_files[0]
            else:
                return csv_files

    @save_verticapy_logs
    def to_db(
        self,
        name: str,
        usecols: Union[str, list] = [],
        relation_type: Literal[
            "view", "temporary", "table", "local", "insert"
        ] = "view",
        inplace: bool = False,
        db_filter: Union[str, list] = "",
        nb_split: int = 0,
    ):
        """
    Saves the vDataFrame current relation to the Vertica database.

    Parameters
    ----------
    name: str
        Name of the relation. To save the relation in a specific schema you can
        write '"my_schema"."my_relation"'. Use double quotes '"' to avoid errors
        due to special characters.
    usecols: str / list, optional
        vColumns to select from the final vDataFrame relation. If empty, all
        vColumns will be selected.
    relation_type: str, optional
        Type of the relation.
            view      : View
            table     : Table
            temporary : Temporary Table
            local     : Local Temporary Table
            insert    : Inserts into an existing table
    inplace: bool, optional
        If set to True, the vDataFrame will be replaced using the new relation.
    db_filter: str / list, optional
        Filter used before creating the relation in the DB. It can be a list of
        conditions or an expression. This parameter is very useful to create train 
        and test sets on TS.
    nb_split: int, optional
        If this parameter is greater than 0, it will add to the final relation a
        new column '_verticapy_split_' which will contain values in 
        [0;nb_split - 1] where each category will represent 1 / nb_split
        of the entire distribution. 

    Returns
    -------
    vDataFrame
        self

    See Also
    --------
    vDataFrame.to_csv : Creates a csv file of the current vDataFrame relation.
        """
        if isinstance(usecols, str):
            usecols = [usecols]
        relation_type = relation_type.lower()
        usecols = self.format_colnames(usecols)
        commit = (
            " ON COMMIT PRESERVE ROWS"
            if (relation_type in ("local", "temporary"))
            else ""
        )
        if relation_type == "temporary":
            relation_type += " table"
        elif relation_type == "local":
            relation_type += " temporary table"
        isflex = self._VERTICAPY_VARIABLES_["isflex"]
        if not (usecols):
            usecols = self.get_columns()
        if not (usecols) and not (isflex):
            select = "*"
        elif usecols and not (isflex):
            select = ", ".join([quote_ident(column) for column in usecols])
        else:
            select = []
            for column in usecols:
                ctype, col = self[column].ctype(), quote_ident(column)
                if ctype.startswith("vmap"):
                    column = f"MAPTOSTRING({col}) AS {col}"
                else:
                    column += f"::{ctype}"
                select += [column]
            select = ", ".join(select)
        insert_usecols = ", ".join([quote_ident(column) for column in usecols])
        random_func = get_random_function(nb_split)
        nb_split = f", {random_func} AS _verticapy_split_" if (nb_split > 0) else ""
        if isinstance(db_filter, Iterable) and not (isinstance(db_filter, str)):
            db_filter = " AND ".join([f"({elem})" for elem in db_filter])
        db_filter = f" WHERE {db_filter}" if (db_filter) else ""
        if relation_type == "insert":
            insert_usecols_str = (
                f" ({insert_usecols})" if not (nb_split) and select != "*" else ""
            )
            query = f"""
                INSERT INTO {name}{insert_usecols_str} 
                    SELECT 
                        {select}{nb_split} 
                    FROM {self.__genSQL__()}
                    {db_filter}
                    {self.__get_last_order_by__()}"""
        else:
            query = f"""
                CREATE 
                    {relation_type.upper()}
                    {name}{commit} 
                AS 
                SELECT 
                    /*+LABEL('vDataframe.to_db')*/ 
                    {select}{nb_split} 
                FROM {self.__genSQL__()}
                {db_filter}
                {self.__get_last_order_by__()}"""
        executeSQL(
            query=query,
            title=f"Creating a new {relation_type} to save the vDataFrame.",
        )
        if relation_type == "insert":
            executeSQL(query="COMMIT;", title="Commit.")
        self.__add_to_history__(
            "[Save]: The vDataFrame was saved into a "
            f"{relation_type} named '{name}'."
        )
        if inplace:
            history, saving = (
                self._VERTICAPY_VARIABLES_["history"],
                self._VERTICAPY_VARIABLES_["saving"],
            )
            catalog_vars = {}
            for column in usecols:
                catalog_vars[column] = self[column].catalog
            if relation_type == "local temporary table":
                self.__init__("v_temp_schema." + name)
            else:
                self.__init__(name)
            self._VERTICAPY_VARIABLES_["history"] = history
            for column in usecols:
                self[column].catalog = catalog_vars[column]
        return self

    @save_verticapy_logs
    def to_geopandas(self, geometry: str):
        """
    Converts the vDataFrame to a Geopandas DataFrame.

    \u26A0 Warning : The data will be loaded in memory.

    Parameters
    ----------
    geometry: str
        Geometry object used to create the GeoDataFrame.
        It can also be a Geography object but it will be casted to Geometry.

    Returns
    -------
    geopandas.GeoDataFrame
        The geopandas.GeoDataFrame of the current vDataFrame relation.
        """
        if not (GEOPANDAS_ON):
            raise ImportError(
                "The geopandas module doesn't seem to be installed in your "
                "environment.\nTo be able to use this method, you'll have to "
                "install it.\n[Tips] Run: 'pip3 install geopandas' in your "
                "terminal to install the module."
            )
        columns = self.get_columns(exclude_columns=[geometry])
        columns = ", ".join(columns + [f"ST_AsText({geometry}) AS {geometry}"])
        query = f"""
            SELECT 
                /*+LABEL('vDataframe.to_geopandas')*/ {columns} 
            FROM {self.__genSQL__()}
            {self.__get_last_order_by__()}"""
        data = executeSQL(
            query, title="Getting the vDataFrame values.", method="fetchall"
        )
        column_names = [column[0] for column in vp.current_cursor().description]
        df = pd.DataFrame(data)
        df.columns = column_names
        if len(geometry) > 2 and geometry[0] == geometry[-1] == '"':
            geometry = geometry[1:-1]
        df[geometry] = df[geometry].apply(wkt.loads)
        df = GeoDataFrame(df, geometry=geometry)
        return df

    @save_verticapy_logs
    def to_json(
        self,
        path: str = "",
        usecols: Union[str, list] = [],
        order_by: Union[str, list, dict] = [],
        n_files: int = 1,
    ):
        """
    Creates a JSON file or folder of JSON files of the current vDataFrame 
    relation.

    Parameters
    ----------
    path: str, optional
        File/Folder system path. Be careful: if a JSON file with the same name 
        exists, it will over-write it.
    usecols: str / list, optional
        vColumns to select from the final vDataFrame relation. If empty, all
        vColumns will be selected.
    order_by: str / dict / list, optional
        List of the vColumns to use to sort the data using asc order or
        dictionary of all sorting methods. For example, to sort by "column1"
        ASC and "column2" DESC, write {"column1": "asc", "column2": "desc"}
    n_files: int, optional
        Integer greater than or equal to 1, the number of CSV files to generate.
        If n_files is greater than 1, you must also set order_by to sort the data,
        ideally with a column with unique values (e.g. ID).
        Greater values of n_files decrease memory usage, but increase execution time.

    Returns
    -------
    str or list
        JSON str or list (n_files>1) if 'path' is not defined; otherwise, nothing

    See Also
    --------
    vDataFrame.to_csv : Creates a CSV file of the current vDataFrame relation.
    vDataFrame.to_db  : Saves the vDataFrame current relation to the Vertica database.
        """
        if isinstance(order_by, str):
            order_by = [order_by]
        if isinstance(usecols, str):
            usecols = [usecols]
        assert n_files >= 1, ParameterError(
            "Parameter 'n_files' must be greater or equal to 1."
        )
        assert (n_files == 1) or order_by, ParameterError(
            "If you want to store the vDataFrame in many JSON files, you "
            "have to sort your data by using at least one column. If "
            "the column hasn't unique values, the final result can not "
            "be guaranteed."
        )
        columns = (
            self.get_columns()
            if not (usecols)
            else [quote_ident(column) for column in usecols]
        )
        transformations, is_complex_vmap = [], []
        for col in columns:
            if self[col].category() == "complex":
                transformations += [f"TO_JSON({col}) AS {col}"]
                is_complex_vmap += [True]
            elif self[col].category() == "vmap":
                transformations += [f"MAPTOSTRING({col}) AS {col}"]
                is_complex_vmap += [True]
            else:
                transformations += [col]
                is_complex_vmap += [False]
        total = self.shape()[0]
        current_nb_rows_written, file_id = 0, 0
        limit = int(total / n_files) + 1
        order_by = self.__get_sort_syntax__(order_by)
        if not (order_by):
            order_by = self.__get_last_order_by__()
        if n_files > 1 and path:
            os.makedirs(path)
        if not (path):
            json_files = []
        while current_nb_rows_written < total:
            json_file = "[\n"
            result = executeSQL(
                query=f"""
                    SELECT 
                        /*+LABEL('vDataframe.to_json')*/ 
                        {', '.join(transformations)} 
                    FROM {self.__genSQL__()}
                    {order_by} 
                    LIMIT {limit} 
                    OFFSET {current_nb_rows_written}""",
                title="Reading the data.",
                method="fetchall",
                sql_push_ext=self._VERTICAPY_VARIABLES_["sql_push_ext"],
                symbol=self._VERTICAPY_VARIABLES_["symbol"],
            )
            for row in result:
                tmp_row = []
                for i, item in enumerate(row):
                    if isinstance(item, (float, int, decimal.Decimal)) or (
                        isinstance(item, (str,)) and is_complex_vmap[i]
                    ):
                        tmp_row += [f"{quote_ident(columns[i])}: {item}"]
                    elif item != None:
                        tmp_row += [f'{quote_ident(columns[i])}: "{item}"']
                json_file += "{" + ", ".join(tmp_row) + "},\n"
            current_nb_rows_written += limit
            file_id += 1
            json_file = json_file[0:-2] + "\n]"
            if n_files == 1 and path:
                file = open(path, "w+")
                file.write(json_file)
                file.close()
            elif path:
                file = open(f"{path}/{file_id}.json", "w+")
                file.write(json_file)
                file.close()
            else:
                json_files += [json_file]
        if not (path):
            if n_files == 1:
                return json_files[0]
            else:
                return json_files

    @save_verticapy_logs
    def to_list(self):
        """
    Converts the vDataFrame to a Python list.

    \u26A0 Warning : The data will be loaded in memory.

    Returns
    -------
    List
        The list of the current vDataFrame relation.
        """
        result = executeSQL(
            query=f"""
                SELECT 
                    /*+LABEL('vDataframe.to_list')*/ * 
                FROM {self.__genSQL__()}
                {self.__get_last_order_by__()}""",
            title="Getting the vDataFrame values.",
            method="fetchall",
            sql_push_ext=self._VERTICAPY_VARIABLES_["sql_push_ext"],
            symbol=self._VERTICAPY_VARIABLES_["symbol"],
        )
        final_result = []
        for elem in result:
            final_result += [
                [
                    float(item) if isinstance(item, decimal.Decimal) else item
                    for item in elem
                ]
            ]
        return final_result

    @save_verticapy_logs
    def to_numpy(self):
        """
    Converts the vDataFrame to a Numpy array.

    \u26A0 Warning : The data will be loaded in memory.

    Returns
    -------
    numpy.array
        The numpy array of the current vDataFrame relation.
        """
        return np.array(self.to_list())

    @save_verticapy_logs
    def to_pandas(self):
        """
    Converts the vDataFrame to a pandas DataFrame.

    \u26A0 Warning : The data will be loaded in memory.

    Returns
    -------
    pandas.DataFrame
        The pandas.DataFrame of the current vDataFrame relation.
        """
        data = executeSQL(
            query=f"""
                SELECT 
                    /*+LABEL('vDataframe.to_pandas')*/ * 
                FROM {self.__genSQL__()}{self.__get_last_order_by__()}""",
            title="Getting the vDataFrame values.",
            method="fetchall",
            sql_push_ext=self._VERTICAPY_VARIABLES_["sql_push_ext"],
            symbol=self._VERTICAPY_VARIABLES_["symbol"],
        )
        column_names = [column[0] for column in vp.current_cursor().description]
        df = pd.DataFrame(data)
        df.columns = column_names
        return df

    @save_verticapy_logs
    def to_parquet(
        self,
        directory: str,
        compression: Literal[
            "snappy", "gzip", "brotli", "zstd", "uncompressed"
        ] = "snappy",
        rowGroupSizeMB: int = 512,
        fileSizeMB: int = 10000,
        fileMode: str = "660",
        dirMode: str = "755",
        int96AsTimestamp: bool = True,
        by: Union[str, list] = [],
        order_by: Union[str, list, dict] = [],
    ):
        """
    Exports a table, columns from a table, or query results to Parquet files.
    You can partition data instead of or in addition to exporting the column data, 
    which enables partition pruning and improves query performance. 

    Parameters
    ----------
    directory: str
        The destination directory for the output file(s). The directory must not 
        already exist, and the current user must have write permissions on it. 
        The destination can be one of the following file systems: 
            HDFS File System
            S3 Object Store
            Google Cloud Storage (GCS) Object Store
            Azure Blob Storage Object Store
            Linux file system (either an NFS mount or local storage on each node)
    compression: str, optional
        Column compression type, one the following:        
            Snappy (default)
            gzip
            Brotli
            zstd
            Uncompressed
    rowGroupSizeMB: int, optional
        The uncompressed size, in MB, of exported row groups, an integer value in the range
        [1, fileSizeMB]. If fileSizeMB is 0, the uncompressed size is unlimited.
        Row groups in the exported files are smaller than this value because Parquet 
        files are compressed on write. 
        For best performance when exporting to HDFS, set this rowGroupSizeMB to be 
        smaller than the HDFS block size.
    fileSizeMB: int, optional
        The maximum file size of a single output file. This fileSizeMB is a hint/ballpark 
        and not a hard limit. 
        A value of 0 indicates that the size of a single output file is unlimited.  
        This parameter affects the size of individual output files, not the total output size. 
        For smaller values, Vertica divides the output into more files; all data is still exported.
    fileMode: int, optional
        HDFS only: the permission to apply to all exported files. You can specify 
        the value in octal (such as 755) or symbolic (such as rwxr-xr-x) modes. 
        The value must be a string even when using octal mode.
        Valid octal values are in the range [0,1777]. For details, see HDFS Permissions in the 
        Apache Hadoop documentation.
        If the destination is not HDFS, this parameter has no effect.
    dirMode: int, optional
        HDFS only: the permission to apply to all exported directories. Values follow 
        the same rules as those for fileMode. Additionally, you must give the Vertica HDFS user full 
        permissions: at least rwx------ (symbolic) or 700 (octal).
        If the destination is not HDFS, this parameter has no effect.
    int96AsTimestamp: bool, optional
        Boolean, specifies whether to export timestamps as int96 physical type (True) or int64 
        physical type (False).
    by: str / list, optional
        vColumns used in the partition.
    order_by: str / dict / list, optional
        If specified as a list: the list of vColumns useed to sort the data in ascending order.
        If specified as a dictionary: a dictionary of all sorting methods.
        For example, to sort by "column1" ASC and "column2" DESC: {"column1": "asc", "column2": "desc"}

    Returns
    -------
    tablesample
        An object containing the number of rows exported. For details, 
        see utilities.tablesample.

    See Also
    --------
    vDataFrame.to_csv : Creates a CSV file of the current vDataFrame relation.
    vDataFrame.to_db  : Saves the current relation's vDataFrame to the Vertica database.
    vDataFrame.to_json: Creates a JSON file of the current vDataFrame relation.
        """
        if isinstance(order_by, str):
            order_by = [order_by]
        if isinstance(by, str):
            by = [by]
        assert 0 < rowGroupSizeMB, ParameterError(
            "Parameter 'rowGroupSizeMB' must be greater than 0."
        )
        assert 0 < fileSizeMB, ParameterError(
            "Parameter 'fileSizeMB' must be greater than 0."
        )
        by = self.format_colnames(by)
        partition = ""
        if by:
            partition = f"PARTITION BY {', '.join(by)}"
        result = util.to_tablesample(
            query=f"""
                EXPORT TO PARQUET(directory = '{directory}',
                                  compression = '{compression}',
                                  rowGroupSizeMB = {rowGroupSizeMB},
                                  fileSizeMB = {fileSizeMB},
                                  fileMode = '{fileMode}',
                                  dirMode = '{dirMode}',
                                  int96AsTimestamp = {str(int96AsTimestamp).lower()}) 
                          OVER({partition}{self.__get_sort_syntax__(order_by)}) 
                       AS SELECT * FROM {self.__genSQL__()};""",
            title="Exporting data to Parquet format.",
            sql_push_ext=self._VERTICAPY_VARIABLES_["sql_push_ext"],
            symbol=self._VERTICAPY_VARIABLES_["symbol"],
        )
        return result

    @save_verticapy_logs
    def to_pickle(self, name: str):
        """
    Saves the vDataFrame to a Python pickle file.

    Parameters
    ----------
    name: str
        Name of the file. Be careful: if a file with the same name exists, it 
        will over-write it.

    Returns
    -------
    vDataFrame
        self
        """
        pickle.dump(self, open(name, "wb"))
        return self

    @save_verticapy_logs
    def to_shp(
        self,
        name: str,
        path: str,
        usecols: Union[str, list] = [],
        overwrite: bool = True,
        shape: Literal[
            "Point",
            "Polygon",
            "Linestring",
            "Multipoint",
            "Multipolygon",
            "Multilinestring",
        ] = "Polygon",
    ):
        """
    Creates a SHP file of the current vDataFrame relation. For the moment, 
    files will be exported in the Vertica server.

    Parameters
    ----------
    name: str
        Name of the SHP file.
    path: str
        Absolute path where the SHP file will be created.
    usecols: list, optional
        vColumns to select from the final vDataFrame relation. If empty, all
        vColumns will be selected.
    overwrite: bool, optional
        If set to True, the function will overwrite the index if an index exists.
    shape: str, optional
        Must be one of the following spatial classes: 
            Point, Polygon, Linestring, Multipoint, Multipolygon, Multilinestring. 
        Polygons and Multipolygons always have a clockwise orientation.

    Returns
    -------
    vDataFrame
        self
        """
        if isinstance(usecols, str):
            usecols = [usecols]
        query = f"""
            SELECT 
                /*+LABEL('vDataframe.to_shp')*/ 
                STV_SetExportShapefileDirectory(
                USING PARAMETERS path = '{path}');"""
        executeSQL(query=query, title="Setting SHP Export directory.")
        columns = (
            self.get_columns()
            if not (usecols)
            else [quote_ident(column) for column in usecols]
        )
        columns = ", ".join(columns)
        query = f"""
            SELECT 
                /*+LABEL('vDataframe.to_shp')*/ 
                STV_Export2Shapefile({columns} 
                USING PARAMETERS shapefile = '{name}.shp',
                                 overwrite = {overwrite}, 
                                 shape = '{shape}') 
                OVER() 
            FROM {self.__genSQL__()};"""
        executeSQL(query=query, title="Exporting the SHP.")
        return self

    @save_verticapy_logs
    def train_test_split(
        self,
        test_size: float = 0.33,
        order_by: Union[str, list, dict] = {},
        random_state: int = None,
    ):
        """
    Creates 2 vDataFrame (train/test) which can be to use to evaluate a model.
    The intersection between the train and the test is empty only if a unique
    order is specified.

    Parameters
    ----------
    test_size: float, optional
        Proportion of the test set comparint to the training set.
    order_by: str / dict / list, optional
        List of the vColumns to use to sort the data using asc order or
        dictionary of all sorting methods. For example, to sort by "column1"
        ASC and "column2" DESC, write {"column1": "asc", "column2": "desc"}
        Without this parameter, the seeded random number used to split the data
        into train and test can not garanty that no collision occurs. Use this
        parameter to avoid collisions.
    random_state: int, optional
        Integer used to seed the randomness.

    Returns
    -------
    tuple
        (train vDataFrame, test vDataFrame)
        """
        if isinstance(order_by, str):
            order_by = [order_by]
        order_by = self.__get_sort_syntax__(order_by)
        if not random_state:
            random_state = vp.OPTIONS["random_state"]
        random_seed = (
            random_state
            if isinstance(random_state, int)
            else random.randint(-10e6, 10e6)
        )
        random_func = f"SEEDED_RANDOM({random_seed})"
        q = executeSQL(
            query=f"""
                SELECT 
                    /*+LABEL('vDataframe.train_test_split')*/ 
                    APPROXIMATE_PERCENTILE({random_func} 
                        USING PARAMETERS percentile = {test_size}) 
                FROM {self.__genSQL__()}""",
            title="Computing the seeded numbers quantile.",
            method="fetchfirstelem",
        )
        test_table = f"""
            (SELECT * 
             FROM {self.__genSQL__()} 
             WHERE {random_func} < {q}{order_by}) x"""
        train_table = f"""
            (SELECT * 
             FROM {self.__genSQL__()} 
             WHERE {random_func} > {q}{order_by}) x"""
        return (
            util.vDataFrameSQL(relation=train_table),
            util.vDataFrameSQL(relation=test_table),
        )

    @save_verticapy_logs
    def var(
        self, columns: list = [], **agg_kwds,
    ):
        """
    Aggregates the vDataFrame using 'variance'.

    Parameters
    ----------
    columns: list, optional
        List of the vColumns names. If empty, all numerical vColumns will be 
        used.
    **agg_kwds
        Any optional parameter to pass to the Aggregate function.

    Returns
    -------
    tablesample
        An object containing the result. For more information, see
        utilities.tablesample.

    See Also
    --------
    vDataFrame.aggregate : Computes the vDataFrame input aggregations.
        """
        return self.aggregate(func=["variance"], columns=columns, **agg_kwds,)

    variance = var

    def vertica_version(self):
        """
    Returns the version of Vertica.

    Returns
    -------
    list
        List containing the version information.
        [MAJOR, MINOR, PATCH, POST]
        """
        return util.vertica_version()

    @save_verticapy_logs
    def iv_woe(
        self,
        y: str,
        columns: Union[str, list] = [],
        nbins: int = 10,
        show: bool = True,
        ax=None,
    ):
        """
    Computes the Information Value (IV) Table. It tells the predictive power of 
    an independent variable in relation to the dependent variable.

    Parameters
    ----------
    y: str
        Response vColumn.
    columns: str / list, optional
        List of the vColumns names. If empty, all vColumns except the response 
        will be used.
    nbins: int, optional
        Maximum number of bins used for the discretization (must be > 1).
    show: bool, optional
        If set to True, the IV Plot will be drawn using Matplotlib.
    ax: Matplotlib axes object, optional
        The axes to plot on.
    

    Returns
    -------
    tablesample
        An object containing the result. For more information, see
        utilities.tablesample.

    See Also
    --------
    vDataFrame[].iv_woe : Computes the Information Value (IV) / 
        Weight Of Evidence (WOE) Table.
        """
        if isinstance(columns, str):
            columns = [columns]
        columns, y = self.format_colnames(columns, y)
        if not (columns):
            columns = self.get_columns(exclude_columns=[y])
        coeff_importances = {}
        for elem in columns:
            coeff_importances[elem] = self[elem].iv_woe(y=y, nbins=nbins)["iv"][-1]
        if show:
            ax = plt.plot_importance(coeff_importances, print_legend=False, ax=ax)
            ax.set_xlabel("IV")
        index = [elem for elem in coeff_importances]
        iv = [coeff_importances[elem] for elem in coeff_importances]
        data = [(index[i], iv[i]) for i in range(len(iv))]
        data = sorted(data, key=lambda tup: tup[1], reverse=True)
        return util.tablesample(
            {"index": [elem[0] for elem in data], "iv": [elem[1] for elem in data],}
        )


#
# Multiprocessing
#

#
# Functions used to send multiple queries at the same time.
#

# Aggregate
def aggregate_parallel_block(vdf, func: list, columns: list, ncols_block: int, i: int):
    return vdf.aggregate(
        func=func, columns=columns[i : i + ncols_block], ncols_block=ncols_block
    )


# Describe
def describe_parallel_block(
    vdf, method: str, columns: list, unique: bool, ncols_block: int, i: int,
):
    return vdf.describe(
        method=method,
        columns=columns[i : i + ncols_block],
        unique=unique,
        ncols_block=ncols_block,
    )