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
import shutil

from verticapy._config.config import ISNOTEBOOK
from verticapy._utils._sql._format import indentSQL


def print_query(query: str, title: str = ""):
    screen_columns = shutil.get_terminal_size().columns
    query_print = indentSQL(query)
    if ISNOTEBOOK:
        display(HTML(f"<h4>{title}</h4>"))
        query_print = query_print.replace("\n", " <br>").replace("  ", " &emsp; ")
        display(HTML(query_print))
    else:
        print(f"$ {title} $\n")
        print(query_print)
        print("-" * int(screen_columns) + "\n")


def print_time(elapsed_time: float):
    screen_columns = shutil.get_terminal_size().columns
    if ISNOTEBOOK:
        display(HTML(f"<div><b>Execution: </b> {round(elapsed_time, 3)}s</div>"))
    else:
        print(f"Execution: {round(elapsed_time, 3)}s")
        print("-" * int(screen_columns) + "\n")