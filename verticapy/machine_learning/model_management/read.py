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
from verticapy._utils._sql._collect import save_verticapy_logs
from verticapy._utils._sql._format import quote_ident, schema_relation
from verticapy._utils._sql._sys import _executeSQL
from verticapy._utils._sql._vertica_version import vertica_version

from verticapy.core.tablesample.base import TableSample


def does_model_exist(
    name: str, raise_error: bool = False, return_model_type: bool = False
):
    """
Checks if the model already exists.

Parameters
----------
name: str
    Model name.
raise_error: bool, optional
    If set to True and an error occurs, it raises the error.
return_model_type: bool, optional
    If set to True, returns the model type.

Returns
-------
int
    0 if the model does not exist.
    1 if the model exists and is native.
    2 if the model exists and is not native.
    """
    model_type = None
    schema, model_name = schema_relation(name)
    schema, model_name = schema[1:-1], model_name[1:-1]
    result = _executeSQL(
        query="""
            SELECT
                /*+LABEL('learn.tools.does_model_exist')*/ * 
            FROM columns 
            WHERE table_schema = 'verticapy' 
              AND table_name = 'models' LIMIT 1""",
        method="fetchrow",
        print_time_sql=False,
    )
    if result:
        result = _executeSQL(
            query=f"""
                SELECT 
                    /*+LABEL('learn.tools.does_model_exist')*/ 
                    model_type
                FROM verticapy.models
                WHERE LOWER(model_name) = LOWER('{quote_ident(name)}') 
                LIMIT 1""",
            method="fetchrow",
            print_time_sql=False,
        )
        if result:
            model_type = result[0]
            result = 2
    if not (result):
        result = _executeSQL(
            query=f"""
                SELECT 
                    /*+LABEL('learn.tools.does_model_exist')*/ 
                    model_type 
                FROM MODELS 
                WHERE LOWER(model_name) = LOWER('{model_name}') 
                  AND LOWER(schema_name) = LOWER('{schema}') 
                LIMIT 1""",
            method="fetchrow",
            print_time_sql=False,
        )
        if result:
            model_type = result[0]
            result = 1
        else:
            result = 0
    if raise_error and result:
        raise NameError(f"The model '{name}' already exists !")
    if return_model_type:
        return model_type
    return result


