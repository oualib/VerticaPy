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
import random, itertools
from typing import Union, Literal

# VerticaPy Modules
from verticapy._utils._collect import save_verticapy_logs
from verticapy.core.vdataframe.vdataframe import vDataFrame
from verticapy.sql.drop import drop
from verticapy.sql.read import vDataFrameSQL
from verticapy.core.tablesample import tablesample
from verticapy._utils._sql import _executeSQL
from verticapy.errors import ParameterError
from verticapy.learn.tools import does_model_exist
from verticapy.machine_learning._utils import reverse_score
from verticapy.plotting._matplotlib import (
    plot_stepwise_ml,
    plot_importance,
)
from verticapy._config.config import OPTIONS
from verticapy.machine_learning.model_selection.model_validation import cross_validate

# Other Python Modules
from tqdm.auto import tqdm


@save_verticapy_logs
def randomized_features_search_cv(
    estimator,
    input_relation: Union[str, vDataFrame],
    X: Union[str, list],
    y: str,
    metric: str = "auto",
    cv: int = 3,
    pos_label: Union[int, float, str] = None,
    cutoff: Union[int, float] = -1,
    training_score: bool = True,
    comb_limit: int = 100,
    skip_error: bool = True,
    print_info: bool = True,
    **kwargs,
):
    """
Computes the k-fold grid search of an estimator using different features
combinations. It can be used to find the parameters which will optimize
the model.

Parameters
----------
estimator: object
    Vertica estimator with a fit method.
input_relation: str/vDataFrame
    Relation to use to train the model.
X: str / list
    List of the predictor columns.
y: str
    Response Column.
metric: str, optional
    Metric used to do the model evaluation.
        auto: logloss for classification & rmse for 
              regression.
    For Classification:
        accuracy    : Accuracy
        auc         : Area Under the Curve (ROC)
        bm          : Informedness 
                      = tpr + tnr - 1
        csi         : Critical Success Index 
                      = tp / (tp + fn + fp)
        f1          : F1 Score 
        logloss     : Log Loss
        mcc         : Matthews Correlation Coefficient 
        mk          : Markedness 
                      = ppv + npv - 1
        npv         : Negative Predictive Value 
                      = tn / (tn + fn)
        prc_auc     : Area Under the Curve (PRC)
        precision   : Precision 
                      = tp / (tp + fp)
        recall      : Recall 
                      = tp / (tp + fn)
        specificity : Specificity 
                      = tn / (tn + fp)
    For Regression:
        max    : Max error
        mae    : Mean absolute error
        median : Median absolute error
        mse    : Mean squared error
        msle   : Mean squared log error
        r2     : R-squared coefficient
        r2a    : R2 adjusted
        rmse   : Root-mean-squared error
        var    : Explained variance
cv: int, optional
    Number of folds.
pos_label: int/float/str, optional
    The main class to be considered as positive 
    (classification only).
cutoff: float, optional
    The model cutoff (classification only).
training_score: bool, optional
    If set to True, the training score will be 
    computed with the validation score.
comb_limit: int, optional
    Maximum number of features combinations used 
    to train the model.
skip_error: bool, optional
    If set to True and an error occurs, it will be 
    displayed and not raised.
print_info: bool, optional
    If set to True, prints the model information at 
    each step.

Returns
-------
tablesample
    An object containing the result. For more information, see
    utilities.tablesample.
    """
    if isinstance(X, str):
        X = [X]
    if estimator.MODEL_SUBTYPE == "REGRESSOR" and metric == "auto":
        metric = "rmse"
    elif metric == "auto":
        metric = "logloss"
    if len(X) < 20:
        all_configuration = []
        for r in range(len(X) + 1):
            combinations_object = itertools.combinations(X, r)
            combinations_list = list(combinations_object)
            if combinations_list[0]:
                all_configuration += combinations_list
        if len(all_configuration) > comb_limit and comb_limit > 0:
            all_configuration = random.sample(all_configuration, comb_limit)
    else:
        all_configuration = []
        for k in range(max(comb_limit, 1)):
            config = sorted(random.sample(X, random.randint(1, len(X))))
            if config not in all_configuration:
                all_configuration += [config]
    if (
        OPTIONS["tqdm"]
        and ("tqdm" not in kwargs or ("tqdm" in kwargs and kwargs["tqdm"]))
        and print_info
    ):
        loop = tqdm(all_configuration)
    else:
        loop = all_configuration
    data = []
    for config in loop:
        if config:
            config = list(config)
            try:
                current_cv = cross_validate(
                    estimator,
                    input_relation,
                    config,
                    y,
                    metric,
                    cv,
                    pos_label,
                    cutoff,
                    True,
                    training_score,
                    tqdm=False,
                )
                if training_score:
                    keys = [elem for elem in current_cv[0].values]
                    data += [
                        (
                            config,
                            current_cv[0][keys[1]][cv],
                            current_cv[1][keys[1]][cv],
                            current_cv[0][keys[2]][cv],
                            current_cv[0][keys[1]][cv + 1],
                            current_cv[1][keys[1]][cv + 1],
                        )
                    ]
                    if print_info:
                        print(
                            f"Model: {str(estimator.__class__).split('.')[-1][:-2]}; "
                            f"Features: {config}; \033[91mTest_score: "
                            f"{current_cv[0][keys[1]][cv]}\033[0m; \033[92mTrain_score:"
                            f" {current_cv[1][keys[1]][cv]}\033[0m; \033[94mTime:"
                            f" {current_cv[0][keys[2]][cv]}\033[0m;"
                        )
                else:
                    keys = [v for v in current_cv.values]
                    data += [
                        (
                            config,
                            current_cv[keys[1]][cv],
                            current_cv[keys[2]][cv],
                            current_cv[keys[1]][cv + 1],
                        )
                    ]
                    if print_info:
                        print(
                            f"Model: {str(estimator.__class__).split('.')[-1][:-2]};"
                            f" Features: {config}; \033[91mTest_score: "
                            f"{current_cv[keys[1]][cv]}\033[0m; \033[94mTime:"
                            f"{current_cv[keys[2]][cv]}\033[0m;"
                        )
            except Exception as e:
                if skip_error and skip_error != "no_print":
                    print(e)
                elif not (skip_error):
                    raise (e)
    if not (data):
        if training_score:
            return tablesample(
                {
                    "parameters": [],
                    "avg_score": [],
                    "avg_train_score": [],
                    "avg_time": [],
                    "score_std": [],
                    "score_train_std": [],
                }
            )
        else:
            return tablesample(
                {"parameters": [], "avg_score": [], "avg_time": [], "score_std": [],}
            )
    reverse = reverse_score(metric)
    data.sort(key=lambda tup: tup[1], reverse=reverse)
    if training_score:
        result = tablesample(
            {
                "features": [d[0] for d in data],
                "avg_score": [d[1] for d in data],
                "avg_train_score": [d[2] for d in data],
                "avg_time": [d[3] for d in data],
                "score_std": [d[4] for d in data],
                "score_train_std": [d[5] for d in data],
            }
        )
        if print_info and (
            "final_print" not in kwargs or kwargs["final_print"] != "no_print"
        ):
            print("\033[1mRandomized Features Search Selected Model\033[0m")
            print(
                f"{str(estimator.__class__).split('.')[-1][:-2]}; Features:"
                f" {result['features'][0]}; \033[91mTest_score: "
                f"{result['avg_score'][0]}\033[0m; \033[92mTrain_score: "
                f"{result['avg_train_score'][0]}\033[0m; \033[94mTime: "
                f"{result['avg_time'][0]}\033[0m;"
            )
    else:
        result = tablesample(
            {
                "features": [d[0] for d in data],
                "avg_score": [d[1] for d in data],
                "avg_time": [d[2] for d in data],
                "score_std": [d[3] for d in data],
            }
        )
        if print_info and (
            "final_print" not in kwargs or kwargs["final_print"] != "no_print"
        ):
            print("\033[1mRandomized Features Search Selected Model\033[0m")
            print(
                f"{str(estimator.__class__).split('.')[-1][:-2]}; Features:"
                f" {result['features'][0]}; \033[91mTest_score: "
                f"{result['avg_score'][0]}\033[0m; \033[94mTime: "
                f"{result['avg_time'][0]}\033[0m;"
            )
    return result


