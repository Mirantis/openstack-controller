#    Copyright 2020 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from openstack_controller import utils


def test_divide_into_groups_of():
    assert [["a", "b", "c"]] == utils.divide_into_groups_of(3, ["a", "b", "c"])
    assert [["a", "b"], ["c", "d"], ["e"]] == utils.divide_into_groups_of(
        2, ["a", "b", "c", "d", "e"]
    )
    assert [] == utils.divide_into_groups_of(2, [])
    assert [["a"]] == utils.divide_into_groups_of(5, ["a"])


def test_cron_validator():
    samples = [
        ["* * * * *", True],
        ["* 9* * * *", False],
        ["00 * * * *", True],
        ["59 * * * *", True],
        ["62 * * * *", False],
        ["* 00 * * *", True],
        ["* 23 * * *", True],
        ["* 30 * * *", False],
        ["* * 00 * *", False],
        ["* * 01 * *", True],
        ["* * 31 * *", True],
        ["* * 33 * *", False],
        ["* * * 00 *", False],
        ["* * * 01 *", True],
        ["* * * 12 *", True],
        ["* * * 15 *", False],
        ["* * * juN *", True],
        ["* * * ser * ", False],
        ["* * * * 00", True],
        ["* * * * 07", True],
        ["* * * * 09", False],
        ["* * * * mon", True],
        ["* * * * vos", False],
        ["*/5 * * * *", True],
        ["* */3/5 * * *", False],
        ["*/1-5 * * * *", False],
        ["1/5 * * * *", False],
        ["1-40/5 * * * *", True],
        ["1-4/* * * * *", False],
        ["1,3,6 * * * *", True],
        ["* * * 1,5,jan,7 *", False],
        ["40-5 * * * *", False],
        ["0-62 * * * *", False],
        ["5-12 * * * *", True],
        ["1-1 * * * *", True],
        ["* * * 02-07,9 *", True],
        ["* * * * 0-5-6", False],
        ["* * * * 1,7,6", True],
        ["*/5 1,18 * 2-4 7", True],
        ["* */3 * * Mon ", True],
        ["02 06 05 01 01", True],
        ["22 06 15 17 *", False],
        ["1-20/3 * * Jan *", True],
        ["* * * Jan,may *", False],
        ["* * * mar-sep *", False],
        ["15- 0 0 0 0", False],
        ["/ 0 0 0 0", False],
        ["1-3 * * */jan *", False],
        ["@weekly", True],
        ["@yearly", True],
        ["* */20,7,*/12 * * *", True],
        ["* * * 1-14 *", False],
        ["* * * ", False],
        ["* * * * * *", False],
    ]
    for schedule, res in samples:
        assert utils.CronValidator(schedule).validate() == res
