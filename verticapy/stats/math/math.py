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
from verticapy.stats.tools import *
from verticapy.core.str_sql import str_sql
from verticapy.sql._utils._format import format_magic, clean_query
from verticapy.utils._cast import to_dtype_category

#
# Global Variables

PI = str_sql("PI()")
E = str_sql("EXP(1)")
TAU = str_sql("2 * PI()")
INF = str_sql("'inf'::float")
NAN = str_sql("'nan'::float")


# Soundex


@check_minimum_version
def edit_distance(
    expr1, expr2,
):
    """
Calculates and returns the Levenshtein distance between the two strings.

Parameters
----------
expr1: object
    Expression.
expr2: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr1 = format_magic(expr1)
    expr2 = format_magic(expr2)
    return str_sql(f"EDIT_DISTANCE({expr1}, {expr2})", "int")


levenshtein = edit_distance


@check_minimum_version
def soundex(expr):
    """
Returns Soundex encoding of a varchar strings as a four -character string.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"SOUNDEX({expr})", "varchar")


@check_minimum_version
def soundex_matches(
    expr1, expr2,
):
    """
Generates and compares Soundex encodings of two strings, and returns a count 
of the matching characters (ranging from 0 for no match to 4 for an exact 
match).

Parameters
----------
expr1: object
    Expression.
expr2: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr1 = format_magic(expr1)
    expr2 = format_magic(expr2)
    return str_sql(f"SOUNDEX_MATCHES({expr1}, {expr2})", "int")


# Jaro & Jaro Winkler


@check_minimum_version
def jaro_distance(
    expr1, expr2,
):
    """
Calculates and returns the Jaro distance between two strings.

Parameters
----------
expr1: object
    Expression.
expr2: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr1 = format_magic(expr1)
    expr2 = format_magic(expr2)
    return str_sql(f"JARO_DISTANCE({expr1}, {expr2})", "float")


@check_minimum_version
def jaro_winkler_distance(
    expr1, expr2,
):
    """
Calculates and returns the Jaro-Winkler distance between two strings.

Parameters
----------
expr1: object
    Expression.
expr2: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr1 = format_magic(expr1)
    expr2 = format_magic(expr2)
    return str_sql(f"JARO_WINKLER_DISTANCE({expr1}, {expr2})", "float")


# Regular Expressions


def regexp_count(
    expr, pattern, position: int = 1,
):
    """
Returns the number times a regular expression matches a string.

Parameters
----------
expr: object
    Expression.
pattern: object
    The regular expression to search for within string.
position: int, optional
    The number of characters from the start of the string where the function 
    should start searching for matches.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    pattern = format_magic(pattern)
    return str_sql(f"REGEXP_COUNT({expr}, {pattern}, {position})", "int")


def regexp_ilike(expr, pattern):
    """
Returns true if the string contains a match for the regular expression.

Parameters
----------
expr: object
    Expression.
pattern: object
    A string containing the regular expression to match against the string.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    pattern = format_magic(pattern)
    return str_sql(f"REGEXP_ILIKE({expr}, {pattern})")


def regexp_instr(
    expr, pattern, position: int = 1, occurrence: int = 1, return_position: int = 0
):
    """
Returns the starting or ending position in a string where a regular 
expression matches.

Parameters
----------
expr: object
    Expression.
pattern: object
    The regular expression to search for within the string.
position: int, optional
    The number of characters from the start of the string where the function 
    should start searching for matches.
occurrence: int, optional
    Controls which occurrence of a pattern match in the string to return.
return_position: int, optional
    Sets the position within the string to return.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    pattern = format_magic(pattern)
    return str_sql(
        f"REGEXP_INSTR({expr}, {pattern}, {position}, {occurrence}, {return_position})"
    )


def regexp_like(expr, pattern):
    """
Returns true if the string matches the regular expression.

Parameters
----------
expr: object
    Expression.
pattern: object
    A string containing the regular expression to match against the string.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    pattern = format_magic(pattern)
    return str_sql(f"REGEXP_LIKE({expr}, {pattern})")


def regexp_replace(expr, target, replacement, position: int = 1, occurrence: int = 1):
    """
Replace all occurrences of a substring that match a regular expression 
with another substring.

Parameters
----------
expr: object
    Expression.
target: object
    The regular expression to search for within the string.
replacement: object
    The string to replace matched substrings.
