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
import math, warnings
from typing import Literal, Optional, TYPE_CHECKING

from matplotlib.axes import Axes
import matplotlib.pyplot as plt

from verticapy._typing import SQLColumns
from verticapy._utils._sql._sys import _executeSQL

if TYPE_CHECKING:
    from verticapy.core.vdataframe.base import vDataFrame

from verticapy.plotting._matplotlib.base import MatplotlibBase


class BoxPlot(MatplotlibBase):
    @property
    def _category(self) -> Literal["plot"]:
        return "plot"

    @property
    def _kind(self) -> Literal["box"]:
        return "box"

    def draw(
        self,
        vdf: "vDataFrame",
        by: str = "",
        h: float = 0.0,
        max_cardinality: int = 8,
        cat_priority: list = [],
        ax: Optional[Axes] = None,
        **style_kwargs,
    ) -> Axes:
        """
        Draws a box plot using the Matplotlib API.
        """
        colors = []
        if "color" in style_kwargs:
            if isinstance(style_kwargs["color"], str):
                colors = [style_kwargs["color"]]
            else:
                colors = style_kwargs["color"]
            del style_kwargs["color"]
        elif "colors" in style_kwargs:
            if isinstance(style_kwargs["colors"], str):
                colors = [style_kwargs["colors"]]
            else:
                colors = style_kwargs["colors"]
            del style_kwargs["colors"]
        colors += self.get_colors()
        # SINGLE BOXPLOT
        if by == "":
            ax, fig = self._get_ax_fig(ax, size=(6, 4), set_axis_below=False, grid="x")
            if not (vdf.isnum()):
                raise TypeError(
                    "The column must be numerical in order to draw a boxplot"
                )
            summarize = (
                vdf._parent.describe(
                    method="numerical", columns=[vdf._alias], unique=False
                )
                .transpose()
                .values[vdf._alias]
            )
            for i in range(0, 2):
                del summarize[0]
            ax.set_xlabel(vdf._alias)
            box = ax.boxplot(
                summarize,
                notch=False,
                sym="",
                whis=float("Inf"),
                vert=False,
                widths=0.7,
                labels=[""],
                patch_artist=True,
                **style_kwargs,
            )
            for median in box["medians"]:
                median.set(color="black", linewidth=1)
            for patch in box["boxes"]:
                patch.set_facecolor(colors[0])
            ax.set_axisbelow(True)
            return ax
        # MULTI BOXPLOT
        else:
            try:
                try:
                    by = vdf._format_colnames(by)
                except:
                    by = vdf._parent._format_colnames(by)
                if vdf._alias == by:
                    raise NameError(
                        "The parameter 'column' and the parameter 'groupby' can not be the same"
                    )
                count = vdf._parent.shape()[0]
                is_numeric = vdf._parent[by].isnum()
                is_categorical = (
                    vdf._parent[by].nunique(True) <= max_cardinality
                ) or not (is_numeric)
                table = vdf._parent._genSQL()
                if not (is_categorical):
                    enum_trans = (
                        vdf._parent[by]
                        .discretize(h=h, return_enum_trans=True)[0]
                        .replace("{}", by)
                        + " AS "
                        + by
                    )
                    enum_trans += f", {vdf._alias}"
                    table = f"(SELECT {enum_trans} FROM {table}) enum_table"
                if not (cat_priority):
                    query_result = _executeSQL(
                        query=f"""
                            SELECT 
                                /*+LABEL('plotting._matplotlib.boxplot')*/ 
                                {by} 
                            FROM {table} 
                            WHERE {vdf._alias} IS NOT NULL 
                            GROUP BY {by} 
                            ORDER BY COUNT(*) DESC 
                            LIMIT {max_cardinality}""",
                        title=f"Computing the categories of {by}",
                        method="fetchall",
                    )
                    cat_priority = [
                        item for sublist in query_result for item in sublist
                    ]
                with_summarize = False
                all_queries = []
                lp = "(" if (len(cat_priority) == 1) else ""
                rp = ")" if (len(cat_priority) == 1) else ""
                for idx, category in enumerate(cat_priority):
                    if category in ("None", None):
                        where = f"WHERE {by} IS NULL"
                    else:
                        category_str = str(category).replace("'", "''")
                        where = f"WHERE {by} = '{category_str}'"
                    tmp_query = f"""
                        SELECT 
                            MIN({vdf._alias}) AS min,
                            APPROXIMATE_PERCENTILE ({vdf._alias} 
                                   USING PARAMETERS percentile = 0.25) AS Q1,
                            APPROXIMATE_PERCENTILE ({vdf._alias} 
                                   USING PARAMETERS percentile = 0.5) AS Median, 
                            APPROXIMATE_PERCENTILE ({vdf._alias} 
                                   USING PARAMETERS percentile = 0.75) AS Q3, 
                            MAX({vdf._alias}) AS max, '{category}' 
                        FROM vdf_table
                        {where}"""
                    all_queries += [tmp_query]
                main_table = f"WITH vdf_table AS (SELECT /*+LABEL('plotting._matplotlib.boxplot')*/ * FROM {table})"
                query = f"""{main_table}{" UNION ALL ".join([lp + q + rp for q in all_queries])}"""
                try:
                    query_result = _executeSQL(
                        query=query,
                        title=(
                            "Computing all the descriptive statistics for each "
                            "category to draw the box plot"
                        ),
                        method="fetchall",
                    )
                except:
                    query_result = []
                    for q in enumerate(all_queries):
                        query_result += [
                            _executeSQL(
                                query=f"{main_table} {q}",
                                title=(
                                    "Computing all the descriptive statistics for "
                                    "each category to draw the box plot, one at a time"
                                ),
                                method="fetchrow",
                            )
                        ]
                cat_priority = [item[-1] for item in query_result]
                result = [
                    [float(item[i]) for i in range(0, 5)] for item in query_result
                ]
                result.reverse()
                cat_priority.reverse()
                if vdf._parent[by].category() == "text":
                    labels = []
                    for item in cat_priority:
                        labels += (
                            [item[0:47] + "..."] if (len(str(item)) > 50) else [item]
                        )
                else:
                    labels = cat_priority
                ax, fig = self._get_ax_fig(
                    ax, size=(10, 6), set_axis_below=True, grid="y"
                )
                ax.set_ylabel(vdf._alias)
                ax.set_xlabel(by)
                other_labels = []
                other_result = []
                all_idx = []
                if not (is_categorical):
                    for idx, item in enumerate(labels):
                        try:
                            math.floor(int(item))
                        except:
                            try:
                                math.floor(float(item))
                            except:
                                try:
                                    math.floor(float(labels[idx][1:-1].split(";")[0]))
                                except:
                                    other_labels += [labels[idx]]
                                    other_result += [result[idx]]
                                    all_idx += [idx]
                    for idx in all_idx:
                        del labels[idx]
                        del result[idx]
                if not (is_categorical):
                    sorted_boxplot = sorted(
                        [
                            [float(labels[i][1:-1].split(";")[0]), labels[i], result[i]]
                            for i in range(len(labels))
                        ]
                    )
                    labels, result = (
                        [item[1] for item in sorted_boxplot] + other_labels,
                        [item[2] for item in sorted_boxplot] + other_result,
                    )
                else:
                    sorted_boxplot = sorted(
                        [(labels[i], result[i]) for i in range(len(labels))]
                    )
                    labels, result = (
                        [item[0] for item in sorted_boxplot],
                        [item[1] for item in sorted_boxplot],
                    )
                box = ax.boxplot(
                    result,
                    notch=False,
                    sym="",
                    whis=float("Inf"),
                    widths=0.5,
                    labels=labels,
                    patch_artist=True,
                    **style_kwargs,
                )
                ax.set_xticklabels(labels, rotation=90)
                for median in box["medians"]:
                    median.set(
                        color="black", linewidth=1,
                    )
                for patch, color in zip(box["boxes"], colors):
                    patch.set_facecolor(color)
                return ax
            except Exception as e:
                raise Exception(f"{e}\nAn error occured during the BoxPlot creation.")


