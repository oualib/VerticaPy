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
import decimal, math
from collections.abc import Iterable
from typing import Union, Literal

# Other modules
from tqdm.auto import tqdm
import numpy as np
import scipy.stats as scipy_st
import scipy.special as scipy_special

# VerticaPy Modules
from verticapy.core.tablesample import tablesample
from verticapy.sql.read import to_tablesample
import verticapy.plotting._matplotlib as plt
from verticapy._utils._collect import save_verticapy_logs
from verticapy.errors import EmptyParameter
from verticapy.sql.drop import drop
from verticapy._version import vertica_version
from verticapy._utils._gen import gen_name, gen_tmp_name
from verticapy._utils._sql import _executeSQL
from verticapy.plotting._colors import gen_cmap
from verticapy.sql._utils._format import quote_ident
from verticapy._config.config import OPTIONS


class vDFCORR:
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
                n, k, r = _executeSQL(
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
                result = _executeSQL(
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
                result = _executeSQL(
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
                vertica_version(condition=[9, 2, 1])
                result = _executeSQL(
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
                loop = tqdm(range(i0, n)) if OPTIONS["tqdm"] else range(i0, n)
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
                        result = _executeSQL(
                            query=f"""
                                SELECT 
                                    /*+LABEL('vDataframe.__aggregate_matrix__')*/ 
                                    {', '.join(all_list)}""",
                            print_time_sql=False,
                            method="fetchrow",
                        )
                    else:
                        result = _executeSQL(
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
            return tablesample(values=values).decimal_to_float()
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
                    result = _executeSQL(
                        query=f"""
                            SELECT 
                                /*+LABEL('vDataframe.__aggregate_vector__')*/ 
                                {', '.join(all_list)}""",
                        method="fetchrow",
                        print_time_sql=False,
                    )
                else:
                    result = _executeSQL(
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
        return tablesample(values={"index": cols, focus: vector}).decimal_to_float()

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
        n = _executeSQL(
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
            nc, nd = _executeSQL(
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
                vt, v1_0, v2_0 = _executeSQL(
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
                vu, v1_1, v2_1 = _executeSQL(
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
                    k, r = _executeSQL(
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
            k, r = _executeSQL(
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
        from verticapy.machine_learning.vertica.linear_model import LinearRegression
        from verticapy.core.vdataframe.vdataframe import vDataFrame

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
                schema=OPTIONS["temp_schema"], name="linear_reg_view"
            )
            tmp_lr0_name = gen_tmp_name(
                schema=OPTIONS["temp_schema"], name="linear_reg0"
            )
            tmp_lr1_name = gen_tmp_name(
                schema=OPTIONS["temp_schema"], name="linear_reg1"
            )
            try:
                drop(tmp_view_name, method="view")
                query = f"""
                    CREATE VIEW {tmp_view_name} 
                        AS SELECT /*+LABEL('vDataframe.pacf')*/ * FROM {relation}"""
                _executeSQL(query, print_time_sql=False)
                vdf = vDataFrame(tmp_view_name)
                drop(tmp_lr0_name, method="model")
                model = LinearRegression(name=tmp_lr0_name, solver="Newton")
                model.fit(
                    input_relation=tmp_view_name,
                    X=[f"lag_{i}_{gen_name([column])}" for i in range(1, p)],
                    y=column,
                )
                model.predict(vdf, name="prediction_0")
                drop(tmp_lr1_name, method="model")
                model = LinearRegression(name=tmp_lr1_name, solver="Newton")
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
                drop(tmp_view_name, method="view")
                drop(tmp_lr0_name, method="model")
                drop(tmp_lr1_name, method="model")
            return result
        else:
            if isinstance(p, (float, int)):
                p = range(0, p + 1)
            loop = tqdm(p) if OPTIONS["tqdm"] else p
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
            result = tablesample({"index": columns, "value": pacf})
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
                result = _executeSQL(
                    query=f"""
                        SELECT 
                            /*+LABEL('vDataframe.regr')*/ 
                            {", ".join(all_list)}""",
                    print_time_sql=False,
                    method="fetchrow",
                )
            else:
                result = _executeSQL(
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
                        _executeSQL(
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
        return tablesample(values=values).decimal_to_float()

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
        return tablesample(
            {"index": [elem[0] for elem in data], "iv": [elem[1] for elem in data],}
        )


class vDCCORR:
    @save_verticapy_logs
    def iv_woe(self, y: str, nbins: int = 10):
        """
    Computes the Information Value (IV) / Weight Of Evidence (WOE) Table. It tells 
    the predictive power of an independent variable in relation to the dependent 
    variable.

    Parameters
    ----------
    y: str
        Response vColumn.
    nbins: int, optional
        Maximum number of nbins used for the discretization (must be > 1)

    Returns
    -------
    tablesample
        An object containing the result. For more information, see
        utilities.tablesample.

    See Also
    --------
    vDataFrame.iv_woe : Computes the Information Value (IV) Table.
        """
        y = self.parent.format_colnames(y)
        assert self.parent[y].nunique() == 2, TypeError(
            f"vColumn {y} must be binary to use iv_woe."
        )
        response_cat = self.parent[y].distinct()
        response_cat.sort()
        assert response_cat == [0, 1], TypeError(
            f"vColumn {y} must be binary to use iv_woe."
        )
        self.parent[y].distinct()
        trans = self.discretize(
            method="same_width" if self.isnum() else "topk",
            nbins=nbins,
            k=nbins,
            new_category="Others",
            return_enum_trans=True,
        )[0].replace("{}", self.alias)
        query = f"""
            SELECT 
                {trans} AS {self.alias}, 
                {self.alias} AS ord, 
                {y}::int AS {y} 
            FROM {self.parent.__genSQL__()}"""
        query = f"""
            SELECT 
                {self.alias}, 
                MIN(ord) AS ord, 
                SUM(1 - {y}) AS non_events, 
                SUM({y}) AS events 
            FROM ({query}) x GROUP BY 1"""
        query = f"""
            SELECT 
                {self.alias}, 
                ord, 
                non_events, 
                events, 
                non_events / NULLIFZERO(SUM(non_events) OVER ()) AS pt_non_events, 
                events / NULLIFZERO(SUM(events) OVER ()) AS pt_events 
            FROM ({query}) x"""
        query = f"""
            SELECT 
                {self.alias} AS index, 
                non_events, 
                events, 
                pt_non_events, 
                pt_events, 
                CASE 
                    WHEN non_events = 0 OR events = 0 THEN 0 
                    ELSE ZEROIFNULL(LN(pt_non_events / NULLIFZERO(pt_events))) 
                END AS woe, 
                CASE 
                    WHEN non_events = 0 OR events = 0 THEN 0 
                    ELSE (pt_non_events - pt_events) 
                        * ZEROIFNULL(LN(pt_non_events 
                        / NULLIFZERO(pt_events))) 
                END AS iv 
            FROM ({query}) x ORDER BY ord"""
        title = f"Computing WOE & IV of {self.alias} (response = {y})."
        result = to_tablesample(
            query,
            title=title,
            sql_push_ext=self.parent._VERTICAPY_VARIABLES_["sql_push_ext"],
            symbol=self.parent._VERTICAPY_VARIABLES_["symbol"],
        )
        result.values["index"] += ["total"]
        result.values["non_events"] += [sum(result["non_events"])]
        result.values["events"] += [sum(result["events"])]
        result.values["pt_non_events"] += [""]
        result.values["pt_events"] += [""]
        result.values["woe"] += [""]
        result.values["iv"] += [sum(result["iv"])]
        return result