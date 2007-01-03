# Copyright (C) 2006 Jelmer Vernooij <jelmer@samba.org>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from bzrlib.bzrdir import BzrDir
from bzrlib.errors import NoSuchRevision
from bzrlib.inventory import Inventory, ROOT_ID
from bzrlib.repository import Repository
from bzrlib.trace import mutter
from bzrlib.tests import TestSkipped, TestCase

import sha

import format
from fileids import SimpleFileIdMap, generate_file_id, generate_svn_file_id
from repository import MAPPING_VERSION
from scheme import TrunkBranchingScheme
from tests import TestCaseWithSubversionRepository, RENAMES

class TestComplexFileids(TestCaseWithSubversionRepository):
    # branchtagcopy.dump
    # changeaftercp.dump
    # combinedbranch.dump
    # executable.dump
    # ignore.dump
    # inheritance.dump
    # movebranch.dump
    # movefileorder.dump
    # recreatebranch.dump
    def test_simplemove(self):
        repos_url = self.make_client('d', 'dc')
        self.build_tree({'dc/foo': "data", "dc/blie": "bloe"})
        self.client_add("dc/foo")
        self.client_commit("dc", "My Message")
        self.client_copy("dc/foo", "dc/bar")
        self.client_delete("dc/foo")
        self.build_tree({'dc/bar': "data2"})
        self.client_commit("dc", "Second Message")

        repository = Repository.open("svn+"+repos_url)

        inv1 = repository.get_inventory(
                "svn-v%d:1@%s-" % (MAPPING_VERSION, repository.uuid))
        inv2 = repository.get_inventory(
                "svn-v%d:2@%s-" % (MAPPING_VERSION, repository.uuid))
        mutter('inv1: %r' % inv1.entries())
        mutter('inv2: %r' % inv2.entries())
        if RENAMES:
            self.assertEqual(inv1.path2id("foo"), inv2.path2id("bar"))
        self.assertNotEqual(None, inv1.path2id("foo"))
        self.assertIs(None, inv2.path2id("foo"))
        self.assertNotEqual(None, inv2.path2id("bar"))
        self.assertNotEqual(inv1.path2id("foo"), inv2.path2id("blie"))
        self.assertNotEqual(inv2.path2id("bar"), inv2.path2id("blie"))

    def test_simplecopy(self):
        repos_url = self.make_client('d', 'dc')
        self.build_tree({'dc/foo': "data", "dc/blie": "bloe"})
        self.client_add("dc/foo")
        self.client_add("dc/blie")
        self.client_commit("dc", "My Message")
        self.client_copy("dc/foo", "dc/bar")
        self.build_tree({'dc/bar': "data2"})
        self.client_commit("dc", "Second Message")

        bzrdir = BzrDir.open("svn+%s" % repos_url)
        repository = bzrdir.find_repository()

        inv1 = repository.get_inventory(
                "svn-v%d:1@%s-" % (MAPPING_VERSION, repository.uuid))
        inv2 = repository.get_inventory(
                "svn-v%d:2@%s-" % (MAPPING_VERSION, repository.uuid))
        self.assertNotEqual(inv1.path2id("foo"), inv2.path2id("bar"))
        self.assertNotEqual(inv1.path2id("foo"), inv2.path2id("blie"))
        self.assertIs(None, inv1.path2id("bar"))
        self.assertNotEqual(None, inv1.path2id("blie"))

    def test_simpledelete(self):
        repos_url = self.make_client('d', 'dc')
        self.build_tree({'dc/foo': "data"})
        self.client_add("dc/foo")
        self.client_commit("dc", "My Message")
        self.client_delete("dc/foo")
        self.client_commit("dc", "Second Message")

        bzrdir = BzrDir.open("svn+%s" % repos_url)
        repository = bzrdir.find_repository()

        inv1 = repository.get_inventory(
                "svn-v%d:1@%s-" % (MAPPING_VERSION, repository.uuid))
        inv2 = repository.get_inventory(
                "svn-v%d:2@%s-" % (MAPPING_VERSION, repository.uuid))
        self.assertNotEqual(None, inv1.path2id("foo"))
        self.assertIs(None, inv2.path2id("foo"))

    def test_replace(self):
        repos_url = self.make_client('d', 'dc')
        self.build_tree({'dc/foo': "data"})
        self.client_add("dc/foo")
        self.client_commit("dc", "My Message")
        self.client_delete("dc/foo")
        self.build_tree({'dc/foo': "data"})
        self.client_add("dc/foo")
        self.client_commit("dc", "Second Message")

        bzrdir = BzrDir.open("svn+"+repos_url)
        repository = bzrdir.find_repository()

        inv1 = repository.get_inventory(
                "svn-v%d:1@%s-" % (MAPPING_VERSION, repository.uuid))
        inv2 = repository.get_inventory(
                "svn-v%d:2@%s-" % (MAPPING_VERSION, repository.uuid))
        self.assertNotEqual(inv1.path2id("foo"), inv2.path2id("foo"))

    def test_copy_branch(self):
        repos_url = self.make_client('d', 'dc')
        self.build_tree({'dc/trunk/dir/file': "data", 'dc/branches': None})
        self.client_add("dc/trunk")
        self.client_add("dc/branches")
        self.client_commit("dc", "My Message")
        self.client_copy("dc/trunk", "dc/branches/mybranch")
        self.client_commit("dc", "Copy branch")

        bzrdir = BzrDir.open("svn+"+repos_url + "/branches/mybranch")
        repository = bzrdir.find_repository()

        inv1 = repository.get_inventory(
                "svn-v%d:1@%s-trunk" % (MAPPING_VERSION, repository.uuid))
        inv2 = repository.get_inventory(
                "svn-v%d:2@%s-branches%%2fmybranch" % (MAPPING_VERSION, repository.uuid))
        self.assertEqual(inv1.path2id("dir"), inv2.path2id("dir"))
        self.assertEqual(inv1.path2id("dir/file"), inv2.path2id("dir/file"))

        fileid, revid = repository.path_to_file_id(2, 
                            "branches/mybranch/dir/file")
        self.assertEqual(fileid, inv1.path2id("dir/file"))
        self.assertEqual(
                "svn-v%d:1@%s-trunk" % (MAPPING_VERSION, repository.uuid), 
                revid)