class MultiBoxPlot(MatplotlibBase):
    @property
    def _category(self) -> Literal["plot"]:
        return "plot"

    @property
    def _kind(self) -> Literal["box"]:
        return "box"

    def draw(
        self,
        vdf: "vDataFrame",
        columns: SQLColumns = [],
        ax: Optional[Axes] = None,
        **style_kwargs,
    ) -> Axes:
        """
        Draws a multi box plot using the Matplotlib API.
        """
        if isinstance(columns, str):
            columns = [columns]
        colors = []
        if "color" in style_kwargs:
            if isinstance(style_kwargs["color"], str):
                colors = [style_kwargs["color"]]
            else:
                colors = style_kwargs["color"]
            del style_kwargs["color"]
        elif "colors" in style_kwargs:
            if isinstance(style_kwargs["colors"], str):
                colors = [style_kwargs["colors"]]
            else:
                colors = style_kwargs["colors"]
            del style_kwargs["colors"]
        colors += self.get_colors()
        if not (columns):
            columns = vdf.numcol()
        for column in columns:
            if column not in vdf.numcol():
                if vdf._vars["display"]["print_info"]:
                    warning_message = f"The Virtual Column {column} is not numerical.\nIt will be ignored."
                    warnings.warn(warning_message, Warning)
                columns.remove(column)
        if not (columns):
            raise MissingColumn("No numerical columns found to draw the multi boxplot")
        # SINGLE BOXPLOT
        if len(columns) == 1:
            vdf[columns[0]].boxplot(
                ax=ax, **style_kwargs,
            )
        # MULTI BOXPLOT
        else:
            try:
                summarize = vdf.describe(columns=columns).transpose()
                result = [summarize.values[column][3:8] for column in summarize.values]
                columns = [column for column in summarize.values]
                del columns[0]
                del result[0]
                ax, fig = self._get_ax_fig(
                    ax, size=(10, 6), set_axis_below=False, grid=False
                )
                box = ax.boxplot(
                    result,
                    notch=False,
                    sym="",
                    whis=float("Inf"),
                    widths=0.5,
                    labels=columns,
                    patch_artist=True,
                    **style_kwargs,
                )
                ax.set_xticklabels(columns, rotation=90)
                for median in box["medians"]:
                    median.set(
                        color="black", linewidth=1,
                    )
                for patch, color in zip(box["boxes"], colors):
                    patch.set_facecolor(color)
                return ax
            except Exception as e:
                raise Exception(f"{e}\nAn error occured during the BoxPlot creation.")
