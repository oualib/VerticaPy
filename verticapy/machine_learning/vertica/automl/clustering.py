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
from typing import Union
from tqdm.auto import tqdm

from verticapy._config.config import OPTIONS
from verticapy._utils._collect import save_verticapy_logs

from verticapy.core.vdataframe.base import vDataFrame

from verticapy.machine_learning.vertica.base import vModel
from verticapy.machine_learning.vertica.cluster import KMeans, KPrototypes
from verticapy.machine_learning.model_selection import best_k


class AutoClustering(vModel):
    """
Automatically creates k different groups with which to generalize the data.

Parameters
----------
name: str
    Name of the model.
n_cluster: int, optional
    Number of clusters. If empty, an optimal number of clusters will be
    determined using multiple k-means models.
init: str / list, optional
    The method for finding the initial cluster centers.
        kmeanspp : Uses the k-means++ method to initialize the centers.
                   [Only available when use_kprototype is set to False]
        random   : Randomly subsamples the data to find initial centers.
    Alternatively, you can specify a list with the initial custer centers.
max_iter: int, optional
    The maximum number of iterations for the algorithm.
tol: float, optional
    Determines whether the algorithm has converged. The algorithm is considered 
    converged after no center has moved more than a distance of 'tol' from the 
    previous iteration.
use_kprototype: bool, optional
    If set to True, the function uses the k-prototypes algorithm instead of
    k-means. k-prototypes can handle categorical features.
gamma: float, optional
    [Only if use_kprototype is set to True] Weighting factor for categorical columns. 
    It determines the relative importance of numerical and categorical attributes.
preprocess_data: bool, optional
    If True, the data will be preprocessed.
preprocess_dict: dict, optional
    Dictionary to pass to the AutoDataPrep class in order to 
    preprocess the data before the clustering.
print_info: bool
    If True, prints the model information at each step.

Attributes
----------
preprocess_: object
    Model used to preprocess the data.
model_: object
    Final model used for the clustering.
    """

    @save_verticapy_logs
    def __init__(
        self,
        name: str,
        n_cluster: int = None,
        init: Union[str, list] = "kmeanspp",
        max_iter: int = 300,
        tol: float = 1e-4,
        use_kprototype: bool = False,
        gamma: float = 1.0,
        preprocess_data: bool = True,
        preprocess_dict: dict = {
            "identify_ts": False,
            "normalize_min_cat": 0,
            "outliers_threshold": 3.0,
            "na_method": "drop",
        },
        print_info: bool = True,
    ):
        self.type, self.name = "AutoClustering", name
        self.parameters = {
            "n_cluster": n_cluster,
            "init": init,
            "max_iter": max_iter,
            "tol": tol,
            "use_kprototype": use_kprototype,
            "gamma": gamma,
            "print_info": print_info,
            "preprocess_data": preprocess_data,
            "preprocess_dict": preprocess_dict,
        }

    def fit(self, input_relation: Union[str, vDataFrame], X: list = []):
        """
    Trains the model.

    Parameters
    ----------
    input_relation: str/vDataFrame
        Training Relation.
    X: list, optional
        List of the predictors.

    Returns
    -------
    object
        clustering model
        """
        if OPTIONS["overwrite_model"]:
            self.drop()
        else:
            does_model_exist(name=self.name, raise_error=True)
        if self.parameters["print_info"]:
            print(f"\033[1m\033[4mStarting AutoClustering\033[0m\033[0m\n")
        if self.parameters["preprocess_data"]:
            model_preprocess = AutoDataPrep(**self.parameters["preprocess_dict"])
            input_relation = model_preprocess.fit(input_relation, X=X)
            X = [elem for elem in model_preprocess.X_out]
            self.preprocess_ = model_preprocess
        else:
            self.preprocess_ = None
        if not (self.parameters["n_cluster"]):
            if self.parameters["print_info"]:
                print(
                    f"\033[1m\033[4mFinding a suitable number of clusters\033[0m\033[0m\n"
                )
            self.parameters["n_cluster"] = best_k(
                input_relation=input_relation,
                X=X,
                n_cluster=(1, 100),
                init=self.parameters["init"],
                max_iter=self.parameters["max_iter"],
                tol=self.parameters["tol"],
                use_kprototype=self.parameters["use_kprototype"],
                gamma=self.parameters["gamma"],
                elbow_score_stop=0.9,
                tqdm=self.parameters["print_info"],
            )
        if self.parameters["print_info"]:
            print(f"\033[1m\033[4mBuilding the Final Model\033[0m\033[0m\n")
        if OPTIONS["tqdm"] and self.parameters["print_info"]:
            loop = tqdm(range(1))
        else:
            loop = range(1)
        for i in loop:
            if self.parameters["use_kprototype"]:
                self.model_ = KPrototypes(
                    self.name,
                    n_cluster=self.parameters["n_cluster"],
                    init=self.parameters["init"],
                    max_iter=self.parameters["max_iter"],
                    tol=self.parameters["tol"],
                    gamma=self.parameters["gamma"],
                )
            else:
                self.model_ = KMeans(
                    self.name,
                    n_cluster=self.parameters["n_cluster"],
                    init=self.parameters["init"],
                    max_iter=self.parameters["max_iter"],
                    tol=self.parameters["tol"],
                )
            self.model_.fit(input_relation, X=X)
        return self.model_