@save_verticapy_logs
def stepwise(
    estimator,
    input_relation: Union[str, vDataFrame],
    X: Union[str, list],
    y: str,
    criterion: Literal["aic", "bic"] = "bic",
    direction: Literal["forward", "backward"] = "backward",
    max_steps: int = 100,
    criterion_threshold: int = 3,
    drop_final_estimator: bool = True,
    x_order: Literal["pearson", "spearman", "random", "none", None] = "pearson",
    print_info: bool = True,
    show: bool = True,
    ax=None,
    **style_kwds,
):
    """
Uses the Stepwise algorithm to find the most suitable number of features
when fitting the estimator.

Parameters
----------
estimator: object
    Vertica estimator with a fit method.
input_relation: str/vDataFrame
    Relation to use to train the model.
X: str / list
    List of the predictor columns.
y: str
    Response Column.
criterion: str, optional
    Criterion used to evaluate the model.
        aic : Akaike’s Information Criterion
        bic : Bayesian Information Criterion
direction: str, optional
    How to start the stepwise search. Can be done 'backward' or 'forward'.
max_steps: int, optional
    The maximum number of steps to be considered.
criterion_threshold: int, optional
    Threshold used when comparing the models criterions. If the difference
    is lesser than the threshold then the current 'best' model is changed.
drop_final_estimator: bool, optional
    If set to True, the final estimator will be dropped.
x_order: str, optional
    How to preprocess X before using the stepwise algorithm.
        pearson  : X is ordered based on the Pearson's correlation coefficient.
        spearman : X is ordered based on the Spearman's correlation coefficient.
        random   : Shuffles the vector X before applying the stepwise algorithm.
        none     : Does not change the order of X.
print_info: bool, optional
    If set to True, prints the model information at each step.
show: bool, optional
    If set to True, the stepwise graphic will be drawn.
ax: Matplotlib axes object, optional
    The axes to plot on.
**style_kwds
    Any optional parameter to pass to the Matplotlib functions.

Returns
-------
tablesample
    An object containing the result. For more information, see
    utilities.tablesample.
    """
    from verticapy.learn.metrics import aic_bic

    if isinstance(X, str):
        X = [X]
    assert len(X) >= 1, ParameterError("Vector X must have at least one element.")
    if not (OPTIONS["overwrite_model"]):
        does_model_exist(name=estimator.name, raise_error=True)
    result, current_step = [], 0
    table = (
        input_relation
        if isinstance(input_relation, str)
        else input_relation.__genSQL__()
    )
    avg = _executeSQL(
        f"SELECT /*+LABEL('learn.model_selection.stepwise')*/ AVG({y}) FROM {table}",
        method="fetchfirstelem",
        print_time_sql=False,
    )
    k = 0 if criterion == "aic" else 1
    if x_order == "random":
        random.shuffle(X)
    elif x_order in ("spearman", "pearson"):
        if isinstance(input_relation, str):
            vdf = vDataFrameSQL(input_relation)
        else:
            vdf = input_relation
        X = [
            elem
            for elem in vdf.corr(method=x_order, focus=y, columns=X, show=False)[
                "index"
            ]
        ]
        if direction == "backward":
            X.reverse()
    if print_info:
        print("\033[1m\033[4mStarting Stepwise\033[0m\033[0m")
    if OPTIONS["tqdm"] and print_info:
        loop = tqdm(range(len(X)))
    else:
        loop = range(len(X))
    model_id = 0
    if direction == "backward":
        X_current = [elem for elem in X]
        estimator.drop()
        estimator.fit(input_relation, X, y)
        current_score = estimator.score(criterion)
        result += [(X_current, current_score, None, None, 0, None)]
        for idx in loop:
            if print_info and idx == 0:
                print(
                    f"\033[1m[Model 0]\033[0m \033[92m{criterion}: "
                    f"{current_score}\033[0m; Variables: {X_current}"
                )
            if current_step >= max_steps:
                break
            X_test = [elem for elem in X_current]
            X_test.remove(X[idx])
            if len(X_test) != 0:
                estimator.drop()
                estimator.fit(input_relation, X_test, y)
                test_score = estimator.score(criterion)
            else:
                test_score = aic_bic(y, str(avg), input_relation, 0)[k]
            score_diff = test_score - current_score
            if test_score - current_score < criterion_threshold:
                sign = "-"
                model_id += 1
                current_score = test_score
                X_current = [elem for elem in X_test]
                if print_info:
                    print(
                        f"\033[1m[Model {model_id}]\033[0m \033[92m{criterion}: "
                        f"{test_score}\033[0m; \033[91m(-) Variable: {X[idx]}\033[0m"
                    )
            else:
                sign = "+"
            result += [(X_test, test_score, sign, X[idx], idx + 1, score_diff)]
            current_step += 1
    else:
        X_current = []
        current_score = aic_bic(y, str(avg), input_relation, 0)[k]
        result += [(X_current, current_score, None, None, 0, None)]
        for idx in loop:
            if print_info and idx == 0:
                print(
                    f"\033[1m[Model 0]\033[0m \033[92m{criterion}: "
                    f"{current_score}\033[0m; Variables: {X_current}"
                )
            if current_step >= max_steps:
                break
            X_test = [elem for elem in X_current] + [X[idx]]
            estimator.drop()
            estimator.fit(input_relation, X_test, y)
            test_score = estimator.score(criterion)
            score_diff = current_score - test_score
            if current_score - test_score > criterion_threshold:
                sign = "+"
                model_id += 1
                current_score = test_score
                X_current = [x for x in X_test]
                if print_info:
                    print(
                        f"\033[1m[Model {model_id}]\033[0m \033[92m{criterion}:"
                        f" {test_score}\033[0m; \033[91m(+) Variable: {X[idx]}\033[0m"
                    )
            else:
                sign = "-"
            result += [(X_test, test_score, sign, X[idx], idx + 1, score_diff)]
            current_step += 1
    if print_info:
        print(f"\033[1m\033[4mSelected Model\033[0m\033[0m\n")
        print(
            f"\033[1m[Model {model_id}]\033[0m \033[92m{criterion}:"
            f" {current_score}\033[0m; Variables: {X_current}"
        )
    features = [x[0] for x in result]
    for idx, x in enumerate(features):
        features[idx] = [item.replace('"', "") for item in x]
    importance = [x[5] if (x[5]) and x[5] > 0 else 0 for x in result]
    importance = [100 * x / sum(importance) for x in importance]
    result = tablesample(
        {
            "index": [x[4] for x in result],
            "features": features,
            criterion: [x[1] for x in result],
            "change": [x[2] for x in result],
            "variable": [x[3] for x in result],
            "importance": importance,
        }
    )
    estimator.drop()
    if not (drop_final_estimator):
        estimator.fit(input_relation, X_current, y)
    result.best_list_ = X_current
    if show:
        plot_stepwise_ml(
            [len(x) for x in result["features"]],
            result[criterion],
            result["variable"],
            result["change"],
            [result["features"][0], X_current],
            x_label="n_features",
            y_label=criterion,
            direction=direction,
            ax=ax,
            **style_kwds,
        )
        coeff_importances = {}
        for idx in range(len(importance)):
            if result["variable"][idx] != None:
                coeff_importances[result["variable"][idx]] = importance[idx]
        plot_importance(coeff_importances, print_legend=False, ax=ax, **style_kwds)
    return result