@save_verticapy_logs
def load_model(name: str, input_relation: str = "", test_relation: str = ""):
    """
Loads a Vertica model and returns the associated object.

Parameters
----------
name: str
    Model Name.
input_relation: str, optional
    Some automated functions may depend on the input relation. If the 
    load_model function cannot find the input relation from the call string, 
    you should fill it manually.
test_relation: str, optional
    Relation to use to do the testing. All the methods will use this relation 
    for the scoring. If empty, the training relation will be used as testing.

Returns
-------
model
    The model.
    """
    import verticapy.machine_learning.vertica as vml

    does_exist = does_model_exist(name=name, raise_error=False)
    schema, model_name = schema_relation(name)
    schema, model_name = schema[1:-1], name[1:-1]
    assert does_exist, NameError(f"The model '{name}' doesn't exist.")
    if does_exist == 2:
        result = _executeSQL(
            query=f"""
                SELECT 
                    /*+LABEL('learn.tools.load_model')*/ 
                    attr_name,
                    value 
                FROM verticapy.attr
                WHERE LOWER(model_name) 
                    = LOWER('{quote_ident(name.lower())}')""",
            method="fetchall",
            print_time_sql=False,
        )
        model_save = {}
        for val in result:
            ldic = {}
            try:
                exec(f"result_tmp = {val[1]}", globals(), ldic)
            except:
                val1 = val[1].replace("'", "''")
                exec(f"result_tmp = '{val1}'", globals(), ldic)
            result_tmp = ldic["result_tmp"]
            try:
                result_tmp = float(result_tmp)
            except:
                pass
            if result_tmp == None:
                result_tmp = "None"
            model_save[val[0]] = result_tmp
        if model_save["type"] == "NearestCentroid":
            model = vml.NearestCentroid(name, model_save["p"])
            model.centroids_ = TableSample(model_save["centroids"])
            model.classes_ = model_save["classes"]
        elif model_save["type"] == "KNeighborsClassifier":
            model = vml.KNeighborsClassifier(
                name, model_save["n_neighbors"], model_save["p"]
            )
            model.classes_ = model_save["classes"]
        elif model_save["type"] == "KNeighborsRegressor":
            model = vml.KNeighborsRegressor(
                name, model_save["n_neighbors"], model_save["p"]
            )
        elif model_save["type"] == "KernelDensity":
            model = vml.KernelDensity(
                name,
                model_save["bandwidth"],
                model_save["kernel"],
                model_save["p"],
                model_save["max_leaf_nodes"],
                model_save["max_depth"],
                model_save["min_samples_leaf"],
                model_save["nbins"],
                model_save["xlim"],
            )
            model.y = "KDE"
            model.map = model_save["map"]
            model.tree_name = model_save["tree_name"]
        elif model_save["type"] == "LocalOutlierFactor":
            model = vml.LocalOutlierFactor(
                name, model_save["n_neighbors"], model_save["p"]
            )
            model.n_errors_ = model_save["n_errors"]
        elif model_save["type"] == "DBSCAN":
            model = vml.DBSCAN(
                name, model_save["eps"], model_save["min_samples"], model_save["p"]
            )
            model.n_cluster_ = model_save["n_cluster"]
            model.n_noise_ = model_save["n_noise"]
        elif model_save["type"] == "CountVectorizer":
            model = vml.CountVectorizer(
                name,
                model_save["lowercase"],
                model_save["max_df"],
                model_save["min_df"],
                model_save["max_features"],
                model_save["ignore_special"],
                model_save["max_text_size"],
            )
            model.stop_words_ = model.compute_stop_words()
            model.vocabulary_ = model.compute_vocabulary()
        elif model_save["type"] == "SARIMAX":
            model = vml.SARIMAX(
                name,
                model_save["p"],
                model_save["d"],
                model_save["q"],
                model_save["P"],
                model_save["D"],
                model_save["Q"],
                model_save["s"],
                model_save["tol"],
                model_save["max_iter"],
                model_save["solver"],
                model_save["max_pik"],
                model_save["papprox_ma"],
            )
            model.transform_relation = model_save["transform_relation"]
            model.coef_ = TableSample(model_save["coef"])
            model.ma_avg_ = model_save["ma_avg"]
            if isinstance(model_save["ma_piq"], dict):
                model.ma_piq_ = TableSample(model_save["ma_piq"])
            else:
                model.ma_piq_ = None
            model.ts = model_save["ts"]
            model.exogenous = model_save["exogenous"]
            model.deploy_predict_ = model_save["deploy_predict"]
        elif model_save["type"] == "VAR":
            model = vml.VAR(
                name,
                model_save["p"],
                model_save["tol"],
                model_save["max_iter"],
                model_save["solver"],
            )
            model.transform_relation = model_save["transform_relation"]
            model.coef_ = []
            for i in range(len(model_save["X"])):
                model.coef_ += [TableSample(model_save[f"coef_{i}"])]
            model.ts = model_save["ts"]
            model.deploy_predict_ = model_save["deploy_predict"]
            model.X = model_save["X"]
            if not (input_relation):
                model.input_relation = model_save["input_relation"]
            else:
                model.input_relation = input_relation
            model.X = model_save["X"]
            if model_save["type"] in (
                "KNeighborsRegressor",
                "KNeighborsClassifier",
                "NearestCentroid",
                "SARIMAX",
            ):
                model.y = model_save["y"]
                model.test_relation = model_save["test_relation"]
            elif model_save["type"] not in ("CountVectorizer", "VAR"):
                model.key_columns = model_save["key_columns"]
    else:
        model_type = does_model_exist(
            name=name, raise_error=False, return_model_type=True
        )
        if model_type.lower() in ("kmeans", "kprototypes",):
            info = _executeSQL(
                query=f"""
                    SELECT 
                        /*+LABEL('learn.tools.load_model')*/ 
                        GET_MODEL_SUMMARY 
                        (USING PARAMETERS 
                        model_name = '{name}')""",
                method="fetchfirstelem",
                print_time_sql=False,
            ).replace("\n", " ")
            mtype = model_type.lower() + "("
            info = mtype + info.split(mtype)[1]
        elif model_type.lower() == "normalize_fit":
            model = vml.Normalizer(name)
            model.param_ = model.get_attr("details")
            model.X = ['"' + item + '"' for item in model.param_.values["column_name"]]
            if "avg" in model.param_.values:
                model.parameters["method"] = "zscore"
            elif "max" in model.param_.values:
                model.parameters["method"] = "minmax"
            else:
                model.parameters["method"] = "robust_zscore"
            return model
        else:
            info = _executeSQL(
                query=f"""
                    SELECT 
                        /*+LABEL('learn.tools.load_model')*/ 
                        GET_MODEL_ATTRIBUTE 
                        (USING PARAMETERS 
                        model_name = '{name}',
                        attr_name = 'call_string')""",
                method="fetchfirstelem",
                print_time_sql=False,
            ).replace("\n", " ")
        if "SELECT " in info:
            info = info.split("SELECT ")[1].split("(")
        else:
            info = info.split("(")
        model_type = info[0].lower()
        info = info[1].split(")")[0].replace(" ", "").split("USINGPARAMETERS")
        if (
            model_type == "svm_classifier"
            and "class_weights='none'" not in " ".join(info).lower()
        ):
            parameters = "".join(info[1].split("class_weights=")[1].split("'"))
            parameters = parameters[3 : len(parameters)].split(",")
            del parameters[0]
            parameters += [
                "class_weights=" + info[1].split("class_weights=")[1].split("'")[1]
            ]
        elif model_type != "svd":
            parameters = info[1].split(",")
        else:
            parameters = []
        parameters = [item.split("=") for item in parameters]
        parameters_dict = {}
        for item in parameters:
            if len(item) > 1:
                parameters_dict[item[0]] = item[1]
        info = info[0]
        for elem in parameters_dict:
            if isinstance(parameters_dict[elem], str):
                parameters_dict[elem] = parameters_dict[elem].replace("'", "")
        if "split_proposal_method" in parameters_dict:
            split_proposal_method = parameters_dict["split_proposal_method"]
        else:
            split_proposal_method = "global"
        if "epsilon" in parameters_dict:
            epsilon = parameters_dict["epsilon"]
        else:
            epsilon = 0.001
        if model_type == "rf_regressor":
            model = vml.RandomForestRegressor(
                name,
                int(parameters_dict["ntree"]),
                int(parameters_dict["mtry"]),
                int(parameters_dict["max_breadth"]),
                float(parameters_dict["sampling_size"]),
                int(parameters_dict["max_depth"]),
                int(parameters_dict["min_leaf_size"]),
                float(parameters_dict["min_info_gain"]),
                int(parameters_dict["nbins"]),
            )
        elif model_type == "rf_classifier":
            model = vml.RandomForestClassifier(
                name,
                int(parameters_dict["ntree"]),
                int(parameters_dict["mtry"]),
                int(parameters_dict["max_breadth"]),
                float(parameters_dict["sampling_size"]),
                int(parameters_dict["max_depth"]),
                int(parameters_dict["min_leaf_size"]),
                float(parameters_dict["min_info_gain"]),
                int(parameters_dict["nbins"]),
            )
        elif model_type == "iforest":
            model = vml.IsolationForest(
                name,
                int(parameters_dict["ntree"]),
                int(parameters_dict["max_depth"]),
                int(parameters_dict["nbins"]),
                float(parameters_dict["sampling_size"]),
                float(parameters_dict["col_sample_by_tree"]),
            )
        elif model_type == "xgb_classifier":
            model = vml.XGBoostClassifier(
                name,
                int(parameters_dict["max_ntree"]),
                int(parameters_dict["max_depth"]),
                int(parameters_dict["nbins"]),
                split_proposal_method,
                float(epsilon),
                float(parameters_dict["learning_rate"]),
                float(parameters_dict["min_split_loss"]),
                float(parameters_dict["weight_reg"]),
                float(parameters_dict["sampling_size"]),
            )
        elif model_type == "xgb_regressor":
            model = vml.XGBoostRegressor(
                name,
                int(parameters_dict["max_ntree"]),
                int(parameters_dict["max_depth"]),
                int(parameters_dict["nbins"]),
                split_proposal_method,
                float(epsilon),
                float(parameters_dict["learning_rate"]),
                float(parameters_dict["min_split_loss"]),
                float(parameters_dict["weight_reg"]),
                float(parameters_dict["sampling_size"]),
            )
        elif model_type == "logistic_reg":
            model = vml.LogisticRegression(
                name,
                parameters_dict["regularization"],
                float(parameters_dict["epsilon"]),
                float(parameters_dict["lambda"]),
                int(parameters_dict["max_iterations"]),
                parameters_dict["optimizer"],
                float(parameters_dict["alpha"]),
            )
        elif model_type == "linear_reg":
            if parameters_dict["regularization"] == "none":
                model = vml.LinearRegression(
                    name,
                    float(parameters_dict["epsilon"]),
                    int(parameters_dict["max_iterations"]),
                    parameters_dict["optimizer"],
                )
            elif parameters_dict["regularization"] == "l1":
                model = vml.Lasso(
                    name,
                    float(parameters_dict["epsilon"]),
                    float(parameters_dict["lambda"]),
                    int(parameters_dict["max_iterations"]),
                    parameters_dict["optimizer"],
                )
            elif parameters_dict["regularization"] == "l2":
                model = vml.Ridge(
                    name,
                    float(parameters_dict["epsilon"]),
                    float(parameters_dict["lambda"]),
                    int(parameters_dict["max_iterations"]),
                    parameters_dict["optimizer"],
                )
            else:
                model = vml.ElasticNet(
                    name,
                    float(parameters_dict["epsilon"]),
                    float(parameters_dict["lambda"]),
                    int(parameters_dict["max_iterations"]),
                    parameters_dict["optimizer"],
                    float(parameters_dict["alpha"]),
                )
        elif model_type == "naive_bayes":
            model = vml.NaiveBayes(name, float(parameters_dict["alpha"]))
        elif model_type == "svm_regressor":
            model = vml.LinearSVR(
                name,
                float(parameters_dict["epsilon"]),
                float(parameters_dict["C"]),
                True,
                float(parameters_dict["intercept_scaling"]),
                parameters_dict["intercept_mode"],
                float(parameters_dict["error_tolerance"]),
                int(parameters_dict["max_iterations"]),
            )
        elif model_type == "svm_classifier":
            class_weights = parameters_dict["class_weights"].split(",")
            for idx, elem in enumerate(class_weights):
                try:
                    class_weights[idx] = float(class_weights[idx])
                except:
                    class_weights[idx] = None
            model = vml.LinearSVC(
                name,
                float(parameters_dict["epsilon"]),
                float(parameters_dict["C"]),
                True,
                float(parameters_dict["intercept_scaling"]),
                parameters_dict["intercept_mode"],
                class_weights,
                int(parameters_dict["max_iterations"]),
            )
        elif model_type in ("kmeans", "kprototypes"):
            if model_type == "kmeans":
                model = vml.KMeans(
                    name,
                    int(info.split(",")[-1]),
                    parameters_dict["init_method"],
                    int(parameters_dict["max_iterations"]),
                    float(parameters_dict["epsilon"]),
                )
            else:
                model = vml.KPrototypes(
                    name,
                    int(info.split(",")[-1]),
                    parameters_dict["init_method"],
                    int(parameters_dict["max_iterations"]),
                    float(parameters_dict["epsilon"]),
                    float(parameters_dict["gamma"]),
                )
            model.cluster_centers_ = model.get_attr("centers")
            result = model.get_attr("metrics").values["metrics"][0]
            values = {
                "index": [
                    "Between-Cluster Sum of Squares",
                    "Total Sum of Squares",
                    "Total Within-Cluster Sum of Squares",
                    "Between-Cluster SS / Total SS",
                    "converged",
                ]
            }
            values["value"] = [
                float(
                    result.split("Between-Cluster Sum of Squares: ")[1].split("\n")[0]
                ),
                float(result.split("Total Sum of Squares: ")[1].split("\n")[0]),
                float(
                    result.split("Total Within-Cluster Sum of Squares: ")[1].split(
                        "\n"
                    )[0]
                ),
                float(
                    result.split("Between-Cluster Sum of Squares: ")[1].split("\n")[0]
                )
                / float(result.split("Total Sum of Squares: ")[1].split("\n")[0]),
                result.split("Converged: ")[1].split("\n")[0] == "True",
            ]
            model.metrics_ = TableSample(values)
        elif model_type == "bisecting_kmeans":
            model = vml.BisectingKMeans(
                name,
                int(info.split(",")[-1]),
                int(parameters_dict["bisection_iterations"]),
                parameters_dict["split_method"],
                int(parameters_dict["min_divisible_cluster_size"]),
                parameters_dict["distance_method"],
                parameters_dict["kmeans_center_init_method"],
                int(parameters_dict["kmeans_max_iterations"]),
                float(parameters_dict["kmeans_epsilon"]),
            )
            model.metrics_ = model.get_attr("Metrics")
            model.cluster_centers_ = model.get_attr("BKTree")
        elif model_type == "pca":
            model = vml.PCA(name, 0, bool(parameters_dict["scale"]))
            model.components_ = model.get_attr("principal_components")
            model.explained_variance_ = model.get_attr("singular_values")
            model.mean_ = model.get_attr("columns")
        elif model_type == "svd":
            model = vml.SVD(name)
            model.singular_values_ = model.get_attr("right_singular_vectors")
            model.explained_variance_ = model.get_attr("singular_values")
        elif model_type == "one_hot_encoder_fit":
            model = vml.OneHotEncoder(name)
            try:
                model.param_ = TableSample.read_sql(
                    query=f"""
                        SELECT 
                            category_name, 
                            category_level::varchar, 
                            category_level_index 
                        FROM 
                            (SELECT 
                                GET_MODEL_ATTRIBUTE(
                                    USING PARAMETERS
                                    model_name = '{model.model_name}',
                                    attr_name = 'integer_categories')) VERTICAPY_SUBTABLE 
                            UNION ALL 
                             SELECT 
                                GET_MODEL_ATTRIBUTE(
                                    USING PARAMETERS 
                                    model_name = '{model.model_name}',
                                    attr_name = 'varchar_categories')""",
                )
            except:
                try:
                    model.param_ = model.get_attr("integer_categories")
                except:
                    model.param_ = model.get_attr("varchar_categories")
        if not (input_relation):
            model.input_relation = info.split(",")[1].replace("'", "").replace("\\", "")
        else:
            model.input_relation = input_relation
        model.test_relation = test_relation if (test_relation) else model.input_relation
        if model_type not in (
            "kmeans",
            "kprototypes",
            "pca",
            "svd",
            "one_hot_encoder_fit",
            "bisecting_kmeans",
            "iforest",
            "normalizer",
        ):
            start = 3
            model.y = info.split(",")[2].replace("'", "").replace("\\", "")
        else:
            start = 2
        end = len(info.split(","))
        if model_type in ("bisecting_kmeans",):
            end -= 1
        model.X = info.split(",")[start:end]
        model.X = [item.replace("'", "").replace("\\", "") for item in model.X]
        if model_type in ("naive_bayes", "rf_classifier", "xgb_classifier"):
            try:
                classes = _executeSQL(
                    query=f"""
                        SELECT 
                            /*+LABEL('learn.tools.load_model')*/ 
                            DISTINCT {model.y} 
                            FROM {model.input_relation} 
                            WHERE {model.y} IS NOT NULL 
                            ORDER BY 1""",
                    method="fetchall",
                    print_time_sql=False,
                )
                model.classes_ = [item[0] for item in classes]
            except:
                model.classes_ = [0, 1]
        elif model_type in ("svm_classifier", "logistic_reg"):
            model.classes_ = [0, 1]
        if model_type in (
            "svm_classifier",
            "svm_regressor",
            "logistic_reg",
            "linear_reg",
        ):
            model.coef_ = model.get_attr("details")
        if model_type in ("xgb_classifier", "xgb_regressor"):
            v = vertica_version()
            v = v[0] > 11 or (v[0] == 11 and (v[1] >= 1 or v[2] >= 1))
            if v:
                model.set_params(
                    {
                        "col_sample_by_tree": float(
                            parameters_dict["col_sample_by_tree"]
                        ),
                        "col_sample_by_node": float(
                            parameters_dict["col_sample_by_node"]
                        ),
                    }
                )
    return model
