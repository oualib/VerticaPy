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
from verticapy._config.connection import VERTICAPY_AUTO_CONNECTION
from verticapy.connection.connect import connect
from verticapy.connection.utils import get_confparser, get_connection_file


def change_auto_connection(name: str):
    """
Changes the current auto connection.

Parameters
----------
name: str
	Name of the new auto connection.
	"""
    confparser = get_confparser()

    if confparser.has_section(name):

        confparser.remove_section(VERTICAPY_AUTO_CONNECTION)
        confparser.add_section(VERTICAPY_AUTO_CONNECTION)
        confparser.set(VERTICAPY_AUTO_CONNECTION, "name", name)
        path = get_connection_file()
        f = open(path, "w+")
        confparser.write(f)
        f.close()

    else:

        raise NameError(
            "The input name is incorrect. The connection "
            f"'{name}' has never been created.\nUse the "
            "new_connection function to create a new "
            "connection."
        )


def delete_connection(name: str):
    """
Deletes a specified connection from the connection file.

Parameters
----------
name: str
    Name of the connection.

Returns
-------
bool
    True if the connection was deleted, False otherwise.
    """
    confparser = get_confparser()

    if confparser.has_section(name):

        confparser.remove_section(name)
        if confparser.has_section(VERTICAPY_AUTO_CONNECTION):
            name_auto = confparser.get(VERTICAPY_AUTO_CONNECTION, "name")
            if name_auto == name:
                confparser.remove_section(VERTICAPY_AUTO_CONNECTION)
        path = get_connection_file()
        f = open(path, "w+")
        confparser.write(f)
        f.close()
        return True

    else:

        warnings.warn(f"The connection {name} does not exist.", Warning)
        return False


def new_connection(
    conn_info: dict,
    name: str = "vertica_connection",
    auto: bool = True,
    overwrite: bool = True,
):
    """
Saves the new connection in the VerticaPy connection file.
The information is saved plaintext in the local machine.
The function 'get_connection_file' returns the associated connection file path.
If you want a temporary connection, you can use the 'set_connection' function.

Parameters
----------
conn_info: dict
	Dictionnary containing the information to set up the connection.
		database : Database Name.
		host     : Server ID.
		password : User Password.
		port     : Database Port (optional, default: 5433).
		user     : User ID (optional, default: dbadmin).
        ...
        env      : Bool to indicate whether the user and password are replaced 
                   by the associated environment variables. If True, VerticaPy 
                   reads the associated environment variables instead of 
                   writing and directly using the username and password. 
                   For example: {'user': 'ENV_USER', 'password': 'ENV_PASSWORD'}
                   This works only for the user and password. The real values 
                   of the other variables are stored plaintext in the VerticaPy 
                   connection file. Using the enviornment variables hides the 
                   username and password in cases where the local machine is 
                   shared.
name: str, optional
	Name of the connection.
auto: bool, optional
    If set to True, the connection will become the new auto-connection.
overwrite: bool, optional
    If set to True and the connection already exists, it will be 
    overwritten.
env: bool, optional
    If True, user and password are replaced by the associated environment 
    variables. VerticaPy reads the associated environment variables instead 
    of writing and directly using the username and password.
    For example: {'user': 'ENV_USER', 'password': 'ENV_PASSWORD'}  
	"""
    path = get_connection_file()
    confparser = get_confparser()

    if confparser.has_section(name):

        if not (overwrite):
            raise ParserError(
                f"The section '{name}' already exists. You "
                "can overwrite it by setting the parameter "
                "'overwrite' to True."
            )
        confparser.remove_section(name)

    confparser.add_section(name)
    for c in conn_info:
        confparser.set(name, c, str(conn_info[c]))
    f = open(path, "w+")
    confparser.write(f)
    f.close()
    if auto:
        change_auto_connection(name)

    connect(name, path)


new_auto_connection = new_connection