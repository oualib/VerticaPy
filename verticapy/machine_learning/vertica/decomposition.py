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
# VerticaPy Modules
from verticapy.utils._decorators import (
    save_verticapy_logs,
    check_minimum_version,
)
from verticapy.utilities import *
from verticapy.utils._toolbox import *
from verticapy.learn.vmodel import *

# Standard Module
from typing import Literal


class MCA(Decomposition):
    """
Creates a MCA (multiple correspondence analysis) object using the Vertica 
PCA algorithm on the data. It uses the property that the MCA is a PCA 
applied to a complete disjunctive table. The input relation is transformed 
to a TCDT (transformed complete disjunctive table) before applying the PCA.
 
Parameters
----------
name: str
    Name of the the model. The model will be stored in the database.
    """

    @check_minimum_version
    @save_verticapy_logs
    def __init__(self, name: str):
        self.type, self.name = "MCA", name
        self.VERTICA_FIT_FUNCTION_SQL = "PCA"
        self.VERTICA_TRANSFORM_FUNCTION_SQL = "APPLY_PCA"
        self.MODEL_TYPE = "UNSUPERVISED"
        self.MODEL_SUBTYPE = "DECOMPOSITION"
        self.VERTICA_INVERSE_TRANSFORM_FUNCTION_SQL = "APPLY_INVERSE_PCA"
        self.parameters = {}

    def plot_var(
        self,
        dimensions: tuple = (1, 2),
        method: Literal["auto", "cos2", "contrib"] = "auto",
        ax=None,
        **style_kwds,
    ):
        """
    Draws the MCA (multiple correspondence analysis) graph.

    Parameters
    ----------
    dimensions: tuple, optional
        Tuple of two IDs of the model's components.
    method: str, optional
        Method used to draw the plot.
            auto   : Only the variables are displayed.
            cos2   : The cos2 is used as CMAP.
            contrib: The feature contribution is used as CMAP.
    ax: Matplotlib axes object, optional
        The axes to plot on.
    **style_kwds
        Any optional parameter to pass to the Matplotlib functions.

    Returns
    -------
    ax
        Matplotlib axes object
        """
        x = self.components_[f"PC{dimensions[0]}"]
        y = self.components_[f"PC{dimensions[1]}"]
        n = len(self.cos2_[f"PC{dimensions[0]}"])
        if method in ("cos2", "contrib"):
            if method == "cos2":
                c = [
                    self.cos2_[f"PC{dimensions[0]}"][i]
                    + self.cos2_[f"PC{dimensions[1]}"][i]
                    for i in range(n)
                ]
            else:
                sum_1, sum_2 = (
                    sum(self.cos2_[f"PC{dimensions[0]}"]),
                    sum(self.cos2_[f"PC{dimensions[1]}"]),
                )
                c = [
                    0.5
                    * 100
                    * (
                        self.cos2_[f"PC{dimensions[0]}"][i] / sum_1
                        + self.cos2_[f"PC{dimensions[1]}"][i] / sum_2
                    )
                    for i in range(n)
                ]
            style_kwds["c"] = c
            if "cmap" not in style_kwds:
                from verticapy.plotting._colors import gen_colors, gen_cmap

                style_kwds["cmap"] = gen_cmap(
                    color=[gen_colors()[0], gen_colors()[1], gen_colors()[2]]
                )
        explained_variance = self.explained_variance_["explained_variance"]
        return plot_var(
            x,
            y,
            self.X,
            (
                explained_variance[dimensions[0] - 1],
                explained_variance[dimensions[1] - 1],
            ),
            dimensions,
            method,
            ax,
            **style_kwds,
        )

    def plot_contrib(self, dimension: int = 1, ax=None, **style_kwds):
        """
    Draws a decomposition contribution plot of the input dimension.

    Parameters
    ----------
    dimension: int, optional
        Integer representing the IDs of the model's component.
    ax: Matplotlib axes object, optional
        The axes to plot on.
    **style_kwds
        Any optional parameter to pass to the Matplotlib functions.

    Returns
    -------
    ax
        Matplotlib axes object
        """
        contrib = self.components_[f"PC{dimension}"]
        contrib = [elem ** 2 for elem in contrib]
        total = sum(contrib)
        contrib = [100 * elem / total for elem in contrib]
        n = len(contrib)
        variables, contribution = zip(
            *sorted(zip(self.X, contrib), key=lambda t: t[1], reverse=True)
        )
        contrib = tablesample(
            {"row_nb": [i + 1 for i in range(n)], "contrib": contribution}
        ).to_vdf()
        contrib["row_nb_2"] = contrib["row_nb"] + 0.5
        ax = contrib["row_nb"].hist(
            method="avg", of="contrib", max_cardinality=1, h=1, ax=ax, **style_kwds
        )
        ax = contrib["contrib"].plot(ts="row_nb_2", ax=ax, color="black")
        ax.set_xlim(1, n + 1)
        ax.set_xticks([i + 1.5 for i in range(n)])
        ax.set_xticklabels(variables)
        ax.set_ylabel("Cos2 - Quality of Representation")
        ax.set_xlabel("")
        ax.set_title(f"Contribution of variables to Dim {dimension}")
        ax.plot([1, n + 1], [1 / n * 100, 1 / n * 100], c="r", linestyle="--")
        for i in range(n):
            ax.text(
                i + 1.5, contribution[i] + 1, f"{round(contribution[i], 1)}%",
            )
        return ax

    def plot_cos2(self, dimensions: tuple = (1, 2), ax=None, **style_kwds):
        """
    Draws a MCA (multiple correspondence analysis) cos2 plot of 
    the two input dimensions.

    Parameters
    ----------
    dimensions: tuple, optional
        Tuple of two IDs of the model's components.
    ax: Matplotlib axes object, optional
        The axes to plot on.
    **style_kwds
        Any optional parameter to pass to the Matplotlib functions.

    Returns
    -------
    ax
        Matplotlib axes object
        """
        cos2_1 = self.cos2_[f"PC{dimensions[0]}"]
        cos2_2 = self.cos2_[f"PC{dimensions[1]}"]
        n = len(cos2_1)
        quality = []
        for i in range(n):
            quality += [cos2_1[i] + cos2_2[i]]
        variables, quality = zip(
            *sorted(zip(self.X, quality), key=lambda t: t[1], reverse=True)
        )
        quality = tablesample({"variables": variables, "quality": quality}).to_vdf()
        ax = quality["variables"].hist(
            method="avg", of="quality", max_cardinality=n, ax=ax, **style_kwds
        )
        ax.set_ylabel("Cos2 - Quality of Representation")
        ax.set_xlabel("")
        ax.set_title(f"Cos2 of variables to Dim {dimensions[0]}-{dimensions[1]}")
        return ax


