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
# Standard Libraries
import uuid

# Global Variable
MINIMUM_VERSION = {
    "Balance": [8, 1, 1],
    "BernoulliNB": [8, 0, 0],
    "BisectingKMeans": [9, 3, 1],
    "CategoricalNB": [8, 0, 0],
    "confusion_matrix": [8, 0, 0],
    "DecisionTreeClassifier": [8, 1, 1],
    "DecisionTreeRegressor": [9, 0, 1],
    "DummyTreeClassifier": [8, 1, 1],
    "DummyTreeRegressor": [9, 0, 1],
    "edit_distance": [10, 1, 0],
    "ElasticNet": [8, 0, 0],
    "GaussianNB": [8, 0, 0],
    "gen_dataset": [9, 3, 0],
    "get_tree": [9, 1, 1],
    "IsolationForest": [12, 0, 0],
    "jaro_distance": [12, 0, 2],
    "jaro_winkler_distance": [12, 0, 2],
    "Lasso": [8, 0, 0],
    "lift_chart": [8, 0, 0],
    "LinearRegression": [8, 0, 0],
    "LinearSVC": [8, 1, 0],
    "LinearSVR": [8, 1, 1],
    "LogisticRegression": [8, 0, 0],
    "KMeans": [8, 0, 0],
    "KPrototypes": [12, 0, 3],
    "MCA": [9, 1, 0],
    "MinMaxScaler": [8, 1, 0],
    "multilabel_confusion_matrix": [8, 0, 0],
    "MultinomialNB": [8, 0, 0],
    "NaiveBayes": [8, 0, 0],
    "Normalizer": [8, 1, 0],
    "OneHotEncoder": [9, 0, 0],
    "PCA": [9, 1, 0],
    "prc_curve": [9, 1, 0],
    "RandomForestClassifier": [8, 1, 1],
    "RandomForestRegressor": [9, 0, 1],
    "read_file": [11, 1, 1],
    "Ridge": [8, 0, 0],
    "RobustScaler": [8, 1, 0],
    "roc_curve": [8, 0, 0],
    "SARIMAX": [8, 0, 0],
    "soundex": [10, 1, 0],
    "soundex_matches": [10, 1, 0],
    "StandardScaler": [8, 1, 0],
    "SVD": [9, 1, 0],
    "VAR": [8, 0, 0],
    "XGBoostClassifier": [10, 1, 0],
    "XGBoostRegressor": [10, 1, 0],
}

OPTIONS = {
    "cache": True,
    "colors": None,
    "connection": {"conn": None, "section": None, "dsn": None,},
    "external_connection": {},
    "interactive": False,
    "count_on": False,
    "footer_on": True,
    "identifier": str(uuid.uuid1()).replace("-", ""),
    "max_columns": 50,
    "max_rows": 100,
    "mode": None,
    "overwrite_model": True,
    "percent_bar": None,
    "print_info": True,
    "save_query_profile": True,
    "sql_on": False,
    "random_state": None,
    "temp_schema": "public",
    "time_on": False,
    "tqdm": True,
    "vertica_version": None,
}