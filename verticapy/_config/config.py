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
import verticapy.plotting._colors as vp_colors

# Standard Python Modules
import warnings
from typing import Union, Literal, overload

# VerticaPy
from verticapy.utils._toolbox import *
from verticapy.errors import ParameterError


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


@overload
def set_option(
    option: Literal["color_style"], value: Literal[tuple(vp_colors.COLORS_OPTIONS)]
) -> None:
    ...


@overload
def set_option(option: Literal["mode"], value: Literal["light", "full"]) -> None:
    ...


def set_option(
    option: Literal[
        "cache",
        "colors",
        "color_style",
        "interactive",
        "count_on",
        "footer_on",
        "max_columns",
        "max_rows",
        "mode",
        "overwrite_model",
        "percent_bar",
        "print_info",
        "random_state",
        "save_query_profile",
        "sql_on",
        "temp_schema",
        "time_on",
        "tqdm",
    ],
    value: Union[bool, int, str, list, None] = None,
) -> None:
    """
    Sets VerticaPy options.

    Parameters
    ----------
    option: str
        Option to use.
        cache              : bool
            If set to True, the vDataFrame will save in memory the computed
            aggregations.
        colors             : list
            List of the colors used to draw the graphics.
        color_style        : str
            Style used to color the graphics, one of the following:
            "rgb", "sunset", "retro", "shimbg", "swamp", "med", "orchid", 
            "magenta", "orange", "vintage", "vivid", "berries", "refreshing", 
            "summer", "tropical", "india", "default".
        count_on           : bool
            If set to True, the total number of rows in vDataFrames and tablesamples is  
            computed and displayed in the footer (if footer_on is True).
        footer_on          : bool
            If set to True, vDataFrames and tablesamples show a footer that includes information 
            about the displayed rows and columns.
        interactive        : bool
            If set to True, verticaPy outputs will be displayed on interactive tables. 
        max_columns        : int
            Maximum number of columns to display. If the parameter is incorrect, 
            nothing is changed.
        max_rows           : int
            Maximum number of rows to display. If the parameter is incorrect, 
            nothing is changed.
        mode               : str
            How to display VerticaPy outputs.
                full  : VerticaPy regular display mode.
                light : Minimalist display mode.
        overwrite_model: bool
            If set to True and you try to train a model with an existing name. 
            It will be automatically overwritten.
        percent_bar        : bool
            If set to True, it displays the percent of non-missing values.
        print_info         : bool
            If set to True, information will be printed each time the vDataFrame 
            is modified.
        random_state       : int
            Integer used to seed the random number generation in VerticaPy.
        save_query_profile : str / list / bool
            If set to "all" or True, all function calls are stored in the query 
            profile table. This makes it possible to differentiate the VerticaPy 
            logs from the Vertica logs.
            You can also provide a list of specific methods to store. For example: 
            if you specify ["corr", "describe"], only the logs associated with 
            those two methods are stored. 
            If set to False, this functionality is deactivated.
        sql_on             : bool
            If set to True, displays all the SQL queries.
        temp_schema        : str
            Specifies the temporary schema that certain methods/functions use to 
            create intermediate objects, if needed. 
        time_on            : bool
            If set to True, displays all the SQL queries elapsed time.
        tqdm               : bool
            If set to True, a loading bar is displayed when using iterative 
            functions.
    value: object, optional
        New value of option.
    """
    wrong_value = False
    if option == "colors":
        if isinstance(value, list):
            OPTIONS["colors"] = [str(elem) for elem in value]
        else:
            wrong_value = True
    elif option == "color_style":
        if value == None:
            value = "default"
        if value in vp_colors.COLORS_OPTIONS:
            OPTIONS["colors"] = vp_colors.COLORS_OPTIONS[value]
        else:
            wrong_value = True
    elif option == "max_columns":
        if isinstance(value, int) and value > 0:
            OPTIONS["max_columns"] = int(value)
        else:
            wrong_value = True
    elif option == "max_rows":
        if isinstance(value, int) and value >= 0:
            OPTIONS["max_rows"] = int(value)
        else:
            wrong_value = True
    elif option == "mode":
        if value in ["light", "full"]:
            OPTIONS["mode"] = value
        else:
            wrong_value = True
    elif option == "random_state":
        if isinstance(value, int) and (value < 0):
            raise ParameterError("Random State Value must be positive.")
        if isinstance(value, int):
            OPTIONS["random_state"] = value
        elif value == None:
            OPTIONS["random_state"] = None
        else:
            wrong_value = True
    elif option in (
        "print_info",
        "sql_on",
        "time_on",
        "count_on",
        "cache",
        "footer_on",
        "tqdm",
        "overwrite_model",
        "percent_bar",
        "interactive",
    ):
        if value in (True, False, None):
            OPTIONS[option] = value
        else:
            wrong_value = True
    elif option == "save_query_profile":
        if value == "all":
            value = True
        elif isinstance(value, (bool, list)):
            pass
        else:
            wrong_value = True
        if not (wrong_value):
            OPTIONS[option] = value
    elif option == "temp_schema":
        if isinstance(value, str):
            value_str = value.replace("'", "''")
            query = f"""
                SELECT /*+LABEL('utilities.set_option')*/
                  schema_name 
               FROM v_catalog.schemata 
               WHERE schema_name = '{value_str}' LIMIT 1;"""
            res = executeSQL(
                query, title="Checking if the schema exists.", method="fetchrow"
            )
            if res:
                OPTIONS["temp_schema"] = str(value)
            else:
                raise ParameterError(f"The schema '{value}' could not be found.")
        else:
            wrong_value = True
    else:
        raise ParameterError(f"Option '{option}' does not exist.")
    if wrong_value:
        warning_message = "The parameter value is incorrect. Nothing was changed."
        warnings.warn(warning_message, Warning)