position: int, optional
    The number of characters from the start of the string where the function 
    should start searching for matches.
occurrence: int, optional
    Controls which occurrence of a pattern match in the string to return.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    target = format_magic(target)
    replacement = format_magic(replacement)
    return str_sql(
        f"REGEXP_REPLACE({expr}, {target}, {replacement}, {position}, {occurrence})"
    )


def regexp_substr(expr, pattern, position: int = 1, occurrence: int = 1):
    """
Returns the substring that matches a regular expression within a string.

Parameters
----------
expr: object
    Expression.
pattern: object
    The regular expression to find a substring to extract.
position: int, optional
    The number of characters from the start of the string where the function 
    should start searching for matches.
occurrence: int, optional
    Controls which occurrence of a pattern match in the string to return.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    pattern = format_magic(pattern)
    return str_sql(f"REGEXP_SUBSTR({expr}, {pattern}, {position}, {occurrence})")


# String Functions


def length(expr):
    """
Returns the length of a string.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"LENGTH({expr})", "int")


def lower(expr):
    """
Returns a VARCHAR value containing the argument converted to 
lowercase letters. 

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"LOWER({expr})", "text")


def substr(expr, position: int, extent: int = None):
    """
Returns VARCHAR or VARBINARY value representing a substring of a specified 
string.

Parameters
----------
expr: object
    Expression.
position: int
    Starting position of the substring.
extent: int, optional
    Length of the substring to extract.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    if extent:
        position = f"{position}, {extent}"
    return str_sql(f"SUBSTR({expr}, {position})", "text")


def upper(expr):
    """
Returns a VARCHAR value containing the argument converted to uppercase 
letters. 

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"UPPER({expr})", "text")


# Aggregate & Analytical functions


def apply(func: str, *args, **kwargs):
    """
Applies any Vertica function on the input expressions.
Please check-out Vertica Documentation to see the available functions:

https://www.vertica.com/docs/10.0.x/HTML/Content/Authoring/
SQLReferenceManual/Functions/SQLFunctions.htm?tocpath=
SQL%20Reference%20Manual|SQL%20Functions|_____0

Parameters
----------
func : str
    Vertica Function. In case of geospatial, you can write the function name
    without the prefix ST_ or STV_.
args : object, optional
    Expressions.
kwargs: object, optional
    Optional Parameters Expressions.

Returns
-------
str_sql
    SQL expression.
    """
    ST_f = [
        "Area",
        "AsBinary",
        "Boundary",
        "Buffer",
        "Centroid",
        "Contains",
        "ConvexHull",
        "Crosses",
        "Difference",
        "Disjoint",
        "Distance",
        "Envelope",
        "Equals",
        "GeographyFromText",
        "GeographyFromWKB",
        "GeoHash",
        "GeometryN",
        "GeometryType",
        "GeomFromGeoHash",
        "GeomFromText",
        "GeomFromWKB",
        "Intersection",
        "Intersects",
        "IsEmpty",
        "IsSimple",
        "IsValid",
        "Length",
        "NumGeometries",
        "NumPoints",
        "Overlaps",
        "PointFromGeoHash",
        "PointN",
        "Relate",
        "SRID",
        "SymDifference",
        "Touches",
        "Transform",
        "Union",
        "Within",
        "X",
        "XMax",
        "XMin",
        "YMax",
        "YMin",
        "Y",
    ]
    STV_f = [
        "AsGeoJSON",
        "Create_Index",
        "Describe_Index",
        "Drop_Index",
        "DWithin",
        "Export2Shapefile",
        "Extent",
        "ForceLHR",
        "Geography",
        "GeographyPoint",
        "Geometry",
        "GeometryPoint",
        "GetExportShapefileDirectory",
        "Intersect",
        "IsValidReason",
        "LineStringPoint",
        "MemSize",
        "NN",
        "PolygonPoint",
        "Reverse",
        "Rename_Index",
        "Refresh_Index",
        "SetExportShapefileDirectory",
        "ShpSource",
        "ShpParser",
        "ShpCreateTable",
    ]
    ST_f_lower = [elem.lower() for elem in ST_f]
    STV_f_lower = [elem.lower() for elem in STV_f]
    if func.lower() in ST_f_lower:
        func = "ST_" + func
    elif func.lower() in STV_f_lower:
        func = "STV_" + func
    if len(args) > 0:
        expr = ", ".join([str(format_magic(elem)) for elem in args])
    else:
        expr = ""
    if len(kwargs) > 0:
        param_expr = ", ".join(
            [str((elem + " = ") + str(format_magic(kwargs[elem]))) for elem in kwargs]
        )
    else:
        param_expr = ""
    if param_expr:
        param_expr = " USING PARAMETERS " + param_expr
    func = func.upper()
    return str_sql(f"{func}({expr}{param_expr})")


def avg(expr):
    """