def sha1(str):
    return sha.new(str).hexdigest()

class TestFileIdGenerator(TestCase):
    def test_generate_file_id_root(self):
        self.assertEqual(ROOT_ID, generate_file_id("svn-v2:2@uuid-bp", ""))

    def test_generate_file_id_path(self):
        self.assertEqual("svn-v2:2@uuid-bp-mypath", 
                         generate_file_id("svn-v2:2@uuid-bp", "mypath"))

    def test_generate_file_id_long(self):
        dir = "this/is/a" + ("/very"*40) + "/long/path/"
        self.assertEqual("svn-v2:2@uuid-bp-" + sha1(dir) + "-filename", 
                         generate_file_id("svn-v2:2@uuid-bp", dir+"filename"))

    def test_generate_file_id_special_char(self):
        self.assertEqual(u"svn-v2:2@uuid-bp-mypath\x2c", 
                         generate_file_id("svn-v2:2@uuid-bp", u"mypath\x2c"))

class TestFileMapping(TestCase):
    def apply_mappings(self, mappings, find_children=None, renames={}):
        map = {}
        revids = mappings.keys()
        revids.sort()
        for r in revids:
             def new_file_id(x):
                 if renames.has_key(r) and renames[r].has_key(x):
                     return renames[r][x]
                 return generate_file_id(r, x)
             revmap = SimpleFileIdMap._apply_changes(new_file_id, mappings[r], find_children)
             map.update(dict([(x,(revmap[x],r)) for x in revmap]))
        return map

    def test_simple(self):
        map = self.apply_mappings({"svn-v%d:1@uuid-" % MAPPING_VERSION: {"foo": ('A', None, None)}})
        self.assertEqual({ 'foo': ("svn-v%d:1@uuid--foo" % MAPPING_VERSION, 
                                       "svn-v%d:1@uuid-" % MAPPING_VERSION)
                         }, map)

    def test_simple_add(self):
        map = self.apply_mappings({"svn-v%d:1@uuid-" % MAPPING_VERSION: {"": ('A', None, None), "foo": ('A', None, None)}})
        self.assertEqual({'': ('TREE_ROOT', "svn-v%d:1@uuid-" % MAPPING_VERSION), 
                               'foo': ("svn-v%d:1@uuid--foo" % MAPPING_VERSION, 
                                       "svn-v%d:1@uuid-" % MAPPING_VERSION)
                         }, map)

    def test_copy(self):
        def find_children(path, revid):
            if path == "foo":
                yield "foo/blie"
                yield "foo/bla"
        map = self.apply_mappings(
                {"svn-v%d:1@uuid-" % MAPPING_VERSION: {
                                   "foo": ('A', None, None), 
                                   "foo/blie": ('A', None, None),
                                   "foo/bla": ('A', None, None)},
                "svn-v%d:2@uuid-" % MAPPING_VERSION: {
                                   "foob": ('A', 'foo', 1), 
                                   "foob/bla": ('M', None, None)}
                }, find_children)
        self.assertTrue(map.has_key("foob/bla"))
        self.assertTrue(map.has_key("foob/blie"))

    def test_touchparent(self):
        map = self.apply_mappings(
                {("svn-v%d:1@uuid-" % MAPPING_VERSION): {
                                   "foo": ('A', None, None), 
                                   "foo/bla": ('A', None, None)},
                 ("svn-v%d:2@uuid-" % MAPPING_VERSION): {
                                   "foo/bla": ('M', None, None)}
                })
        self.assertEqual("svn-v%d:1@uuid-" % MAPPING_VERSION, map["foo"][1])
        self.assertEqual("svn-v%d:1@uuid-" % MAPPING_VERSION, map["foo/bla"][1])

    def test_usemap(self):
        map = self.apply_mappings(
                {("svn-v%d:1@uuid-" % MAPPING_VERSION): {
                                   "foo": ('A', None, None), 
                                   "foo/bla": ('A', None, None)},
                 ("svn-v%d:2@uuid-" % MAPPING_VERSION): {
                                   "foo/bla": ('M', None, None)}
                 }, 
                renames={("svn-v%d:1@uuid-" % MAPPING_VERSION): {"foo": "myid"}})
        self.assertEqual("myid", map["foo"][0])

    def test_usemap_later(self):
        map = self.apply_mappings(
                {("svn-v%d:1@uuid-" % MAPPING_VERSION): {
                                   "foo": ('A', None, None), 
                                   "foo/bla": ('A', None, None)},
                 ("svn-v%d:2@uuid-" % MAPPING_VERSION): {
                                   "foo/bla": ('M', None, None)}
                 }, 
                renames={("svn-v%d:2@uuid-" % MAPPING_VERSION): {"foo": "myid"}})
        self.assertEqual("svn-v%d:1@uuid--foo" % MAPPING_VERSION, map["foo"][0])
        self.assertEqual("svn-v%d:1@uuid-" % MAPPING_VERSION, map["foo"][1])

