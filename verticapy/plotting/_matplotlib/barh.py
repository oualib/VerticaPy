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
from typing import Optional, TYPE_CHECKING
import numpy as np

from matplotlib.axes import Axes
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from verticapy._config.colors import get_colors
import verticapy._config.config as conf
from verticapy._typing import SQLColumns
from verticapy.errors import ParameterError

if TYPE_CHECKING:
    from verticapy.core.vdataframe.base import vDataFrame

from verticapy.plotting.base import PlottingBase


class HorizontalBarChart(PlottingBase):
    def barh(
        self,
        vdf: "vDataFrame",
        method: str = "density",
        of: Optional[str] = None,
        max_cardinality: int = 6,
        nbins: int = 0,
        h: float = 0.0,
        ax: Optional[Axes] = None,
        **style_kwds,
    ) -> Axes:
        """
        Draws a bar chart using the Matplotlib API.
        """
        x, y, z, h, is_categorical = self._compute_plot_params(
            vdf, method=method, of=of, max_cardinality=max_cardinality, nbins=nbins, h=h
        )
        if not (ax):
            fig, ax = plt.subplots()
            if conf._get_import_success("jupyter"):
                fig.set_size_inches(10, min(int(len(x) / 1.8) + 1, 600))
            ax.xaxis.grid()
            ax.set_axisbelow(True)
        param = {"color": get_colors()[0], "alpha": 0.86}
        ax.barh(x, y, h, **self.updated_dict(param, style_kwds, 0))
        ax.set_ylabel(vdf._alias)
        if is_categorical:
            if vdf.category() == "text":
                new_z = []
                for item in z:
                    new_z += [item[0:47] + "..."] if (len(str(item)) > 50) else [item]
            else:
                new_z = z
            ax.set_yticks(x)
            ax.set_yticklabels(new_z, rotation=0)
        else:
            ax.set_yticks([elem - round(h / 2 / 0.94, 10) for elem in x])
        if method.lower() == "density":
            ax.set_xlabel("Density")
        elif (method.lower() in ["avg", "min", "max", "sum"] or "%" == method[-1]) and (
            of != None
        ):
            aggregate = f"{method.upper()}({of})"
            ax.set_xlabel(aggregate)
        elif method.lower() == "count":
            ax.set_xlabel("Frequency")
        else:
            ax.set_xlabel(method)
        return ax

    def barh2D(
        self,
        vdf: "vDataFrame",
        columns: SQLColumns,
        method: str = "density",
        of: str = "",
        max_cardinality: tuple[int, int] = (6, 6),
        h: tuple[Optional[float], Optional[float]] = (None, None),
        stacked: bool = False,
        fully_stacked: bool = False,
        density: bool = False,
        ax: Optional[Axes] = None,
        **style_kwds,
    ) -> Axes:
        """
        Draws a 2D bar chart using the Matplotlib API.
        """
        colors = get_colors()
        if fully_stacked:
            if method != "density":
                raise ValueError(
                    "Fully Stacked Bar works only with the 'density' method."
                )
        if density:
            if method != "density":
                raise ValueError("Pyramid Bar works only with the 'density' method.")
            unique = vdf.nunique(columns)["approx_unique"]
            if unique[1] != 2 and unique[0] != 2:
                raise ValueError(
                    "One of the 2 columns must have 2 categories to draw a Pyramid Bar."
                )
            if unique[1] != 2:
                columns = [columns[1], columns[0]]
        xlabel = self._map_method(method, of)[0]
        matrix, y_labels, x_labels = self._compute_pivot_table(
            vdf, columns, method=method, of=of, h=h, max_cardinality=max_cardinality,
        )[0:3]
        m, n = matrix.shape
        yticks = [j for j in range(m)]
        bar_height = 0.5
        if not (ax):
            fig, ax = plt.subplots()
            if conf._get_import_success("jupyter"):
                if density:
                    fig.set_size_inches(10, min(m * 3, 600) / 8 + 1)
                else:
                    fig.set_size_inches(10, min(m * 3, 600) / 2 + 1)
            ax.set_axisbelow(True)
            ax.xaxis.grid()
        if fully_stacked:
            for i in range(0, m):
                matrix[i] /= sum(matrix[i])
        for i in range(0, n):
            current_column = matrix[:, i]
            params = {
                "y": [j for j in range(m)],
                "width": matrix[:, i],
                "height": bar_height,
                "label": x_labels[i],
                "alpha": 0.86,
                "color": colors[i % len(colors)],
            }
            params = self.updated_dict(params, style_kwds, i)
            if stacked or fully_stacked:
                if i == 0:
                    last_column = np.array([0.0 for j in range(m)])
                else:
                    last_column += matrix[:, i - 1].astype(float)
                params["left"] = last_column
            elif density:
                if i == 1:
                    current_column = [-j for j in current_column]
                params["width"] = current_column
                params["height"] = bar_height / 1.5
            else:
                params["y"] = [j + i * bar_height / n for j in range(m)]
                params["height"] = bar_height / n
            ax.barh(**params)
        if not (stacked):
            yticks = [j + bar_height / 2 - bar_height / 2 / (n - 1) for j in range(m)]
        ax.set_yticks(yticks)
        ax.set_yticklabels(y_labels)
        ax.set_ylabel(columns[0])
        ax.set_xlabel(xlabel)
        if density or fully_stacked:
            vals = ax.get_xticks()
            max_val = max([abs(x) for x in vals])
            ax.xaxis.set_major_locator(mticker.FixedLocator(vals))
            ax.set_xticklabels(["{:,.2%}".format(abs(x)) for x in vals])
        ax.legend(title=columns[1], loc="center left", bbox_to_anchor=[1, 0.5])
        box = ax.get_position()
        ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
        return ax