Computes the average (arithmetic mean) of an expression over a group of rows.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"AVG({expr})", "float")


mean = avg


def bool_and(expr):
    """
Processes Boolean values and returns a Boolean value result. If all input 
values are true, BOOL_AND returns True. Otherwise it returns False.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"BOOL_AND({expr})", "int")


def bool_or(expr):
    """
Processes Boolean values and returns a Boolean value result. If at least one 
input value is true, BOOL_OR returns True. Otherwise, it returns False.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"BOOL_OR({expr})", "int")


def bool_xor(expr):
    """
Processes Boolean values and returns a Boolean value result. If specifically 
only one input value is true, BOOL_XOR returns True. Otherwise, it returns 
False.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"BOOL_XOR({expr})", "int")


def conditional_change_event(expr):
    """
Assigns an event window number to each row, starting from 0, and increments 
by 1 when the result of evaluating the argument expression on the current 
row differs from that on the previous row.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"CONDITIONAL_CHANGE_EVENT({expr})", "int")


def conditional_true_event(expr):
    """
Assigns an event window number to each row, starting from 0, and increments 
the number by 1 when the result of the boolean argument expression evaluates 
true.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"CONDITIONAL_TRUE_EVENT({expr})", "int")


def count(expr):
    """
Returns as a BIGINT the number of rows in each group where the expression is 
not NULL.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"COUNT({expr})", "int")


def lag(expr, offset: int = 1):
    """
Returns the value of the input expression at the given offset before the 
current row within a window. 

Parameters
----------
expr: object
    Expression.
offset: int
    Indicates how great is the lag.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"LAG({expr}, {offset})")


def lead(expr, offset: int = 1):
    """
Returns values from the row after the current row within a window, letting 
you access more than one row in a table at the same time. 

Parameters
----------
expr: object
    Expression.
offset: int
    Indicates how great is the lead.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"LEAD({expr}, {offset})")


def max(expr):
    """
Returns the greatest value of an expression over a group of rows.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"MAX({expr})", "float")


def median(expr):
    """
Computes the approximate median of an expression over a group of rows.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"APPROXIMATE_MEDIAN({expr})", "float")


def min(expr):
    """
Returns the smallest value of an expression over a group of rows.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"MIN({expr})", "float")


def nth_value(expr, row_number: int):
    """
Returns the value evaluated at the row that is the nth row of the window 
(counting from 1).

Parameters
----------
expr: object
    Expression.
row_number: int
    Specifies the row to evaluate.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"NTH_VALUE({expr}, {row_number})", "int")


def quantile(expr, number: float):
    """
Computes the approximate percentile of an expression over a group of rows.

Parameters
----------
expr: object
    Expression.
number: float
    Percentile value, which must be a FLOAT constant ranging from 0 to 1 
    (inclusive).

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(
        f"APPROXIMATE_PERCENTILE({expr} USING PARAMETERS percentile = {number})",
        "float",
    )


def rank():
    """
Within each window partition, ranks all rows in the query results set 
according to the order specified by the window's ORDER BY clause.

Returns
-------
str_sql
    SQL expression.
    """
    return str_sql("RANK()", "int")


def row_number():
    """
Assigns a sequence of unique numbers, starting from 1, to each row in a 
window partition.

Returns
-------
str_sql
    SQL expression.
    """
    return str_sql("ROW_NUMBER()", "int")


def std(expr):
    """
Evaluates the statistical sample standard deviation for each member of the 
group.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"STDDEV({expr})", "float")


stddev = std


def sum(expr):
    """
Computes the sum of an expression over a group of rows.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"SUM({expr})", "float")


def var(expr):
    """
Evaluates the sample variance for each row of the group.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"VARIANCE({expr})", "float")


variance = var


# Mathematical Functions


def abs(expr):
    """
Absolute Value.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"ABS({expr})", "float")


def acos(expr):
    """
