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
from verticapy.jupyter.extensions.sql_magic import sql_magic as sql
from verticapy.jupyter.extensions.hchart_magic import hchart_magic as hchart


def load_ipython_extension(ipython):
    ipython.register_magic_function(sql, "cell", "sql")
    ipython.register_magic_function(sql, "line", "sql")
    ipython.register_magic_function(hchart, "cell", "sql")
    ipython.register_magic_function(hchart, "line", "sql")