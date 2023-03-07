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
import math
from typing import Optional, TYPE_CHECKING

from matplotlib.axes import Axes
import matplotlib.pyplot as plt

from verticapy._config.colors import get_colors
from verticapy._typing import SQLColumns
from verticapy.errors import ParameterError

if TYPE_CHECKING:
    from verticapy.core.vdataframe.base import vDataFrame

from verticapy.plotting.base import PlottingBase


class SpiderPlot(PlottingBase):
    def spider(
        self,
        vdf: "vDataFrame",
        columns: SQLColumns,
        method: str = "density",
        of: str = "",
        max_cardinality: tuple[int, int] = (6, 6),
        h: tuple[Optional[float], Optional[float]] = (None, None),
        ax: Optional[Axes] = None,
        **style_kwds,
    ) -> Axes:
        """
        Draws a spider plot using the Matplotlib API.
        """
        if isinstance(columns, str):
            columns = [columns]
        unique = vdf[columns[0]].nunique(True)
        if unique < 3:
            raise ParameterError(
                "The first column of the Spider Plot must have at "
                f"least 3 categories. Found {int(unique)}."
            )
        colors = get_colors()
        all_columns = vdf.pivot_table(
            columns,
            method=method,
            of=of,
            h=h,
            max_cardinality=max_cardinality,
            show=False,
        ).values
        all_cat = [category for category in all_columns]
        n = len(all_columns)
        m = len(all_columns[all_cat[0]])
        angles = [i / float(m) * 2 * math.pi for i in range(m)]
        angles += angles[:1]
        categories = all_columns[all_cat[0]]
        fig = plt.figure()
        if not (ax):
            ax = fig.add_subplot(111, polar=True)
        all_vals = []
        for idx, category in enumerate(all_columns):
            if idx != 0:
                values = all_columns[category]
                values += values[:1]
                for i, v in enumerate(values):
                    if isinstance(v, str) or v == None:
                        values[i] = 0
                    else:
                        values[i] = float(v)
                all_vals += values
                plt.xticks(angles[:-1], categories, color="grey", size=8)
                ax.set_rlabel_position(0)
                param = {"linewidth": 1, "linestyle": "solid", "color": colors[idx - 1]}
                ax.plot(
                    angles,
                    values,
                    label=category,
                    **self.updated_dict(param, style_kwds, idx - 1),
                )
                color = self.updated_dict(param, style_kwds, idx - 1)["color"]
                ax.fill(angles, values, alpha=0.1, color=color)
        ax.set_yticks(
            [min(all_vals), (max(all_vals) + min(all_vals)) / 2, max(all_vals)]
        )
        ax.set_rgrids(
            [min(all_vals), (max(all_vals) + min(all_vals)) / 2, max(all_vals)],
            angle=180.0,
            fmt="%0.1f",
        )
        ax.set_xlabel(columns[0])
        if method.lower() == "mean":
            method = "avg"
        if method.lower() == "density":
            ax.set_ylabel("Density")
        elif (method.lower() in ["avg", "min", "max", "sum"]) and (of != None):
            ax.set_ylabel(f"{method}({of})")
        elif method.lower() == "count":
            ax.set_ylabel("Frequency")
        else:
            ax.set_ylabel(method)
        if len(columns) > 1:
            ax.legend(
                title=columns[1], loc="center left", bbox_to_anchor=[1.1, 0.5],
            )
            box = ax.get_position()
            ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
        return ax