Trigonometric Inverse Cosine.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"ACOS({expr})", "float")


def asin(expr):
    """
Trigonometric Inverse Sine.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"ASIN({expr})", "float")


def atan(expr):
    """
Trigonometric Inverse Tangent.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"ATAN({expr})", "float")


def atan2(quotient, divisor):
    """
Trigonometric Inverse Tangent of the arithmetic dividend of the arguments.

Parameters
----------
quotient: object
    Expression representing the quotient.
divisor: object
    Expression representing the divisor.

Returns
-------
str_sql
    SQL expression.
    """
    quotient, divisor = format_magic(quotient), format_magic(divisor)
    return str_sql(f"ATAN2({quotient}, {divisor})", "float")


def case_when(*argv):
    """
Returns the conditional statement of the input arguments.

Parameters
----------
argv: object
    Infinite Number of Expressions.
    The expression generated will look like:
    even: CASE ... WHEN argv[2 * i] THEN argv[2 * i + 1] ... END
    odd : CASE ... WHEN argv[2 * i] THEN argv[2 * i + 1] ... ELSE argv[n] END

Returns
-------
str_sql
    SQL expression.
    """
    n = len(argv)
    if n < 2:
        raise ParameterError(
            "The number of arguments of the 'case_when' function must be strictly greater than 1."
        )
    category = to_dtype_category(argv[1])
    i = 0
    expr = "CASE"
    while i < n:
        if i + 1 == n:
            expr += " ELSE " + str(format_magic(argv[i]))
            i += 1
        else:
            expr += (
                " WHEN "
                + str(format_magic(argv[i]))
                + " THEN "
                + str(format_magic(argv[i + 1]))
            )
            i += 2
    expr += " END"
    return str_sql(expr, category)


def cbrt(expr):
    """
Cube Root.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"CBRT({expr})", "float")


def ceil(expr):
    """
Ceiling Function.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"CEIL({expr})", "float")


def coalesce(expr, *argv):
    """
Returns the value of the first non-null expression in the list.

Parameters
----------
expr: object
    Expression.
argv: object
    Infinite Number of Expressions.

Returns
-------
str_sql
    SQL expression.
    """
    category = to_dtype_category(expr)
    expr = [format_magic(expr)]
    for arg in argv:
        expr += [format_magic(arg)]
    expr = ", ".join([str(elem) for elem in expr])
    return str_sql(f"COALESCE({expr})", category)


def comb(n: int, k: int):
    """
Number of ways to choose k items from n items.

Parameters
----------
n : int
    items to choose from.
k : int
    items to choose.

Returns
-------
str_sql
    SQL expression.
    """
    return str_sql(f"({n})! / (({k})! * ({n} - {k})!)", "float")


def cos(expr):
    """
Trigonometric Cosine.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"COS({expr})", "float")


def cosh(expr):
    """
Hyperbolic Cosine.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"COSH({expr})", "float")


def cot(expr):
    """
Trigonometric Cotangent.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"COT({expr})", "float")


def date(expr):
    """
Converts the input value to a DATE data type.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"DATE({expr})", "date")


def day(expr):
    """
Returns as an integer the day of the month from the input expression. 

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"DAY({expr})", "float")


def dayofweek(expr):
    """
Returns the day of the week as an integer, where Sunday is day 1.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"DAYOFWEEK({expr})", "float")


def dayofyear(expr):
    """
Returns the day of the year as an integer, where January 1 is day 1.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"DAYOFYEAR({expr})", "float")


def decode(expr, *argv):
    """
Compares expression to each search value one by one.

Parameters
----------
expr: object
    Expression.
argv: object
    Infinite Number of Expressions.
    The expression generated will look like:
    even: CASE ... WHEN expr = argv[2 * i] THEN argv[2 * i + 1] ... END
    odd : CASE ... WHEN expr = argv[2 * i] THEN argv[2 * i + 1] ... ELSE argv[n] END

Returns
-------
str_sql
    SQL expression.
    """
    n = len(argv)
    if n < 2:
        raise ParameterError(
            "The number of arguments of the 'decode' function must be greater than 3."
        )
    category = to_dtype_category(argv[1])
    expr = (
        "DECODE("
        + str(format_magic(expr))
        + ", "
        + ", ".join([str(format_magic(elem)) for elem in argv])
        + ")"
    )
    return str_sql(expr, category)


def degrees(expr):
    """
