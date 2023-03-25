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
from typing import Optional

from vertica_highcharts import Highchart, Highstock

from verticapy._typing import HChart
from verticapy.plotting.base import PlottingBase


class HighchartsBase(PlottingBase):
    def _get_chart(
        self,
        chart: Optional[HChart] = None,
        width: int = 600,
        height: int = 400,
        stock: bool = False,
    ) -> HChart:
        if chart != None:
            return chart
        elif stock or ("stock" in self.layout and self.layout["stock"]):
            return Highstock(width=width, height=height)
        else:
            return Highchart(width=width, height=height)
