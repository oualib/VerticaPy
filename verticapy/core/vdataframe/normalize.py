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
# Standard Python Modules
import warnings, math
from typing import Union, Literal

# VerticaPy Modules
from verticapy._utils._collect import save_verticapy_logs
from verticapy._config.config import OPTIONS
from verticapy._utils._sql import _executeSQL


class vDFNORM:
    @save_verticapy_logs
    def normalize(
        self,
        columns: Union[str, list] = [],
        method: Literal["zscore", "robust_zscore", "minmax"] = "zscore",
    ):
        """
    Normalizes the input vDataColumns using the input method.

    Parameters
    ----------
    columns: str / list, optional
        List of the vDataColumns names. If empty, all numerical vDataColumns will be 
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
    vDataFrame[].normalize : Normalizes the vDataColumn. This method is more complete 
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
            elif OPTIONS["print_info"]:
                warning_message = (
                    f"The vDataColumn {column} was skipped.\n"
                    "Normalize only accept numerical data types."
                )
                warnings.warn(warning_message, Warning)
        return self


class vDCNORM:
    @save_verticapy_logs
    def normalize(
        self,
        method: Literal["zscore", "robust_zscore", "minmax"] = "zscore",
        by: Union[str, list] = [],
        return_trans: bool = False,
    ):
        """
    Normalizes the input vDataColumns using the input method.

    Parameters
    ----------
    method: str, optional
        Method to use to normalize.
            zscore        : Normalization using the Z-Score (avg and std).
                (x - avg) / std
            robust_zscore : Normalization using the Robust Z-Score (median and mad).
                (x - median) / (1.4826 * mad)
            minmax        : Normalization using the MinMax (min and max).
                (x - min) / (max - min)
    by: str / list, optional
        vDataColumns used in the partition.
    return_trans: bool, optimal
        If set to True, the method will return the transformation used instead of
        the parent vDataFrame. This parameter is used for testing purpose.

    Returns
    -------
    vDataFrame
        self.parent

    See Also
    --------
    vDataFrame.outliers : Computes the vDataFrame Global Outliers.
        """
        if isinstance(by, str):
            by = [by]
        method = method.lower()
        by = self.parent.format_colnames(by)
        nullifzero, n = 1, len(by)
        if self.isbool():

            warning_message = "Normalize doesn't work on booleans"
            warnings.warn(warning_message, Warning)

        elif self.isnum():

            if method == "zscore":

                if n == 0:
                    nullifzero = 0
                    avg, stddev = self.aggregate(["avg", "std"]).values[self.alias]
                    if stddev == 0:
                        warning_message = (
                            f"Can not normalize {self.alias} using a "
                            "Z-Score - The Standard Deviation is null !"
                        )
                        warnings.warn(warning_message, Warning)
                        return self
                elif (n == 1) and (self.parent[by[0]].nunique() < 50):
                    try:
                        result = _executeSQL(
                            query=f"""
                                SELECT 
                                    /*+LABEL('vDataColumn.normalize')*/ {by[0]}, 
                                    AVG({self.alias}), 
                                    STDDEV({self.alias}) 
                                FROM {self.parent.__genSQL__()} GROUP BY {by[0]}""",
                            title="Computing the different categories to normalize.",
                            method="fetchall",
                            sql_push_ext=self.parent._VERTICAPY_VARIABLES_[
                                "sql_push_ext"
                            ],
                            symbol=self.parent._VERTICAPY_VARIABLES_["symbol"],
                        )
                        for i in range(len(result)):
                            if result[i][2] == None:
                                pass
                            elif math.isnan(result[i][2]):
                                result[i][2] = None
                        avg_stddev = []
                        for i in range(1, 3):
                            if x[0] != None:
                                x0 = f"""'{str(x[0]).replace("'", "''")}'"""
                            else:
                                x0 = "NULL"
                            x_tmp = [
                                f"""{x0}, {x[i] if x[i] != None else "NULL"}"""
                                for x in result
                                if x[i] != None
                            ]
                            avg_stddev += [
                                f"""DECODE({by[0]}, {", ".join(x_tmp)}, NULL)"""
                            ]
                        avg, stddev = avg_stddev
                        _executeSQL(
                            query=f"""
                                SELECT 
                                    /*+LABEL('vDataColumn.normalize')*/ 
                                    {avg},
                                    {stddev} 
                                FROM {self.parent.__genSQL__()} 
                                LIMIT 1""",
                            print_time_sql=False,
                            sql_push_ext=self.parent._VERTICAPY_VARIABLES_[
                                "sql_push_ext"
                            ],
                            symbol=self.parent._VERTICAPY_VARIABLES_["symbol"],
                        )
                    except:
                        avg, stddev = (
                            f"AVG({self.alias}) OVER (PARTITION BY {', '.join(by)})",
                            f"STDDEV({self.alias}) OVER (PARTITION BY {', '.join(by)})",
                        )
                else:
                    avg, stddev = (
                        f"AVG({self.alias}) OVER (PARTITION BY {', '.join(by)})",
                        f"STDDEV({self.alias}) OVER (PARTITION BY {', '.join(by)})",
                    )
                nullifzero = "NULLIFZERO" if (nullifzero) else ""
                if return_trans:
                    return f"({self.alias} - {avg}) / {nullifzero}({stddev})"
                else:
                    final_transformation = [
                        (f"({{}} - {avg}) / {nullifzero}({stddev})", "float", "float",)
                    ]

            elif method == "robust_zscore":

                if n > 0:
                    warning_message = (
                        "The method 'robust_zscore' is available only if the "
                        "parameter 'by' is empty\nIf you want to normalize by "
                        "grouping by elements, please use a method in zscore|minmax"
                    )
                    warnings.warn(warning_message, Warning)
                    return self
                mad, med = self.aggregate(["mad", "approx_median"]).values[self.alias]
                mad *= 1.4826
                if mad != 0:
                    if return_trans:
                        return f"({self.alias} - {med}) / ({mad})"
                    else:
                        final_transformation = [
                            (f"({{}} - {med}) / ({mad})", "float", "float",)
                        ]
                else:
                    warning_message = (
                        f"Can not normalize {self.alias} using a "
                        "Robust Z-Score - The MAD is null !"
                    )
                    warnings.warn(warning_message, Warning)
                    return self

            elif method == "minmax":

                if n == 0:
                    nullifzero = 0
                    cmin, cmax = self.aggregate(["min", "max"]).values[self.alias]
                    if cmax - cmin == 0:
                        warning_message = (
                            f"Can not normalize {self.alias} using "
                            "the MIN and the MAX. MAX = MIN !"
                        )
                        warnings.warn(warning_message, Warning)
                        return self
                elif n == 1:
                    try:
                        result = _executeSQL(
                            query=f"""
                                SELECT 
                                    /*+LABEL('vDataColumn.normalize')*/ {by[0]}, 
                                    MIN({self.alias}), 
                                    MAX({self.alias})
                                FROM {self.parent.__genSQL__()} 
                                GROUP BY {by[0]}""",
                            title=f"Computing the different categories {by[0]} to normalize.",
                            method="fetchall",
                            sql_push_ext=self.parent._VERTICAPY_VARIABLES_[
                                "sql_push_ext"
                            ],
                            symbol=self.parent._VERTICAPY_VARIABLES_["symbol"],
                        )
                        cmin_cmax = []
                        for i in range(1, 3):
                            if x[0] != None:
                                x0 = f"""'{str(x[0]).replace("'", "''")}'"""
                            else:
                                x0 = "NULL"
                            x_tmp = [
                                f"""{x0}, {x[i] if x[i] != None else "NULL"}"""
                                for x in result
                                if x[i] != None
                            ]
                            cmin_cmax += [
                                f"""DECODE({by[0]}, {", ".join(x_tmp)}, NULL)"""
                            ]
                        cmin, cmax = cmin_cmax
                        _executeSQL(
                            query=f"""
                                SELECT 
                                    /*+LABEL('vDataColumn.normalize')*/ 
                                    {cmin_cmax[1]}, 
                                    {cmin_cmax[0]} 
                                FROM {self.parent.__genSQL__()} 
                                LIMIT 1""",
                            print_time_sql=False,
                            sql_push_ext=self.parent._VERTICAPY_VARIABLES_[
                                "sql_push_ext"
                            ],
                            symbol=self.parent._VERTICAPY_VARIABLES_["symbol"],
                        )
                    except:
                        cmax, cmin = (
                            f"MAX({self.alias}) OVER (PARTITION BY {', '.join(by)})",
                            f"MIN({self.alias}) OVER (PARTITION BY {', '.join(by)})",
                        )
                else:
                    cmax, cmin = (
                        f"MAX({self.alias}) OVER (PARTITION BY {', '.join(by)})",
                        f"MIN({self.alias}) OVER (PARTITION BY {', '.join(by)})",
                    )
                nullifzero = "NULLIFZERO" if (nullifzero) else ""
                if return_trans:
                    return f"({self.alias} - {cmin}) / {nullifzero}({cmax} - {cmin})"
                else:
                    final_transformation = [
                        (
                            f"({{}} - {cmin}) / {nullifzero}({cmax} - {cmin})",
                            "float",
                            "float",
                        )
                    ]

            if method != "robust_zscore":
                max_floor = 0
                for elem in by:
                    if len(self.parent[elem].transformations) > max_floor:
                        max_floor = len(self.parent[elem].transformations)
                max_floor -= len(self.transformations)
                for k in range(max_floor):
                    self.transformations += [("{}", self.ctype(), self.category())]
            self.transformations += final_transformation
            sauv = {}
            for elem in self.catalog:
                sauv[elem] = self.catalog[elem]
            self.parent.__update_catalog__(erase=True, columns=[self.alias])
            try:

                if "count" in sauv:
                    self.catalog["count"] = sauv["count"]
                    self.catalog["percent"] = (
                        100 * sauv["count"] / self.parent.shape()[0]
                    )

                for elem in sauv:

                    if "top" in elem:

                        if "percent" in elem:
                            self.catalog[elem] = sauv[elem]
                        elif elem == None:
                            self.catalog[elem] = None
                        elif method == "robust_zscore":
                            self.catalog[elem] = (sauv[elem] - sauv["approx_50%"]) / (
                                1.4826 * sauv["mad"]
                            )
                        elif method == "zscore":
                            self.catalog[elem] = (sauv[elem] - sauv["mean"]) / sauv[
                                "std"
                            ]
                        elif method == "minmax":
                            self.catalog[elem] = (sauv[elem] - sauv["min"]) / (
                                sauv["max"] - sauv["min"]
                            )

            except:
                pass
            if method == "robust_zscore":
                self.catalog["median"] = 0
                self.catalog["mad"] = 1 / 1.4826
            elif method == "zscore":
                self.catalog["mean"] = 0
                self.catalog["std"] = 1
            elif method == "minmax":
                self.catalog["min"] = 0
                self.catalog["max"] = 1
            self.parent.__add_to_history__(
                f"[Normalize]: The vDataColumn '{self.alias}' was "
                f"normalized with the method '{method}'."
            )
        else:
            raise TypeError("The vDataColumn must be numerical for Normalization")
        return self.parent