Converts Radians to Degrees.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"DEGREES({expr})", "float")


def distance(
    lat0: float, lon0: float, lat1: float, lon1: float, radius: float = 6371.009
):
    """
Returns the distance (in kilometers) between two points.

Parameters
----------
lat0: float
    Starting point latitude.
lon0: float
    Starting point longitude.
lat1: float
    Ending point latitude.
lon1: float
    Ending point longitude.
radius: float
    Specifies the radius of the curvature of the earth at the midpoint 
    between the starting and ending points.

Returns
-------
str_sql
    SQL expression.
    """
    return str_sql(f"DISTANCE({lat0}, {lon0}, {lat1}, {lon1}, {radius})", "float")


def exp(expr):
    """
Exponential.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"EXP({expr})", "float")


def extract(expr, field: str):
    """
Extracts a sub-field such as year or hour from a date/time expression.

Parameters
----------
expr: object
    Expression.
field: str
    The field to extract. It must be one of the following: 
 		CENTURY / DAY / DECADE / DOQ / DOW / DOY / EPOCH / HOUR / ISODOW / ISOWEEK /
 		ISOYEAR / MICROSECONDS / MILLENNIUM / MILLISECONDS / MINUTE / MONTH / QUARTER / 
 		SECOND / TIME ZONE / TIMEZONE_HOUR / TIMEZONE_MINUTE / WEEK / YEAR

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"DATE_PART('{field}', {expr})", "int")


def factorial(expr):
    """
Factorial.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"({expr})!", "int")


def floor(expr):
    """
Floor Function.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"FLOOR({expr})", "int")


def gamma(expr):
    """
Gamma Function.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"({expr} - 1)!", "float")


def getdate():
    """
Returns the current statement's start date and time as a TIMESTAMP value.

Returns
-------
str_sql
    SQL expression.
    """
    return str_sql("GETDATE()", "date")


def getutcdate():
    """
Returns the current statement's start date and time at TIME ZONE 'UTC' 
as a TIMESTAMP value.

Returns
-------
str_sql
    SQL expression.
    """
    return str_sql("GETUTCDATE()", "date")


def hash(*argv):
    """
Calculates a hash value over the function arguments.

Parameters
----------
argv: object
    Infinite Number of Expressions.

Returns
-------
str_sql
    SQL expression.
    """
    expr = []
    for arg in argv:
        expr += [format_magic(arg)]
    expr = ", ".join([str(elem) for elem in expr])
    return str_sql(f"HASH({expr})", "float")


def hour(expr):
    """
Returns the hour portion of the specified date as an integer, where 0 is 
00:00 to 00:59.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"HOUR({expr})", "int")


def interval(expr):
    """
Converts the input value to a INTERVAL data type.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"({expr})::interval", "interval")


def isfinite(expr):
    """
Returns True if the expression is finite.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr, cat = format_magic(expr, True)
    return str_sql(f"(({expr}) = ({expr})) AND (ABS({expr}) < 'inf'::float)", cat)


def isinf(expr):
    """
Returns True if the expression is infinite.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"ABS({expr}) = 'inf'::float", "float")


def isnan(expr):
    """
Returns True if the expression is NaN.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr, cat = format_magic(expr, True)
    return str_sql(f"(({expr}) != ({expr}))", cat)


def lgamma(expr):
    """
Natural Logarithm of the expression Gamma.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"LN(({expr} - 1)!)", "float")


def ln(expr):
    """
Natural Logarithm.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"LN({expr})", "float")


def log(expr, base: int = 10):
    """
Logarithm.

Parameters
----------
expr: object
    Expression.
base: int
    Specifies the base.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"LOG({base}, {expr})", "float")


def minute(expr):
    """
Returns the minute portion of the specified date as an integer.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"MINUTE({expr})", "int")


def microsecond(expr):
    """
Returns the microsecond portion of the specified date as an integer.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"MICROSECOND({expr})", "int")


def month(expr):
    """
Returns the month portion of the specified date as an integer.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"MONTH({expr})", "int")


def nullifzero(expr):
    """
Evaluates to NULL if the value in the expression is 0.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr, cat = format_magic(expr, True)
    return str_sql(f"NULLIFZERO({expr})", cat)


def overlaps(start0, end0, start1, end1):
    """
Evaluates two time periods and returns true when they overlap, false 
otherwise.