class PCA(Decomposition):
    """
Creates a PCA (Principal Component Analysis) object using the Vertica PCA
algorithm on the data.
 
Parameters
----------
name: str
	Name of the the model. The model will be stored in the DB.
n_components: int, optional
	The number of components to keep in the model. If this value is not 
    provided, all components are kept. The maximum number of components 
    is the number of non-zero singular values returned by the internal 
    call to SVD. This number is less than or equal to SVD (number of 
    columns, number of rows). 
scale: bool, optional
	A Boolean value that specifies whether to standardize the columns 
    during the preparation step.
method: str, optional
	The method to use to calculate PCA.
		lapack: Lapack definition.
	"""

    @check_minimum_version
    @save_verticapy_logs
    def __init__(
        self,
        name: str,
        n_components: int = 0,
        scale: bool = False,
        method: Literal["lapack"] = "lapack",
    ):
        self.type, self.name = "PCA", name
        self.VERTICA_FIT_FUNCTION_SQL = "PCA"
        self.VERTICA_TRANSFORM_FUNCTION_SQL = "APPLY_PCA"
        self.VERTICA_INVERSE_TRANSFORM_FUNCTION_SQL = "APPLY_INVERSE_PCA"
        self.MODEL_TYPE = "UNSUPERVISED"
        self.MODEL_SUBTYPE = "DECOMPOSITION"
        self.parameters = {
            "n_components": n_components,
            "scale": scale,
            "method": str(method).lower(),
        }


class SVD(Decomposition):
    """
Creates an SVD (Singular Value Decomposition) object using the Vertica SVD
algorithm on the data.
 
Parameters
----------
name: str
	Name of the the model. The model will be stored in the DB.
n_components: int, optional
	The number of components to keep in the model. If this value is not 
    provided, all components are kept. The maximum number of components 
    is the number of non-zero singular values returned by the internal 
    call to SVD. This number is less than or equal to SVD (number of 
    columns, number of rows).
method: str, optional
	The method to use to calculate SVD.
		lapack: Lapack definition.
	"""

    @check_minimum_version
    @save_verticapy_logs
    def __init__(
        self, name: str, n_components: int = 0, method: Literal["lapack"] = "lapack"
    ):
        self.type, self.name = "SVD", name
        self.VERTICA_FIT_FUNCTION_SQL = "SVD"
        self.VERTICA_TRANSFORM_FUNCTION_SQL = "APPLY_SVD"
        self.VERTICA_INVERSE_TRANSFORM_FUNCTION_SQL = "APPLY_INVERSE_SVD"
        self.MODEL_TYPE = "UNSUPERVISED"
        self.MODEL_SUBTYPE = "DECOMPOSITION"
        self.parameters = {
            "n_components": n_components,
            "method": str(method).lower(),
        }