class GetMapTests(TestCaseWithSubversionRepository):
    def setUp(self):
        super(GetMapTests, self).setUp()
        self.repos_url = self.make_client("d", "dc")
        self.repos = Repository.open(self.repos_url)

    def test_empty(self):
        self.assertEqual({"": (ROOT_ID, None)}, 
                         self.repos.get_fileid_map(0, ""))

    def test_empty_trunk(self):
        self.repos.set_branching_scheme(TrunkBranchingScheme())
        self.build_tree({"dc/trunk": None})
        self.client_add("dc/trunk")
        self.client_commit("dc", "Msg")
        self.assertEqual({"": (ROOT_ID, "svn-v%d:1@%s-trunk" % (MAPPING_VERSION, 
                               self.repos.uuid))}, self.repos.get_fileid_map(1, "trunk"))

    def test_change_parent(self):
        self.repos.set_branching_scheme(TrunkBranchingScheme())
        self.build_tree({"dc/trunk": None})
        self.client_add("dc/trunk")
        self.client_commit("dc", "Msg")
        self.build_tree({"dc/trunk/file": 'data'})
        self.client_add("dc/trunk/file")
        self.client_commit("dc", "Msg")
        self.assertEqual({"": (ROOT_ID, "svn-v%d:2@%s-trunk" % (MAPPING_VERSION, self.repos.uuid)), "file": (generate_svn_file_id(self.repos.uuid, 2, "trunk", "file"), "svn-v%d:2@%s-trunk" % (MAPPING_VERSION, self.repos.uuid))}, self.repos.get_fileid_map(2, "trunk"))

    def test_change_updates(self):
        self.repos.set_branching_scheme(TrunkBranchingScheme())
        self.build_tree({"dc/trunk": None})
        self.client_add("dc/trunk")
        self.client_commit("dc", "Msg")
        self.build_tree({"dc/trunk/file": 'data'})
        self.client_add("dc/trunk/file")
        self.client_commit("dc", "Msg")
        self.build_tree({"dc/trunk/file": 'otherdata'})
        self.client_commit("dc", "Msg")
        self.assertEqual({"": (ROOT_ID, "svn-v%d:3@%s-trunk" % (MAPPING_VERSION, self.repos.uuid)), "file": (generate_svn_file_id(self.repos.uuid, 2, "trunk", "file"), "svn-v%d:3@%s-trunk" % (MAPPING_VERSION, self.repos.uuid))}, self.repos.get_fileid_map(3, "trunk"))

    def test_sibling_unrelated(self):
        self.repos.set_branching_scheme(TrunkBranchingScheme())
        self.build_tree({"dc/trunk": None})
        self.client_add("dc/trunk")
        self.client_commit("dc", "Msg")
        self.build_tree({"dc/trunk/file": 'data', 'dc/trunk/bar': 'data2'})
        self.client_add("dc/trunk/file")
        self.client_add("dc/trunk/bar")
        self.client_commit("dc", "Msg")
        self.build_tree({"dc/trunk/file": 'otherdata'})
        self.client_commit("dc", "Msg")
        self.assertEqual({"": (ROOT_ID, "svn-v%d:3@%s-trunk" % (MAPPING_VERSION, self.repos.uuid)), "bar": (generate_svn_file_id(self.repos.uuid, 2, "trunk", "bar"), "svn-v%d:2@%s-trunk" % (MAPPING_VERSION, self.repos.uuid)), "file": (generate_svn_file_id(self.repos.uuid, 2, "trunk", "file"), "svn-v%d:3@%s-trunk" % (MAPPING_VERSION, self.repos.uuid))}, self.repos.get_fileid_map(3, "trunk"))

    def test_copy(self):
        self.repos.set_branching_scheme(TrunkBranchingScheme())
        self.build_tree({"dc/trunk": None})
        self.client_add("dc/trunk")
        self.client_commit("dc", "Msg")
        self.build_tree({"dc/trunk/file": 'data'})
        self.client_add("dc/trunk/file")
        self.client_commit("dc", "Msg")
        self.client_copy("dc/trunk/file", "dc/trunk/bar")
        self.client_commit("dc", "Msg")
        self.assertEqual({"": (ROOT_ID, "svn-v%d:3@%s-trunk" % (MAPPING_VERSION, self.repos.uuid)), "bar": (generate_svn_file_id(self.repos.uuid, 3, "trunk", "bar"), "svn-v%d:3@%s-trunk" % (MAPPING_VERSION, self.repos.uuid)), "file": (generate_svn_file_id(self.repos.uuid, 2, "trunk", "file"), "svn-v%d:2@%s-trunk" % (MAPPING_VERSION, self.repos.uuid))}, self.repos.get_fileid_map(3, "trunk"))

    def test_copy_nested_modified(self):
        self.repos.set_branching_scheme(TrunkBranchingScheme())
        self.build_tree({"dc/trunk": None})
        self.client_add("dc/trunk")
        self.client_commit("dc", "Msg")
        self.build_tree({"dc/trunk/dir/file": 'data'})
        self.client_add("dc/trunk/dir")
        self.client_commit("dc", "Msg")
        self.client_copy("dc/trunk/dir", "dc/trunk/bar")
        self.build_tree({"dc/trunk/bar/file": "data2"})
        self.client_commit("dc", "Msg")
        self.assertEqual({
          "": (ROOT_ID, 
            "svn-v%d:3@%s-trunk" % (MAPPING_VERSION, self.repos.uuid)), 
          "dir": (generate_svn_file_id(self.repos.uuid, 2, "trunk", "dir"), 
               "svn-v%d:2@%s-trunk" % (MAPPING_VERSION, self.repos.uuid)), 
          "dir/file": (generate_svn_file_id(self.repos.uuid, 2, "trunk", "dir/file"), 
            "svn-v%d:2@%s-trunk" % (MAPPING_VERSION, self.repos.uuid)), 
          "bar": (generate_svn_file_id(self.repos.uuid, 3, "trunk", "bar"), 
               "svn-v%d:3@%s-trunk" % (MAPPING_VERSION, self.repos.uuid)), 
          "bar/file": (generate_svn_file_id(self.repos.uuid, 3, "trunk", "bar/file"), 
               "svn-v%d:3@%s-trunk" % (MAPPING_VERSION, self.repos.uuid))}, 
            self.repos.get_fileid_map(3, "trunk"))