Parameters
----------
start0: object
    DATE, TIME, or TIMESTAMP/TIMESTAMPTZ value that specifies the beginning 
    of a time period.
end0: object
    DATE, TIME, or TIMESTAMP/TIMESTAMPTZ value that specifies the end of a 
    time period.
start1: object
    DATE, TIME, or TIMESTAMP/TIMESTAMPTZ value that specifies the beginning 
    of a time period.
end1: object
    DATE, TIME, or TIMESTAMP/TIMESTAMPTZ value that specifies the end of a 
    time period.

Returns
-------
str_sql
    SQL expression.
    """
    expr = f"""
        ({format_magic(start0)},
         {format_magic(end0)})
         OVERLAPS
        ({format_magic(start1)},
         {format_magic(end1)})"""
    return str_sql(clean_query(expr), "int")


def quarter(expr):
    """
Returns calendar quarter of the specified date as an integer, where the 
January-March quarter is 1.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"QUARTER({expr})", "int")


def radians(expr):
    """
Converts Degrees to Radians.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"RADIANS({expr})", "float")


def random():
    """
Returns a Random Number.

Returns
-------
str_sql
    SQL expression.
    """
    return str_sql("RANDOM()", "float")


def randomint(n: int):
    """
Returns a Random Number from 0 through n – 1.

Parameters
----------
n: int
    Integer Value.

Returns
-------
str_sql
    SQL expression.
    """
    return str_sql(f"RANDOMINT({n})", "int")


def round(expr, places: int = 0):
    """
Rounds the expression.

Parameters
----------
expr: object
    Expression.
places: int
    Number used to round the expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"ROUND({expr}, {places})", "float")


def round_date(expr, precision: str = "DD"):
    """
Rounds the specified date or time.

Parameters
----------
expr: object
    Expression.
precision: str, optional
    A string constant that specifies precision for the rounded value, 
    one of the following:
	    Century: CC | SCC
	    Year: SYYY | YYYY | YEAR | YYY | YY | Y
	    ISO Year: IYYY | IYY | IY | I
	    Quarter: Q
	    Month: MONTH | MON | MM | RM
	    Same weekday as first day of year: WW
	    Same weekday as first day of ISO year: IW
	    Same weekday as first day of month: W
	    Day (default): DDD | DD | J
	    First weekday: DAY | DY | D
	    Hour: HH | HH12 | HH24
	    Minute: MI
	    Second: SS

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"ROUND({expr}, '{precision}')", "date")


def second(expr):
    """
Returns the seconds portion of the specified date as an integer.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"SECOND({expr})", "int")


def seeded_random(random_state: int):
    """
Returns a Seeded Random Number using the input random state.

Parameters
----------
random_state: int
    Integer used to seed the randomness.

Returns
-------
str_sql
    SQL expression.
    """
    return str_sql(f"SEEDED_RANDOM({random_state})", "float")


def sign(expr):
    """
Sign of the expression.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"SIGN({expr})", "int")


def sin(expr):
    """
Trigonometric Sine.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"SIN({expr})", "float")


def sinh(expr):
    """
Hyperbolic Sine.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"SINH({expr})", "float")


def sqrt(expr):
    """
Arithmetic Square Root.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"SQRT({expr})", "float")


def tan(expr):
    """
Trigonometric Tangent.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"TAN({expr})", "float")


def tanh(expr):
    """
Hyperbolic Tangent.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"TANH({expr})", "float")


def timestamp(expr):
    """
Converts the input value to a TIMESTAMP data type.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"({expr})::timestamp", "date")


def trunc(expr, places: int = 0):
    """
Truncates the expression.

Parameters
----------
expr: object
    Expression.
places: int
    Number used to truncate the expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"TRUNC({expr}, {places})", "float")


def week(expr):
    """
Returns the week of the year for the specified date as an integer, where the 
first week begins on the first Sunday on or preceding January 1.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"WEEK({expr})", "int")


def year(expr):
    """
Returns an integer that represents the year portion of the specified date.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr = format_magic(expr)
    return str_sql(f"YEAR({expr})", "int")


def zeroifnull(expr):
    """
Evaluates to 0 if the expression is NULL.

Parameters
----------
expr: object
    Expression.

Returns
-------
str_sql
    SQL expression.
    """
    expr, cat = format_magic(expr, True)
    return str_sql(f"ZEROIFNULL({expr})", cat)